#!/usr/bin/env python3
"""
R075 Compilation Utility for GSR v14
Compiles GoldScalperResearch_v14_NY_LondonRetest.mq5 using MetaEditor 64 Build 6272.
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

WORKSPACE = Path(r"c:\Users\trueh\Documents\GSR-Codex-v6.5")
R075_DIR = WORKSPACE / "research" / "R075_High_Expectancy_Edge_Discovery"
SOURCE_MQ5 = R075_DIR / "GoldScalperResearch_v14_NY_LondonRetest.mq5"

EDITOR = Path(r"C:\MT5-GSR-Research\metaeditor64.exe")
MT5_DIR = Path(r"C:\MT5-GSR-Research\MQL5\Experts")
APPDATA_DIR = Path(r"C:\Users\trueh\AppData\Roaming\MetaQuotes\Terminal\8A14A3FFBE2FB59A4E8E5AA90F8EB807\MQL5\Experts")

def main():
    print("=== COMPILING GSR v14 NY-LONDON RETEST EA ===", flush=True)
    assert SOURCE_MQ5.exists(), f"Source missing: {SOURCE_MQ5}"
    
    # 1. Copy to MT5 Experts and AppData Experts
    dest_mt5 = MT5_DIR / SOURCE_MQ5.name
    dest_appdata = APPDATA_DIR / SOURCE_MQ5.name
    
    shutil.copyfile(SOURCE_MQ5, dest_mt5)
    shutil.copyfile(SOURCE_MQ5, dest_appdata)
    print(f"[+] Deployed to {dest_mt5}")
    print(f"[+] Deployed to {dest_appdata}")
    
    # 2. Compile via MetaEditor
    log_file = APPDATA_DIR / "GoldScalperResearch_v14_NY_LondonRetest.log"
    binary_file = APPDATA_DIR / "GoldScalperResearch_v14_NY_LondonRetest.ex5"
    
    cmd = [str(EDITOR), f'/compile:{dest_appdata}', '/log']
    print(f"[+] Running: {' '.join(cmd)}", flush=True)
    
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.time() - t0
    print(f"[+] MetaEditor finished in {dur:.2f}s (exit code {proc.returncode})", flush=True)
    
    time.sleep(1.0)
    
    # Check log
    if log_file.exists():
        raw = log_file.read_bytes()
        try:
            log_text = raw.decode("utf-16le", errors="replace").lstrip("\ufeff")
        except:
            log_text = raw.decode("utf-8", errors="replace")
            
        print("\n--- MetaEditor Compilation Log ---")
        print(log_text.strip())
        
        # Copy log to R075_DIR
        shutil.copyfile(log_file, R075_DIR / "compile_v14.log")
        
        if "0 errors, 0 warnings" in log_text:
            print("\n[SUCCESS] 0 errors, 0 warnings verified!")
        else:
            print("\n[WARNING] Log does not contain '0 errors, 0 warnings'")
    else:
        print(f"[!] Log not found at {log_file}")
        
    # Check binary
    if binary_file.exists():
        sz = binary_file.stat().st_size
        print(f"[+] Binary created: {binary_file} ({sz:,} bytes)")
        shutil.copyfile(binary_file, dest_mt5.with_suffix(".ex5"))
        shutil.copyfile(binary_file, R075_DIR / "GoldScalperResearch_v14_NY_LondonRetest.ex5")
        print(f"[+] Copied binary to {R075_DIR / binary_file.name}")
    else:
        print("[ERROR] Binary .ex5 was not generated!")
        sys.exit(1)

if __name__ == "__main__":
    main()
