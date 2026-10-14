import json
from pathlib import Path

from core.state import write_json_atomic

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SNAPS_FILE = DATA_DIR / "snaps.json"      # one record per camera snap
OUTPUT_FILE = DATA_DIR / "output.json"    # one record per participant

def read_records(path):
    # Return the list stored in a JSON log file, or [] if it doesn't exist yet
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path) as file:
        return json.load(file)

def append_record(path, record):
    records = read_records(path)
    records.append(record)
    write_json_atomic(path, records)

def log_snap(snap):
    # Called as soon as a snap is scored, so a crash mid-session keeps earlier snaps
    append_record(SNAPS_FILE, snap)

def log_summary(record):
    append_record(OUTPUT_FILE, record)
