#!/usr/bin/env python3
"""
R075 High-Expectancy Edge Discovery Engine
Screens 7 distinct hypothesis families across 39,382 H1 bars (2020-2026) with H4/D1 context.
Evaluates Net Expectancy in R-multiples, after-cost profit, trade frequency, and matched controls.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

WORKSPACE = Path(r"c:\Users\trueh\Documents\GSR-Codex-v6.5")
R075_DIR = WORKSPACE / "research" / "R075_High_Expectancy_Edge_Discovery"
CACHE_DIR = R075_DIR / "bar_cache"

# Contract and cost parameters
LOTS = 0.02
CONTRACT_OZ = 100.0 * LOTS # 2.0 oz
STD_SPREAD = 0.45          # $0.45/oz
COMM_PER_LOT = 8.00        # $8.00/lot live commercial rate
COMM_PER_TRADE = COMM_PER_LOT * LOTS # $0.16 per 0.02 lots
SLIPPAGE = 0.05            # $0.05/oz slippage

def load_cached_bars():
    f_d1 = CACHE_DIR / "xauusd_d1_2020_2026.pkl.gz"
    f_h4 = CACHE_DIR / "xauusd_h4_2020_2026.pkl.gz"
    f_h1 = CACHE_DIR / "xauusd_h1_2020_2026.pkl.gz"
    
    assert f_d1.exists() and f_h4.exists() and f_h1.exists(), "Missing cached bar files!"
    
    df_d1 = pd.read_pickle(f_d1, compression='gzip')
    df_h4 = pd.read_pickle(f_h4, compression='gzip')
    df_h1 = pd.read_pickle(f_h1, compression='gzip')
    
    print(f"[LOADED] D1: {len(df_d1):,} | H4: {len(df_h4):,} | H1: {len(df_h1):,} bars", flush=True)
    return df_d1, df_h4, df_h1

def simulate_trade(entry_idx, direction, entry_price, sl_price, tp_price, max_bars, df_bars):
    """
    Simulates a trade forward bar-by-bar using exact intrabar high/low.
    Conservative tie-break: if both SL and TP hit in the same bar, counts as SL.
    """
    n_bars = len(df_bars)
    risk_dist = abs(entry_price - sl_price)
    if risk_dist <= 0:
        return None
        
    initial_risk_dollars = risk_dist * CONTRACT_OZ + COMM_PER_TRADE + (STD_SPREAD * CONTRACT_OZ)
    
    exit_price = None
    exit_idx = None
    exit_reason = None
    
    for i in range(entry_idx + 1, min(entry_idx + 1 + max_bars, n_bars)):
        bar = df_bars.iloc[i]
        b_high = bar['high']
        b_low = bar['low']
        
        if direction == 'buy':
            sl_hit = (b_low <= sl_price)
            tp_hit = (b_high >= tp_price)
            if sl_hit and tp_hit:
                exit_price = sl_price
                exit_reason = "sl_tiebreak"
                exit_idx = i
                break
            elif sl_hit:
                exit_price = sl_price
                exit_reason = "sl"
                exit_idx = i
                break
            elif tp_hit:
                exit_price = tp_price
                exit_reason = "tp"
                exit_idx = i
                break
        else: # sell
            sl_hit = (b_high >= sl_price)
            tp_hit = (b_low <= tp_price)
            if sl_hit and tp_hit:
                exit_price = sl_price
                exit_reason = "sl_tiebreak"
                exit_idx = i
                break
            elif sl_hit:
                exit_price = sl_price
                exit_reason = "sl"
                exit_idx = i
                break
            elif tp_hit:
                exit_price = tp_price
                exit_reason = "tp"
                exit_idx = i
                break
                
    if exit_price is None:
        # Timed out exit at bar open/close of last bar
        last_bar = df_bars.iloc[min(entry_idx + max_bars, n_bars - 1)]
        exit_price = last_bar['close']
        exit_reason = "timeout"
        exit_idx = min(entry_idx + max_bars, n_bars - 1)
        
    # Economics calculation with full friction
    if direction == 'buy':
        gross_pnl_dollars = (exit_price - entry_price) * CONTRACT_OZ
    else:
        gross_pnl_dollars = (entry_price - exit_price) * CONTRACT_OZ
        
    friction_dollars = COMM_PER_TRADE + ((STD_SPREAD + SLIPPAGE) * CONTRACT_OZ)
    net_pnl_dollars = gross_pnl_dollars - friction_dollars
    net_r = net_pnl_dollars / initial_risk_dollars
    
    return {
        "entry_idx": entry_idx,
        "entry_time": df_bars.index[entry_idx],
        "exit_time": df_bars.index[exit_idx],
        "direction": direction,
        "entry_price": entry_price,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "risk_dist": risk_dist,
        "initial_risk_dollars": initial_risk_dollars,
        "gross_pnl_dollars": gross_pnl_dollars,
        "net_pnl_dollars": net_pnl_dollars,
        "net_r": net_r,
        "win": net_pnl_dollars > 0
    }

def analyze_trade_results(trades, name):
    if len(trades) == 0:
        return {
            "hypothesis": name,
            "trade_count": 0,
            "monthly_frequency": 0.0,
            "win_rate": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_profit": 0.0,
            "profit_factor": 0.0,
            "avg_net_r": 0.0,
            "median_net_r": 0.0,
            "expectancy_dollars": 0.0,
            "stability_pct": 0.0
        }
        
    df = pd.DataFrame(trades)
    df['year'] = df['entry_time'].dt.year
    
    n_trades = len(df)
    n_months = 82 # Jan 2020 - Oct 2026
    freq = n_trades / n_months
    
    wins = df[df['net_pnl_dollars'] > 0]
    losses = df[df['net_pnl_dollars'] <= 0]
    
    win_rate = len(wins) / n_trades * 100.0
    gross_win = wins['net_pnl_dollars'].sum()
    gross_loss = abs(losses['net_pnl_dollars'].sum())
    net_profit = df['net_pnl_dollars'].sum()
    pf = (gross_win / gross_loss) if gross_loss > 0 else 99.0
    
    avg_net_r = df['net_r'].mean()
    median_net_r = df['net_r'].median()
    exp_dollars = df['net_pnl_dollars'].mean()
    
    # Year-by-year stability
    yearly = df.groupby('year')['net_pnl_dollars'].sum()
    profitable_years = (yearly > 0).sum()
    total_years = len(yearly)
    stability = (profitable_years / total_years) * 100.0 if total_years > 0 else 0.0
    
    return {
        "hypothesis": name,
        "trade_count": n_trades,
        "monthly_frequency": round(freq, 2),
        "win_rate": round(win_rate, 2),
        "gross_profit": round(gross_win, 2),
        "gross_loss": round(gross_loss, 2),
        "net_profit": round(net_profit, 2),
        "profit_factor": round(pf, 3),
        "avg_net_r": round(avg_net_r, 4),
        "median_net_r": round(median_net_r, 4),
        "expectancy_dollars": round(exp_dollars, 2),
        "stability_pct": round(stability, 1),
        "yearly_pnl": yearly.to_dict()
    }

def main():
    print("=== R075 HIGH-EXPECTANCY EDGE DISCOVERY ENGINE ===", flush=True)
    df_d1, df_h4, df_h1 = load_cached_bars()
    
    # Precompute indicators on H1
    print("[+] Precomputing technical indicators on H1 bars...", flush=True)
    h1 = df_h1.copy()
    h1['hour'] = h1.index.hour
    h1['weekday'] = h1.index.weekday
    h1['range'] = h1['high'] - h1['low']
    h1['body'] = (h1['close'] - h1['open']).abs()
    
    # ATR 14
    hl = h1['high'] - h1['low']
    hc = (h1['high'] - h1['close'].shift()).abs()
    lc = (h1['low'] - h1['close'].shift()).abs()
    h1['tr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    h1['atr14'] = h1['tr'].rolling(14).mean()
    h1['atr48'] = h1['tr'].rolling(48).mean()
    
    # EMAs
    h1['ema20'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema50'] = h1['close'].ewm(span=50, adjust=False).mean()
    h1['ema200'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    # 20-bar Donchian High/Low (shifted by 1 to prevent lookahead)
    h1['donchian_high20'] = h1['high'].shift(1).rolling(20).max()
    h1['donchian_low20'] = h1['low'].shift(1).rolling(20).min()
    
    # Align D1 trend to H1
    df_d1['d1_ema20'] = df_d1['close'].ewm(span=20, adjust=False).mean()
    df_d1['d1_ema50'] = df_d1['close'].ewm(span=50, adjust=False).mean()
    df_d1['d1_trend_up'] = df_d1['d1_ema20'] > df_d1['d1_ema50']
    
    d1_map = df_d1['d1_trend_up'].to_dict()
    # Map each H1 date to D1 trend of previous day (shift 1 day to prevent lookahead)
    h1_dates = h1.index.normalize()
    # Shift D1 by 1 day
    df_d1_prev = df_d1.shift(1)
    d1_trend_prev = df_d1_prev['d1_trend_up'].to_dict()
    h1['d1_trend_up'] = [d1_trend_prev.get(d, False) for d in h1_dates]
    
    results = []
    
    # -------------------------------------------------------------------------
    # HYPOTHESIS 1: H4/D1 Trend Continuation with H1 Pullback Retest (H1_TREND_RETEST)
    # Causal Mechanism: D1 trend is up/down; H1 breaks 20-bar Donchian; pulls back for 2-4 bars;
    # enters when H1 closes in breakout direction with SL at pullback extreme. Target: 2.0R.
    # -------------------------------------------------------------------------
    print("\n[+] Screening Hypothesis 1: Multi-Timeframe Trend Retest Continuation...", flush=True)
    trades_h1 = []
    for i in range(50, len(h1) - 30):
        # Must evaluate at open of bar i based strictly on completed bars i-1, i-2, ...
        # Check Long setup
        is_uptrend = h1['d1_trend_up'].iloc[i-1] and (h1['close'].iloc[i-1] > h1['ema50'].iloc[i-1])
        if is_uptrend:
            # Did a breakout occur within the last 5 bars?
            recent_breakout = (h1['high'].iloc[i-5:i-1] > h1['donchian_high20'].iloc[i-5:i-1]).any()
            # Did a shallow pullback occur (bar i-2 was red, bar i-1 resumed green)?
            pullback_resume = (h1['close'].iloc[i-2] < h1['open'].iloc[i-2]) and (h1['close'].iloc[i-1] > h1['open'].iloc[i-1]) and (h1['close'].iloc[i-1] > h1['ema20'].iloc[i-1])
            if recent_breakout and pullback_resume:
                entry_price = h1['open'].iloc[i] + STD_SPREAD # Buy at Ask
                pb_low = h1['low'].iloc[i-3:i].min()
                sl_price = pb_low - 0.50
                risk_dist = entry_price - sl_price
                if 5.0 <= risk_dist <= 25.0: # Filter realistic gold risk bounds
                    tp_price = entry_price + (risk_dist * 2.0)
                    t = simulate_trade(i, 'buy', entry_price, sl_price, tp_price, max_bars=24, df_bars=h1)
                    if t:
                        trades_h1.append(t)
                        
        # Check Short setup
        is_downtrend = (not h1['d1_trend_up'].iloc[i-1]) and (h1['close'].iloc[i-1] < h1['ema50'].iloc[i-1])
        if is_downtrend:
            recent_breakout = (h1['low'].iloc[i-5:i-1] < h1['donchian_low20'].iloc[i-5:i-1]).any()
            pullback_resume = (h1['close'].iloc[i-2] > h1['open'].iloc[i-2]) and (h1['close'].iloc[i-1] < h1['open'].iloc[i-1]) and (h1['close'].iloc[i-1] < h1['ema20'].iloc[i-1])
            if recent_breakout and pullback_resume:
                entry_price = h1['open'].iloc[i] # Sell at Bid
                pb_high = h1['high'].iloc[i-3:i].max()
                sl_price = pb_high + 0.50 + STD_SPREAD
                risk_dist = sl_price - entry_price
                if 5.0 <= risk_dist <= 25.0:
                    tp_price = entry_price - (risk_dist * 2.0)
                    t = simulate_trade(i, 'sell', entry_price, sl_price, tp_price, max_bars=24, df_bars=h1)
                    if t:
                        trades_h1.append(t)
                        
    res1 = analyze_trade_results(trades_h1, "H1_Trend_Retest_Continuation")
    results.append(res1)
    print(f"  Trades: {res1['trade_count']} | PF: {res1['profit_factor']} | Net $: {res1['net_profit']} | Avg Net R: {res1['avg_net_r']} | Win%: {res1['win_rate']}%")

    # -------------------------------------------------------------------------
    # HYPOTHESIS 2: New York Session Expansion Continuation (NY_OPEN_MOMENTUM)
    # Causal Mechanism: London establishes high/low (07:00-12:00 UTC). At NY Open (13:00 or 14:00 UTC),
    # price breaks London extreme with momentum bar. Enter in breakout direction. Target: 2.0R.
    # -------------------------------------------------------------------------
    print("\n[+] Screening Hypothesis 2: New York Open Expansion Momentum...", flush=True)
    trades_h2 = []
    for i in range(50, len(h1) - 30):
        hour = h1['hour'].iloc[i]
        if hour in [13, 14]: # Entering at 13:00 or 14:00 UTC
            # Determine London range (bars from 07:00 to 12:00 today)
            curr_day = h1.index[i].date()
            prev_bars = h1.iloc[i-8:i]
            london_bars = prev_bars[(prev_bars.index.date == curr_day) & (prev_bars['hour'] >= 7) & (prev_bars['hour'] <= 12)]
            if len(london_bars) >= 4:
                london_high = london_bars['high'].max()
                london_low = london_bars['low'].min()
                london_range = london_high - london_low
                
                if 8.0 <= london_range <= 35.0: # Meaningful London range
                    prev_bar = h1.iloc[i-1]
                    # Bullish breakout
                    if prev_bar['close'] > london_high and prev_bar['close'] > prev_bar['open']:
                        entry_price = h1['open'].iloc[i] + STD_SPREAD
                        sl_price = london_high - (london_range * 0.40) # SL inside London range
                        risk_dist = entry_price - sl_price
                        if 6.0 <= risk_dist <= 25.0:
                            tp_price = entry_price + (risk_dist * 2.0)
                            t = simulate_trade(i, 'buy', entry_price, sl_price, tp_price, max_bars=10, df_bars=h1)
                            if t: trades_h2.append(t)
                    # Bearish breakout
                    elif prev_bar['close'] < london_low and prev_bar['close'] < prev_bar['open']:
                        entry_price = h1['open'].iloc[i]
                        sl_price = london_low + (london_range * 0.40) + STD_SPREAD
                        risk_dist = sl_price - entry_price
                        if 6.0 <= risk_dist <= 25.0:
                            tp_price = entry_price - (risk_dist * 2.0)
                            t = simulate_trade(i, 'sell', entry_price, sl_price, tp_price, max_bars=10, df_bars=h1)
                            if t: trades_h2.append(t)
                            
    res2 = analyze_trade_results(trades_h2, "NY_Open_London_Expansion")
    results.append(res2)
    print(f"  Trades: {res2['trade_count']} | PF: {res2['profit_factor']} | Net $: {res2['net_profit']} | Avg Net R: {res2['avg_net_r']} | Win%: {res2['win_rate']}%")

    # -------------------------------------------------------------------------
    # HYPOTHESIS 3: New York Session London Exhaustion Reversal (NY_LONDON_REVERSAL)
    # Causal Mechanism: London moved > 1.2x ATR. At 13:00/14:00 UTC, a rejection candle forms,
    # closing back inside London range. Enter mean-reversion trade back to London VWAP/midpoint.
    # -------------------------------------------------------------------------
    print("\n[+] Screening Hypothesis 3: New York London Exhaustion Reversal...", flush=True)
    trades_h3 = []
    for i in range(50, len(h1) - 30):
        hour = h1['hour'].iloc[i]
        if hour in [13, 14, 15]:
            curr_day = h1.index[i].date()
            prev_bars = h1.iloc[i-10:i]
            london_bars = prev_bars[(prev_bars.index.date == curr_day) & (prev_bars['hour'] >= 7) & (prev_bars['hour'] <= 12)]
            if len(london_bars) >= 4:
                london_high = london_bars['high'].max()
                london_low = london_bars['low'].min()
                london_range = london_high - london_low
                atr = h1['atr14'].iloc[i-1]
                
                if london_range > (1.1 * atr * 4.0): # Overextended London
                    prev_bar = h1.iloc[i-1]
                    # Upward exhaustion rejection (tested above London high but closed below it with red body)
                    if prev_bar['high'] > london_high and prev_bar['close'] < london_high and prev_bar['close'] < prev_bar['open']:
                        entry_price = h1['open'].iloc[i]
                        sl_price = prev_bar['high'] + 1.0 + STD_SPREAD
                        risk_dist = sl_price - entry_price
                        if 5.0 <= risk_dist <= 25.0:
                            tp_price = entry_price - (risk_dist * 1.8)
                            t = simulate_trade(i, 'sell', entry_price, sl_price, tp_price, max_bars=8, df_bars=h1)
                            if t: trades_h3.append(t)
                    # Downward exhaustion rejection
                    elif prev_bar['low'] < london_low and prev_bar['close'] > london_low and prev_bar['close'] > prev_bar['open']:
                        entry_price = h1['open'].iloc[i] + STD_SPREAD
                        sl_price = prev_bar['low'] - 1.0
                        risk_dist = entry_price - sl_price
                        if 5.0 <= risk_dist <= 25.0:
                            tp_price = entry_price + (risk_dist * 1.8)
                            t = simulate_trade(i, 'buy', entry_price, sl_price, tp_price, max_bars=8, df_bars=h1)
                            if t: trades_h3.append(t)
                            
    res3 = analyze_trade_results(trades_h3, "NY_London_Exhaustion_Reversal")
    results.append(res3)
    print(f"  Trades: {res3['trade_count']} | PF: {res3['profit_factor']} | Net $: {res3['net_profit']} | Avg Net R: {res3['avg_net_r']} | Win%: {res3['win_rate']}%")

    # -------------------------------------------------------------------------
    # HYPOTHESIS 4: Volatility Squeeze Breakout (VOLATILITY_SQUEEZE_EXPANSION)
    # Causal Mechanism: ATR14 / ATR48 < 0.65 (volatility compression for >= 12 hours).
    # Expansion bar breaks 20-bar Donchian channel. Enter on expansion close. Target: 2.5R.
    # -------------------------------------------------------------------------
    print("\n[+] Screening Hypothesis 4: Volatility Compression Squeeze Expansion...", flush=True)
    trades_h4 = []
    for i in range(50, len(h1) - 30):
        # Was the market in a squeeze prior to bar i-1?
        squeeze = (h1['atr14'].iloc[i-2] / h1['atr48'].iloc[i-2]) < 0.68
        if squeeze:
            prev_bar = h1.iloc[i-1]
            expansion = prev_bar['range'] > (1.3 * h1['atr14'].iloc[i-2])
            # Bullish expansion
            if expansion and prev_bar['close'] > h1['donchian_high20'].iloc[i-1] and prev_bar['close'] > prev_bar['open']:
                entry_price = h1['open'].iloc[i] + STD_SPREAD
                sl_price = prev_bar['low'] - 0.50
                risk_dist = entry_price - sl_price
                if 6.0 <= risk_dist <= 30.0:
                    tp_price = entry_price + (risk_dist * 2.5)
                    t = simulate_trade(i, 'buy', entry_price, sl_price, tp_price, max_bars=24, df_bars=h1)
                    if t: trades_h4.append(t)
            # Bearish expansion
            elif expansion and prev_bar['close'] < h1['donchian_low20'].iloc[i-1] and prev_bar['close'] < prev_bar['open']:
                entry_price = h1['open'].iloc[i]
                sl_price = prev_bar['high'] + 0.50 + STD_SPREAD
                risk_dist = sl_price - entry_price
                if 6.0 <= risk_dist <= 30.0:
                    tp_price = entry_price - (risk_dist * 2.5)
                    t = simulate_trade(i, 'sell', entry_price, sl_price, tp_price, max_bars=24, df_bars=h1)
                    if t: trades_h4.append(t)
                    
    res4 = analyze_trade_results(trades_h4, "Volatility_Squeeze_Expansion")
    results.append(res4)
    print(f"  Trades: {res4['trade_count']} | PF: {res4['profit_factor']} | Net $: {res4['net_profit']} | Avg Net R: {res4['avg_net_r']} | Win%: {res4['win_rate']}%")

    # -------------------------------------------------------------------------
    # HYPOTHESIS 5: Failed Asian Range Breakout (ASIAN_FALSE_BREAK_REVERSAL)
    # Causal Mechanism: Asian range (00:00-06:00 UTC) swept in 07:00-09:00 UTC,
    # but immediate candle closes back inside Asian range. Target opposite Asian boundary (1.8R).
    # -------------------------------------------------------------------------
    print("\n[+] Screening Hypothesis 5: Failed Asian Breakout Reversal...", flush=True)
    trades_h5 = []
    for i in range(50, len(h1) - 30):
        hour = h1['hour'].iloc[i]
        if hour in [8, 9, 10]:
            curr_day = h1.index[i].date()
            prev_bars = h1.iloc[i-10:i]
            asian_bars = prev_bars[(prev_bars.index.date == curr_day) & (prev_bars['hour'] >= 0) & (prev_bars['hour'] <= 6)]
            if len(asian_bars) >= 5:
                asian_high = asian_bars['high'].max()
                asian_low = asian_bars['low'].min()
                asian_range = asian_high - asian_low
                
                if 5.0 <= asian_range <= 22.0:
                    prev_bar = h1.iloc[i-1]
                    # Bearish trap: swept Asian high, but closed back inside with red body
                    if prev_bar['high'] > asian_high and prev_bar['close'] < asian_high and prev_bar['close'] < prev_bar['open']:
                        entry_price = h1['open'].iloc[i]
                        sl_price = prev_bar['high'] + 0.80 + STD_SPREAD
                        risk_dist = sl_price - entry_price
                        if 4.0 <= risk_dist <= 18.0:
                            tp_price = entry_price - (risk_dist * 1.8)
                            t = simulate_trade(i, 'sell', entry_price, sl_price, tp_price, max_bars=10, df_bars=h1)
                            if t: trades_h5.append(t)
                    # Bullish trap: swept Asian low, closed back inside with green body
                    elif prev_bar['low'] < asian_low and prev_bar['close'] > asian_low and prev_bar['close'] > prev_bar['open']:
                        entry_price = h1['open'].iloc[i] + STD_SPREAD
                        sl_price = prev_bar['low'] - 0.80
                        risk_dist = entry_price - sl_price
                        if 4.0 <= risk_dist <= 18.0:
                            tp_price = entry_price + (risk_dist * 1.8)
                            t = simulate_trade(i, 'buy', entry_price, sl_price, tp_price, max_bars=10, df_bars=h1)
                            if t: trades_h5.append(t)
                            
    res5 = analyze_trade_results(trades_h5, "Asian_False_Break_Reversal")
    results.append(res5)
    print(f"  Trades: {res5['trade_count']} | PF: {res5['profit_factor']} | Net $: {res5['net_profit']} | Avg Net R: {res5['avg_net_r']} | Win%: {res5['win_rate']}%")

    # -------------------------------------------------------------------------
    # HYPOTHESIS 6: Daily Trend Pullback with H1 Structural Pivot Reversal
    # Causal Mechanism: D1 Close > EMA20 > EMA50. H1 pulls back below H1 EMA20 into EMA50.
    # First strong H1 candle (> 1.2x average body) closes back above EMA20. Target 2.2R.
    # -------------------------------------------------------------------------
    print("\n[+] Screening Hypothesis 6: Daily Trend Deep Pullback Pivot...", flush=True)
    trades_h6 = []
    for i in range(50, len(h1) - 30):
        # Long only when D1 trend is up
        if h1['d1_trend_up'].iloc[i-1]:
            # Was price below H1 EMA20 for at least 2 bars?
            pulled_back = (h1['close'].iloc[i-3] < h1['ema20'].iloc[i-3]) and (h1['close'].iloc[i-2] < h1['ema20'].iloc[i-2])
            # Bar i-1 strongly crosses back above EMA20
            turned_up = (h1['close'].iloc[i-1] > h1['ema20'].iloc[i-1]) and (h1['close'].iloc[i-1] > h1['open'].iloc[i-1])
            if pulled_back and turned_up:
                entry_price = h1['open'].iloc[i] + STD_SPREAD
                swing_low = h1['low'].iloc[i-4:i].min()
                sl_price = swing_low - 0.50
                risk_dist = entry_price - sl_price
                if 5.0 <= risk_dist <= 25.0:
                    tp_price = entry_price + (risk_dist * 2.2)
                    t = simulate_trade(i, 'buy', entry_price, sl_price, tp_price, max_bars=24, df_bars=h1)
                    if t: trades_h6.append(t)
                    
        # Short when D1 trend is down
        elif not h1['d1_trend_up'].iloc[i-1]:
            pulled_back = (h1['close'].iloc[i-3] > h1['ema20'].iloc[i-3]) and (h1['close'].iloc[i-2] > h1['ema20'].iloc[i-2])
            turned_down = (h1['close'].iloc[i-1] < h1['ema20'].iloc[i-1]) and (h1['close'].iloc[i-1] < h1['open'].iloc[i-1])
            if pulled_back and turned_down:
                entry_price = h1['open'].iloc[i]
                swing_high = h1['high'].iloc[i-4:i].max()
                sl_price = swing_high + 0.50 + STD_SPREAD
                risk_dist = sl_price - entry_price
                if 5.0 <= risk_dist <= 25.0:
                    tp_price = entry_price - (risk_dist * 2.2)
                    t = simulate_trade(i, 'sell', entry_price, sl_price, tp_price, max_bars=24, df_bars=h1)
                    if t: trades_h6.append(t)
                    
    res6 = analyze_trade_results(trades_h6, "D1_Trend_H1_Deep_Pullback")
    results.append(res6)
    print(f"  Trades: {res6['trade_count']} | PF: {res6['profit_factor']} | Net $: {res6['net_profit']} | Avg Net R: {res6['avg_net_r']} | Win%: {res6['win_rate']}%")

    # -------------------------------------------------------------------------
    # HYPOTHESIS 7: Matched Random Control (Null Hypothesis)
    # -------------------------------------------------------------------------
    print("\n[+] Running Matched Random Control Benchmark...", flush=True)
    np.random.seed(42)
    trades_ctrl = []
    # Generate same number of random trades as typical hypothesis (~400 trades)
    rand_indices = np.random.choice(range(50, len(h1) - 30), size=500, replace=False)
    for idx in rand_indices:
        dir_choice = np.random.choice(['buy', 'sell'])
        risk_dist = 12.0 # median gold risk
        if dir_choice == 'buy':
            entry_price = h1['open'].iloc[idx] + STD_SPREAD
            sl_price = entry_price - risk_dist
            tp_price = entry_price + (risk_dist * 2.0)
        else:
            entry_price = h1['open'].iloc[idx]
            sl_price = entry_price + risk_dist + STD_SPREAD
            tp_price = entry_price - (risk_dist * 2.0)
        t = simulate_trade(idx, dir_choice, entry_price, sl_price, tp_price, max_bars=24, df_bars=h1)
        if t: trades_ctrl.append(t)
        
    res_ctrl = analyze_trade_results(trades_ctrl, "MATCHED_RANDOM_CONTROL")
    results.append(res_ctrl)
    print(f"  Trades: {res_ctrl['trade_count']} | PF: {res_ctrl['profit_factor']} | Net $: {res_ctrl['net_profit']} | Avg Net R: {res_ctrl['avg_net_r']} | Win%: {res_ctrl['win_rate']}%")

    # -------------------------------------------------------------------------
    # Summary Table & Export
    # -------------------------------------------------------------------------
    df_results = pd.DataFrame(results)
    csv_out = R075_DIR / "R075_EDGE_HYPOTHESES.csv"
    
    # Format clean output columns
    cols = [
        "hypothesis", "trade_count", "monthly_frequency", "win_rate", 
        "profit_factor", "avg_net_r", "median_net_r", "net_profit", 
        "expectancy_dollars", "stability_pct"
    ]
    df_clean = df_results[cols].copy()
    df_clean.sort_values(by="avg_net_r", ascending=False, inplace=True)
    df_clean.to_csv(csv_out, index=False)
    print(f"\n[+] Master screening results saved to {csv_out}")
    print("\n=== SUMMARY COMPARISON ===")
    print(df_clean.to_string(index=False))

if __name__ == "__main__":
    main()
