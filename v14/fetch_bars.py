#!/usr/bin/env python3
"""
R075 Data Extraction & Cache Utility
Connects to MT5 terminal once, pulls D1, H4, H1, M15 bars (2020-2026) for GSR_XAUUSD_HISTDATA,
and caches them locally to compressed Parquet files for fast, credit-efficient edge discovery.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import MetaTrader5 as mt5

WORKSPACE = Path(r"c:\Users\trueh\Documents\GSR-Codex-v6.5")
TERMINAL_PATH = r"C:\MT5-GSR-Research\terminal64.exe"
SYMBOL = "GSR_XAUUSD_HISTDATA"
CACHE_DIR = WORKSPACE / "research" / "R075_High_Expectancy_Edge_Discovery" / "bar_cache"

def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print("=== R075 BAR CACHE EXTRACTION ===", flush=True)
    
    if not mt5.initialize(TERMINAL_PATH):
        print(f"FAILED to initialize MT5 at {TERMINAL_PATH}: {mt5.last_error()}", flush=True)
        sys.exit(1)
    
    print("MT5 Connected successfully.", flush=True)
    
    d1 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    d2 = datetime(2026, 10, 23, 23, 59, 59, tzinfo=timezone.utc)
    
    timeframes = [
        ("D1", mt5.TIMEFRAME_D1),
        ("H4", mt5.TIMEFRAME_H4),
        ("H1", mt5.TIMEFRAME_H1),
        ("M15", mt5.TIMEFRAME_M15),
    ]
    
    for tf_name, tf_val in timeframes:
        out_file = CACHE_DIR / f"xauusd_{tf_name.lower()}_2020_2026.pkl.gz"
        if out_file.exists():
            print(f"[CACHE HIT] {out_file.name} already exists ({out_file.stat().st_size / 1024:.1f} KB). Skipping.", flush=True)
            continue
            
        print(f"Fetching {tf_name} bars from {d1.date()} to {d2.date()}...", flush=True)
        rates = mt5.copy_rates_range(SYMBOL, tf_val, d1, d2)
        if rates is None or len(rates) == 0:
            print(f"ERROR: No rates returned for {tf_name}: {mt5.last_error()}", flush=True)
            continue
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df.set_index('time', inplace=True)
        df.to_pickle(out_file, compression='gzip')
        print(f"[SAVED] {tf_name}: {len(df):,} bars -> {out_file.name} ({out_file.stat().st_size / 1024:.1f} KB)", flush=True)
        
    mt5.shutdown()
    print("MT5 Disconnected cleanly. Bar extraction complete.", flush=True)

if __name__ == "__main__":
    main()
