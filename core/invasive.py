import json
from pathlib import Path

WEEDS_FILE = Path(__file__).resolve().parent.parent / "data" / "invasive_weeds.json"

def load_weeds():
    # List of weed dicts from invasive_weeds.json ({"willow": {...}, ...}), or [] if missing
    if WEEDS_FILE.exists():
        with open(WEEDS_FILE) as file:
            return list(json.load(file).values())
    return []

def match_weed(top_species):
    # Only Pl@ntNet's TOP species counts (match_card checks all 5): stricter, so fewer
    # false "invasive" results. The researcher override covers the misses.
    for weed in load_weeds():
        if top_species.lower() in [name.lower() for name in weed["accepted_ids"]]:
            return weed
    return None

def find_weed(common_name):
    # For the researcher override, which sends the weed's common_name (or None)
    for weed in load_weeds():
        if weed["common_name"] == common_name:
            return weed
    return None
