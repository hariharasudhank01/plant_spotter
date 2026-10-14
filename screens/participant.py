import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
import time
from streamlit_autorefresh import st_autorefresh

from core.identify import identify_plant, match_card
from core.plants import load_plants, native_cards
from core.state import read_state, write_phone_status
from core.logger import log_snap, log_summary

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "data" / "snap"
ASSETS_DIR = PROJECT_ROOT / "assets"

CHECK_MODE = "api"          # "api": Pl@ntNet decides, researcher override as fallback
                            # "researcher": every snap waits for the researcher's tap
CHALLENGE_SECONDS = 60
POINTS_PER_NATIVE = 10
POST_QUIZ_URL = ""          # TODO: paste the Google Form post-quiz link here

def read_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as file:
            data = json.load(file)
            if data:
                return data
    return []    # file missing or empty

def write_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

def page_setup():
    st.title("ANU Campus Plant Spotter")

def consent_form():
    with st.form(key="consent_form", clear_on_submit=True):
        st.subheader("Please provide your consent to participate in this research")

        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        uid = st.text_input("UID")

        consent = st.selectbox(
            "This application is a prototype of ANU Campus Plant Spotter. The use case will be explained by the researcher." \
            "This section will be recorded both Audio and Screen, and user inputs. The data will be used for analysis and shared" \
            "with Course Teaching Team",
            ["Yes", "No"]
        )

        submit_button = st.form_submit_button(label="Submit")

    if submit_button:
        if not first_name or not last_name or not uid:
            st.error("Please provide your details")
            return None
        if not consent:
            st.error("Please provide your consent")
            return None
        if consent == "No":
            st.success("Thank you for paticipating in this research. Your details are not stored")
            st.stop()
        else:
            st.success("Thank you for your consent")
            return {
                "first_name": first_name,
                "last_name": last_name,
                "uid": uid,
                "consent": consent
            }

def update_user_list(new_user):
    uid_list = []

    user_data = read_json(
        os.path.join(PROJECT_ROOT, "data", "user.json")
    )

    for data in user_data:
        uid_list.append(data["uid"].lower())

    if new_user:
        if not new_user["uid"].lower() in uid_list:
            user_data.append(new_user)
            write_json(os.path.join(PROJECT_ROOT, "data", "user.json"), user_data)
            st.success("Participant Recorded")
            return new_user["uid"]
        else:
            st.error("User already Participated")
            st.stop()

def start_challenge():
    st.session_state.start_time = time.time()
    st.session_state.found = []        # native cards found so far
    st.session_state.points = 0
    st.session_state.snaps = []        # one dict per snap (also logged to data/snaps.json)
    st.session_state.pending = None    # a snap waiting for the researcher's override
    st.session_state.feedback = None   # ("success" / "warning" / "info", message)
    st.session_state.screen = "challenge"

def handle_new_photo(picture):
    snap = {
        "participant_id": st.session_state.uid,
        "snap_no": len(st.session_state.snaps) + 1,
        "seconds_since_start": round(time.time() - st.session_state.start_time, 1),
        "api_top_species": "",
        "api_score": "",
        "api_error": "",
        "override_used": False,
    }

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    with open(IMAGE_DIR / f"{snap['participant_id']}_{snap['snap_no']}.jpg", "wb") as f:
        f.write(picture.getvalue())

    card = None
    if CHECK_MODE == "api":
        results, error = identify_plant(picture.getvalue())
        if results:
            snap["api_top_species"] = results[0][0]
            snap["api_score"] = round(results[0][1], 3)
        snap["api_error"] = error or ""
        card = match_card(results)

    if card is None:
        # Pl@ntNet couldn't place it (or researcher mode): wait for the researcher's tap.
        # Remember the current override id, so only a NEW tap counts.
        snap["override_used"] = True
        st.session_state.pending = {"snap": snap,
                                    "override_from": read_state()["override_id"]}
    else:
        score_snap(card, snap)

def score_snap(card, snap):
    # Same scoring whether the card came from Pl@ntNet or the researcher's override
    natives = native_cards()
    found = st.session_state.found

    if card is None:
        outcome = "unrecognised"
        st.session_state.feedback = ("info", "Couldn't recognise that. Try again.")
    elif card in found:
        outcome = "already_found"
        st.session_state.feedback = ("info", "Already found! Look for another one.")
    elif card in natives:
        outcome = "hit"
        found.append(card)
        st.session_state.points += POINTS_PER_NATIVE
        st.session_state.feedback = (
            "success",
            f"Native! +{POINTS_PER_NATIVE} points ({len(found)} of {len(natives)})")
    else:
        outcome = "false_positive"     # logged, not penalised
        st.session_state.feedback = ("warning", "Not native, keep looking.")

    snap["card"] = card or ""
    snap["native"] = card in natives if card else ""
    snap["outcome"] = outcome
    st.session_state.snaps.append(snap)
    log_snap(snap)                     # data/snaps.json, written straight away

@st.fragment(run_every=1)
def timer_panel():
    # Re-runs only this function every second, so the camera and the API call are not interrupted
    natives = native_cards()
    left = CHALLENGE_SECONDS - (time.time() - st.session_state.start_time)

    # Researcher override arrived?
    if st.session_state.pending:
        state = read_state()
        if state["override_id"] > st.session_state.pending["override_from"]:
            score_snap(state["override_card"], st.session_state.pending["snap"])
            st.session_state.pending = None
            st.rerun()                 # full rerun: show feedback and a fresh camera

    if left <= 0:
        finish_challenge(timed_out=True)
        st.rerun()

    write_phone_status({
        "participant_id": st.session_state.uid,
        "screen": "challenge",
        "found": len(st.session_state.found),
        "points": st.session_state.points,
        "seconds_left": int(left),
        "waiting_for_override": st.session_state.pending is not None,
    })

    st.progress(left / CHALLENGE_SECONDS, text=f"{int(left)} s left")
    col1, col2 = st.columns(2)
    col1.metric("Found", f"{len(st.session_state.found)} of {len(natives)}")
    col2.metric("Points", st.session_state.points)

def challenge_screen():
    if len(st.session_state.found) == len(native_cards()):
        finish_challenge(timed_out=False)
        st.rerun()

    timer_panel()

    if st.session_state.feedback:
        kind, message = st.session_state.feedback
        if kind == "success":
            st.success(message)
        elif kind == "warning":
            st.warning(message)
        else:
            st.info(message)

    if st.session_state.pending:
        st.info("Checking...")         # waiting for the researcher; camera hidden
        return

    # A new key after every snap gives a fresh camera (no "Clear photo" tap needed)
    picture = st.camera_input("Snap a plant",
                              key=f"camera_{len(st.session_state.snaps)}")
    if picture is not None and picture.file_id != st.session_state.get("last_saved"):
        st.session_state.last_saved = picture.file_id
        with st.spinner("Checking..."):
            handle_new_photo(picture)
        st.rerun()                     # redraw with feedback and a fresh camera

def save_output():
    # One record per participant in data/output.json
    natives = native_cards()
    snaps = st.session_state.snaps
    record = {
        "uid": st.session_state.uid,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "check_mode": CHECK_MODE,
        "time_taken_seconds": st.session_state.total_seconds,
        "timed_out": st.session_state.timed_out,
        "points": st.session_state.points,
        "natives_found": st.session_state.found,
        "missed_natives": [card for card in natives if card not in st.session_state.found],
        "hits": len(st.session_state.found),
        "false_positives": sum(1 for s in snaps if s["outcome"] == "false_positive"),
        "snaps": len(snaps),
        "overrides_used": sum(1 for s in snaps if s["override_used"]),
    }
    log_summary(record)                # data/output.json

def finish_challenge(timed_out):
    if st.session_state.pending:       # time ran out while waiting for the researcher
        snap = st.session_state.pending["snap"]
        snap.update(card="", native="", outcome="unresolved")
        st.session_state.snaps.append(snap)
        log_snap(snap)
        st.session_state.pending = None
    elapsed = time.time() - st.session_state.start_time
    st.session_state.total_seconds = round(min(elapsed, CHALLENGE_SECONDS), 1)
    st.session_state.timed_out = timed_out
    st.session_state.screen = "reveal"
    save_output()
    write_phone_status({"participant_id": st.session_state.uid, "screen": "reveal",
                        "found": len(st.session_state.found),
                        "points": st.session_state.points})

def go_to(screen):
    # Move to another screen and tell the researcher console where the phone is
    st.session_state.screen = screen
    write_phone_status({"participant_id": st.session_state.uid, "screen": screen,
                        "found": len(st.session_state.found),
                        "points": st.session_state.points})
    st.rerun()

def card_image(plant):
    # The card photo from plants.json "image" (a path relative to the project folder)
    path = PROJECT_ROOT / plant["image"]
    if path.exists():
        st.image(str(path))
    else:
        st.caption("(card photo missing)")

def reveal_screen():
    # P5: all cards, native or not, and why
    st.header("Time's up!" if st.session_state.timed_out else "You found them all!")
    st.subheader("Here are all the cards")

    found = st.session_state.found
    wrong_picks = {s["card"] for s in st.session_state.snaps if s["outcome"] == "false_positive"}

    for card, plant in load_plants().items():
        with st.container(border=True):
            st.markdown(f"**Card {card}: {plant['common_name']}**  \n*{plant['scientific_name']}*")
            card_image(plant)
            if plant["native"]:
                st.success("Native")
            else:
                st.error("Not native")
            st.write(plant["reason"])

            if card in found:
                st.caption("You found this one ✅")
            elif card in wrong_picks:
                st.caption("You picked this one, but it isn't native")
            elif plant["native"]:
                st.caption("You missed this one")

    if st.button("Learn about the natives", type="primary"):
        go_to("info")

def info_screen():
    # P6: one info card per native plant
    st.header("Meet the natives")
    plants = load_plants()

    for card in native_cards():
        plant = plants[card]
        with st.container(border=True):
            st.subheader(plant["common_name"])
            st.markdown(f"*{plant['scientific_name']}*")
            card_image(plant)
            st.markdown(f"**Conservation status:** {plant['conservation_status']}")
            st.markdown(f"**Why it matters:** {plant['why_it_matters']}")
            st.markdown(f"**How to protect it:** {plant['how_to_protect']}")

    if st.button("Finish", type="primary"):
        go_to("done")

def done_screen():
    # P7: results and the post-quiz link
    natives = native_cards()
    plants = load_plants()
    found = st.session_state.found
    wrong = sum(1 for s in st.session_state.snaps if s["outcome"] == "false_positive")

    if len(found) == len(natives) and not st.session_state.get("celebrated"):
        st.balloons()                  # only once, not on every rerun
        st.session_state.celebrated = True

    st.header("Thanks for playing!")
    col1, col2, col3 = st.columns(3)
    col1.metric("Points", st.session_state.points)
    col2.metric("Natives found", f"{len(found)} of {len(natives)}")
    col3.metric("Wrong picks", wrong)
    st.write(f"Time: {st.session_state.total_seconds} s")

    missed = [plants[card]["common_name"] for card in natives if card not in found]
    if missed:
        st.write("Missed: " + ", ".join(missed))

    st.divider()
    if POST_QUIZ_URL:
        st.link_button("Open the post-quiz", POST_QUIZ_URL, type="primary")
    else:
        st.info("The researcher will give you the post-quiz link.")
    st.caption("Please don't tell other participants which cards are native.")

def alert_screen():
    st.toast("You've entered a native plant zone!")

    st.header("Native plant zone")
    st.write("Few native plants are around you. Can you find them all?")

    if st.button("Start challenge", type="primary"):
        start_challenge()
        st.rerun()


def scenario_screen():
    st_autorefresh(interval=2000, key="poll")

    if os.path.exists(os.path.join(ASSETS_DIR, "scenario.mp3")):
        st.audio(os.path.join(ASSETS_DIR, "scenario.mp3"), autoplay=True)
    st.subheader("Imagine.....")
    st.write("You are walking along ANU Campus with a cup of coffee and phone in your hand on your way to class."
             "Enjoying the windy canberra with birds flying around in the evening")
    st.caption("Waiting......")

    trigger_id = read_state()["trigger_id"]
    if trigger_id > st.session_state.seen_trigger:
        st.session_state.seen_trigger = trigger_id
        st.session_state.alert_time = time.time()
        st.session_state.screen = "alert"
        st.rerun()        

def start_screen():
    new_user = consent_form()
    if new_user:
        st.session_state.uid = update_user_list(new_user)
        st.session_state.seen_trigger = read_state()["trigger_id"]
        st.session_state.screen = "scenario"
        st.rerun()

def show():
    page_setup()
    if "screen" not in st.session_state:
        st.session_state.screen = "start"

    screen = st.session_state.screen
    if screen == "start":
        start_screen()
    elif screen == "scenario":
        scenario_screen()
    elif screen == "alert":
        alert_screen()
    elif screen == "challenge":
        challenge_screen()
    elif screen == "reveal":
        reveal_screen()
    elif screen == "info":
        info_screen()
    elif screen == "done":
        done_screen()
