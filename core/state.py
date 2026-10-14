import json
import os
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "logs" / "state.json"
INITIAL_VALUE = {
    "trigger_id": 0,
    "triggered_at": None,
    "override_id": 0,
    "override_card": None
}

def read_state():
    if not STATE_FILE.exists():
        return dict(INITIAL_VALUE)
    with open(STATE_FILE) as file:
        return json.load(file)

PHONE_FILE = STATE_FILE.parent / "phone.json"   # phone writes it, researcher reads it

def write_json_atomic(path, data):
    path.parent.mkdir(exist_ok=True)
    temp_file = path.with_suffix(".tmp") # As the other page reads this file, using temp file to avoid reading it halfway
    with open(temp_file, "w") as file:
        json.dump(data, file, indent=2)
    os.replace(temp_file, path)

def write_state(state):
    write_json_atomic(STATE_FILE, state)

def set_trigger():
    state = read_state()
    state["trigger_id"] += 1
    state["triggered_at"] = datetime.now().isoformat(timespec="seconds")
    write_state(state)

def set_override(card):
    # card is 'A'..'E', or None for "not a card / retake"
    state = read_state()
    state["override_id"] += 1
    state["override_card"] = card
    write_state(state)

def write_phone_status(status):
    status["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json_atomic(PHONE_FILE, status)

def reset_phone_status():
    # Between participants. trigger_id/override_id are NOT reset: they must keep increasing.
    if PHONE_FILE.exists():
        PHONE_FILE.unlink()

def read_phone_status():
    if not PHONE_FILE.exists():
        return None
    with open(PHONE_FILE) as file:
        return json.load(file)