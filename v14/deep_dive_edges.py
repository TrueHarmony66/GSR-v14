#!/usr/bin/env python3
"""
R075 Deep-Dive Edge Optimization & Discovery
Investigates 4 refined structural hypotheses to discover > 0.10R - 0.25R net expectancy:
1. H4_H1_Confluence_Retest: H4 trend + H1 retest with 1.5R to 2.5R targets
2. London_NY_Session_Retest: London establishes trend; NY open retests and continues
3. High_Momentum_Impulse_Retest: Initial impulse > 1.5x ATR14 with tight retest invalidation
4. Volatility_Breakout_with_Trailing_Swing: Dynamic ATR trailing exit to capture fat-tail runners
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

LOTS = 0.02
CONTRACT_OZ = 2.0
STD_SPREAD = 0.45
COMM_PER_TRADE = 0.16 # $8.00/lot live commercial rate
SLIPPAGE = 0.05

def load_data():
    f_d1 = CACHE_DIR / "xauusd_d1_2020_2026.pkl.gz"
    f_h4 = CACHE_DIR / "xauusd_h4_2020_2026.pkl.gz"
    f_h1 = CACHE_DIR / "xauusd_h1_2020_2026.pkl.gz"
    
    df_d1 = pd.read_pickle(f_d1, compression='gzip')
    df_h4 = pd.read_pickle(f_h4, compression='gzip')
    df_h1 = pd.read_pickle(f_h1, compression='gzip')
    return df_d1, df_h4, df_h1

def simulate_trade_advanced(entry_idx, direction, entry_price, sl_price, target_r, max_bars, df_bars, trailing=False):
    n_bars = len(df_bars)
    risk_dist = abs(entry_price - sl_price)
    if risk_dist <= 0: return None
    
    initial_risk_dollars = risk_dist * CONTRACT_OZ + COMM_PER_TRADE + (STD_SPREAD * CONTRACT_OZ)
    tp_price = entry_price + (risk_dist * target_r) if direction == 'buy' else entry_price - (risk_dist * target_r)
    
    curr_sl = sl_price
    exit_price = None
    exit_idx = None
    exit_reason = None
    
    for i in range(entry_idx + 1, min(entry_idx + 1 + max_bars, n_bars)):
        bar = df_bars.iloc[i]
        b_high = bar['high']
        b_low = bar['low']
        
        # Trailing stop logic if enabled
        if trailing and i > entry_idx + 1:
            if direction == 'buy':
                # Trail by 1.5x ATR below previous bar low
                trail_sl = bar['low'] - 1.50
                if trail_sl > curr_sl: curr_sl = trail_sl
            else:
                trail_sl = bar['high'] + 1.50 + STD_SPREAD
                if trail_sl < curr_sl: curr_sl = trail_sl
                
        if direction == 'buy':
            sl_hit = (b_low <= curr_sl)
            tp_hit = (b_high >= tp_price) if not trailing else False
            if sl_hit and tp_hit:
                exit_price = curr_sl; exit_reason = "sl_tiebreak"; exit_idx = i; break
            elif sl_hit:
                exit_price = curr_sl; exit_reason = "sl"; exit_idx = i; break
            elif tp_hit:
                exit_price = tp_price; exit_reason = "tp"; exit_idx = i; break
        else:
            sl_hit = (b_high >= curr_sl)
            tp_hit = (b_low <= tp_price) if not trailing else False
            if sl_hit and tp_hit:
                exit_price = curr_sl; exit_reason = "sl_tiebreak"; exit_idx = i; break
            elif sl_hit:
                exit_price = curr_sl; exit_reason = "sl"; exit_idx = i; break
            elif tp_hit:
                exit_price = tp_price; exit_reason = "tp"; exit_idx = i; break
                
    if exit_price is None:
        last_bar = df_bars.iloc[min(entry_idx + max_bars, n_bars - 1)]
        exit_price = last_bar['close']
        exit_reason = "timeout"
        exit_idx = min(entry_idx + max_bars, n_bars - 1)
        
    gross_pnl = (exit_price - entry_price) * CONTRACT_OZ if direction == 'buy' else (entry_price - exit_price) * CONTRACT_OZ
    friction = COMM_PER_TRADE + ((STD_SPREAD + SLIPPAGE) * CONTRACT_OZ)
    net_pnl = gross_pnl - friction
    net_r = net_pnl / initial_risk_dollars
    
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
        "gross_pnl_dollars": gross_pnl,
        "net_pnl_dollars": net_pnl,
        "net_r": net_r,
        "win": net_pnl > 0
    }

def analyze_trades(trades, name):
    if not trades: return {"name": name, "n": 0, "r": 0, "pf": 0, "net": 0, "win": 0, "freq": 0}
    df = pd.DataFrame(trades)
    df['year'] = df['entry_time'].dt.year
    n = len(df)
    freq = n / 82.0
    wins = df[df['net_pnl_dollars'] > 0]
    losses = df[df['net_pnl_dollars'] <= 0]
    gw = wins['net_pnl_dollars'].sum()
    gl = abs(losses['net_pnl_dollars'].sum())
    pf = (gw / gl) if gl > 0 else 99.0
    net = df['net_pnl_dollars'].sum()
    avg_r = df['net_r'].mean()
    win_pct = len(wins) / n * 100.0
    yearly = df.groupby('year')['net_pnl_dollars'].sum()
    pos_years = (yearly > 0).sum()
    stability = pos_years / len(yearly) * 100.0 if len(yearly) > 0 else 0
    
    print(f"\n--- {name} ---")
    print(f"  Trades: {n} ({freq:.1f}/mo) | Win%: {win_pct:.1f}% | PF: {pf:.3f} | Net: ${net:.2f}")
    print(f"  Avg Net R: {avg_r:+.4f}R | Expectancy: ${net/n:.2f}/trade | Stability: {stability:.0f}% ({pos_years}/{len(yearly)} yrs)")
    print(f"  Yearly: {yearly.to_dict()}")
    
    return {
        "hypothesis": name,
        "trade_count": n,
        "monthly_frequency": round(freq, 2),
        "win_rate": round(win_pct, 2),
        "profit_factor": round(pf, 3),
        "avg_net_r": round(avg_r, 4),
        "net_profit": round(net, 2),
        "stability_pct": round(stability, 1)
    }

def main():
    print("=== R075 DEEP-DIVE EDGE INVESTIGATION ===", flush=True)
    df_d1, df_h4, df_h1 = load_data()
    
    h1 = df_h1.copy()
    h1['hour'] = h1.index.hour
    h1['weekday'] = h1.index.weekday
    
    # ATR & EMAs
    hl = h1['high'] - h1['low']
    hc = (h1['high'] - h1['close'].shift()).abs()
    lc = (h1['low'] - h1['close'].shift()).abs()
    h1['tr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    h1['atr14'] = h1['tr'].rolling(14).mean()
    
    h1['ema20'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema50'] = h1['close'].ewm(span=50, adjust=False).mean()
    h1['ema200'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    # Shifted Donchian
    h1['dh20'] = h1['high'].shift(1).rolling(20).max()
    h1['dl20'] = h1['low'].shift(1).rolling(20).min()
    h1['dh50'] = h1['high'].shift(1).rolling(50).max()
    h1['dl50'] = h1['low'].shift(1).rolling(50).min()
    
    # Align H4 EMAs
    df_h4['h4_ema20'] = df_h4['close'].ewm(span=20, adjust=False).mean()
    df_h4['h4_ema50'] = df_h4['close'].ewm(span=50, adjust=False).mean()
    df_h4['h4_trend_up'] = df_h4['h4_ema20'] > df_h4['h4_ema50']
    
    # Map H4 trend to H1 (using previous completed H4 bar)
    h4_shifted = df_h4.shift(1)
    h1 = pd.merge_asof(h1, h4_shifted[['h4_trend_up', 'h4_ema20', 'h4_ema50']], left_index=True, right_index=True)
    
    # -------------------------------------------------------------------------
    # VARIANT A1: H4 Trend + H1 Shallow Pullback + 1.5R Target
    # -------------------------------------------------------------------------
    trades_a1 = []
    for i in range(50, len(h1) - 30):
        h4_up = h1['h4_trend_up'].iloc[i-1]
        atr = h1['atr14'].iloc[i-1]
        
        if h4_up and (h1['close'].iloc[i-1] > h1['ema200'].iloc[i-1]):
            # Strong impulse in last 4 bars (> 1.2 ATR)
            impulse = (h1['high'].iloc[i-4:i-1] - h1['low'].iloc[i-4:i-1] > 1.2 * atr).any()
            # Orderly 1-2 bar pullback that holds above EMA20
            pb_holds = (h1['low'].iloc[i-2:i] > h1['ema20'].iloc[i-2:i]).all()
            # Bar i-1 confirms with green close
            conf = (h1['close'].iloc[i-1] > h1['open'].iloc[i-1]) and (h1['close'].iloc[i-1] > h1['high'].iloc[i-2])
            
            if impulse and pb_holds and conf:
                entry = h1['open'].iloc[i] + STD_SPREAD
                sl = h1['low'].iloc[i-3:i].min() - 0.50
                risk = entry - sl
                if 5.0 <= risk <= 20.0:
                    t = simulate_trade_advanced(i, 'buy', entry, sl, target_r=1.5, max_bars=16, df_bars=h1)
                    if t: trades_a1.append(t)
                    
        elif (not h4_up) and (h1['close'].iloc[i-1] < h1['ema200'].iloc[i-1]):
            impulse = (h1['high'].iloc[i-4:i-1] - h1['low'].iloc[i-4:i-1] > 1.2 * atr).any()
            pb_holds = (h1['high'].iloc[i-2:i] < h1['ema20'].iloc[i-2:i]).all()
            conf = (h1['close'].iloc[i-1] < h1['open'].iloc[i-1]) and (h1['close'].iloc[i-1] < h1['low'].iloc[i-2])
            
            if impulse and pb_holds and conf:
                entry = h1['open'].iloc[i]
                sl = h1['high'].iloc[i-3:i].max() + 0.50 + STD_SPREAD
                risk = sl - entry
                if 5.0 <= risk <= 20.0:
                    t = simulate_trade_advanced(i, 'sell', entry, sl, target_r=1.5, max_bars=16, df_bars=h1)
                    if t: trades_a1.append(t)
                    
    analyze_trades(trades_a1, "H4_H1_Shallow_Pullback_1.5R")

    # -------------------------------------------------------------------------
    # VARIANT A2: H4 Trend + H1 Shallow Pullback + 2.0R Target
    # -------------------------------------------------------------------------
    trades_a2 = []
    for i in range(50, len(h1) - 30):
        h4_up = h1['h4_trend_up'].iloc[i-1]
        atr = h1['atr14'].iloc[i-1]
        
        if h4_up and (h1['close'].iloc[i-1] > h1['ema200'].iloc[i-1]):
            impulse = (h1['high'].iloc[i-4:i-1] - h1['low'].iloc[i-4:i-1] > 1.2 * atr).any()
            pb_holds = (h1['low'].iloc[i-2:i] > h1['ema20'].iloc[i-2:i]).all()
            conf = (h1['close'].iloc[i-1] > h1['open'].iloc[i-1]) and (h1['close'].iloc[i-1] > h1['high'].iloc[i-2])
            
            if impulse and pb_holds and conf:
                entry = h1['open'].iloc[i] + STD_SPREAD
                sl = h1['low'].iloc[i-3:i].min() - 0.50
                risk = entry - sl
                if 5.0 <= risk <= 20.0:
                    t = simulate_trade_advanced(i, 'buy', entry, sl, target_r=2.0, max_bars=24, df_bars=h1)
                    if t: trades_a2.append(t)
                    
        elif (not h4_up) and (h1['close'].iloc[i-1] < h1['ema200'].iloc[i-1]):
            impulse = (h1['high'].iloc[i-4:i-1] - h1['low'].iloc[i-4:i-1] > 1.2 * atr).any()
            pb_holds = (h1['high'].iloc[i-2:i] < h1['ema20'].iloc[i-2:i]).all()
            conf = (h1['close'].iloc[i-1] < h1['open'].iloc[i-1]) and (h1['close'].iloc[i-1] < h1['low'].iloc[i-2])
            
            if impulse and pb_holds and conf:
                entry = h1['open'].iloc[i]
                sl = h1['high'].iloc[i-3:i].max() + 0.50 + STD_SPREAD
                risk = sl - entry
                if 5.0 <= risk <= 20.0:
                    t = simulate_trade_advanced(i, 'sell', entry, sl, target_r=2.0, max_bars=24, df_bars=h1)
                    if t: trades_a2.append(t)
                    
    analyze_trades(trades_a2, "H4_H1_Shallow_Pullback_2.0R")

    # -------------------------------------------------------------------------
    # VARIANT B: London-to-New York Pre-Session Retest Continuation
    # Causal Mechanism: London establishes trend (07:00-11:00 UTC).
    # Pre-NY (11:00-12:00 UTC) pulls back to London midpoint.
    # At 13:00 UTC, H1 candle confirms resumption in London direction. Target 2.0R.
    # -------------------------------------------------------------------------
    trades_b = []
    for i in range(50, len(h1) - 30):
        if h1['hour'].iloc[i] == 13: # 13:00 UTC bar open (NY prep)
            curr_day = h1.index[i].date()
            prev_bars = h1.iloc[i-7:i]
            london = prev_bars[(prev_bars.index.date == curr_day) & (prev_bars['hour'] >= 7) & (prev_bars['hour'] <= 11)]
            if len(london) >= 4:
                l_high = london['high'].max()
                l_low = london['low'].min()
                l_range = l_high - l_low
                l_mid = (l_high + l_low) / 2.0
                
                if 8.0 <= l_range <= 30.0:
                    l_close = london['close'].iloc[-1]
                    bar_12 = h1.iloc[i-1] # 12:00 UTC bar
                    
                    # Bullish London trend (closed in top 35% of range)
                    if l_close > (l_low + 0.65 * l_range):
                        # 12:00 bar pulled back toward midpoint but closed above it
                        if (bar_12['low'] <= l_mid + 2.0) and (bar_12['close'] > l_mid):
                            entry = h1['open'].iloc[i] + STD_SPREAD
                            sl = l_low - 0.50 # Stop below London low
                            risk = entry - sl
                            if 6.0 <= risk <= 25.0:
                                t = simulate_trade_advanced(i, 'buy', entry, sl, target_r=2.0, max_bars=12, df_bars=h1)
                                if t: trades_b.append(t)
                                
                    # Bearish London trend (closed in bottom 35% of range)
                    elif l_close < (l_low + 0.35 * l_range):
                        if (bar_12['high'] >= l_mid - 2.0) and (bar_12['close'] < l_mid):
                            entry = h1['open'].iloc[i]
                            sl = l_high + 0.50 + STD_SPREAD
                            risk = sl - entry
                            if 6.0 <= risk <= 25.0:
                                t = simulate_trade_advanced(i, 'sell', entry, sl, target_r=2.0, max_bars=12, df_bars=h1)
                                if t: trades_b.append(t)
                                
    analyze_trades(trades_b, "London_NY_Midpoint_Retest_2.0R")

    # -------------------------------------------------------------------------
    # VARIANT C: High-Momentum Donchian Breakout + Retest with Structural SL (50-bar Donchian)
    # Causal Mechanism: Multi-day 50-bar Donchian breakout (institutional regime shift).
    # Retest holds broken level. Enter on breakout resumption. Target 2.5R.
    # -------------------------------------------------------------------------
    trades_c = []
    for i in range(60, len(h1) - 30):
        # Bullish 50-bar Donchian breakout within last 5 bars
        recent_breakout = (h1['high'].iloc[i-5:i-1] > h1['dh50'].iloc[i-5:i-1]).any()
        if recent_breakout and (h1['close'].iloc[i-1] > h1['ema50'].iloc[i-1]):
            # Retest touched near broken 50-bar level but closed above it
            level = h1['dh50'].iloc[i-5]
            retest_held = (h1['low'].iloc[i-3:i].min() <= level + 2.0) and (h1['close'].iloc[i-1] > level)
            resumption = h1['close'].iloc[i-1] > h1['open'].iloc[i-1]
            if retest_held and resumption:
                entry = h1['open'].iloc[i] + STD_SPREAD
                sl = h1['low'].iloc[i-3:i].min() - 0.50
                risk = entry - sl
                if 6.0 <= risk <= 25.0:
                    t = simulate_trade_advanced(i, 'buy', entry, sl, target_r=2.5, max_bars=30, df_bars=h1)
                    if t: trades_c.append(t)
                    
        # Bearish 50-bar Donchian breakout
        recent_breakout_dn = (h1['low'].iloc[i-5:i-1] < h1['dl50'].iloc[i-5:i-1]).any()
        if recent_breakout_dn and (h1['close'].iloc[i-1] < h1['ema50'].iloc[i-1]):
            level = h1['dl50'].iloc[i-5]
            retest_held = (h1['high'].iloc[i-3:i].max() >= level - 2.0) and (h1['close'].iloc[i-1] < level)
            resumption = h1['close'].iloc[i-1] < h1['open'].iloc[i-1]
            if retest_held and resumption:
                entry = h1['open'].iloc[i]
                sl = h1['high'].iloc[i-3:i].max() + 0.50 + STD_SPREAD
                risk = sl - entry
                if 6.0 <= risk <= 25.0:
                    t = simulate_trade_advanced(i, 'sell', entry, sl, target_r=2.5, max_bars=30, df_bars=h1)
                    if t: trades_c.append(t)
                    
    analyze_trades(trades_c, "Donchian50_Institutional_Retest_2.5R")

if __name__ == "__main__":
    main()
