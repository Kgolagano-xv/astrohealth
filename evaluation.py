# analysis.py
# Explain it simply: this module turns raw readings into baselines, trends and risk explanations.
# It compares each astronaut with their own 14-day history and creates a combined score.

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from config import ASTRONAUT_PROFILES, RED_ALERT_COMBINATION, SIGNAL_CAPS, STRESS_WEIGHTING


def _as_df(readings: List[dict]):
    if not readings:
        return pd.DataFrame(columns=["astronaut_id", "ts", "signal", "value", "source", "quality", "sync_pending"])
    return pd.DataFrame(readings)


def _to_dt(value):
    try:
        return pd.to_datetime(value)
    except Exception:
        return pd.NaT


def compute_baseline(records: list[dict], astronaut_id: str, signal: str):
    df = _as_df(records)
    subset = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == signal)].copy()
    if subset.empty:
        return {"mean": 0.0, "std": 0.0, "count": 0}
    subset["ts"] = subset["ts"].apply(_to_dt)
    subset = subset[pd.notna(subset["ts"])].copy()
    values = pd.to_numeric(subset["value"], errors="coerce").dropna()
    if values.empty:
        return {"mean": 0.0, "std": 0.0, "count": 0}
    return {"mean": float(values.mean()), "std": float(values.std(ddof=0)), "count": int(len(values))}


def compute_recent_trend(records: list[dict], astronaut_id: str, signal: str, points: int = 12):
    df = _as_df(records)
    subset = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == signal)].copy()
    if subset.empty:
        return {"recent": [], "slope": 0.0, "mean": 0.0}
    subset["ts"] = subset["ts"].apply(_to_dt)
    subset = subset[pd.notna(subset["ts"])].sort_values("ts")
    recent = subset.tail(points)
    values = pd.to_numeric(recent["value"], errors="coerce").dropna().tolist()
    if len(values) < 2:
        slope = 0.0
    else:
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
    return {"recent": values, "slope": float(slope), "mean": float(np.mean(values)) if values else 0.0}


def determine_status_for_signal(astronaut_id: str, signal: str, current_value: float, baseline: Dict[str, float]):
    mean_v = float(baseline.get("mean", 0.0))
    std = float(baseline.get("std", 0.0))
    if std == 0:
        z = 0.0
    else:
        z = (current_value - mean_v) / std

    low, high = ASTRONAUT_PROFILES.get(astronaut_id, {}).get(signal, (0.0, 0.0))
    if low == 0.0 and high == 0.0:
        if z < -1.5:
            return "YELLOW", f"{signal} is below baseline by {abs(z):.1f} SD."
        if z > 1.5:
            return "YELLOW", f"{signal} is above baseline by {abs(z):.1f} SD."
        return "GREEN", "Within personal baseline."

    if current_value < low or current_value > high:
        return "YELLOW", f"Current {signal} is outside the astronaut's normal range."
    return "GREEN", "Within personal range."


def compute_health_score(astronaut_id: str, records: list[dict]):
    df = _as_df(records)
    subset = df[df["astronaut_id"] == astronaut_id].copy()
    if subset.empty:
        return {"score": 100.0, "contributions": {}, "level": "GREEN"}

    contributions = {}
    total_penalty = 0.0

    for signal, weight in {
        "hr": 0.20,
        "bp_sys": 0.10,
        "spo2": 0.20,
        "resp_rate": 0.20,
        "temp_c": 0.05,
        "sleep_hours": 0.12,
        "stress_score": 0.10,
        "hydration_pct": 0.10,
        "body_mass_kg": 0.05,
        "radiation_msv_day": 0.05,
    }.items():
        signal_values = pd.to_numeric(subset[subset["signal"] == signal]["value"], errors="coerce")
        if signal_values.empty:
            continue
        current = float(signal_values.iloc[-1])
        baseline = compute_baseline(records, astronaut_id, signal)
        mean_v = baseline["mean"]
        dist = abs(current - mean_v)
        cap = SIGNAL_CAPS.get(signal, 10)
        penalty = min(dist / max(cap, 1.0), 1.0) * 100 * weight
        contributions[signal] = penalty
        total_penalty += penalty

    score = max(0.0, min(100.0, 100.0 - total_penalty))
    if score >= 85:
        level = "GREEN"
    elif score >= 60:
        level = "YELLOW"
    elif score >= 35:
        level = "ORANGE"
    else:
        level = "RED"
    return {"score": round(score, 1), "contributions": contributions, "level": level}


def compute_nutrition_flag(records: list[dict], astronaut_id: str):
    df = _as_df(records)
    subset = df[(df["astronaut_id"] == astronaut_id) & (df["signal"].isin(["intake_kcal", "need_kcal", "body_mass_kg"]))].copy()
    if subset.empty:
        return {"level": "GREEN", "reason": "No nutrition data."}

    intake = subset[subset["signal"] == "intake_kcal"].sort_values("ts")
    need = subset[subset["signal"] == "need_kcal"].sort_values("ts")
    count_gap = 0
    if not intake.empty and not need.empty:
        merged = intake.merge(need, on=["astronaut_id", "ts"], how="inner", suffixes=("_int", "_need"))
        merged["gap_pct"] = (merged["value_need"] - merged["value_int"]) / merged["value_need"]
        count_gap = int((merged["gap_pct"] > 0.10).sum())

    body_mass = subset[subset["signal"] == "body_mass_kg"]
    if count_gap >= 3 or (not body_mass.empty and float(body_mass["value"].iloc[-1]) < float(body_mass["value"].mean()) - 0.6):
        return {"level": "YELLOW", "reason": "Nutrition gap and body mass trend suggest under-fueling or dehydration."}
    return {"level": "GREEN", "reason": "Nutrition estimate is stable."}


def compute_mind_sleep(records: list[dict], astronaut_id: str):
    df = _as_df(records)
    checks = {}
    for signal in ["sleep_hours", "deep_sleep_pct", "stress_score", "contact_min", "reaction_ms"]:
        subset = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == signal)].sort_values("ts")
        checks[signal] = float(subset["value"].iloc[-1]) if not subset.empty else 0.0

    bad = 0
    if checks["sleep_hours"] < 6.0:
        bad += 1
    if checks["deep_sleep_pct"] < 18:
        bad += 1
    if checks["stress_score"] > 60:
        bad += 1
    if checks["contact_min"] < 50:
        bad += 1
    if checks["reaction_ms"] > 600:
        bad += 1

    if bad >= 2:
        return {
            "level": "YELLOW",
            "title": "Check-in needed",
            "what": "Sleep, stress and contact are trending worse together.",
            "why": "This is a proxy only, not a diagnosis.",
            "next": "A brief check-in with the crew medical officer is recommended.",
        }
    return {
        "level": "GREEN",
        "title": "Mind and sleep stable",
        "what": "Patterns are stable.",
        "why": "No strong combined proxy signal is present.",
        "next": "Keep routine monitoring.",
    }


def compute_stress_score(records: list[dict], astronaut_id: str):
    df = _as_df(records)
    sleep = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == "sleep_hours")].sort_values("ts")
    workload = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == "activity_min")].sort_values("ts")
    contact = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == "contact_min")].sort_values("ts")
    hrv = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == "hrv")].sort_values("ts")

    if sleep.empty or workload.empty or contact.empty or hrv.empty:
        return 30

    s = float(sleep["value"].iloc[-1])
    w = float(workload["value"].iloc[-1])
    c = float(contact["value"].iloc[-1])
    h = float(hrv["value"].iloc[-1])

    sleep_component = max(0, 100 * (7.5 - s) / 7.5)
    workload_component = min(100, max(0, (w / 120) * 100))
    contact_component = max(0, 100 * (1 - c / 120))
    hrv_component = max(0, (60 - h) / 60 * 100)

    stress = (
        STRESS_WEIGHTING["sleep_loss"] * sleep_component
        + STRESS_WEIGHTING["workload"] * workload_component
        + STRESS_WEIGHTING["low_contact"] * contact_component
        + STRESS_WEIGHTING["hrv_drop"] * hrv_component
    )
    return max(0, min(100, round(float(stress), 1)))


def detect_red_alert(astronaut_id: str, records: list[dict]):
    df = _as_df(records)
    subset = df[df["astronaut_id"] == astronaut_id].copy()
    latest = subset.sort_values("ts").tail(200)
    values = {}
    for signal in ["spo2", "hr", "bp_sys", "bp_dia"]:
        signal_values = latest[latest["signal"] == signal]
        if not signal_values.empty:
            values[signal] = float(signal_values["value"].iloc[-1])

    spo2 = values.get("spo2", 100)
    hr = values.get("hr", 50)
    bp_sys = values.get("bp_sys", 120)
    bp_drop = max(0, 120 - bp_sys)

    if spo2 < RED_ALERT_COMBINATION["spo2_lt"] and hr > RED_ALERT_COMBINATION["hr_gt"] and bp_drop > RED_ALERT_COMBINATION["bp_drop"]:
        return True, {
            "title": "Immediate medical review",
            "what": "SpO2 fell, heart rate rose and blood pressure dropped.",
            "why": "This combination matches the placeholder RED rule.",
            "todo": "Use the emergency checklist and notify Mission Control.",
        }
    return False, {"title": "No red alert", "what": "No life-threatening pattern detected.", "why": "Monitor continues.", "todo": "Continue routine observation."}


def compute_explanation(astronaut_id: str, signal: str, records: list[dict]):
    df = _as_df(records)
    subset = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == signal)].sort_values("ts")
    if subset.empty:
        return "No data available."
    current = float(subset["value"].iloc[-1])
    baseline = compute_baseline(records, astronaut_id, signal)
    mean_v = baseline["mean"]
    delta = current - mean_v
    return f"Current value {current:.1f} vs personal baseline {mean_v:.1f}; change is {delta:+.1f}."


def compute_buddy_routing(records: list[dict], astronaut_id: str):
    score_summary = compute_health_score(astronaut_id, records)
    level = score_summary["level"]
    if level == "GREEN":
        return {"recipient": "none", "message": "No one is told."}
    if level == "YELLOW":
        return {"recipient": "astronaut_only", "message": "Private nudge: please review your personal trend."}
    if level == "ORANGE":
        return {"recipient": "astronaut_and_medical_officer", "message": f"Please check in on {astronaut_id} today"}
    return {"recipient": "whole_crew", "message": "Emergency crew alarm and Mission Control notice."}


if __name__ == "__main__":
    print("Analysis module ready.")
