"""
EDA & data preparation script:
 - Generates realistic 15-min call centre data (7 days).
 - Cleans, caps AHT, interpolates missing values.
 - Saves clean dataset to data/clean_historical.csv.

Usage: python scripts/eda_generate_historical.py
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Generation parameters
INTERVALS_PER_DAY = 96  # 15-min steps
DAYS = 7
TOTAL_INTERVALS = INTERVALS_PER_DAY * DAYS

# Timestamp range starting Monday midnight
start_date = datetime(2025, 5, 5, 0, 0, 0)
timestamps = [start_date + timedelta(minutes=15 * i) for i in range(TOTAL_INTERVALS)]

# Base pattern (sinusoidal daily + weekly trend)
base_call_vol = 50 + 30 * np.sin(
    np.linspace(0, 2 * np.pi, INTERVALS_PER_DAY)
)  # shape for one day
base_call_vol = np.tile(base_call_vol, DAYS)

# Weekly factor (higher on Mon, Tue, lower on Sat, Sun)
day_of_week = np.array([ts.weekday() for ts in timestamps])
weekly_factor = np.select(
    [day_of_week < 5, day_of_week == 5, day_of_week == 6],
    [1.0, 0.7, 0.5],
)
call_volume = (base_call_vol * weekly_factor).astype(int)

# AHT (seconds) with daily peak
aht_base = 300 + 60 * np.sin(np.linspace(0, 2 * np.pi, INTERVALS_PER_DAY))
aht_base = np.tile(aht_base, DAYS)
aht_noise = np.random.normal(0, 20, TOTAL_INTERVALS)
aht_seconds = aht_base + aht_noise

# Agents present (staffing)
agents_present = (call_volume / 12).astype(int) + np.random.randint(-2, 3, TOTAL_INTERVALS)
agents_present = np.clip(agents_present, 1, None)

df = pd.DataFrame(
    {
        "interval_start": timestamps,
        "call_volume": call_volume,
        "aht_seconds": aht_seconds,
        "agents_present": agents_present,
    }
)

# Introduce some missing values (5%)
mask = np.random.random(len(df)) < 0.05
df.loc[mask, "call_volume"] = np.nan

# Cleaning steps
df["call_volume"] = df["call_volume"].interpolate(method="linear").round(0).astype(int)
df["aht_seconds"] = df["aht_seconds"].clip(upper=420)  # cap at 7 min
df["aht_seconds"] = df["aht_seconds"].fillna(method="ffill").fillna(method="bfill")
df["agents_present"] = df["agents_present"].fillna(0).astype(int)
df = df.drop_duplicates(subset="interval_start")

df.to_csv("data/clean_historical.csv", index=False)
print(f"EDA script completed. {len(df)} clean rows saved to data/clean_historical.csv")