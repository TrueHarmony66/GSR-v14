#!/usr/bin/env python3
"""
R075 Selective Native MT5 Strategy Tester Automation for GSR v14
Executes Stage 3 (Smoke Test 2026) and Stage 4 (Full 2020-2026 Multi-Year Test)
using Model=4 real ticks on GSR_XAUUSD_HISTDATA.
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

WORKSPACE = Path(r"c:\Users\trueh\Documents\GSR-Codex-v6.5")
R075_DIR = WORKSPACE / "research" / "R075_High_Expectancy_Edge_Discovery"
REPORTS_DIR = R075_DIR / "native_mt5_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TERMINAL_ROOT = Path(r"C:\MT5-GSR-Research")
DATA_ROOT = Path(r"C:\Users\trueh\AppData\Roaming\MetaQuotes\Terminal\8A14A3FFBE2FB59A4E8E5AA90F8EB807")
TERMINAL = TERMINAL_ROOT / "terminal64.exe"

EXPERT_NAME = "GoldScalperResearch_v14_NY_LondonRetest.ex5"
PRESET_NAME = "GSR14_NY_LondonRetest.set"

def deploy_assets():
    print("[+] Deploying EA binary and preset to MT5...", flush=True)
    src_ex5 = R075_DIR / EXPERT_NAME
    src_set = R075_DIR / PRESET_NAME
    
    assert src_ex5.exists(), f"Missing binary: {src_ex5}"
    assert src_set.exists(), f"Missing preset: {src_set}"
    
    # Destination directories
    dests_ex5 = [
        TERMINAL_ROOT / "MQL5" / "Experts" / EXPERT_NAME,
        DATA_ROOT / "MQL5" / "Experts" / EXPERT_NAME
    ]
    dests_set = [
        TERMINAL_ROOT / "MQL5" / "Presets" / PRESET_NAME,
        DATA_ROOT / "MQL5" / "Profiles" / "Tester" / PRESET_NAME
    ]
    
    for d in dests_ex5:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_ex5, d)
        print(f"  Deployed binary -> {d}")
        
    for d in dests_set:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_set, d)
        print(f"  Deployed preset -> {d}")

def run_tester(ini_name, from_date, to_date, report_rel_path):
    print(f"\n[+] Running MT5 Strategy Tester: {from_date} to {to_date}...", flush=True)
    
    # Ensure report directories exist
    (DATA_ROOT / Path(report_rel_path).parent).mkdir(parents=True, exist_ok=True)
    (TERMINAL_ROOT / Path(report_rel_path).parent).mkdir(parents=True, exist_ok=True)
    
    ini_content = f"""[Experts]
AllowLiveTrading=0
AllowDllImport=0
Enabled=1
[Tester]
Expert={EXPERT_NAME}
ExpertParameters={PRESET_NAME}
Symbol=GSR_XAUUSD_HISTDATA
Period=H1
Model=4
ExecutionMode=0
Optimization=0
ForwardMode=0
FromDate={from_date}
ToDate={to_date}
Deposit=5000
Currency=USD
Leverage=1:100
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
Report={report_rel_path}
ReplaceReport=1
ShutdownTerminal=1
"""
    ini_file = TERMINAL_ROOT / ini_name
    ini_file.write_text(ini_content, encoding="utf-8")
    
    # Ensure terminal is not running
    os.system("taskkill /F /IM terminal64.exe >nul 2>&1")
    time.sleep(2)
    
    t0 = time.time()
    res = subprocess.run([str(TERMINAL), f"/config:{ini_file}"], timeout=600)
    elapsed = time.time() - t0
    print(f"  MT5 finished in {elapsed:.1f}s (code {res.returncode})", flush=True)
    
    # Locate report in DATA_ROOT or TERMINAL_ROOT
    rep1 = DATA_ROOT / report_rel_path
    rep2 = TERMINAL_ROOT / report_rel_path
    
    target_rep = rep1 if rep1.exists() else (rep2 if rep2.exists() else None)
    if target_rep and target_rep.exists():
        sz = target_rep.stat().st_size
        print(f"  Report generated: {target_rep} ({sz:,} bytes)", flush=True)
        # Copy to REPORTS_DIR
        local_rep = REPORTS_DIR / Path(report_rel_path).name
        shutil.copy2(target_rep, local_rep)
        return local_rep
    else:
        print(f"  FAILED: Report not found at {rep1} or {rep2}", flush=True)
        return None

def parse_report(report_path):
    print(f"[+] Parsing report with analyze_mt5.py: {report_path.name}...", flush=True)
    cmd = [sys.executable, str(WORKSPACE / "analyze_mt5.py"), str(report_path), "--out", str(REPORTS_DIR / "analysis")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("ERRORS:", res.stderr)
    return res.returncode == 0

def main():
    print("=== GSR v14 NATIVE MT5 REAL-TICK VALIDATION ===", flush=True)
    deploy_assets()
    
    # -------------------------------------------------------------------------
    # STAGE 3: Native MT5 Smoke Test on 2026 (2026.01.01 to 2026.10.23)
    # -------------------------------------------------------------------------
    smoke_rep_rel = "Reports\\R075_VALIDATION\\smoke_v14_2026.htm"
    rep_smoke = run_tester("tester_smoke_v14.ini", "2026.01.01", "2026.10.23", smoke_rep_rel)
    
    if not rep_smoke:
        print("[-] Stage 3 Smoke Test Failed to produce report. Halting.", flush=True)
        sys.exit(1)
        
    parse_report(rep_smoke)
    
    # -------------------------------------------------------------------------
    # STAGE 4: Full Multi-Year Native MT5 Real-Tick Backtest (2020.01.01 to 2026.10.23)
    # -------------------------------------------------------------------------
    full_rep_rel = "Reports\\R075_VALIDATION\\full_v14_2020_2026.htm"
    rep_full = run_tester("tester_full_v14.ini", "2020.01.01", "2026.10.23", full_rep_rel)
    
    if rep_full:
        parse_report(rep_full)
        print("\n[SUCCESS] GSR v14 Native MT5 Real-Tick Multi-Year Validation Complete!", flush=True)
    else:
        print("[-] Full multi-year run did not produce report.", flush=True)

if __name__ == "__main__":
    main()
