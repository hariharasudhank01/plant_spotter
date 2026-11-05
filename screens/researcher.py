import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core.invasive import load_weeds
from core.logger import SNAPS_FILE, OUTPUT_FILE, INVASIVE_FILE, read_records
from core.plants import load_plants
from core.state import (read_state, set_trigger, set_override, set_invasive_override,
                        read_phone_status, reset_phone_status)

def show():
    st_autorefresh(interval=2000, key="console_poll")   # keep the phone status live
    st.title("Researcher console")

    if st.button("Trigger Notification", type="primary"):
        set_trigger()
        st.success("Triggered")

    state = read_state()
    st.write(f"Last Triggered: {state['trigger_id']} at {state['triggered_at']}")

    # Live status written by the phone (logs/phone.json)
    st.subheader("Phone")
    phone = read_phone_status()
    if phone is None:
        st.caption("No status yet")
    else:
        if phone.get("waiting_for_override"):
            st.error("Phone is WAITING: tap the card they snapped")
        if phone.get("waiting_for_invasive_override"):
            said = phone.get("api_top_species") or "nothing"
            st.error(f"Phone is WAITING on the invasive check (Pl@ntNet said: {said})")
        st.write(phone)

    # Card override: only tap when the phone is WAITING
    st.subheader("Card override")
    cards = sorted(load_plants())
    cols = st.columns(len(cards) + 1)
    for col, card in zip(cols, cards):
        if col.button(card, use_container_width=True):
            set_override(card)
            st.success(f"Sent {card}")
    if cols[-1].button("Not a card", use_container_width=True):
        set_override(None)
        st.success("Sent: not a card")

    # Invasive override: only tap when the phone is WAITING on the invasive check
    st.subheader("Invasive override")
    weeds = load_weeds()
    cols = st.columns(len(weeds) + 1)
    for col, weed in zip(cols, weeds):
        if col.button(f"Invasive: {weed['common_name']}", use_container_width=True):
            set_invasive_override(weed["common_name"])
            st.success(f"Sent: invasive ({weed['common_name']})")
    if cols[-1].button("Not invasive", use_container_width=True):
        set_invasive_override(None)
        st.success("Sent: not invasive")

    # Logs written by the phone
    st.subheader("Logs")
    snaps = read_records(SNAPS_FILE)
    if snaps:
        st.caption("Latest 10 snaps")
        st.dataframe(snaps[-10:])
    else:
        st.caption("No snaps logged yet")

    col1, col2, col3 = st.columns(3)
    for col, path in ((col1, SNAPS_FILE), (col2, OUTPUT_FILE), (col3, INVASIVE_FILE)):
        if path.exists():
            col.download_button(f"Download {path.name}", path.read_bytes(),
                                file_name=path.name, mime="application/json")

    # Between participants: clear the phone status, then reload the page on the phone
    if st.button("Reset phone status"):
        reset_phone_status()
        st.success("Phone status cleared. Reload the participant page on the phone.")
