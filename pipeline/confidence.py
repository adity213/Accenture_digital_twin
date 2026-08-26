"""
DigitalTwin.ai - Confidence Scoring & Twin Confidence Aggregator
PRD Section 5.2 Formula:
confidence = w1*sensor_tier_score + w2*recency_score + w3*(1 - imputation_disagreement)
(w1=0.5, w2=0.3, w3=0.2)
Aggregates data confidence and model certainty into a 0-100% Twin Confidence.
"""
import math
from typing import Dict, Any

class ConfidenceEngine:
    def __init__(self, w1: float = 0.5, w2: float = 0.3, w3: float = 0.2):
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3

    def compute_data_confidence(
        self,
        sensor_tier: str,
        is_blackout: bool,
        ticks_since_last_reading: int,
        imputation_disagreement: float = 0.0
    ) -> float:
        # Sensor Tier Score: Rich PLC = 1.0, Manual Checklist = 0.35
        if is_blackout:
            tier_score = 0.05
            recency_score = max(0.05, math.exp(-0.08 * max(1, ticks_since_last_reading)))
        elif sensor_tier == "rich":
            tier_score = 1.0
            recency_score = max(0.2, math.exp(-0.05 * ticks_since_last_reading))
        else: # manual checklist
            tier_score = 0.35
            recency_score = max(0.15, math.exp(-0.06 * ticks_since_last_reading))

        agreement_score = max(0.0, 1.0 - imputation_disagreement)

        confidence = (
            self.w1 * tier_score +
            self.w2 * recency_score +
            self.w3 * agreement_score
        )
        return round(min(1.0, max(0.05, confidence)), 3)

    def compute_twin_confidence(
        self,
        data_confidence: float,
        model_confidence: float = 0.92,
        has_conflicting_imputation: bool = False
    ) -> int:
        composite = 0.70 * data_confidence + 0.30 * model_confidence
        if has_conflicting_imputation:
            composite = max(0.15, composite * 0.85)
        return int(round(composite * 100))

    def compute_composite_twin_confidence(
        self,
        data_confidence: float,
        model_risk_prob: float,
        spc_deviation_flag: bool
    ) -> int:
        model_certainty = 1.0 - 2.0 * abs(model_risk_prob - 0.5)
        model_confidence = 0.6 + 0.4 * (1.0 - model_certainty)
        composite = 0.70 * data_confidence + 0.30 * model_confidence
        if spc_deviation_flag:
            composite = max(0.15, composite * 0.9)
        return int(round(composite * 100))
