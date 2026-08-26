"""
DigitalTwin.ai - Statistical Process Control (SPC) Engine
Calculates EWMA (lambda=0.3) and z-scores against calibrated station baseline.
Flags statistically significant process deviations (|z| > 3.0) and detects early drift.
"""
from typing import Dict, List, Any
import math
from collections import deque

class SPCEngine:
    def __init__(self, lambda_ewma: float = 0.3, z_threshold: float = 3.0, window_size: int = 30):
        self.lambda_ewma = lambda_ewma
        self.z_threshold = z_threshold
        self.window_size = window_size
        
        self.ewma_state: Dict[str, float] = {}
        self.history_windows: Dict[str, deque] = {}

    def update_station(self, station_id: str, cycle_time_s: float, target_cycle_time_s: float) -> Dict[str, Any]:
        if station_id not in self.history_windows:
            self.history_windows[station_id] = deque(maxlen=self.window_size)
            self.ewma_state[station_id] = target_cycle_time_s
            
        win = self.history_windows[station_id]
        win.append(cycle_time_s)
        
        # Update EWMA
        prev_ewma = self.ewma_state[station_id]
        curr_ewma = self.lambda_ewma * cycle_time_s + (1.0 - self.lambda_ewma) * prev_ewma
        self.ewma_state[station_id] = curr_ewma
        
        # Baseline sigma is 4% of target cycle time per plant calibration
        baseline_sigma = max(0.5, target_cycle_time_s * 0.04)
        
        # z-score against calibrated target baseline
        z_score = (curr_ewma - target_cycle_time_s) / baseline_sigma
        deviation_flag = abs(z_score) > self.z_threshold
        
        # Trend detection across sliding window
        trend = "STABLE"
        if len(win) >= 5:
            first_half = list(win)[:len(win)//2]
            second_half = list(win)[len(win)//2:]
            diff = (sum(second_half)/len(second_half)) - (sum(first_half)/len(first_half))
            if diff > 0.6:
                trend = "DRIFT_UP"
            elif diff < -0.6:
                trend = "DRIFT_DOWN"

        return {
            "station_id": station_id,
            "ewma": round(curr_ewma, 2),
            "target": target_cycle_time_s,
            "baseline_sigma": round(baseline_sigma, 3),
            "z_score": round(z_score, 2),
            "deviation_flag": deviation_flag,
            "trend": trend
        }
