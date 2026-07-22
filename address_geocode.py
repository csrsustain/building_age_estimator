"""
Precise address-level geocoding via OS Places API ("Find" endpoint) —
replaces postcode-centroid geocoding with an actual address match.

Needs the "OS Places API" product added to your OS Data Hub project (same
API key, just add the product on the Data Hub site).

IMPORTANT: the exact field names OS returns for coordinates haven't been
confirmed against a live response yet (same situation we hit with OS NGD
earlier) — this prints the raw first result on first use so we can check
and correct field names immediately if needed, rather than guessing.
"""
import requests

FIND_URL = "https://api.os.uk/search/places/v1/find"

_debug_shown = [False]

# Candidate field names for lon/lat — confirm against the debug printout
_LNG_CANDIDATES = ["LNG", "LONGITUDE", "X_COORDINATE"]
_LAT_CANDIDATES = ["LAT", "LATITUDE", "Y_COORDINATE"]


def geocode_address(address_text: str, postcode: str, api_key: str):
    """Look up a full address via OS Places 'Find'. Returns
    (lon, lat, uprn, match_score, matched_address) or None if no match."""
    query = f"{address_text}, {postcode}".strip(", ")
    params = {"query": query, "key": api_key, "maxresults": 1, "output_srs": "WGS84"}
    resp = requests.get(FIND_URL, params=params, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(str(e).replace(api_key, "REDACTED"), response=resp) from None
    data = resp.json()

    results = data.get("results", [])
    if not results:
        return None

    dpa = results[0].get("DPA", {})

    if not _debug_shown[0]:
        print("[debug] Example raw OS Places result (first hit only):")
        print(dpa)
        _debug_shown[0] = True

    lng = next((dpa[k] for k in _LNG_CANDIDATES if dpa.get(k) is not None), None)
    lat = next((dpa[k] for k in _LAT_CANDIDATES if dpa.get(k) is not None), None)
    if lng is None or lat is None:
        return None

    return {
        "lon": float(lng),
        "lat": float(lat),
        "uprn": dpa.get("UPRN"),
        "match_score": dpa.get("MATCH"),
        "matched_address": dpa.get("ADDRESS"),
        "classification_code": dpa.get("CLASSIFICATION_CODE"),
        "classification_description": dpa.get("CLASSIFICATION_CODE_DESCRIPTION"),
    }
