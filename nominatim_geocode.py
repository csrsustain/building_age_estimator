"""
Free address-level geocoding via Nominatim (OpenStreetMap).

No API key needed. Usage policy (nominatim.org) requires:
  - A descriptive User-Agent identifying your app (not a browser string)
  - Max 1 request per second
  - Not to be used for heavy/bulk commercial use without separate
    arrangement (see https://operations.osmfoundation.org/policies/nominatim/)

Precision/reliability is generally lower than OS Places for UK commercial
buildings specifically — OSM's address coverage varies a lot by area and
building type. Treat this as a free fallback, not your primary source at
production scale.
"""
import time

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "uk-building-age-pilot/0.1 (testing only)"}

_last_call_time = [0.0]
_MIN_INTERVAL = 1.05  # a little over 1s to safely respect the rate limit


def geocode_address_nominatim(address: str, postcode: str):
    """Look up a full address via Nominatim. Returns
    {lon, lat, display_name, type} or None if no match."""
    # Respect the 1 req/sec limit even across repeated calls
    elapsed = time.time() - _last_call_time[0]
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    query = f"{address}, {postcode}, UK".strip(", ")
    params = {"q": query, "format": "json", "addressdetails": 1, "countrycodes": "gb", "limit": 1}

    resp = requests.get(NOMINATIM_URL, params=params, headers=_HEADERS, timeout=15)
    _last_call_time[0] = time.time()
    resp.raise_for_status()
    results = resp.json()

    if not results:
        return None

    r = results[0]
    return {
        "lon": float(r["lon"]),
        "lat": float(r["lat"]),
        "display_name": r.get("display_name"),
        "osm_type": r.get("type"),
        "importance": r.get("importance"),
    }
