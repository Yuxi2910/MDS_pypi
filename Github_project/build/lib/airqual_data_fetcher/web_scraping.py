from __future__ import annotations

import time
from io import StringIO
from typing import Optional

import pandas as pd
import requests

from .cleaning import (
    WIKI_MONTH_RE,
    WIKI_METRIC_MAP,
    drop_nan_metric_cols,
    flatten_columns,
    climate_table_to_monthly_panel
)

# -----------------------
# Session + headers
# -----------------------
def get_headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }

_session = requests.Session()
_session.headers.update(get_headers())


def city_label_to_wiki_slug(city_label: str) -> str:
    # "Beijing, China" -> "Beijing"
    base = city_label.split(",")[0].strip()
    return base.replace(" ", "_")


def fetch_wiki_climate_table(city_slug: str, timeout: int = 30) -> pd.DataFrame:
    """
    Fetch Wikipedia page and return the most climate-like table (wide with Jan–Dec columns).
    """
    url = f"https://en.wikipedia.org/wiki/{city_slug}"
    r = _session.get(url, timeout=timeout)
    r.raise_for_status()

    # Prefer wikitable tables; fallback to all tables if needed
    try:
        tables = pd.read_html(StringIO(r.text), attrs={"class": "wikitable"})
        if not tables:
            tables = pd.read_html(StringIO(r.text))
    except ValueError:
        tables = pd.read_html(StringIO(r.text))

    best = None
    best_score = -1

    for t in tables:
        t2 = flatten_columns(t)
        cols = [str(c).strip() for c in t2.columns]

        month_hits = sum(1 for c in cols if WIKI_MONTH_RE.match(c))
        year_hit = any(str(c).strip().lower().startswith("year") for c in cols)

        first_col = t2.columns[0]
        first_vals = t2[first_col].astype(str).str.strip().str.lower()

        metric_key_hits = any(first_vals.str.startswith(k.lower()).any() for k in WIKI_METRIC_MAP.keys())
        common_row_hits = (
            first_vals.str.contains("daily mean").any()
            or first_vals.str.contains("precip").any()
            or first_vals.str.contains("humidity").any()
            or first_vals.str.contains("record high").any()
            or first_vals.str.contains("record low").any()
        )

        score = month_hits * 10 + (20 if year_hit else 0) + (30 if (metric_key_hits or common_row_hits) else 0)

        if year_hit and month_hits >= 8 and score > best_score:
            best = t2
            best_score = score

    if best is None:
        raise ValueError(f"No climate-like table found for {city_slug}.")

    return best


def build_source2_wiki_climate(
    cities: list[str],
    sleep_s: float = 0.5,
    include_unknown: bool = True,
    metrics: Optional[list[str]] = None,
    slug_overrides: Optional[dict[str, str]] = None,
    drop_nan_cols_how: bool = True,  
) -> pd.DataFrame:
    """
    Build Source 2 monthly panel for multiple cities.

    Returns: DataFrame with columns:
      city, month_num, <climate metrics...>
    """
    slug_overrides = slug_overrides or {}
    parts: list[pd.DataFrame] = []

    for city_label in cities:
        slug = slug_overrides.get(city_label, city_label_to_wiki_slug(city_label))
        try:
            raw = fetch_wiki_climate_table(slug)
            panel = climate_table_to_monthly_panel(
                df_raw=raw,
                city_label=city_label,
                include_unknown=include_unknown,
                metrics=metrics,
            )
            parts.append(panel)
            print("OK:", city_label, "->", slug, "| rows:", len(panel))
        except Exception as e:
            print("FAILED:", city_label, "->", slug, "|", e)

        time.sleep(sleep_s)

    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    if not df.empty and drop_nan_cols_how is not None:
        df = drop_nan_metric_cols(df, how=drop_nan_cols_how, key_cols=("city", "month_num"))

    return df
