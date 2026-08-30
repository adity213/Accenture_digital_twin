"""
DigitalTwin.ai - Predictive Risk Scoring Model
Predicts P(bottleneck within next 15 minutes) and P(defect).
Implements a robust Gradient Boosted Decision Tree (GBDT) ensemble.
Uses scikit-learn for high performance and reliability.
"""
import math
import random
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
import numpy as np

# Single source of truth for the feature vector's name/order.
FEATURE_NAMES = [
    "processing_time_ratio",
    "buffer_utilization",
    "degradation_momentum",
    "spc_z_score",
    "avg_upstream_starvation_risk",
    "max_upstream_starvation_risk",
    "sensor_confidence",
    "shift_tick_sin",
    "shift_tick_cos",
    "is_manual_sensor",
    "zone_code",
    "station_type_code",
    "rolling_mean_ct_ratio",
    "rolling_std_ct_ratio",
    "buffer_utilization_delta",
    "ticks_since_spc_flag",
    "machine_shaking_vibration",
    "motor_heat_temperature",
    "active_power_draw_kw",
]

ZONE_MAP = {"body": 0.0, "paint": 1.0, "assembly": 2.0}

STATION_TYPE_MAP = {
    "subassembly": 0.0, "roboticweld": 1.0, "laserbrazing": 2.0, "mainframing": 3.0, "respotweld": 4.0,
    "dispensing": 5.0, "fitting": 6.0, "qualityscan": 7.0, "manualfinishing": 8.0, "transferbuffer": 9.0,
    "chemicalbath": 10.0, "electrodeposition": 11.0, "thermaloven": 12.0, "manualsealing": 13.0, "roboticspray": 14.0,
    "visionqc": 15.0, "manualwiring": 16.0, "modulemarriage": 17.0, "mechanicaltorque": 18.0, "automatedmarriage": 19.0,
    "robotictorque": 20.0, "roboticurethane": 21.0, "manualtrim": 22.0, "safetycalibration": 23.0, "automatedtorque": 24.0,
    "fluidfill": 25.0, "manualfitting": 26.0, "electronicflash": 27.0, "dynamictest": 28.0, "finalinspection": 29.0
}


def _make_deque():
    return deque(maxlen=15)

def _make_neg_tick():
    return -100


class RiskScoringModel:
    def __init__(self):
        # Categorical features at index 10 (zone_code) and 11 (station_type_code)
        self.bottleneck_model = HistGradientBoostingClassifier(
            max_iter=40, learning_rate=0.08, max_depth=4, categorical_features=[10, 11], random_state=42
        )
        self.defect_model = HistGradientBoostingClassifier(
            max_iter=30, learning_rate=0.08, max_depth=4, categorical_features=[10, 11], random_state=42
        )
        self.is_trained = False
        self.history_buffers: Dict[str, deque] = defaultdict(_make_deque)
        self.last_spc_flag_tick: Dict[str, int] = defaultdict(_make_neg_tick)

    def reset_history(self):
        """Clears rolling temporal buffers (useful between independent simulated days)."""
        self.history_buffers.clear()
        self.last_spc_flag_tick.clear()

    def extract_features(
        self,
        station_id: str,
        telemetry: Dict[str, Any],
        spc_result: Dict[str, Any],
        sensor_confidence: float,
        upstream_risks: List[float],
        target_cycle_time_s: float,
        buffer_capacity: int,
        shift_tick: int,
        zone: str = "Body",
        station_type: str = "RoboticWeld"
    ) -> List[float]:
        # Feature Extraction - STRICTLY NO GROUND TRUTH LABELS (ZERO DATA LEAKAGE)
        actual_processing_time = telemetry.get("cycle_time_s") or target_cycle_time_s
        waiting_line_count = telemetry.get("buffer_level") if telemetry.get("buffer_level") is not None else int(buffer_capacity * 0.5)

        processing_time_ratio = actual_processing_time / max(1.0, target_cycle_time_s)
        buffer_utilization = waiting_line_count / max(1.0, buffer_capacity)

        trend_map = {"STABLE": 0.0, "DRIFT_UP": 1.0, "DRIFT_DOWN": -1.0}
        degradation_momentum = trend_map.get(spc_result.get("trend", "STABLE"), 0.0)
        spc_z_score = float(spc_result.get("z_score", 0.0))

        avg_upstream_starvation_risk = sum(upstream_risks) / len(upstream_risks) if upstream_risks else 0.0
        max_upstream_starvation_risk = max(upstream_risks) if upstream_risks else 0.0

        # Sinusoidal / Cosine diurnal circadian phase encoding (1440-tick 3-shift day)
        phase = 2.0 * math.pi * ((shift_tick % 1440) / 1440.0)
        shift_tick_sin = math.sin(phase)
        shift_tick_cos = math.cos(phase)

        is_manual_sensor = 1.0 if telemetry.get("sensor_tier") == "manual" else 0.0

        # Zone & Station Type Categorical Encodings
        z_str = str(telemetry.get("zone") or zone).lower()
        st_str = str(telemetry.get("station_type") or telemetry.get("type") or station_type).lower()
        zone_code = ZONE_MAP.get(z_str, 0.0)
        station_type_code = STATION_TYPE_MAP.get(st_str, 0.0)

        # Temporal Rolling Window Calculations
        buf = self.history_buffers[station_id]
        buf.append((processing_time_ratio, buffer_utilization))

        ct_ratios = [item[0] for item in buf]
        rolling_mean_ct_ratio = float(np.mean(ct_ratios)) if ct_ratios else processing_time_ratio
        rolling_std_ct_ratio = float(np.std(ct_ratios)) if len(ct_ratios) > 1 else 0.0

        # Rate of change of buffer utilization (current vs 5 ticks ago)
        if len(buf) >= 6:
            buffer_utilization_delta = buffer_utilization - buf[-6][1]
        else:
            buffer_utilization_delta = 0.0

        # Ticks since last SPC deviation flag
        if spc_result.get("ewma_drift_flag", False) or abs(spc_z_score) > 3.0:
            self.last_spc_flag_tick[station_id] = shift_tick

        ticks_since_spc_flag = min(50.0, float(max(0, shift_tick - self.last_spc_flag_tick[station_id])))

        machine_shaking_vibration = telemetry.get("vibration") or 0.8
        motor_heat_temperature = telemetry.get("temperature") or 24.0
        active_power_draw_kw = telemetry.get("power_kw") or 20.0

        return [
            round(processing_time_ratio, 3),
            round(buffer_utilization, 3),
            round(degradation_momentum, 1),
            round(spc_z_score, 3),
            round(avg_upstream_starvation_risk, 3),
            round(max_upstream_starvation_risk, 3),
            round(sensor_confidence, 3),
            round(shift_tick_sin, 3),
            round(shift_tick_cos, 3),
            is_manual_sensor,
            zone_code,
            station_type_code,
            round(rolling_mean_ct_ratio, 3),
            round(rolling_std_ct_ratio, 3),
            round(buffer_utilization_delta, 3),
            round(ticks_since_spc_flag, 1),
            round(machine_shaking_vibration, 3),
            round(motor_heat_temperature, 2),
            round(active_power_draw_kw, 2)
        ]

    def train_on_history(
        self,
        features_list: List[List[float]],
        bottleneck_labels: List[int],
        defect_labels: List[int],
        train_idx: Optional[List[int]] = None,
        test_idx: Optional[List[int]] = None,
        decision_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Trains both models with class-imbalance-aware sample weighting (bottlenecks and
        defects are rare events -- see REFERENCES.md base rates -- so unweighted fitting
        would let the model minimize loss by mostly predicting the majority "NORMAL" class).
        """
        n = len(features_list)
        if train_idx is None or test_idx is None:
            split_idx = int(n * 0.70)
            train_idx = list(range(split_idx))
            test_idx = list(range(split_idx, n))

        X_train_arr = np.asarray([features_list[i] for i in train_idx], dtype=np.float32)
        X_test_arr = np.asarray([features_list[i] for i in test_idx], dtype=np.float32)
        y_bn_train = [bottleneck_labels[i] for i in train_idx]
        y_bn_test = [bottleneck_labels[i] for i in test_idx]
        y_def_train = [defect_labels[i] for i in train_idx]
        y_def_test = [defect_labels[i] for i in test_idx]

        bn_weights = self._balanced_sample_weights(y_bn_train)
        def_weights = self._balanced_sample_weights(y_def_train)

        self.bottleneck_model.fit(X_train_arr, y_bn_train, sample_weight=bn_weights)
        self.defect_model.fit(X_train_arr, y_def_train, sample_weight=def_weights)
        self.is_trained = True

        bn_metrics = self._evaluate(self.bottleneck_model, X_test_arr, y_bn_test, decision_threshold)
        def_metrics = self._evaluate(self.defect_model, X_test_arr, y_def_test, decision_threshold)

        return {
            "train_samples": len(X_train_arr),
            "test_samples": len(X_test_arr),
            "bottleneck_positive_rate_train": round(sum(y_bn_train) / max(1, len(y_bn_train)), 4),
            "bottleneck_positive_rate_test": round(sum(y_bn_test) / max(1, len(y_bn_test)), 4),
            "bottleneck_auc": bn_metrics["auc"],
            "bottleneck_pr_auc": bn_metrics["pr_auc"],
            "bottleneck_precision": bn_metrics["precision"],
            "bottleneck_recall": bn_metrics["recall"],
            "defect_positive_rate_train": round(sum(y_def_train) / max(1, len(y_def_train)), 4),
            "defect_positive_rate_test": round(sum(y_def_test) / max(1, len(y_def_test)), 4),
            "defect_auc": def_metrics["auc"],
            "defect_pr_auc": def_metrics["pr_auc"],
            "defect_precision": def_metrics["precision"],
            "defect_recall": def_metrics["recall"],
        }

    @staticmethod
    def _balanced_sample_weights(labels: List[int]) -> List[float]:
        n = len(labels)
        n_pos = sum(labels)
        n_neg = n - n_pos
        if n_pos == 0 or n_neg == 0:
            return [1.0] * n
        w_pos = n / (2.0 * n_pos)
        w_neg = n / (2.0 * n_neg)
        return [w_pos if y == 1 else w_neg for y in labels]

    @staticmethod
    def _evaluate(model, X_test, y_test: List[int], threshold: float) -> Dict[str, float]:
        X_arr = np.asarray(X_test, dtype=np.float32)
        if len(X_arr) == 0:
            return {"auc": 0.5, "pr_auc": 0.0, "precision": 0.0, "recall": 0.0}

        probs = model.predict_proba(X_arr)[:, 1]
        preds = [1 if p >= threshold else 0 for p in probs]

        y_arr = np.asarray(y_test, dtype=np.int32)
        if len(np.unique(y_arr)) > 1:
            auc = float(roc_auc_score(y_arr, probs))
            pr_auc = float(average_precision_score(y_arr, probs))
        else:
            auc = 0.5
            pr_auc = 0.0

        tp_c = sum(1 for i in range(len(X_arr)) if preds[i] == 1 and y_test[i] == 1)
        fp_c = sum(1 for i in range(len(X_arr)) if preds[i] == 1 and y_test[i] == 0)
        fn_c = sum(1 for i in range(len(X_arr)) if preds[i] == 0 and y_test[i] == 1)
        tn_c = sum(1 for i in range(len(X_arr)) if preds[i] == 0 and y_test[i] == 0)

        precision = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
        recall = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
        f1 = (2.0 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        n_neg = fp_c + tn_c
        false_alarm_rate = fp_c / n_neg if n_neg > 0 else 0.0
        brier = float(np.mean([(probs[i] - y_test[i]) ** 2 for i in range(len(X_arr))])) if len(X_arr) > 0 else 0.0

        return {
            "auc": round(auc, 3),
            "pr_auc": round(pr_auc, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "brier_score": round(brier, 4),
            "false_alarm_rate": round(false_alarm_rate, 4),
        }

    def compute_baseline_risk(self, features: List[float]) -> Tuple[float, float, float]:
        """
        Computes deterministic, physics-grounded baseline risk probabilities (Phase 25).
        Returns: (baseline_bottleneck_risk, baseline_defect_risk, baseline_composite_risk)
        """
        processing_time_ratio = features[0]
        buffer_utilization = features[1]
        degradation_momentum = features[2]
        spc_z_score = features[3]
        max_upstream_risk = features[5]
        machine_shaking_vibration = features[16]
        motor_heat_temperature = features[17]

        # Bottleneck Baseline Physics
        bn_risk = 0.05
        if processing_time_ratio > 1.30:
            bn_risk = 0.75 + min(0.24, (processing_time_ratio - 1.30) * 0.5)
        elif processing_time_ratio > 1.15 or degradation_momentum > 0:
            bn_risk = 0.55
        elif buffer_utilization < 0.20 and max_upstream_risk > 0.6:
            bn_risk = 0.65
        elif abs(spc_z_score) > 3.0:
            bn_risk = 0.60

        # Defect Baseline Physics (ISO 10816 Zone C/D limits + Oven overheat)
        def_risk = 0.02
        if machine_shaking_vibration > 4.5:
            def_risk = 0.65
        elif machine_shaking_vibration > 2.8:
            def_risk = 0.35
        elif motor_heat_temperature > 65.0 and machine_shaking_vibration > 1.0:
            def_risk = 0.45
        elif motor_heat_temperature > 45.0 and machine_shaking_vibration > 1.0:
            def_risk = 0.20

        comp_risk = max(bn_risk, def_risk)
        return round(float(bn_risk), 3), round(float(def_risk), 3), round(float(comp_risk), 3)

    def predict_risk_with_routing(
        self,
        features: List[float],
        divergence_threshold: float = 0.45,
        min_sensor_confidence: float = 0.65,
        is_ood: bool = False,
        ood_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Shadow Mode Router for Risk Model (Phase 25 & Issue 4):
        Evaluates deterministic baseline, ML model, divergence, sensor confidence,
        and topology Out-Of-Distribution (OOD) status.
        Routes to ML serving or fails safe to conservative baseline if divergence, blackout,
        or topological structural OOD drift is detected.
        """
        base_bn, base_def, base_comp = self.compute_baseline_risk(features)
        sensor_conf = features[6] if len(features) > 6 else 1.0
        
        if not self.is_trained:
            return {
                "bottleneck_risk": base_bn,
                "defect_risk": base_def,
                "composite_risk": base_comp,
                "risk_level": "CRITICAL" if base_comp > 0.80 else ("WARNING" if base_comp > 0.60 else "NORMAL"),
                "serving_mode": "baseline_heuristic",
                "divergence_score": 0.0,
                "router_fallback_active": False,
                "sensor_confidence": sensor_conf,
                "is_ood": is_ood,
                "ood_reason": ood_reason
            }
            
        X_infer = np.asarray([features], dtype=np.float32)
        ml_bn = float(self.bottleneck_model.predict_proba(X_infer)[0, 1])
        ml_def = float(self.defect_model.predict_proba(X_infer)[0, 1])
        ml_comp = max(ml_bn, ml_def)
        
        divergence = abs(ml_comp - base_comp)
        fallback_triggered = is_ood or (sensor_conf < min_sensor_confidence) or (divergence > divergence_threshold)
        
        if fallback_triggered:
            final_bn = round(max(ml_bn, base_bn), 3)
            final_def = round(max(ml_def, base_def), 3)
            final_comp = round(max(final_bn, final_def), 3)
            if is_ood:
                serving_mode = "shadow_fallback_ood_conservative"
            else:
                serving_mode = "shadow_fallback_conservative"
        else:
            final_bn, final_def, final_comp = round(ml_bn, 3), round(ml_def, 3), round(ml_comp, 3)
            serving_mode = "ml_model"
            
        risk_level = "NORMAL"
        if final_comp > 0.80:
            risk_level = "CRITICAL"
        elif final_comp > 0.60:
            risk_level = "WARNING"
            
        return {
            "bottleneck_risk": final_bn,
            "defect_risk": final_def,
            "composite_risk": final_comp,
            "risk_level": risk_level,
            "serving_mode": serving_mode,
            "divergence_score": round(divergence, 3),
            "router_fallback_active": fallback_triggered,
            "ml_bottleneck_risk": round(ml_bn, 3),
            "ml_defect_risk": round(ml_def, 3),
            "base_bottleneck_risk": base_bn,
            "base_defect_risk": base_def,
            "sensor_confidence": sensor_conf,
            "is_ood": is_ood,
            "ood_reason": ood_reason
        }

    def predict_risk(self, features: List[float]) -> Tuple[float, float, str]:
        routing_res = self.predict_risk_with_routing(features)
        return routing_res["bottleneck_risk"], routing_res["defect_risk"], routing_res["risk_level"]

    def get_feature_contributions(self, station_id: str, features: List[float]) -> List[Dict[str, Any]]:
        """
        Calculates standardized statistical Z-score risk driver attributions relative to calibrated baselines.
        Uses unit-invariant sigma scaling (Z = |Observed - Mean| / Std) and feature importance weighting
        to eliminate raw magnitude distortion (e.g. kW vs mm/s).
        """
        # Calibrated nominal baselines (mean, std_dev, weight, unit, label)
        feature_specs = {
            "processing_time_ratio": {
                "mean": 1.0, "std": 0.08, "weight": 2.2, "unit": "x",
                "label": "Cycle Time Takt Drift",
                "expl": lambda v, z: f"Cycle time running {int((v-1.0)*100)}% slower than nominal target ({z:.1f}σ deviation)."
            },
            "rolling_mean_ct_ratio": {
                "mean": 1.0, "std": 0.06, "weight": 2.0, "unit": "x",
                "label": "Rolling Cycle Time Elevation",
                "expl": lambda v, z: f"Rolling average job duration sustained at {int((v-1.0)*100)}% above baseline."
            },
            "machine_shaking_vibration": {
                "mean": 0.80, "std": 0.35, "weight": 2.5, "unit": "mm/s",
                "label": "Mechanical ISO Vibration",
                "expl": lambda v, z: f"ISO 10816 mechanical vibration elevated ({v:.2f} mm/s vs 0.80 mm/s nominal - {z:.1f}σ spike)."
            },
            "motor_heat_temperature": {
                "mean": 24.0, "std": 6.0, "weight": 1.8, "unit": "°C",
                "label": "Thermal Motor Heat",
                "expl": lambda v, z: f"Motor core temperature elevated ({v:.1f}°C vs 24.0°C ambient baseline)."
            },
            "active_power_draw_kw": {
                "mean": 25.0, "std": 7.5, "weight": 1.8, "unit": "kW",
                "label": "Active Power Draw",
                "expl": lambda v, z: f"Spindle electrical draw surged ({v:.1f} kW vs 25.0 kW nominal load - {z:.1f}σ)."
            },
            "spc_z_score": {
                "mean": 0.0, "std": 1.0, "weight": 2.0, "unit": "σ",
                "label": "Statistical Process Drift (SPC)",
                "expl": lambda v, z: f"Statistical Process Control EWMA drift detected (|z|={v:.2f} > 2.0σ control bound)."
            },
            "degradation_momentum": {
                "mean": 0.0, "std": 0.04, "weight": 1.9, "unit": "rate",
                "label": "Tool Wear Degradation Momentum",
                "expl": lambda v, z: "Accelerated sequential cycle time degradation detected across active batch."
            },
            "buffer_utilization": {
                "mean": 0.50, "std": 0.18, "weight": 1.6, "unit": "%",
                "label": "Buffer Queue Starvation/Blockage",
                "expl": lambda v, z: f"Buffer queue critical ({int(v*100)}% capacity utilization - {z:.1f}σ offset)."
            },
            "max_upstream_starvation_risk": {
                "mean": 0.05, "std": 0.15, "weight": 1.7, "unit": "prob",
                "label": "Upstream Starvation Ripple",
                "expl": lambda v, z: f"Upstream feeder line blockage propagating {int(v*100)}% starvation ripple risk."
            },
            "sensor_confidence": {
                "mean": 1.0, "std": 0.15, "weight": 1.5, "unit": "%",
                "label": "Sensor Signal Quality Degradation",
                "expl": lambda v, z: f"Sensor fidelity degraded ({int(v*100)}% telemetry confidence - fallback active)."
            },
            "buffer_utilization_delta": {
                "mean": 0.0, "std": 0.10, "weight": 1.4, "unit": "Δ/tick",
                "label": "Buffer Queue Inflow/Outflow Disparity",
                "expl": lambda v, z: "Buffer inventory delta rate diverging from line flow equilibrium."
            }
        }

        contributions = []
        for i, name in enumerate(FEATURE_NAMES):
            if name not in feature_specs:
                continue  # Skip non-actionable contextual encoding features (e.g. station_type_code, shift_tick_cos)

            spec = feature_specs[name]
            val = float(features[i])
            mean_val = spec["mean"]
            std_val = spec["std"]
            weight = spec["weight"]

            # Compute standardized Z-score deviation
            if name in ["sensor_confidence"]:
                z_score = max(0.0, (mean_val - val) / std_val)
            elif name in ["processing_time_ratio", "rolling_mean_ct_ratio", "machine_shaking_vibration", "motor_heat_temperature", "active_power_draw_kw", "degradation_momentum", "max_upstream_starvation_risk"]:
                z_score = max(0.0, (val - mean_val) / std_val)
            else:
                z_score = abs(val - mean_val) / std_val

            # Minimum statistical significance threshold (0.4 sigma)
            if z_score < 0.35:
                continue

            impact_score = z_score * weight
            expl_text = spec["expl"](val, z_score)

            contributions.append({
                "feature": spec["label"],
                "raw_feature_name": name,
                "value": round(val, 2),
                "baseline": round(mean_val, 2),
                "unit": spec["unit"],
                "z_score": round(z_score, 2),
                "impact_score": round(impact_score, 3),
                "explanation": expl_text
            })

        # Fallback if all metrics are in deep nominal state
        if not contributions:
            contributions.append({
                "feature": "Nominal Baseline Variance",
                "raw_feature_name": "nominal",
                "value": 1.0,
                "baseline": 1.0,
                "unit": "norm",
                "z_score": 0.0,
                "impact_score": 1.0,
                "explanation": "All telemetry sensors operating within calibrated 3-sigma statistical process bounds."
            })

        contributions.sort(key=lambda c: -c["impact_score"])
        return contributions[:3]
