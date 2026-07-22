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

Precision is tracked as "high" / "medium" / "low", not just a yes/no —
e.g. Google's RANGE_INTERPOLATED (estimated between known address points
on a street) is meaningfully better than a street- or postcode-level
match, even though it's not an exact rooftop match either.

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
    (lon, lat, method_description, precision_level, debug_log) where
    precision_level is 'high' / 'medium' / 'low'."""
    debug_log = []

    try:
        match = geocode_address(address, postcode, os_api_key)
        if match:
            debug_log.append("OS Places: SUCCESS")
            return (
                match["lon"],
                match["lat"],
                f"OS Places (match score: {match['match_score']}, matched: {match['matched_address']})",
                "high",
                debug_log,
            )
        debug_log.append("OS Places: no match returned (empty result)")
    except Exception as e:
        debug_log.append(f"OS Places: FAILED — {e}")

    if google_api_key:
        try:
            match = geocode_address_google(address, postcode, google_api_key)
            if match:
                debug_log.append(f"Google: SUCCESS (location_type={match['location_type']})")
                return (
                    match["lon"],
                    match["lat"],
                    f"Google ({match['location_type']}) — matched: {match['formatted_address']}",
                    match["precision_level"],
                    debug_log,
                )
            debug_log.append("Google: no match returned (empty result)")
        except Exception as e:
            debug_log.append(f"Google: FAILED — {e}")
    else:
        debug_log.append("Google: skipped (no API key provided)")

    try:
        match = geocode_address_nominatim(address, postcode)
        if match:
            exact = match.get("matched_exact_building")
            debug_log.append(f"Nominatim: SUCCESS (exact_building={exact})")
            precision_note = "exact building match" if exact else "STREET-LEVEL ONLY, not the exact building"
            return (
                match["lon"],
                match["lat"],
                f"Nominatim/OSM ({precision_note}) — matched: {match['display_name']}",
                "high" if exact else "low",
                debug_log,
            )
        debug_log.append("Nominatim: no match returned (empty result)")
    except Exception as e:
        debug_log.append(f"Nominatim: FAILED — {e}")

    coords = geocode_postcode(postcode)
    if coords:
        debug_log.append("Postcode centroid: SUCCESS (last-resort fallback)")
        return coords[0], coords[1], "postcode centroid (least precise fallback)", "low", debug_log

    debug_log.append("Postcode centroid: FAILED — could not geocode postcode at all")
    return None, None, None, "low", debug_log


def estimate_building_age(address: str, postcode: str, os_api_key: str, google_api_key: str = None) -> dict:
    """Look up one property live: geocode (best available method) -> OS
    NGD building age lookup around that point."""
    lon, lat, geocode_method, precision_level, debug_log = _get_coords(
        address, postcode, os_api_key, google_api_key
    )

    if lon is None:
        return {
            "address": address,
            "postcode": postcode,
            "estimated_age": None,
            "confidence": "none",
            "note": "Could not geocode this address or postcode via any method.",
            "debug_log": debug_log,
        }

    min_x, max_x = lon - _BUFFER_DEG, lon + _BUFFER_DEG
    min_y, max_y = lat - _BUFFER_DEG, lat + _BUFFER_DEG

    client = os_ngd_client.OSNGDClient(os_api_key)
    features = client.get_building_by_bbox(min_x, min_y, max_x, max_y)

    for feat in features:
        signal = os_ngd_client.extract_age_signal(feat)
        if signal:
            has_exact_year = bool(signal["exact_year"])
            # Overall confidence is capped by whichever is weaker: the age
            # data's own precision, or the geocoding precision.
            if precision_level == "high":
                confidence = "high" if has_exact_year else "medium"
                note = None
            elif precision_level == "medium":
                confidence = "medium"
                note = (
                    "NOTE: the address was matched to an estimated position along its "
                    "street (not an exact rooftop match) — generally close, but not "
                    "guaranteed to be the precise building."
                )
            else:
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
                "debug_log": debug_log,
            }

    return {
        "address": address,
        "postcode": postcode,
        "geocode_method": geocode_method,
        "estimated_age": None,
        "confidence": "none",
        "note": "No OS NGD building age record found for this location.",
        "debug_log": debug_log,
    }
