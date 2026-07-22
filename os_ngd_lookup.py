"""
Ties together: postcode -> coordinates (via the free postcodes.io API) ->
OS NGD building lookup (Tier 1: real construction age data).

Designed to be called from a Colab cell so your API key stays in memory
only, never written to a file:

    from os_ngd_lookup import run_os_ngd_lookup
    run_os_ngd_lookup(OS_API_KEY, "pilot_results.csv", "pilot_results_with_os_ngd.csv")

This does NOT print or save your API key anywhere, and redacts it from
any error message before printing.

Scaling notes (added once we moved past an 11-property test):
  - Duplicate postcodes are only geocoded once (many properties on the
    same industrial estate share a postcode) — cached in-memory.
  - Progress is printed every 25 properties so a 500-row run doesn't look
    like it's hung.
  - A coverage summary is printed at the end: % exact year, % banded,
    % no match — this is the real number you're after.
  - A small pause between requests keeps you well under any rate limit.
"""
import csv
import time
from collections import Counter

import requests

import os_ngd_client

POSTCODES_IO_URL = "https://api.postcodes.io/postcodes/"
# Roughly a 40m box around the point, in degrees (good enough for one building)
_BUFFER_DEG = 0.0004

_geocode_cache = {}


def geocode_postcode(postcode: str):
    """Free, no-key UK postcode -> lat/lon lookup via postcodes.io, cached
    so repeated postcodes (common on industrial estates) cost one call."""
    pc = (postcode or "").strip().upper()
    if not pc:
        return None
    if pc in _geocode_cache:
        return _geocode_cache[pc]
    try:
        resp = requests.get(POSTCODES_IO_URL + pc, timeout=15)
        result = resp.json().get("result") if resp.status_code == 200 else None
        coords = (result["longitude"], result["latitude"]) if result else None
    except requests.RequestException:
        coords = None
    _geocode_cache[pc] = coords
    return coords


def run_os_ngd_lookup(api_key: str, input_csv: str, output_csv: str, pause_seconds: float = 0.25):
    client = os_ngd_client.OSNGDClient(api_key)

    with open(input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    results = []
    tier_counts = Counter()
    debug_shown = False

    for i, row in enumerate(rows, start=1):
        if i % 25 == 0 or i == total:
            print(f"  ...processed {i}/{total}")

        postcode = row.get("postcode", "")
        coords = geocode_postcode(postcode)

        os_tier = "TIER_1_NO_MATCH"
        os_detail = None

        if coords:
            lon, lat = coords
            min_x, max_x = lon - _BUFFER_DEG, lon + _BUFFER_DEG
            min_y, max_y = lat - _BUFFER_DEG, lat + _BUFFER_DEG
            try:
                features = client.get_building_by_bbox(min_x, min_y, max_x, max_y)
                if features and not debug_shown:
                    print("[debug] Example raw feature properties (first hit only):")
                    print(features[0].get("properties", {}))
                    debug_shown = True
                for feat in features:
                    signal = os_ngd_client.extract_age_signal(feat)
                    if signal:
                        os_tier = signal["source"]
                        os_detail = signal["exact_year"] or signal["age_period"]
                        break
            except requests.HTTPError as e:
                os_detail = f"API error: {str(e).replace(api_key, 'REDACTED')}"
        else:
            os_detail = "postcode geocoding failed"

        tier_counts[os_tier] += 1
        results.append({**row, "os_ngd_tier": os_tier, "os_ngd_detail": os_detail})
        time.sleep(pause_seconds)

    fieldnames = list(rows[0].keys()) + ["os_ngd_tier", "os_ngd_detail"]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n--- OS NGD coverage summary ({total} properties) ---")
    for tier, count in sorted(tier_counts.items()):
        pct = 100 * count / total if total else 0
        print(f"  {tier}: {count} ({pct:.1f}%)")
    print(f"\nWritten to {output_csv}")
    return results
