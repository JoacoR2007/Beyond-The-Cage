"""Descarga los CSV públicos de UFCStats (repo Greco1899/scrape_ufc_stats) a data/raw/.
Ese repo se actualiza después de cada evento. Uso: python scripts/fetch_ufc_data.py"""
import sys, urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/"
FILES = {"ufc_event_details.csv": "EVENT,", "ufc_fight_results.csv": "EVENT,", "ufc_fight_stats.csv": "EVENT,", "ufc_fighter_tott.csv": "FIGHTER,"}
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

for name, header in FILES.items():
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "beyond-the-cage/1.0"})
    data = urllib.request.urlopen(req, timeout=60).read()
    if not data.decode("utf-8", "ignore").startswith(header):
        sys.exit(f"{name}: formato inesperado, no se sobrescribe")
    (RAW / name).write_bytes(data)
    print(f"{name}: {len(data) // 1024} KB")
