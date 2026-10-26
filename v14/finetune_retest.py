#!/usr/bin/env python3
"""
R075 Fine-Tuning of London-to-NY Retest Strategy & Correlation Analysis with v13.A / v13.B
Tests:
1. Target R variations: 1.5R, 1.8R, 2.0R, 2.2R, 2.5R
2. H4 trend filter impact
3. Correlation with v13.A and v13.B trades
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

WORKSPACE = Path(r"c:\Users\trueh\Documents\GSR-Codex-v6.5")
R075_DIR = WORKSPACE / "research" / "R075_High_Expectancy_Edge_Discovery"
CACHE_DIR = R075_DIR / "bar_cache"
M4_DIR = WORKSPACE / "research" / "R074_Profitability_Breakthrough" / "04_INDEPENDENT_MT5_VALIDATION"

LOTS = 0.02
CONTRACT_OZ = 2.0
STD_SPREAD = 0.45
COMM_PER_TRADE = 0.16
SLIPPAGE = 0.05

def load_data():
    df_h4 = pd.read_pickle(CACHE_DIR / "xauusd_h4_2020_2026.pkl.gz", compression='gzip')
    df_h1 = pd.read_pickle(CACHE_DIR / "xauusd_h1_2020_2026.pkl.gz", compression='gzip')
    return df_h4, df_h1

def simulate(h1, target_r=2.0, use_h4=False, max_bars=12):
    trades = []
    n_bars = len(h1)
    
    for i in range(50, n_bars - 30):
        if h1['hour'].iloc[i] == 13: # 13:00 UTC
            curr_day = h1.index[i].date()
            prev_bars = h1.iloc[i-7:i]
            london = prev_bars[(prev_bars.index.date == curr_day) & (prev_bars['hour'] >= 7) & (prev_bars['hour'] <= 11)]
            
            if len(london) >= 4:
                l_high = london['high'].max()
                l_low = london['low'].min()
                l_range = l_high - l_low
                l_mid = (l_high + l_low) / 2.0
                
                if 8.0 <= l_range <= 32.0:
                    l_close = london['close'].iloc[-1]
                    bar_12 = h1.iloc[i-1] # 12:00 bar
                    
                    # Bullish London trend (closed in top 35% of range)
                    if l_close > (l_low + 0.65 * l_range):
                        if (bar_12['low'] <= l_mid + 2.5) and (bar_12['close'] > l_mid):
                            if use_h4 and not h1['h4_up'].iloc[i-1]:
                                continue
                            entry = h1['open'].iloc[i] + STD_SPREAD
                            sl = l_low - 0.50
                            risk = entry - sl
                            if 6.0 <= risk <= 25.0:
                                tp = entry + (risk * target_r)
                                t = run_trade(i, 'buy', entry, sl, tp, max_bars, h1)
                                if t: trades.append(t)
                                
                    # Bearish London trend (closed in bottom 35% of range)
                    elif l_close < (l_low + 0.35 * l_range):
                        if (bar_12['high'] >= l_mid - 2.5) and (bar_12['close'] < l_mid):
                            if use_h4 and h1['h4_up'].iloc[i-1]:
                                continue
                            entry = h1['open'].iloc[i]
                            sl = l_high + 0.50 + STD_SPREAD
                            risk = sl - entry
                            if 6.0 <= risk <= 25.0:
                                tp = entry - (risk * target_r)
                                t = run_trade(i, 'sell', entry, sl, tp, max_bars, h1)
                                if t: trades.append(t)
                                
    return trades

def run_trade(entry_idx, direction, entry, sl, tp, max_bars, h1):
    risk_dist = abs(entry - sl)
    init_risk_dlr = risk_dist * CONTRACT_OZ + COMM_PER_TRADE + (STD_SPREAD * CONTRACT_OZ)
    n_bars = len(h1)
    
    exit_p = None
    exit_i = None
    exit_r = None
    
    for i in range(entry_idx + 1, min(entry_idx + 1 + max_bars, n_bars)):
        bar = h1.iloc[i]
        bh = bar['high']
        bl = bar['low']
        
        if direction == 'buy':
            if bl <= sl and bh >= tp:
                exit_p = sl; exit_r = "sl_tiebreak"; exit_i = i; break
            elif bl <= sl:
                exit_p = sl; exit_r = "sl"; exit_i = i; break
            elif bh >= tp:
                exit_p = tp; exit_r = "tp"; exit_i = i; break
        else:
            if bh >= sl and bl <= tp:
                exit_p = sl; exit_r = "sl_tiebreak"; exit_i = i; break
            elif bh >= sl:
                exit_p = sl; exit_r = "sl"; exit_i = i; break
            elif bl <= tp:
                exit_p = tp; exit_r = "tp"; exit_i = i; break
                
    if exit_p is None:
        last = h1.iloc[min(entry_idx + max_bars, n_bars - 1)]
        exit_p = last['close']
        exit_r = "timeout"
        exit_i = min(entry_idx + max_bars, n_bars - 1)
        
    gross = (exit_p - entry) * CONTRACT_OZ if direction == 'buy' else (entry - exit_p) * CONTRACT_OZ
    fric = COMM_PER_TRADE + ((STD_SPREAD + SLIPPAGE) * CONTRACT_OZ)
    net = gross - fric
    net_r = net / init_risk_dlr
    
    return {
        "entry_idx": entry_idx,
        "entry_time": h1.index[entry_idx],
        "exit_time": h1.index[exit_i],
        "direction": direction,
        "entry_price": entry,
        "sl_price": sl,
        "tp_price": tp,
        "exit_price": exit_p,
        "exit_reason": exit_r,
        "risk_dist": risk_dist,
        "initial_risk_dollars": init_risk_dlr,
        "gross_pnl_dollars": gross,
        "net_pnl_dollars": net,
        "net_r": net_r,
        "win": net > 0
    }

def summarize(trades, label):
    if not trades:
        print(f"{label}: No trades")
        return None
    df = pd.DataFrame(trades)
    df['year'] = df['entry_time'].dt.year
    n = len(df)
    net = df['net_pnl_dollars'].sum()
    wins = df[df['net_pnl_dollars'] > 0]
    losses = df[df['net_pnl_dollars'] <= 0]
    pf = wins['net_pnl_dollars'].sum() / abs(losses['net_pnl_dollars'].sum())
    avg_r = df['net_r'].mean()
    win_pct = len(wins) / n * 100.0
    yearly = df.groupby('year')['net_pnl_dollars'].sum()
    pos_years = (yearly > 0).sum()
    
    print(f"\n{label}")
    print(f"  Trades: {n} ({n/82:.2f}/mo) | Win: {win_pct:.1f}% | PF: {pf:.3f} | Net: ${net:.2f} | Avg Net R: {avg_r:+.4f}R | Exp: ${net/n:.2f}/trade | Pos Yrs: {pos_years}/7")
    print(f"  Yearly: {yearly.round(2).to_dict()}")
    return df

def main():
    df_h4, df_h1 = load_data()
    h1 = df_h1.copy()
    h1['hour'] = h1.index.hour
    
    # H4 EMAs
    df_h4['h4_ema20'] = df_h4['close'].ewm(span=20, adjust=False).mean()
    df_h4['h4_ema50'] = df_h4['close'].ewm(span=50, adjust=False).mean()
    df_h4['h4_up'] = df_h4['h4_ema20'] > df_h4['h4_ema50']
    
    h4_prev = df_h4.shift(1)
    h1 = pd.merge_asof(h1, h4_prev[['h4_up']], left_index=True, right_index=True)
    
    # Target R sweep
    for tr in [1.5, 1.8, 2.0, 2.2, 2.5]:
        t = simulate(h1, target_r=tr, use_h4=False)
        summarize(t, f"Target {tr}R (No H4 filter)")
        
    # With H4 trend filter
    for tr in [1.8, 2.0, 2.2]:
        t = simulate(h1, target_r=tr, use_h4=True)
        summarize(t, f"Target {tr}R (WITH H4 trend filter)")

if __name__ == "__main__":
    main()
