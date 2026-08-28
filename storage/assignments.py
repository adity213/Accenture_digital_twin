"""
DigitalTwin.ai - Operator Assignment Storage Manager
Manages worker-to-station assignments for the filtered Operator SCADA view.
"""
import os
import json
from typing import Dict, List, Any, Optional

ASSIGNMENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "operator_assignments.json")


class AssignmentStore:
    def __init__(self, file_path: str = ASSIGNMENTS_FILE):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.assignments: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.assignments = {w["worker_id"]: w for w in data if "worker_id" in w}
            except Exception:
                self.assignments = {}
        else:
            # Default initial demo assignments
            self.assignments = {
                "W01": {
                    "worker_id": "W01",
                    "worker_name": "Marcus Chen (Body Lead)",
                    "assigned_station_ids": ["ST01", "ST02", "ST03", "ST04", "ST05", "ST06"]
                },
                "W02": {
                    "worker_id": "W02",
                    "worker_name": "Elena Rostova (Paint Tech)",
                    "assigned_station_ids": ["ST15", "ST16", "ST17", "ST18", "ST19", "ST20", "ST21", "ST22"]
                },
                "W03": {
                    "worker_id": "W03",
                    "worker_name": "David Kim (Assembly Marriage)",
                    "assigned_station_ids": ["ST24", "ST25", "ST26", "ST27", "ST28", "ST29", "ST30"]
                }
            }
            self._save()

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(list(self.assignments.values()), f, indent=2)
        except Exception as e:
            print(f"[AssignmentStore] Error saving assignments: {e}")

    def list_assignments(self) -> List[Dict[str, Any]]:
        return list(self.assignments.values())

    def get_assignment(self, worker_id: str) -> Optional[Dict[str, Any]]:
        return self.assignments.get(worker_id)

    def set_assignment(self, worker_id: str, worker_name: str, assigned_station_ids: List[str]) -> Dict[str, Any]:
        rec = {
            "worker_id": worker_id,
            "worker_name": worker_name,
            "assigned_station_ids": assigned_station_ids
        }
        self.assignments[worker_id] = rec
        self._save()
        return rec

    def delete_assignment(self, worker_id: str) -> bool:
        if worker_id in self.assignments:
            del self.assignments[worker_id]
            self._save()
            return True
        return False
