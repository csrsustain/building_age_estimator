"""
Address-level geocoding via Google's Geocoding API — better UK
building-level matching than Nominatim, no sales call needed (unlike OS
Places), just a Google Cloud API key with the Geocoding API enabled.

Key insight this uses: Google's response includes a `location_type` field
that tells you HOW precise the match actually is:
  - ROOFTOP: matched to the exact building — high confidence
  - RANGE_INTERPOLATED: estimated between known points on the street — 
    lower confidence, similar risk to Nominatim's street-level matches
  - GEOMETRIC_CENTER / APPROXIMATE: matched to a broader area, not a
    building — low confidence

We use this to flag precision explicitly, the same way we now do for
Nominatim's house-number check.
"""
import requests

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode_address_google(address: str, postcode: str, api_key: str):
    """Look up a full address via Google Geocoding API. Returns
    {lon, lat, formatted_address, location_type, is_precise} or None."""
    query = f"{address}, {postcode}, UK"
    params = {"address": query, "key": api_key, "region": "uk"}

    resp = requests.get(GEOCODE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status != "OK":
        if status not in ("ZERO_RESULTS",):
            print(f"[warn] Google Geocoding API returned status: {status} — {data.get('error_message', '')}")
        return None

    result = data["results"][0]
    location = result["geometry"]["location"]
    location_type = result["geometry"].get("location_type")

    return {
        "lon": location["lng"],
        "lat": location["lat"],
        "formatted_address": result.get("formatted_address"),
        "location_type": location_type,
        "is_precise": location_type == "ROOFTOP",
        "precision_level": {
            "ROOFTOP": "high",
            "RANGE_INTERPOLATED": "medium",
        }.get(location_type, "low"),
    }
