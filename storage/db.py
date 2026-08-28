"""
DigitalTwin.ai - High-Performance SQLite Database Manager & In-Memory Store
Optimized for industrial real-time streaming:
- Write-Ahead Logging (WAL Mode) for concurrent lock-free reads and writes.
- Memory-mapped I/O (mmap 256MB) and 64MB LRU cache.
- Vectorized executemany batch insertion (sub-millisecond persistence).
- Composite B-Tree indexing for instantaneous telemetry and VIN genealogy querying.
"""
import sqlite3
import os
import json
from typing import Dict, List, Any, Optional
from collections import deque

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "digitaltwin.db")


class TwinStore:
    def __init__(self, db_path: str = DB_PATH, ring_buffer_size: int = 60):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.ring_buffer = deque(maxlen=ring_buffer_size)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        self._configure_pragmas(conn)
        return conn

    @staticmethod
    def _configure_pragmas(conn: sqlite3.Connection):
        """Applies high-throughput industrial SQLite tuning parameters."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA cache_size = -64000;")  # 64 MB cache
        cursor.execute("PRAGMA temp_store = MEMORY;")
        cursor.execute("PRAGMA mmap_size = 268435456;")  # 256 MB memory-mapped I/O
        cursor.execute("PRAGMA busy_timeout = 5000;")

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stations (
                    station_id TEXT PRIMARY KEY,
                    name TEXT,
                    zone TEXT,
                    station_type TEXT,
                    sensor_tier TEXT,
                    target_cycle_time_s REAL,
                    power_base_kw REAL,
                    buffer_capacity_units INTEGER,
                    upstream_ids TEXT,
                    downstream_ids TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER,
                    timestamp TEXT,
                    station_id TEXT,
                    cycle_time_s REAL,
                    buffer_level INTEGER,
                    buffer_capacity INTEGER,
                    vibration REAL,
                    temperature REAL,
                    power_kw REAL,
                    energy_kwh REAL,
                    defect_flag INTEGER,
                    defect_type TEXT,
                    vehicle_id TEXT,
                    sensor_tier TEXT,
                    is_blackout INTEGER,
                    is_stopped INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ground_truth_anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER,
                    timestamp TEXT,
                    station_id TEXT,
                    true_anomaly_type TEXT,
                    severity REAL,
                    details TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recommendations (
                    id TEXT PRIMARY KEY,
                    tick INTEGER,
                    timestamp TEXT,
                    station_id TEXT,
                    zone TEXT,
                    rule_id TEXT,
                    title TEXT,
                    recommended_action TEXT,
                    rationale TEXT,
                    expected_impact TEXT,
                    downtime_avoided_min REAL,
                    cost_savings_usd REAL,
                    confidence REAL,
                    status TEXT,
                    override_reason TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vehicle_genealogy (
                    vehicle_id TEXT PRIMARY KEY,
                    entry_tick INTEGER,
                    completion_tick INTEGER,
                    status TEXT,
                    visit_history TEXT,
                    defect_flags TEXT
                )
            ''')

            # High-Speed Composite B-Tree Indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_station_tick ON telemetry(station_id, tick DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_id ON telemetry(vehicle_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_tick ON telemetry(tick DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_status_tick ON recommendations(status, tick DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ground_truth_tick ON ground_truth_anomalies(tick DESC);")
            
            conn.commit()

    def store_stations(self, stations: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            records = [
                (
                    sid, s["name"], s["zone"], s["station_type"], s["sensor_tier"],
                    s["target_cycle_time_s"], s["power_base_kw"], s["buffer_capacity_units"],
                    json.dumps(s["upstream_ids"]), json.dumps(s["downstream_ids"])
                )
                for sid, s in stations.items()
            ]
            cursor.executemany('''
                INSERT OR REPLACE INTO stations 
                (station_id, name, zone, station_type, sensor_tier, target_cycle_time_s, power_base_kw, buffer_capacity_units, upstream_ids, downstream_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            conn.commit()

    def store_tick_telemetry(self, tick_events: List[Dict[str, Any]], ground_truth: Optional[List[Dict[str, Any]]] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Vectorized batch insertion for telemetry
            telemetry_records = [
                (
                    ev["tick"], ev["timestamp"], ev["station_id"], ev.get("cycle_time_s"),
                    ev.get("buffer_level"), ev.get("buffer_capacity"), ev.get("vibration"), ev.get("temperature"),
                    ev.get("power_kw"), ev.get("energy_kwh"), 1 if ev.get("defect_flag") else 0,
                    ev.get("defect_type"), ev.get("vehicle_id"), ev.get("sensor_tier"),
                    1 if ev.get("is_blackout") else 0, 1 if ev.get("is_stopped") else 0
                )
                for ev in tick_events
            ]
            cursor.executemany('''
                INSERT INTO telemetry 
                (tick, timestamp, station_id, cycle_time_s, buffer_level, buffer_capacity, vibration, temperature, power_kw, energy_kwh, defect_flag, defect_type, vehicle_id, sensor_tier, is_blackout, is_stopped)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', telemetry_records)
            
            if ground_truth:
                gt_records = [
                    (
                        gt["tick"], gt["timestamp"], gt["station_id"], gt["true_anomaly_type"],
                        gt["severity"], json.dumps(gt.get("details", {}))
                    )
                    for gt in ground_truth
                ]
                cursor.executemany('''
                    INSERT INTO ground_truth_anomalies
                    (tick, timestamp, station_id, true_anomaly_type, severity, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', gt_records)
                
            conn.commit()

    # Aliases for compatibility
    def insert_telemetry_batch(self, tick_events: List[Dict[str, Any]]):
        self.store_tick_telemetry(tick_events, None)

    def insert_ground_truth_batch(self, ground_truth: List[Dict[str, Any]]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            gt_records = [
                (
                    gt["tick"], gt["timestamp"], gt["station_id"], gt["true_anomaly_type"],
                    gt["severity"], json.dumps(gt.get("details", {}))
                )
                for gt in ground_truth
            ]
            cursor.executemany('''
                INSERT INTO ground_truth_anomalies
                (tick, timestamp, station_id, true_anomaly_type, severity, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', gt_records)
            conn.commit()

    def insert_vehicle_genealogy_batch(self, genealogy_records: List[Dict[str, Any]]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            records = [
                (
                    rec["vehicle_id"], rec.get("entry_tick", 0), rec.get("completion_tick", 0),
                    rec.get("status", "IN_PROGRESS"), json.dumps(rec.get("visit_history", [])),
                    json.dumps(rec.get("defect_flags", []))
                )
                for rec in genealogy_records
            ]
            cursor.executemany('''
                INSERT OR REPLACE INTO vehicle_genealogy
                (vehicle_id, entry_tick, completion_tick, status, visit_history, defect_flags)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', records)
            conn.commit()

    def save_recommendations_batch(self, recs: List[Dict[str, Any]]):
        if not recs:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            records = [
                (
                    rec["id"], rec["tick"], rec["timestamp"], rec["station_id"], rec["zone"],
                    rec["rule_id"], rec["title"], rec["recommended_action"], rec["rationale"],
                    rec["expected_impact"], rec.get("downtime_avoided_min", 0.0), rec.get("cost_savings_usd", 0.0),
                    rec["confidence"], rec.get("status", "ACTIVE"), rec.get("override_reason", "")
                )
                for rec in recs
            ]
            cursor.executemany('''
                INSERT OR REPLACE INTO recommendations
                (id, tick, timestamp, station_id, zone, rule_id, title, recommended_action, rationale, expected_impact, downtime_avoided_min, cost_savings_usd, confidence, status, override_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            conn.commit()

    def get_recent_history(self, station_id: str, limit: int = 60) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM telemetry 
                WHERE station_id = ? 
                ORDER BY id DESC LIMIT ?
            ''', (station_id, limit))
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]

    def get_recent_telemetry_window(self, window_minutes: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM telemetry 
                ORDER BY id DESC LIMIT ?
            ''', (window_minutes * 40,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def log_recommendation(self, rec: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO recommendations
                (id, tick, timestamp, station_id, zone, rule_id, title, recommended_action, rationale, expected_impact, downtime_avoided_min, cost_savings_usd, confidence, status, override_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec["id"], rec["tick"], rec["timestamp"], rec["station_id"], rec["zone"],
                rec["rule_id"], rec["title"], rec["recommended_action"], rec["rationale"],
                rec["expected_impact"], rec.get("downtime_avoided_min", 0.0), rec.get("cost_savings_usd", 0.0),
                rec["confidence"], rec.get("status", "ACTIVE"), rec.get("override_reason", "")
            ))
            conn.commit()

    def log_override(self, rec_id: str, action: str, reason: str = ""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE recommendations
                SET status = ?, override_reason = ?
                WHERE id = ?
            ''', (action, reason, rec_id))
            conn.commit()

    def get_active_recommendations(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM recommendations 
                WHERE status = 'ACTIVE' OR status = 'ACCEPTED' OR status = 'OVERRIDDEN'
                ORDER BY tick DESC LIMIT 20
            ''')
            return [dict(r) for r in cursor.fetchall()]

    def get_ground_truth_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ground_truth_anomalies 
                ORDER BY id DESC LIMIT ?
            ''', (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_max_tick(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(tick) FROM telemetry")
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0

    def get_vehicle_genealogy_record(self, vin: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vehicle_genealogy WHERE vehicle_id = ?", (vin,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_vehicle_genealogy(self, vin: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM telemetry 
                WHERE vehicle_id = ?
                ORDER BY tick ASC
            ''', (vin,))
            return [dict(r) for r in cursor.fetchall()]
