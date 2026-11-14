# mock_data.py
# Explain it simply: this module creates the demo crew and injects known event patterns.
# The goal is to test the detection logic with a known ground truth.

from __future__ import annotations

import random
from datetime import datetime, timedelta

from config import BASELINE_DAYS, MOCK_DATA_LABEL
from db import connect_db, init_db, insert_event, insert_notification, insert_reading

ASTRONAUTS = ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"]


def _iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _normal_value(base: float, spread: float, drift: float = 0.0):
    return base + drift + random.uniform(-spread, spread)


def create_mock_crew_data():
    random.seed(42)
    start_day = datetime(2026, 3, 15, 0, 0)
    rows = []
    events = []

    profiles = {
        "A. Mokoena": {
            "hr": (78, 8, 0.12),
            "hrv": (52, 12, -0.07),
            "bp_sys": (118, 10, 0.05),
            "bp_dia": (76, 7, 0.02),
            "spo2": (97.4, 1.5, 0.0),
            "resp_rate": (15, 3, 0.05),
            "temp_c": (36.9, 0.35, 0.0),
            "sleep_hours": (7.2, 1.3, -0.3),
            "deep_sleep_pct": (24, 6, -0.8),
            "stress_score": (42, 14, 5.0),
            "hydration_pct": (81, 12, -0.8),
            "intake_kcal": (2400, 240, -40),
            "need_kcal": (2600, 220, 0),
            "protein_g": (96, 18, -4),
            "body_mass_kg": (73.5, 1.4, -0.09),
            "radiation_msv_day": (0.08, 0.05, 0.0),
            "activity_min": (60, 20, 3.0),
            "contact_min": (75, 28, -5),
            "reaction_ms": (430, 70, 20),
        },
        "Dr. B. Smith": {
            "hr": (70, 7, 0.02),
            "hrv": (60, 15, 0.0),
            "bp_sys": (120, 8, 0.03),
            "bp_dia": (78, 7, 0.0),
            "spo2": (97.8, 1.1, 0.0),
            "resp_rate": (14, 3, 0.04),
            "temp_c": (36.8, 0.25, 0.0),
            "sleep_hours": (7.3, 1.2, -0.1),
            "deep_sleep_pct": (25, 6, 0.0),
            "stress_score": (36, 10, 1.8),
            "hydration_pct": (84, 8, -0.3),
            "intake_kcal": (2450, 200, -15),
            "need_kcal": (2650, 200, 0),
            "protein_g": (100, 18, -2),
            "body_mass_kg": (76.2, 1.1, -0.05),
            "radiation_msv_day": (0.05, 0.05, 0.0),
            "activity_min": (58, 18, 1.5),
            "contact_min": (78, 20, -4),
            "reaction_ms": (415, 50, 10),
        },
        "C. Tanaka": {
            "hr": (66, 6, 0.0),
            "hrv": (64, 14, 0.0),
            "bp_sys": (116, 7, 0.0),
            "bp_dia": (74, 6, 0.0),
            "spo2": (98.1, 1.0, 0.0),
            "resp_rate": (14, 2.5, 0.0),
            "temp_c": (36.7, 0.3, 0.0),
            "sleep_hours": (7.6, 0.9, 0.0),
            "deep_sleep_pct": (27, 5, 0.0),
            "stress_score": (28, 8, 0.5),
            "hydration_pct": (89, 7, 0.0),
            "intake_kcal": (2520, 220, -8),
            "need_kcal": (2700, 180, 0),
            "protein_g": (110, 16, 0),
            "body_mass_kg": (74.8, 1.0, -0.02),
            "radiation_msv_day": (0.04, 0.04, 0.0),
            "activity_min": (62, 18, 1.0),
            "contact_min": (90, 25, 0),
            "reaction_ms": (390, 40, 0),
        },
        "D. Okafor": {
            "hr": (68, 7, 0.0),
            "hrv": (62, 14, 0.0),
            "bp_sys": (118, 8, 0.0),
            "bp_dia": (78, 7, 0.0),
            "spo2": (98.0, 1.0, 0.0),
            "resp_rate": (14, 2.9, 0.0),
            "temp_c": (36.8, 0.3, 0.0),
            "sleep_hours": (7.5, 1.0, 0.0),
            "deep_sleep_pct": (26, 5, 0.0),
            "stress_score": (30, 9, 0.5),
            "hydration_pct": (87, 8, 0.0),
            "intake_kcal": (2500, 210, -8),
            "need_kcal": (2680, 210, 0),
            "protein_g": (108, 16, 0),
            "body_mass_kg": (79.0, 1.4, -0.02),
            "radiation_msv_day": (0.06, 0.05, 0.0),
            "activity_min": (60, 18, 1.0),
            "contact_min": (86, 22, -2),
            "reaction_ms": (405, 45, 0),
        },
    }

    signal_list = [
        "hr", "hrv", "bp_sys", "bp_dia", "spo2", "resp_rate", "temp_c",
        "sleep_hours", "deep_sleep_pct", "stress_score", "hydration_pct",
        "intake_kcal", "need_kcal", "protein_g", "body_mass_kg", "radiation_msv_day",
        "activity_min", "contact_min", "reaction_ms",
    ]

    for astronaut_id, profile in profiles.items():
        for day_index in range(BASELINE_DAYS):
            day_start = start_day + timedelta(days=day_index)
            for hour in range(24):
                for minute in [0, 15, 30, 45]:
                    ts = day_start + timedelta(hours=hour, minutes=minute)
                    for signal in signal_list:
                        base, spread, drift = profile[signal]
                        value = _normal_value(base, spread, drift * (day_index / 14) + (hour / 24) * 0.2)
                        if signal == "sleep_hours":
                            value = max(4.0, min(9.0, value))
                        if signal == "spo2":
                            value = max(90.0, min(100.0, value))
                        if signal == "stress_score":
                            value = max(5, min(90, value))
                        if signal == "hydration_pct":
                            value = max(50, min(100, value))
                        if signal == "reaction_ms":
                            value = max(250, min(900, value))
                        if signal == "intake_kcal":
                            value = max(1200, min(3200, value))
                        if signal == "need_kcal":
                            value = max(1800, min(3300, value))
                        if signal == "bp_sys":
                            value = max(90, min(150, value))
                        if signal == "bp_dia":
                            value = max(55, min(100, value))
                        if signal == "body_mass_kg":
                            value = max(55, min(90, value))
                        if signal == "radiation_msv_day":
                            value = max(0.0, min(1.5, value))
                        rows.append(
                            {
                                "astronaut_id": astronaut_id,
                                "ts": _iso(ts),
                                "signal": signal,
                                "value": round(float(value), 2),
                                "source": "simulator",
                                "quality": "demo",
                                "sync_pending": 0,
                            }
                        )

    events.extend([
        {"astronaut_id": "A. Mokoena", "ts": _iso(start_day + timedelta(days=9, hours=20)), "kind": "poor_sleep"},
        {"astronaut_id": "A. Mokoena", "ts": _iso(start_day + timedelta(days=10, hours=12)), "kind": "skipped_meal"},
        {"astronaut_id": "Dr. B. Smith", "ts": _iso(start_day + timedelta(days=11, hours=14)), "kind": "sleep"},
        {"astronaut_id": "C. Tanaka", "ts": _iso(start_day + timedelta(days=12, hours=8)), "kind": "exercise"},
        {"astronaut_id": "D. Okafor", "ts": _iso(start_day + timedelta(days=13, hours=12)), "kind": "medication"},
    ])

    return rows, events


def seed_database(db_path: str | None = None):
    conn = connect_db(db_path)
    init_db(conn)

    rows, events = create_mock_crew_data()
    if conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 0:
        for row in rows:
            insert_reading(conn, row)

    if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        for event in events:
            insert_event(conn, event["astronaut_id"], event["ts"], event["kind"])

    if conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 0:
        insert_notification(
            conn,
            _iso(datetime.now() - timedelta(minutes=8)),
            "mission_control",
            "A. Mokoena",
            "MOCK DATA - DEMO ONLY: Crew medical officer notified.",
            1,
        )

    conn.commit()
    conn.close()
    return {"status": "seeded", "label": MOCK_DATA_LABEL}


if __name__ == "__main__":
    print(seed_database())
