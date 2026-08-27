"""
DigitalTwin.ai - Predictive Risk Scoring Model
Predicts P(bottleneck within next 15 minutes) and P(defect).
Implements a robust Gradient Boosted Decision Tree (GBDT) ensemble.
Uses scikit-learn for high performance and reliability.
Trained strictly on chronological 70/30 train-test split with ZERO data leakage.
"""
import math
import random
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import HistGradientBoostingClassifier
import numpy as np

class RiskScoringModel:
    def __init__(self):
        self.bottleneck_model = HistGradientBoostingClassifier(max_iter=30, learning_rate=0.1, max_depth=3, random_state=42)
        self.defect_model = HistGradientBoostingClassifier(max_iter=20, learning_rate=0.1, max_depth=3, random_state=42)
        self.is_trained = False

    def extract_features(
        self,
        station_id: str,
        telemetry: Dict[str, Any],
        spc_result: Dict[str, Any],
        sensor_confidence: float,
        upstream_risks: List[float],
        target_cycle_time_s: float,
        buffer_capacity: int,
        shift_tick: int
    ) -> List[float]:
        # Feature Extraction - STRICTLY NO GROUND TRUTH LABELS (ZERO DATA LEAKAGE)
        actual_processing_time = telemetry.get("cycle_time_s") or target_cycle_time_s
        waiting_line_count = telemetry.get("buffer_level") if telemetry.get("buffer_level") is not None else int(buffer_capacity * 0.5)
        
        processing_time_ratio = actual_processing_time / max(1.0, target_cycle_time_s)
        buffer_utilization = waiting_line_count / max(1.0, buffer_capacity)
        
        trend_map = {"STABLE": 0.0, "DRIFT_UP": 1.0, "DRIFT_DOWN": -1.0}
        degradation_momentum = trend_map.get(spc_result.get("trend", "STABLE"), 0.0)
        
        avg_upstream_starvation_risk = sum(upstream_risks) / len(upstream_risks) if upstream_risks else 0.0
        max_upstream_starvation_risk = max(upstream_risks) if upstream_risks else 0.0
        
        shift_progress = (shift_tick % 480) / 480.0
        is_manual_sensor = 1.0 if telemetry.get("sensor_tier") == "manual" else 0.0
        machine_shaking_vibration = telemetry.get("vibration") or 0.8
        motor_heat_temperature = telemetry.get("temperature") or 24.0
        active_power_draw_kw = telemetry.get("power_kw") or 20.0

        return [
            round(processing_time_ratio, 3),
            round(buffer_utilization, 3),
            round(degradation_momentum, 1),
            round(avg_upstream_starvation_risk, 3),
            round(max_upstream_starvation_risk, 3),
            round(sensor_confidence, 3),
            round(shift_progress, 3),
            is_manual_sensor,
            round(machine_shaking_vibration, 3),
            round(motor_heat_temperature, 2),
            round(active_power_draw_kw, 2)
        ]

    def train_on_history(
        self,
        features_list: List[List[float]],
        bottleneck_labels: List[int],
        defect_labels: List[int]
    ) -> Dict[str, Any]:
        n = len(features_list)
        split_idx = int(n * 0.70)
        
        X_train, X_test = features_list[:split_idx], features_list[split_idx:]
        y_bn_train, y_bn_test = bottleneck_labels[:split_idx], bottleneck_labels[split_idx:]
        y_def_train, y_def_test = defect_labels[:split_idx], defect_labels[split_idx:]
        
        # Fit models
        self.bottleneck_model.fit(X_train, y_bn_train)
        self.defect_model.fit(X_train, y_def_train)
        self.is_trained = True
        
        # Evaluate on held-out test window
        bn_probs = self.bottleneck_model.predict_proba(X_test)[:, 1]
        bn_preds = self.bottleneck_model.predict(X_test)
        
        # Compute AUC using Wilcoxon-Mann-Whitney rank statistic
        pos_scores = [bn_probs[i] for i in range(len(X_test)) if y_bn_test[i] == 1]
        neg_scores = [bn_probs[i] for i in range(len(X_test)) if y_bn_test[i] == 0]
        
        if pos_scores and neg_scores:
            auc = sum(1.0 for p in pos_scores for neg in neg_scores if p > neg) + 0.5 * sum(1.0 for p in pos_scores for neg in neg_scores if p == neg)
            auc /= (len(pos_scores) * len(neg_scores))
        else:
            auc = 0.5
            
        tp = sum(1 for i in range(len(X_test)) if bn_preds[i] == 1 and y_bn_test[i] == 1)
        fp = sum(1 for i in range(len(X_test)) if bn_preds[i] == 1 and y_bn_test[i] == 0)
        fn = sum(1 for i in range(len(X_test)) if bn_preds[i] == 0 and y_bn_test[i] == 1)
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        return {
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "bottleneck_auc": round(auc, 3),
            "bottleneck_precision": round(prec, 3),
            "bottleneck_recall": round(rec, 3)
        }

    def predict_risk(self, features: List[float]) -> Tuple[float, float, str]:
        if not self.is_trained:
            # Calibrated physics / heuristic fallback
            processing_time_ratio = features[0]
            buffer_utilization = features[1]
            degradation_momentum = features[2]
            max_upstream_risk = features[4]
            machine_shaking_vibration = features[8]
            motor_heat_temperature = features[9]
            
            bn_risk = 0.05
            if processing_time_ratio > 1.3:
                bn_risk = 0.75 + min(0.24, (processing_time_ratio - 1.3) * 0.5)
            elif processing_time_ratio > 1.15 or degradation_momentum > 0:
                bn_risk = 0.55
            elif buffer_utilization < 0.20 and max_upstream_risk > 0.6:
                bn_risk = 0.65

            def_risk = 0.02
            # ISO 10816: Unacceptable vibration warning limit is > 4.5 mm/s for Class I/II machinery
            if machine_shaking_vibration > 4.5 or (motor_heat_temperature > 220.0 and machine_shaking_vibration > 1.0):
                def_risk = 0.45

            comp_risk = max(bn_risk, def_risk)
        else:
            X_infer = [features]
            bn_risk = self.bottleneck_model.predict_proba(X_infer)[0, 1]
            def_risk = self.defect_model.predict_proba(X_infer)[0, 1]
            comp_risk = max(bn_risk, def_risk)
            
        risk_level = "NORMAL"
        if comp_risk > 0.80:
            risk_level = "CRITICAL"
        elif comp_risk > 0.60:
            risk_level = "WARNING"
            
        return round(float(bn_risk), 3), round(float(def_risk), 3), risk_level
