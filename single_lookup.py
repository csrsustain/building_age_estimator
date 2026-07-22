"""
Single-address building age lookup, with a 3-tier geocoding fallback:
  1. OS Places API (most precise, but currently trial-limited for you)
  2. Nominatim/OpenStreetMap (free, no key, lower precision — new)
  3. Postcode centroid via postcodes.io (least precise, always available)

Use from a Colab cell:
    from single_lookup import estimate_building_age
    result = estimate_building_age("124 Commercial Street", "E1 6NF", OS_API_KEY)
    print(result)
"""
import os_ngd_client
from address_geocode import geocode_address
from nominatim_geocode import geocode_address_nominatim
from os_ngd_lookup import geocode_postcode

_BUFFER_DEG = 0.00015


def _get_coords(address: str, postcode: str, api_key: str):
    """Try each geocoding tier in order of precision, return
    (lon, lat, method_description) from the first one that succeeds."""
    try:
        match = geocode_address(address, postcode, api_key)
        if match:
            return (
                match["lon"],
                match["lat"],
                f"OS Places (match score: {match['match_score']}, matched: {match['matched_address']})",
            )
    except Exception as e:
        print(f"[info] OS Places unavailable ({e}), trying Nominatim...")

    try:
        match = geocode_address_nominatim(address, postcode)
        if match:
            return match["lon"], match["lat"], f"Nominatim/OSM (matched: {match['display_name']})"
    except Exception as e:
        print(f"[info] Nominatim unavailable ({e}), falling back to postcode centroid...")

    coords = geocode_postcode(postcode)
    if coords:
        return coords[0], coords[1], "postcode centroid (least precise fallback)"

    return None, None, None


def estimate_building_age(address: str, postcode: str, api_key: str) -> dict:
    """Look up one property live: geocode (best available method) -> OS
    NGD building age lookup around that point."""
    lon, lat, geocode_method = _get_coords(address, postcode, api_key)

    if lon is None:
        return {
            "address": address,
            "postcode": postcode,
            "estimated_age": None,
            "confidence": "none",
            "note": "Could not geocode this address or postcode via any method.",
        }

    min_x, max_x = lon - _BUFFER_DEG, lon + _BUFFER_DEG
    min_y, max_y = lat - _BUFFER_DEG, lat + _BUFFER_DEG

    client = os_ngd_client.OSNGDClient(api_key)
    features = client.get_building_by_bbox(min_x, min_y, max_x, max_y)

    for feat in features:
        signal = os_ngd_client.extract_age_signal(feat)
        if signal:
            return {
                "address": address,
                "postcode": postcode,
                "geocode_method": geocode_method,
                "estimated_age": signal["exact_year"] or signal["age_period"],
                "confidence": "high" if signal["exact_year"] else "medium",
                "source": signal["source"],
                "provenance": signal.get("age_source"),
                "note": None,
            }

    return {
        "address": address,
        "postcode": postcode,
        "geocode_method": geocode_method,
        "estimated_age": None,
        "confidence": "none",
        "note": "No OS NGD building age record found for this location.",
    }
