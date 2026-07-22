"""
Streamlit web app: UK building age lookup.

Deploy this on Streamlit Community Cloud (free) to get a shareable link
your colleagues can open in a browser — no code, no API key entry on
their end. Your API key lives in Streamlit's "secrets" (server-side only),
never sent to or visible by anyone using the link.
"""
import streamlit as st

from single_lookup import estimate_building_age

st.set_page_config(page_title="UK Building Age Lookup", page_icon="🏢")

st.title("UK Building Age Lookup")
st.write(
    "Enter a UK property address and postcode to get an estimated construction "
    "age, sourced from Ordnance Survey's building database."
)

# API keys come from Streamlit secrets — set once when you deploy, never
# visible to anyone using the app.
try:
    OS_API_KEY = st.secrets["OS_API_KEY"]
except Exception:
    st.error(
        "No OS API key configured. If you're the app owner: add OS_API_KEY in "
        "your Streamlit Cloud app's Settings -> Secrets."
    )
    st.stop()

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")  # optional — improves accuracy if set

with st.form("lookup_form"):
    address = st.text_input("Address", placeholder="e.g. 124 Commercial Street")
    postcode = st.text_input("Postcode", placeholder="e.g. E1 6NF")
    submitted = st.form_submit_button("Estimate age")

if submitted:
    if not address or not postcode:
        st.warning("Please enter both an address and a postcode.")
    else:
        with st.spinner("Looking up..."):
            result = estimate_building_age(address, postcode, OS_API_KEY, GOOGLE_API_KEY)

        if result.get("estimated_age"):
            if result.get("confidence") == "low":
                st.warning(result.get("note", "Low confidence match."))
            elif result.get("confidence") == "medium" and result.get("note"):
                st.info(result["note"])
            st.success(f"Estimated age: **{result['estimated_age']}**")
            col1, col2 = st.columns(2)
            col1.metric("Confidence", result["confidence"])
            col2.metric("Source", result.get("source", "-"))
            st.caption(f"Geocoded via: {result.get('geocode_method', '-')}")
            if result.get("provenance"):
                st.caption(f"Age data provenance: {result['provenance']}")
        else:
            st.info("No age data found for this address.")
            st.caption(result.get("note", ""))

        with st.expander("Debug: what happened during geocoding"):
            for line in result.get("debug_log", []):
                st.text(line)

st.divider()
st.caption(
    "Prototype tool — building age estimates are sourced from third-party "
    "data (Verisk, via Ordnance Survey) and should be treated as an "
    "estimate, not a certified record."
)
