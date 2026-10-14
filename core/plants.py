import json
from pathlib import Path
import os

PLANTS_FILE = Path(__file__).resolve().parent.parent / "data" / "plants.json"

def load_plants():
    if os.path.exists(PLANTS_FILE):
        with open(PLANTS_FILE) as file:
            return json.load(file)
    return {}

def native_cards():
    # Card letters of the native plants, e.g. ['A', 'B']. Empty list if no plants.
    return [card for card, plant in load_plants().items() if plant["native"]]
