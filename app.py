# tests.py
# Explain it simply: this module runs a few plain assert checks to keep the logic teachable.
# No pytest is needed.

from __future__ import annotations

from analysis import compute_baseline, compute_health_score, compute_nutrition_flag, compute_stress_score, detect_red_alert
from db import connect_db, init_db
from mock_data import seed_database

readings = [
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:00:00", "signal": "hr", "value": 70.0, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:15:00", "signal": "hr", "value": 73.0, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:30:00", "signal": "hr", "value": 78.0, "source": "sim", "quality": "demo", "sync_pending": 0},
]
base = compute_baseline(readings, "A. Mokoena", "hr")
assert base["count"] == 3
assert base["mean"] > 70

red_records = [
    {"astronaut_id": "D. Okafor", "ts": "2026-03-15 00:00:00", "signal": "spo2", "value": 88.0, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "D. Okafor", "ts": "2026-03-15 00:15:00", "signal": "hr", "value": 134.0, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "D. Okafor", "ts": "2026-03-15 00:30:00", "signal": "bp_sys", "value": 97.0, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "D. Okafor", "ts": "2026-03-15 00:45:00", "signal": "bp_dia", "value": 66.0, "source": "sim", "quality": "demo", "sync_pending": 0},
]
was_red, payload = detect_red_alert("D. Okafor", red_records)
assert was_red is True
assert "Immediate medical review" in payload["title"]

health = compute_health_score("C. Tanaka", readings)
assert 0 <= health["score"] <= 100
assert health["level"] in ["GREEN", "YELLOW", "ORANGE", "RED"]

nutrition_records = [
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:00:00", "signal": "intake_kcal", "value": 1800, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:00:00", "signal": "need_kcal", "value": 2400, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-16 00:00:00", "signal": "intake_kcal", "value": 1900, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-16 00:00:00", "signal": "need_kcal", "value": 2400, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-17 00:00:00", "signal": "intake_kcal", "value": 1900, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-17 00:00:00", "signal": "need_kcal", "value": 2400, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-17 00:00:00", "signal": "body_mass_kg", "value": 69.0, "source": "sim", "quality": "demo", "sync_pending": 0},
]
assert compute_nutrition_flag(nutrition_records, "A. Mokoena")["level"] == "YELLOW"

stress_value = compute_stress_score([
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:00:00", "signal": "sleep_hours", "value": 4.8, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:00:00", "signal": "activity_min", "value": 110, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:00:00", "signal": "contact_min", "value": 20, "source": "sim", "quality": "demo", "sync_pending": 0},
    {"astronaut_id": "A. Mokoena", "ts": "2026-03-15 00:00:00", "signal": "hrv", "value": 25, "source": "sim", "quality": "demo", "sync_pending": 0},
], "A. Mokoena")
assert 0 <= stress_value <= 100

conn = connect_db()
init_db(conn)
seed_database()
assert conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] > 0
conn.close()

print("All tests passed.")
