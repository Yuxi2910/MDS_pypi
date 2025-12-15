from __future__ import annotations

# =========================
# Source 1 (Google air quality api) cleaning
# =========================
import re
from typing import List
import pandas as pd

KEYS = ["city", "latitude", "longitude", "dateTime"]


def _safe_col(s: str) -> str:
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def clean_source1_to_hourly_panel(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Convert stacked raw (AQI rows + pollutant rows) into a tidy hourly panel:

      1 row = 1 city-hour
      columns = AQI columns (one per AQI type) + pollutant concentration columns

    AQI type column naming:
      - uses aqi_code if available, else uses aqi_displayName (e.g., 'Universal AQI', 'NAQI (IN)')
    """
    df = df_raw.copy()

    # datetime to UTC
    df["dateTime"] = pd.to_datetime(df["dateTime"], utc=True, errors="coerce")
    df = df[df["dateTime"].notna()].copy()
    df["month_num"] = df["dateTime"].dt.month
    df["year"] = df["dateTime"].dt.year

    # --- AQI long -> wide
    aqi_long = df[df["aqi"].notna()].copy()
    aqi_long["aqi"] = pd.to_numeric(aqi_long["aqi"], errors="coerce")
    aqi_long = aqi_long[aqi_long["aqi"].notna()].copy()

    aqi_long["aqi_type"] = (
        aqi_long["aqi_code"]
        .fillna(aqi_long["aqi_displayName"])
        .fillna("AQI")
        .map(_safe_col)
    )

    aqi_wide = (
        aqi_long.pivot_table(index=KEYS, columns="aqi_type", values="aqi", aggfunc="max")
        .reset_index()
    )
    aqi_wide.columns = [f"aqi_{c}" if c not in KEYS else c for c in aqi_wide.columns]

    meta_cols = [c for c in ["region_code", "category", "dominantPollutant"] if c in aqi_long.columns]
    meta = (
        aqi_long[KEYS + meta_cols]
        .sort_values(KEYS)
        .groupby(KEYS, as_index=False)
        .agg({c: "first" for c in meta_cols})
    )

    pol_long = df[df["pollutant_code"].notna()].copy()
    pol_long["pollutant_concentration_value"] = pd.to_numeric(
        pol_long["pollutant_concentration_value"], errors="coerce"
    )
    pol_long = pol_long.dropna(subset=["pollutant_concentration_value"]).copy()

    pol_wide = (
        pol_long.pivot_table(
            index=KEYS,
            columns="pollutant_code",
            values="pollutant_concentration_value",
            aggfunc="mean",
        )
        .reset_index()
    )

    panel = aqi_wide.merge(meta, on=KEYS, how="left").merge(pol_wide, on=KEYS, how="outer")
    panel = panel.sort_values(KEYS).reset_index(drop=True)

    aqi_cols = [c for c in panel.columns if c.startswith("aqi_")]
    pollutant_cols = [
        c for c in panel.columns
        if c not in KEYS and not c.startswith("aqi_") and c not in meta_cols
    ]
    panel["has_any_aqi"] = panel[aqi_cols].notna().any(axis=1) if aqi_cols else False
    panel["n_pollutants_present"] = panel[pollutant_cols].notna().sum(axis=1)

    return panel


def summarize_city_30d(panel_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    City-level summary over the 30-day window:

      1 row per city
      - mean/max for each AQI column
      - mean for each pollutant column
      - coverage counts (hours_total, hours_with_any_aqi)
    """
    df = panel_hourly.copy()

    aqi_cols = [c for c in df.columns if c.startswith("aqi_")]
    pollutant_cols = [
        c for c in df.columns
        if c not in KEYS
        and c not in ["region_code", "category", "dominantPollutant", "n_pollutants_present", "has_any_aqi"]
        and not c.startswith("aqi_")
    ]

    agg = {}
    for c in aqi_cols:
        agg[c] = ["mean", "max"]
    for c in pollutant_cols:
        agg[c] = ["mean"]

    out = df.groupby(["city", "latitude", "longitude"], as_index=False).agg(agg)

    # flatten multi-index columns
    out.columns = [
        col[0] if col[1] == "" else f"{col[0]}_{col[1]}"
        for col in out.columns.to_flat_index()
    ]

    hours_total = df.groupby(["city", "latitude", "longitude"])["dateTime"].nunique()
    hours_with_any_aqi = df[df["has_any_aqi"]].groupby(["city", "latitude", "longitude"])["dateTime"].nunique()

    out = out.set_index(["city", "latitude", "longitude"])
    out["hours_total"] = hours_total
    out["hours_with_any_aqi"] = hours_with_any_aqi
    out["hours_with_any_aqi"] = out["hours_with_any_aqi"].fillna(0).astype(int)
    out = out.reset_index()

    return out



# =========================
# Source 2 (Wikipedia) cleaning
# =========================
import re
from typing import Optional, Sequence
import pandas as pd

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
MONTH_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", re.I)

METRIC_MAP = {
    "Record high": "record_high_c",
    "Mean daily maximum": "mean_daily_max_c",
    "Daily mean": "daily_mean_c",
    "Mean daily minimum": "mean_daily_min_c",
    "Record low": "record_low_c",
    "Average precipitation mm": "avg_precip_mm",
    "Average precipitation days": "avg_precip_days_ge_1mm",
    "Average relative humidity": "avg_rel_humidity_pct",
    "Average dew point": "avg_dew_point_c",
    "Mean monthly sunshine hours": "mean_monthly_sunshine_hours",
    "Average ultraviolet index": "avg_uv_index",
}


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            str(c[-1]).strip() if str(c[-1]).strip() else str(c[0]).strip()
            for c in df.columns
        ]
    else:
        df.columns = [str(c).strip() for c in df.columns]
    return df


def _slugify_metric(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s[:80]


def _standardize_metric(label: str, metric_map: dict) -> Optional[str]:
    if label is None:
        return None
    s = str(label).strip()
    s_low = s.lower()
    for k, v in metric_map.items():
        if s_low.startswith(k.lower()):
            return v
    return None


def _first_float(x):
    if pd.isna(x):
        return None
    s = str(x)
    m = re.search(r"[-+]?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None


def climate_table_to_monthly_panel(
    df_raw: pd.DataFrame,
    city_label: str,
    metric_map: dict = METRIC_MAP,
    include_unknown: bool = True,
    metrics: list[str] | None = None,   
) -> pd.DataFrame:
    """
    Output: one row per (city, month_num), columns are standardized metrics.
    """
    df = _flatten_columns(df_raw).copy()

    # Rename first column to metric
    df = df.rename(columns={df.columns[0]: "metric"})

    # Month columns
    month_cols = [c for c in df.columns if MONTH_RE.match(str(c).strip())]
    if not month_cols:
        raise ValueError("No month columns detected in climate table.")

    # Keep only metric + months, year dropped
    df = df[["metric"] + month_cols].copy()

    # Long form
    long = df.melt(id_vars=["metric"], value_vars=month_cols, var_name="month", value_name="raw")
    long["value"] = long["raw"].map(_first_float)

    # Drop completely non-numeric entries
    long = long[long["value"].notna()].copy()

    # standardize metric name
    long["metric_std"] = long["metric"].apply(lambda x: _standardize_metric(x, metric_map))

    if include_unknown:
        mask = long["metric_std"].isna()
        long.loc[mask, "metric_std"] = long.loc[mask, "metric"].apply(_slugify_metric)
    else:
        long = long[long["metric_std"].notna()].copy()

    if metrics is not None:
        keep = set(metrics)
        long = long[long["metric_std"].isin(keep)].copy()

    long["city"] = city_label
    long["month"] = long["month"].astype(str).str[:3]
    month_order = {m: i + 1 for i, m in enumerate(MONTHS)}
    long["month_num"] = long["month"].map(month_order)

    panel = (
        long.pivot_table(
            index=["city", "month_num"],
            columns="metric_std",
            values="value",
            aggfunc="first",
        )
        .reset_index()
        .sort_values(["city", "month_num"])
    )
    return panel


def drop_nan_metric_cols(
    df: pd.DataFrame,
    how: str = "any",               
    key_cols: Sequence[str] = ("city", "month_num"),
) -> pd.DataFrame:
    """
    Drop metric columns that contain NaN.
      how="any": drop columns that have >=1 NaN
      how="all": drop columns that are all NaN
    Keeps key_cols always.
    """
    if df.empty:
        return df

    keys = [c for c in key_cols if c in df.columns]
    metric_cols = [c for c in df.columns if c not in keys]

    if how == "any":
        keep_metrics = [c for c in metric_cols if not df[c].isna().any()]
    elif how == "all":
        keep_metrics = [c for c in metric_cols if not df[c].isna().all()]
    else:
        raise ValueError("how must be 'any' or 'all'")

    return df[keys + keep_metrics]


# =========================
# Source 3 (city catalog) cleaning
# =========================

import re
import unicodedata
import pandas as pd
from pathlib import Path


def normalize_text_nfkc(x) -> str | pd.NA:
    """Normalize text for reliable joins (Unicode NFKC + whitespace cleanup)."""
    if pd.isna(x):
        return pd.NA
    s = str(x).strip()
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace(" ,", ",")
    return s