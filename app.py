"""
Native Plant Spotter.

http://localhost:8501/?role=admin
https://<tunnel-url>/?role=user        (phone, via cloudflared)
"""
import streamlit as st

from screens import participant, researcher

st.set_page_config(page_title="Native Plant Spotter", layout="centered")

role = st.query_params.get("role", "")

if role == "user":
    participant.show()
elif role == "admin":
    researcher.show()
else:
    st.title("Native Plant Spotter")
    st.info("Add ?role=user or ?role=admin to the end of the URL.")
