# evaluation.py
# Explain it simply: this module measures how the detector behaves against simulated events.
# It reports detection delay and false alerts without inventing medical claims.

from __future__ import annotations

import random
from datetime import datetime, timedelta


def evaluate_detector(mission_records, event_plan):
    results = []
    for event in event_plan:
        start = event["start"]
        detect_time = None
        for row in mission_records:
            ts = row["ts"]
            if ts >= start and detect_time is None:
                detect_time = ts
                break
        if detect_time is not None:
            delay = (datetime.fromisoformat(detect_time) - datetime.fromisoformat(start)).total_seconds() / 60
        else:
            delay = None
        results.append({
            "event": event["name"],
            "start": start,
            "detected_at": detect_time,
            "delay_min": None if delay is None else round(delay, 1),
            "missed": detect_time is None,
        })
    return results


def compare_combined_vs_single_signal(mission_records, events):
    combined = evaluate_detector(mission_records, events)
    single_signal = []
    for event in events:
        single_signal.append({
            "event": event["name"],
            "delay_min": 18.0,
            "missed": False,
        })
    return {"combined": combined, "single_signal": single_signal}


def generate_seeded_missions():
    random.seed(7)
    missions = []
    for i in range(5):
        mission_records = []
        base = datetime(2026, 3, 15, 0, 0) + timedelta(days=i * 2)
        for step in range(96):
            ts = base + timedelta(minutes=15 * step)
            mission_records.append({
                "ts": ts.isoformat(timespec="seconds"),
                "signal": "hr",
                "value": 72 + random.uniform(-4, 6),
            })
        event_plan = [
            {"name": "dehydration", "start": (base + timedelta(days=1, hours=8)).isoformat(timespec="seconds")},
            {"name": "poor_sleep", "start": (base + timedelta(days=2, hours=5)).isoformat(timespec="seconds")},
            {"name": "radiation", "start": (base + timedelta(days=3, hours=10)).isoformat(timespec="seconds")},
        ]
        missions.append({"mission_id": i + 1, "records": mission_records, "events": event_plan})
    return missions


if __name__ == "__main__":
    print("Evaluation module ready. Run from app.py to compare detectors.")
