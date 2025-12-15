import os
import time
from typing import Dict, Tuple, List, Any, Optional

import requests
import pandas as pd

BASE_URL = "https://airquality.googleapis.com/v1/history:lookup"


def _post_history(payload: dict, api_key: str, timeout: int = 30) -> dict:
    url = f"{BASE_URL}?key={api_key}"
    r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)

    # transient errors
    if r.status_code in (429, 500, 502, 503, 504):
        raise RuntimeError(f"Transient API error {r.status_code}: {r.text}")

    if r.status_code != 200:
        raise RuntimeError(f"API error {r.status_code}: {r.text}")

    return r.json()


def fetch_hourly_history_30d(
    lat: float,
    lon: float,
    api_key: str,
    page_size: int = 168,
    extra_computations: Optional[List[str]] = None,
    sleep_s: float = 0.1,
) -> pd.DataFrame:
    """
    Fetch rolling last-30-days hourly history for one coordinate.
    Returns a STACKED DataFrame:
      - AQI rows (aqi fields filled, pollutant fields None)
      - pollutant rows (pollutant fields filled, aqi fields None)
    """
    if extra_computations is None:
        extra_computations = ["LOCAL_AQI", "HEALTH_RECOMMENDATIONS", "POLLUTANT_CONCENTRATION"]

    rows: List[Dict[str, Any]] = []
    page_token = ""

    while True:
        payload = {
            "location": {"latitude": lat, "longitude": lon},
            "hours": 24 * 30,              # rolling last 30 days
            "pageSize": page_size,
            "pageToken": page_token,
            "extraComputations": extra_computations,
            "universalAqi": True,
            "languageCode": "en",
        }

        # retry loop
        for attempt in range(6):
            try:
                data = _post_history(payload, api_key)
                break
            except RuntimeError:
                time.sleep(2 ** attempt)
        else:
            raise RuntimeError("Failed after retries when calling history endpoint.")

        region_code = data.get("regionCode")

        for h in data.get("hoursInfo", []):
            dt = h.get("dateTime")

            # AQI index rows
            for idx in h.get("indexes", []):
                rows.append({
                    "dateTime": dt,
                    "region_code": region_code,
                    "aqi_code": idx.get("code"),  # sometimes missing
                    "aqi_displayName": idx.get("displayName"),
                    "aqi": idx.get("aqi"),
                    "category": idx.get("category"),
                    "dominantPollutant": idx.get("dominantPollutant"),
                    # pollutant fields empty
                    "pollutant_code": None,
                    "pollutant_displayName": None,
                    "pollutant_fullName": None,
                    "pollutant_concentration_value": None,
                    "pollutant_concentration_units": None,
                })

            # pollutant rows
            for pol in h.get("pollutants", []):
                conc = pol.get("concentration", {})
                rows.append({
                    "dateTime": dt,
                    "region_code": region_code,
                    # aqi fields empty
                    "aqi_code": None,
                    "aqi_displayName": None,
                    "aqi": None,
                    "category": None,
                    "dominantPollutant": None,
                    # pollutant fields filled
                    "pollutant_code": pol.get("code"),
                    "pollutant_displayName": pol.get("displayName"),
                    "pollutant_fullName": pol.get("fullName"),
                    "pollutant_concentration_value": conc.get("value"),
                    "pollutant_concentration_units": conc.get("units"),
                })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        time.sleep(sleep_s)

    return pd.DataFrame(rows)


def build_source1_dataset(
    cities: Dict[str, Tuple[float, float]],
    api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    Loop over city -> (lat, lon) dict and return stacked raw dataset for all cities.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_AIR_QUALITY_API_KEY")
    if not api_key:
        raise RuntimeError("Missing env var GOOGLE_AIR_QUALITY_API_KEY")

    parts = []
    for city, (lat, lon) in cities.items():
        df_city = fetch_hourly_history_30d(lat, lon, api_key=api_key)
        df_city.insert(0, "city", city)
        df_city.insert(1, "latitude", lat)
        df_city.insert(2, "longitude", lon)
        parts.append(df_city)

    return pd.concat(parts, ignore_index=True)

