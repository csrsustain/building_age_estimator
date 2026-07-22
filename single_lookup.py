"""
Single-address building age lookup, with a 4-tier geocoding fallback,
ordered by precision:
  1. OS Places API (most precise — needs a proper commercial licence to
     use beyond the free trial)
  2. Google Geocoding API (very good UK building-level accuracy, simple
     self-serve key, small pay-as-you-go cost)
  3. Nominatim/OpenStreetMap (free, no key — but frequently only matches
     to street level, not the exact building; flagged as low confidence
     when that happens)
  4. Postcode centroid via postcodes.io (least precise, always available)

Use from a Colab cell or app.py:
    from single_lookup import estimate_building_age
    result = estimate_building_age("124 Commercial Street", "E1 6NF", os_api_key, google_api_key)
    print(result)
"""
import os_ngd_client
from address_geocode import geocode_address
from google_geocode import geocode_address_google
from nominatim_geocode import geocode_address_nominatim
from os_ngd_lookup import geocode_postcode

_BUFFER_DEG = 0.00015


def _get_coords(address: str, postcode: str, os_api_key: str, google_api_key: str = None):
    """Try each geocoding tier in order of precision, return
    (lon, lat, method_description, is_precise_building_match)."""
    try:
        match = geocode_address(address, postcode, os_api_key)
        if match:
            return (
                match["lon"],
                match["lat"],
                f"OS Places (match score: {match['match_score']}, matched: {match['matched_address']})",
                True,
            )
    except Exception as e:
        print(f"[info] OS Places unavailable ({e}), trying Google...")

    if google_api_key:
        try:
            match = geocode_address_google(address, postcode, google_api_key)
            if match:
                precision_note = (
                    "exact building (ROOFTOP)" if match["is_precise"] else f"approximate ({match['location_type']})"
                )
                return (
                    match["lon"],
                    match["lat"],
                    f"Google ({precision_note}) — matched: {match['formatted_address']}",
                    match["is_precise"],
                )
        except Exception as e:
            print(f"[info] Google Geocoding unavailable ({e}), trying Nominatim...")

    try:
        match = geocode_address_nominatim(address, postcode)
        if match:
            if not match.get("matched_exact_building"):
                print(
                    f"[warn] Nominatim only matched street-level, not the exact building: "
                    f"{match['display_name']}"
                )
            precision_note = (
                "exact building match" if match.get("matched_exact_building") else "STREET-LEVEL ONLY, not the exact building"
            )
            return (
                match["lon"],
                match["lat"],
                f"Nominatim/OSM ({precision_note}) — matched: {match['display_name']}",
                match.get("matched_exact_building", False),
            )
    except Exception as e:
        print(f"[info] Nominatim unavailable ({e}), falling back to postcode centroid...")

    coords = geocode_postcode(postcode)
    if coords:
        return coords[0], coords[1], "postcode centroid (least precise fallback)", False

    return None, None, None, False


def estimate_building_age(address: str, postcode: str, os_api_key: str, google_api_key: str = None) -> dict:
    """Look up one property live: geocode (best available method) -> OS
    NGD building age lookup around that point."""
    lon, lat, geocode_method, is_precise = _get_coords(address, postcode, os_api_key, google_api_key)

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

    client = os_ngd_client.OSNGDClient(os_api_key)
    features = client.get_building_by_bbox(min_x, min_y, max_x, max_y)

    for feat in features:
        signal = os_ngd_client.extract_age_signal(feat)
        if signal:
            confidence = "high" if signal["exact_year"] else "medium"
            note = None
            if not is_precise:
                confidence = "low"
                note = (
                    "CAUTION: the address could only be matched approximately, not to "
                    "the exact building — this age may belong to a nearby property, "
                    "not the one requested."
                )
            return {
                "address": address,
                "postcode": postcode,
                "geocode_method": geocode_method,
                "estimated_age": signal["exact_year"] or signal["age_period"],
                "confidence": confidence,
                "source": signal["source"],
                "provenance": signal.get("age_source"),
                "note": note,
            }

    return {
        "address": address,
        "postcode": postcode,
        "geocode_method": geocode_method,
        "estimated_age": None,
        "confidence": "none",
        "note": "No OS NGD building age record found for this location.",
    }
