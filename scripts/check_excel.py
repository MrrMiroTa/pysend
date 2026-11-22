"""Diagnose Excel loading.  Run from the project folder:
     python scripts/check_excel.py                 (checks the file set in .env)
     python scripts/check_excel.py "D:\\my clients.xlsx"   (checks any file)"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"), interpolate=False)
import pandas as pd
from excel_manager import _read

if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    ep = (os.getenv("EXCEL_PATH") or "").strip().strip("\"'")
    path = os.path.normpath(os.path.join(ROOT, ep)) if ep else "(EXCEL_PATH is empty in .env)"
    print("EXCEL_PATH in .env :", repr(os.getenv("EXCEL_PATH")))
print("Resolved path      :", path)
print("Exists / is folder :", os.path.exists(path), "/", os.path.isdir(path))
if not os.path.isfile(path):
    sys.exit("-> Not a file. Set EXCEL_PATH=data/clients_sample.xlsx in .env, or pass a file path to this script.")
print("Size               :", os.path.getsize(path), "bytes")
lock = os.path.join(os.path.dirname(path), "~$" + os.path.basename(path))
print("Open in Excel?     :", "YES (close it)" if os.path.exists(lock) else "no")
try:
    raw = pd.read_excel(path, dtype=str, nrows=0) if path.lower().endswith((".xlsx", ".xlsm")) else pd.read_csv(path, nrows=0)
    print("Columns in file    :", list(raw.columns))
    df = _read(path)
except Exception as e:
    sys.exit(f"-> CANNOT READ: {type(e).__name__}: {e}")
bad = int((df["expiry_date"] == "").sum())
print(f"Rows loaded        : {len(df)}   (rows with unreadable expiry date: {bad})")
print(df[["user", "type", "plate", "imei", "expiry_date"]].head(5).to_string(index=False))
print("-> OK: this file can be loaded." if len(df) and bad < len(df) else "-> File opened but has no usable rows/dates.")
