# Native Plant Spotter: prototype

COMP3900/6390 Assignment 3 (individual). A phone web app built with Streamlit, tested as a
tabletop study.

**Research question:** What effects can a location-triggered camera spotting challenge have on
students' awareness and knowledge of overlooked native plants on campus?

**What the prototype does.** The participant imagines walking along Sullivans Creek. The
researcher triggers a "native plant zone" alert (Wizard-of-Oz, no real GPS). The participant
then has 60 seconds to find the native plants among printed cards A to E by snapping them with
the camera. Each snap is checked with the Pl@ntNet API and gets instant feedback. The researcher
can step in when Pl@ntNet can't place a photo. The app ends with a reveal of all cards, info
cards for the natives and a results screen.

One app runs in two roles, chosen by the URL:

| Role | URL | Runs on |
|---|---|---|
| Researcher console | `http://localhost:8501/?role=researcher` | Laptop browser |
| Participant app | `http://localhost:8501/?role=participant` (or the tunnel URL on a phone) | Phone, or a second browser tab |

---

## Quick start (one computer, about 5 minutes)

You can run the whole prototype on one computer, using **two browser tabs** and the laptop
webcam. No phone and no tunnel are needed.

### 1. Requirements

- **Python 3.10 or newer.** Developed and tested on Python 3.12 with Streamlit 1.65.
- A webcam, for the participant camera.
- A **Pl@ntNet API key** if you want real plant identification. A free key is available at
  <https://my.plantnet.org> (500 identifications per day). Without a key, use
  **researcher mode** (step 4).

### 2. Install

Open a terminal **in this folder**, the one containing `app.py`.

macOS / Linux:
```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):
```powershell
python -m venv env
env\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Add the Pl@ntNet API key

Create the file `.streamlit/secrets.toml` with this content:
```toml
api_key = "YOUR-PLANTNET-API-KEY"
```
This file is excluded from version control and is **not included in the submission**.

### 4. Without an API key: use researcher mode

In `screens/participant.py`, change:
```python
CHECK_MODE = "api"
```
to:
```python
CHECK_MODE = "researcher"
```
In researcher mode, Pl@ntNet is never called. Every snap waits for the researcher to tap the
card letter on the console, which is the Wizard-of-Oz fallback the study relies on.

### 5. Run

Start the app **from this folder**. Streamlit only finds `.streamlit/secrets.toml` when you run
it from here.
```bash
streamlit run app.py
```

Then open both URLs, side by side if possible:

- **Researcher:** <http://localhost:8501/?role=researcher>
- **Participant:** <http://localhost:8501/?role=participant>

---

## Walkthrough of one session

| Step | Participant tab | Researcher tab |
|---|---|---|
| 1 | **P0 Start:** fill in the consent form and press Submit. **Use a new UID for every run** (any text, e.g. `test1`, `test2`); a UID that has already been used is blocked. | — |
| 2 | **P1 Scenario:** "Imagine…" text, then the screen waits. | Press **Trigger Notification**. |
| 3 | **P2 Zone alert** appears within about 2 seconds. Press **Start challenge**. | — |
| 4 | **P3 Challenge:** a 60-second timer, a "Found x of y" counter, points and the camera. Point the camera at a card and take a photo. | The **Phone** panel shows the live status. |
| 5 | **Feedback:** "Native! +10", "Not native, keep looking" or "Already found". | If the phone shows "Checking…", the console shows a red **WAITING** message. Tap the card letter (A to E) that was photographed, or **Not a card**. |
| 6 | Repeat until all natives are found or time runs out. | The **Logs** table shows each snap. |
| 7 | **P5 Reveal** of all cards → **P6 Info cards** for the natives → **P7 Finish** with results. | — |
| 8 | — | **Download** `snaps.json` / `output.json`, then **Reset phone status**. Reload the participant tab to start a new participant. |

**No printed cards?** Show the card photos from `data/images/` on another screen (or a phone)
and point the webcam at them, or use researcher mode and tap the card letter on the console.

**Testing a specific outcome:**

| Outcome | How |
|---|---|
| Hit | Tap **A** or **B** (the native cards). |
| Not native | Tap **C**, **D** or **E**. |
| Already found | Tap the same native twice. |
| Unrecognised | Tap **Not a card**. |

---

## Running it on a real phone (as in the study)

The phone's camera only works over **HTTPS**, so the laptop is exposed through a temporary
Cloudflare tunnel.

1. Install `cloudflared` (macOS: `brew install cloudflared`; others:
   <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/>).
2. With the app already running, open a **second terminal** and run:
   ```bash
   cloudflared tunnel --url http://localhost:8501
   ```
3. Cloudflared prints a URL like `https://something-random.trycloudflare.com`. On the phone,
   open that URL with `?role=participant` added to the end, and allow camera access.
4. Keep the researcher console on the laptop at `http://localhost:8501/?role=researcher`.

---

## Settings

All settings are at the top of `screens/participant.py`:

| Setting | Default | Meaning |
|---|---|---|
| `CHECK_MODE` | `"api"` | `"api"`: Pl@ntNet decides, researcher override as fallback. `"researcher"`: every snap waits for the researcher. |
| `CHALLENGE_SECONDS` | `60` | Length of the challenge. |
| `POINTS_PER_NATIVE` | `10` | Points per native found. Wrong picks are logged but not penalised. |
| `POST_QUIZ_URL` | `""` | Link to the post-quiz form shown on the finish screen. |

The plant cards are defined in `data/plants.json`, one entry per card (A to E): names, the
species names Pl@ntNet may return (`accepted_ids`), native or not, reason, conservation status,
why it matters, how to protect it, image path and sources. The number of natives is counted from
this file, not hard-coded.

---

## Project structure

```
app.py                  entry point: page setup and role routing (?role=...)
screens/
  participant.py        participant screens P0 to P7, challenge loop, scoring
  researcher.py         trigger, live phone status, card override, logs, downloads, reset
core/
  identify.py           Pl@ntNet API call; match_card() maps a species to a card A to E
  plants.py             loads data/plants.json; list of native cards
  state.py              shared files between the two roles (trigger, override, phone status)
  logger.py             appends records to data/snaps.json and data/output.json
data/
  plants.json           the 5 cards
  images/               card photos (also shown on the reveal and info screens)
assets/                 scenario audio
.streamlit/secrets.toml Pl@ntNet API key (not submitted)
requirements.txt
```

**How the two roles communicate.** The researcher page and the participant page are separate
Streamlit sessions, so they talk through small JSON files in `logs/`:

- `state.json` is written by the researcher (trigger and override). Each event has an
  increasing id, so old events are never handled twice.
- `phone.json` is written by the participant (live status).

The participant page polls with `streamlit-autorefresh` while waiting. During the challenge, the
timer is an `st.fragment(run_every=1)`, so only the timer refreshes each second, not the camera
or the API call. Files are written to a temp file first and then swapped in, so the other page
never reads a half-written file.

## Files created while running

| File | Contents |
|---|---|
| `data/user.json` | Consent form entries (name, UID, consent) |
| `data/snaps.json` | One record per snap: time since start, card, native, outcome, Pl@ntNet top species and score, error, whether an override was used |
| `data/output.json` | One record per participant: time taken, points, natives found and missed, hits, false positives, snaps, overrides used |
| `data/snap/` | The photos taken during the challenge |
| `logs/state.json`, `logs/phone.json` | Shared state between researcher and participant (runtime only) |

To start completely fresh, delete these files. They are recreated automatically.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `KeyError: st.secrets has no key "api_key"` | Run `streamlit run app.py` **from this folder**, and check `.streamlit/secrets.toml` exists. Restart Streamlit after editing it. Alternatively, use `CHECK_MODE = "researcher"`. |
| "User already Participated" | That UID was used before. Enter a different UID, or remove it from `data/user.json`. |
| Camera does not open | Allow camera access in the browser. On a phone, the page must be opened via the **https** tunnel URL, not an http address. |
| Photo upload fails with **403** over the tunnel | Create `.streamlit/config.toml` with `[server]` and `enableXsrfProtection = false` on the next line, then restart. |
| Phone does not react to **Trigger** | It only reacts to triggers made **after** the consent form was submitted. Press Trigger again. |
| No sound on the alert | Browsers (especially iPhone Safari) block autoplay; the on-screen alert still works. |
| Pl@ntNet says "no result" or matches nothing | Expected for some photos (prints, screens, glare). The console shows **WAITING**; tap the right card letter. |

## Credits

Card photos C, D and E are from Wikimedia Commons (CC BY 2.0 / CC BY-SA 4.0 / CC BY-SA 2.0).
Photographer and licence for each card are listed in the `source` field of `data/plants.json`.
Plant identification by the [Pl@ntNet API](https://my.plantnet.org).
