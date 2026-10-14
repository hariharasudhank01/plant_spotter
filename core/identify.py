import io
import requests
import streamlit as st
from PIL import Image
from core.plants import load_plants

URL = "https://my-api.plantnet.org/v2/identify/all"
# MIN_SCORE = 0.30

def match_card(results):
    plants = load_plants()
    for species, score in results:
        # if score < MIN_SCORE:
        #     break
        for card, plant in plants.items():
            if species.lower() in [name.lower() for name in plant["accepted_ids"]]:
                return card
    return None

def resize_photo(photo_bytes, max_side=1280):
    img = Image.open(
        io.BytesIO(photo_bytes)
    ).convert("RGB")
    img.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()

def identify_plant(photo_bytes):
    try:
        resp = requests.post(
            URL,
            params={
                "api-key": st.secrets["api_key"]
            },
            files={
                "images": ("snap.jpg", resize_photo(photo_bytes), "image/jpeg")
            },
            data={
                "organs": "auto"
            },
            timeout=15
        )
    except requests.RequestException as e:
        return [], f"network error: {e}"

    if resp.status_code == 404:
        return [], "no result"
    if resp.status_code != 200:
        return [], f"HTTP {resp.status_code}: {resp.text[:200]}"

    results = [
        (r["species"]["scientificNameWithoutAuthor"], r["score"])
        for r in resp.json()["results"]
    ]
    return results[:5], None