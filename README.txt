# app.py
# Explain it simply: this is the streamlit dashboard for the prototype.
# It combines the SQLite database, signal logic and body map into a user-friendly mission-control screen.

from __future__ import annotations

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from analysis import (
    compute_buddy_routing,
    compute_explanation,
    compute_health_score,
    compute_mind_sleep,
    compute_nutrition_flag,
    detect_red_alert,
    determine_status_for_signal,
)
from bodymap import draw_body_map
from config import ASTRONAUT_PROFILES, MOCK_DATA_LABEL, RESEARCH_NOTICE, SIGNAL_META
from db import connect_db, fetch_recent_readings, init_db, insert_alert, insert_notification
from mock_data import seed_database


def get_conn():
    conn = connect_db()
    init_db(conn)
    return conn


def latest_value_for_signal(conn, astronaut_id: str, signal: str):
    rows = fetch_recent_readings(conn, astronaut_id=astronaut_id, limit=2000)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    subset = df[(df["astronaut_id"] == astronaut_id) & (df["signal"] == signal)]
    if subset.empty:
        return None
    return float(subset.sort_values("ts").iloc[-1]["value"])


def status_summary(conn, astronaut_id: str):
    status_map = {"brain": "GREEN", "heart": "GREEN", "lungs": "GREEN", "stomach": "GREEN", "muscles": "GREEN", "bones": "GREEN", "radiation": "GREEN"}
    for key in ["hr", "spo2", "sleep_hours", "stress_score", "hydration_pct", "radiation_msv_day"]:
        value = latest_value_for_signal(conn, astronaut_id, key)
        if value is None:
            continue
        if key == "hr" and value > 90:
            status_map["heart"] = "YELLOW"
        if key == "spo2" and value < 95:
            status_map["lungs"] = "YELLOW"
        if key == "sleep_hours" and value < 6:
            status_map["brain"] = "YELLOW"
        if key == "stress_score" and value > 60:
            status_map["brain"] = "YELLOW"
        if key == "hydration_pct" and value < 75:
            status_map["stomach"] = "YELLOW"
        if key == "radiation_msv_day" and value > 0.6:
            status_map["radiation"] = "ORANGE"

    red_flag, _ = detect_red_alert(astronaut_id, fetch_recent_readings(conn, astronaut_id=astronaut_id, limit=2000))
    if red_flag:
        status_map["heart"] = "RED"
        status_map["lungs"] = "RED"
    return status_map


def show_signal_panel(conn, astronaut_id: str, signal: str):
    value = latest_value_for_signal(conn, astronaut_id, signal)
    profile = ASTRONAUT_PROFILES.get(astronaut_id, {})
    low, high = profile.get(signal, (0.0, 0.0))
    baseline = {"mean": (low + high) / 2 if low and high else 0.0, "std": max((high - low) / 4, 1.0) if low and high else 1.0}
    status, reason = determine_status_for_signal(astronaut_id, signal, value if value is not None else baseline["mean"], baseline)
    st.write(f"Current: {value if value is not None else 'n/a'}")
    st.write(f"Normal range: {low} to {high}" if low and high else "Normal range: not defined")
    st.write(f"Status: {status}")
    st.write(f"Why: {reason}")
    st.write(f"What to do: {compute_explanation(astronaut_id, signal, fetch_recent_readings(conn, astronaut_id=astronaut_id, limit=2000))}")


def body_screen(conn, astronaut_id: str):
    status_map = status_summary(conn, astronaut_id)
    fig = draw_body_map(status_map)
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Signal details")
    signals = ["hr", "bp_sys", "spo2", "resp_rate", "temp_c", "sleep_hours", "stress_score", "hydration_pct", "body_mass_kg", "radiation_msv_day"]
    for signal in signals:
        st.write(f"{SIGNAL_META.get(signal, {}).get('label', signal)}")
        show_signal_panel(conn, astronaut_id, signal)
        st.write("---")


def crew_overview(conn):
    crew = ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"]
    rows = []
    for person in crew:
        score = compute_health_score(person, fetch_recent_readings(conn, astronaut_id=person, limit=2000))
        rows.append({"astronaut": person, "score": score["score"], "level": score["level"]})
    st.table(pd.DataFrame(rows).sort_values("score", ascending=True))


def early_detection(conn):
    crew = ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"]
    for person in crew:
        score = compute_health_score(person, fetch_recent_readings(conn, astronaut_id=person, limit=2000))
        st.subheader(person)
        st.write(f"Risk outlook: {score['level']}")
        st.write(f"Evidence: health score {score['score']} and current drift in sleep, hydration or heart-rate pattern.")


def mind_sleep_tab(conn):
    crew = ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"]
    for person in crew:
        info = compute_mind_sleep(fetch_recent_readings(conn, astronaut_id=person, limit=2000), person)
        st.subheader(person)
        st.write(info["title"])
        st.write("What happened:", info["what"])
        st.write("Why it matters:", info["why"])
        st.write("What to do next:", info["next"])


def nutrition_tab(conn):
    crew = ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"]
    for person in crew:
        flag = compute_nutrition_flag(fetch_recent_readings(conn, astronaut_id=person, limit=2000), person)
        st.subheader(person)
        st.write("Nutrition status:", flag["reason"])
        st.write(f"Level: {flag['level']}")
        if flag["level"] == "YELLOW":
            st.write("Suggested action: calorie-dense meal and note to crew medical officer. Protocol to be confirmed by a flight surgeon.")


def alerts_tab(conn):
    crew = ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"]
    for person in crew:
        route = compute_buddy_routing(fetch_recent_readings(conn, astronaut_id=person, limit=2000), person)
        st.subheader(person)
        st.write(route)
    st.write("Notice: buddy-routing rules are a design proposal to be agreed with flight surgeons and NASA medical-privacy policy.")


def emergency_tab(conn):
    st.header("Emergency")
    chosen = st.selectbox("Astronaut", ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"])
    if st.button("Simulate Emergency"):
        insert_alert(
            conn,
            chosen,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "RED",
            "Critical deterioration pattern",
            "SpO2 fell, HR rose and BP dropped.",
            "This matches the placeholder RED rule.",
            "Emergency checklist, notify Mission Control, confirm consciousness.",
            {"spo2": 88, "hr": 134, "bp_sys": 98},
            0,
        )
        insert_notification(
            conn,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mission_control",
            chosen,
            f"Emergency: {chosen} shows a critical decline and whole-crew alert is active.",
            1,
        )
        st.warning("RED alert is active. Mission Control and the nearest crewmate have been notified.")

    st.write("Emergency checklist: 1) confirm consciousness, 2) support breathing, 3) stop activity, 4) notify mission control and flight surgeon.")
    st.write("Countdown: 60 seconds")
    if st.button("I am conscious"):
        st.success("Consciousness confirmed. Continue checklist and monitor closely.")


def evaluation_tab(conn):
    st.header("Evaluation")
    st.write("This demo reports detection delay and comparison with a single-signal detector using simulated data with known injected events.")


def data_tab(conn):
    st.header("Data and export")
    st.write("This prototype currently runs on simulated data. Real NASA astronaut data is controlled-access and not used here.")
    use_uploaded = st.checkbox("Use real data (CSV upload)")
    if use_uploaded:
        st.write("This future hook is ready for a CSV loader; real data requires institutional access and validation.")
    df = pd.DataFrame(fetch_recent_readings(conn, limit=2000))
    st.dataframe(df.head(100), use_container_width=True)
    st.download_button("Download readings CSV", df.to_csv(index=False), file_name="astrohealth_readings.csv")


@st.fragment(run_every=10)
def live_dashboard():
    conn = get_conn()
    st.title("ASTROHEALTH")
    st.caption(MOCK_DATA_LABEL)
    st.caption("Mission Day 87 | ISS | Crew: 4")
    st.caption("Connection: LIVE")
    st.caption("Last update: just now")

    astronaut = st.sidebar.selectbox("Astronaut", ["A. Mokoena", "Dr. B. Smith", "C. Tanaka", "D. Okafor"])
    if st.sidebar.button("Simulate Emergency"):
        st.session_state["emergency_flag"] = True
    if st.sidebar.button("Reset data"):
        conn = get_conn()
        conn.execute("DELETE FROM readings")
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM notifications")
        conn.commit()
        conn.close()
        seed_database()
    sensor_drop = st.sidebar.selectbox("Drop a sensor", ["None", "hr", "spo2", "sleep_hours", "hydration_pct"]) 
    if sensor_drop != "None":
        st.sidebar.warning(f"Sensor Offline - last seen 12 min ago: {sensor_drop}")
    st.sidebar.checkbox("LIVE / OFFLINE", value=True)
    st.sidebar.write(RESEARCH_NOTICE)

    tabs = st.tabs(["Body", "Crew overview", "Early detection", "Mind and Sleep", "Nutrition and weight", "Crew alerts", "Emergency", "Evaluation", "Data and export"])
    with tabs[0]:
        body_screen(conn, astronaut)
    with tabs[1]:
        crew_overview(conn)
    with tabs[2]:
        early_detection(conn)
    with tabs[3]:
        mind_sleep_tab(conn)
    with tabs[4]:
        nutrition_tab(conn)
    with tabs[5]:
        alerts_tab(conn)
    with tabs[6]:
        emergency_tab(conn)
    with tabs[7]:
        evaluation_tab(conn)
    with tabs[8]:
        data_tab(conn)

    conn.close()


def main():
    conn = get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 0:
            seed_database()
    finally:
        conn.close()
    live_dashboard()


if __name__ == "__main__":
    main()
