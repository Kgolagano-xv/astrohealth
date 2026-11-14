# data_loader.py
# Explain it simply: this module loads a CSV file into the same SQLite tables used by the dashboard.
# It lets the app switch from simulated data to uploaded data without changing the rest of the app.

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from config import MOCK_DATA_LABEL, REQUIRED_READINGS_COLUMNS
from db import connect_db, init_db


def validate_readings_frame(df: pd.DataFrame):
    missing = [c for c in REQUIRED_READINGS_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df.empty:
        raise ValueError("CSV file is empty. Nothing to import.")

    df = df.copy()
    df["astronaut_id"] = df["astronaut_id"].astype(str)
    df["signal"] = df["signal"].astype(str)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    if df["value"].isna().any():
        raise ValueError("One or more values are not numeric. Please check the CSV.")

    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    if df["ts"].isna().any():
        raise ValueError("One or more timestamps are invalid.")
    df["ts"] = df["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")

    if "source" not in df.columns:
        df["source"] = "uploaded"
    if "quality" not in df.columns:
        df["quality"] = "uploaded"
    if "sync_pending" not in df.columns:
        df["sync_pending"] = 1

    return df


def load_csv_to_db(csv_path: str | Path, db_path: Optional[str | Path] = None):
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    df = pd.read_csv(csv_file)
    df = validate_readings_frame(df)

    conn = connect_db(str(db_path) if db_path else None)
    init_db(conn)
    for _, row in df.iterrows():
        conn.execute(
            """
            INSERT INTO readings (astronaut_id, ts, signal, value, source, quality, sync_pending)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["astronaut_id"],
                row["ts"],
                row["signal"],
                float(row["value"]),
                row["source"],
                row["quality"],
                int(row["sync_pending"]),
            ),
        )
    conn.commit()
    conn.close()
    return {"rows_loaded": len(df), "notice": MOCK_DATA_LABEL}


if __name__ == "__main__":
    print("CSV adapter ready. Import this module in app.py to swap in uploaded data.")
