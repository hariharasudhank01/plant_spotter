import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core.logger import SNAPS_FILE, OUTPUT_FILE, read_records
from core.plants import load_plants
from core.state import (read_state, set_trigger, set_override,
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

    # Logs written by the phone
    st.subheader("Logs")
    snaps = read_records(SNAPS_FILE)
    if snaps:
        st.caption("Latest 10 snaps")
        st.dataframe(snaps[-10:])
    else:
        st.caption("No snaps logged yet")

    col1, col2 = st.columns(2)
    for col, path in ((col1, SNAPS_FILE), (col2, OUTPUT_FILE)):
        if path.exists():
            col.download_button(f"Download {path.name}", path.read_bytes(),
                                file_name=path.name, mime="application/json")

    # Between participants: clear the phone status, then reload the page on the phone
    if st.button("Reset phone status"):
        reset_phone_status()
        st.success("Phone status cleared. Reload the participant page on the phone.")
