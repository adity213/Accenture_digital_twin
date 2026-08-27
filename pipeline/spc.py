"""
DigitalTwin.ai - Statistical Process Control (SPC) Engine
Calculates EWMA (lambda=0.3) and z-scores against calibrated station baseline.
Flags statistically significant process deviations (|z| > 3.0) and detects early drift.
Calibrated with ISO 10816-3 industrial vibration standards (Warning limit > 4.5 mm/s).
"""
from typing import Dict, List, Any, Optional
import math
from collections import deque

class SPCEngine:
    def __init__(self, lambda_ewma: float = 0.3, z_threshold: float = 3.0, window_size: int = 30, iso_vibration_limit: float = 4.5):
        self.lambda_ewma = lambda_ewma
        self.z_threshold = z_threshold
        self.window_size = window_size
        self.iso_vibration_limit = iso_vibration_limit
        
        self.ewma_state: Dict[str, float] = {}
        self.vib_ewma_state: Dict[str, float] = {}
        self.history_windows: Dict[str, deque] = {}

    def update_station(
        self,
        station_id: str,
        cycle_time_s: float,
        target_cycle_time_s: float,
        vibration: Optional[float] = None
    ) -> Dict[str, Any]:
        if station_id not in self.history_windows:
            self.history_windows[station_id] = deque(maxlen=self.window_size)
            self.ewma_state[station_id] = target_cycle_time_s
            
        win = self.history_windows[station_id]
        win.append(cycle_time_s)
        
        # Update EWMA for cycle time
        prev_ewma = self.ewma_state[station_id]
        curr_ewma = self.lambda_ewma * cycle_time_s + (1.0 - self.lambda_ewma) * prev_ewma
        self.ewma_state[station_id] = curr_ewma
        
        # Baseline sigma is 4% of target cycle time per plant calibration
        baseline_sigma = max(0.5, target_cycle_time_s * 0.04)
        
        # z-score against calibrated target baseline
        z_score = (curr_ewma - target_cycle_time_s) / baseline_sigma
        ct_deviation_flag = abs(z_score) > self.z_threshold

        # Vibration ISO 10816-3 Evaluation
        iso_vibration_status = "NORMAL"
        iso_vibration_alarm = False
        vib_ewma = None
        if vibration is not None:
            prev_vib_ewma = self.vib_ewma_state.get(station_id, vibration)
            curr_vib_ewma = self.lambda_ewma * vibration + (1.0 - self.lambda_ewma) * prev_vib_ewma
            self.vib_ewma_state[station_id] = curr_vib_ewma
            vib_ewma = round(curr_vib_ewma, 3)
            
            if vibration < 1.12:
                iso_vibration_status = "GOOD"
            elif vibration <= 2.80:
                iso_vibration_status = "SATISFACTORY"
            elif vibration <= self.iso_vibration_limit:
                iso_vibration_status = "UNSATISFACTORY"
            else:
                iso_vibration_status = "UNACCEPTABLE"
                iso_vibration_alarm = True

        # Total deviation flag (Cycle Time z-score or ISO vibration breach)
        deviation_flag = ct_deviation_flag or iso_vibration_alarm
        
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
            "ewma_drift_flag": deviation_flag,
            "trend": trend,
            "iso_vibration_status": iso_vibration_status,
            "iso_vibration_alarm": iso_vibration_alarm,
            "vibration_ewma": vib_ewma
        }
