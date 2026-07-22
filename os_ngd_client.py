"""
OS NGD Building Features client — Tier 1 source (Building Age Period /
Building Age Year attributes).

Access: OS Data Hub, "OS NGD API - Features", Premium API plan. First
£1,000/month of transactions are free, then pay-per-transaction — you do
NOT need a PSGA (public sector) agreement as a private company, contrary
to some guidance floating around online. Sign up at:
    https://osdatahub.os.uk/

Key caveats to keep in mind when reading results:
  - `buildingageyear` (an exact year) is only populated for buildings
    constructed after 1999. Everything older only gets `buildingageperiod`
    (a banded range, e.g. "1919-1944"), and pre-1919 buildings often only
    get the broad "Pre-1919" catch-all unless better data exists.
  - The underlying age data originates from Verisk, supplemented by OS
    survey — treat it as a strong signal, not a certified record.
"""
from typing import Optional

import requests

FEATURES_URL = "https://api.os.uk/features/ngd/ofa/v1/collections/bld-fts-building-4/items"


class OSNGDClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_building_by_bbox(
        self, min_x: float, min_y: float, max_x: float, max_y: float, limit: int = 100
    ) -> list:
        """Fetch building features intersecting a bounding box. Coordinates
        should be lon/lat (WGS84) — that's the API's default CRS, so no
        extra CRS parameter is needed."""
        params = {
            "key": self.api_key,
            "bbox": f"{min_x},{min_y},{max_x},{max_y}",
            "limit": limit,
        }
        resp = requests.get(FEATURES_URL, params=params, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise requests.HTTPError(str(e).replace(self.api_key, "REDACTED"), response=resp) from None
        return resp.json().get("features", [])


_AGE_YEAR_CANDIDATES = ["buildingage_year", "buildingageyear", "BuildingAgeYear"]
_AGE_PERIOD_CANDIDATES = ["buildingage_period", "buildingageperiod", "BuildingAgePeriod"]


def extract_age_signal(feature: dict) -> Optional[dict]:
    """Pull age fields out of one OS NGD building feature (GeoJSON)."""
    props = feature.get("properties", {})
    age_year = next((props[k] for k in _AGE_YEAR_CANDIDATES if props.get(k)), None)
    age_period = next((props[k] for k in _AGE_PERIOD_CANDIDATES if props.get(k)), None)
    if age_year is None and not age_period:
        return None
    return {
        "toid": props.get("toid"),
        "exact_year": age_year,
        "age_period": age_period,
        "age_source": props.get("buildingage_source"),
        "age_evidence_date": props.get("buildingage_evidencedate"),
        "source": "OS_NGD_TIER1" if age_year else "OS_NGD_TIER1_BAND",
    }
