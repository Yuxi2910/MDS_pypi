"""
One orchestration function that produces all Source 1 outputs (raw + cleaned + city summary)

"""
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import pandas as pd

from airqual_data_fetcher.api_client import build_source1_dataset
from airqual_data_fetcher.cleaning import clean_source1_to_hourly_panel, summarize_city_30d
from .web_scraping import build_source2_wiki_climate
from .city_catalog import build_city_catalog
from .merge_utils import (
    prepare_source1_hourly_for_merge,
    prepare_source2_monthly_for_merge,
    merge_source1_hourly_with_source2_monthly,
    merge_hourly_with_city_catalog,
)

# -------------------------
# SOURCE 1 (Google Air Quality API)
# -------------------------
def run_source1_pipeline(
    cities: Dict[str, Tuple[float, float]],
    out_dir: str = "data",
    api_key: Optional[str] = None
) -> dict:
    """
    Runs Source 1 end-to-end and writes 3 files:
      - source1_raw.csv
      - source1_hourly_panel.csv
      - source1_city_summary_30d.csv

    Returns dict of DataFrames: {"raw": ..., "hourly_panel": ..., "city_summary": ...}
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    df_raw = build_source1_dataset(cities, api_key=api_key)
    df_raw.to_csv(out / "source1_raw.csv", index=False)

    hourly_panel = clean_source1_to_hourly_panel(df_raw)
    hourly_panel.to_csv(out / "source1_hourly_panel.csv", index=False)

    city_summary = summarize_city_30d(hourly_panel)
    city_summary.to_csv(out / "source1_city_summary_30d.csv", index=False)

    return {"raw": df_raw, "hourly_panel": hourly_panel, "city_summary": city_summary}


# -------------------------
# SOURCE 2 (Wikipedia)
# -------------------------
def run_source2_pipeline(
    cities: List[str],
    out_dir: str = "data",
    drop_nan_cols_how: Optional[str] = "any", 
    slug_overrides: Optional[dict[str, str]] = None,
    include_unknown: bool = True,
    metrics: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Writes:
      - source2_wikipedia_climate_monthly.csv
    Returns:
      - df_source2 (city, month_num, climate metrics...)
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    df_source2 = build_source2_wiki_climate(
        cities=cities,
        drop_nan_cols_how=drop_nan_cols_how,
        slug_overrides=slug_overrides,
        include_unknown=include_unknown,
        metrics=metrics,
    )

    df_source2.to_csv(out / "source2_wikipedia_climate_monthly.csv", index=False)
    return df_source2


# -------------------------
# MERGE (Source 1 + 2) 
# -------------------------
def merge_source1_source2(data_dir: Path) -> Path:
    df_s1 = pd.read_csv(data_dir / "source1_hourly_panel.csv")
    df_s2 = pd.read_csv(data_dir / "source2_wikipedia_climate_monthly.csv")

    df_s1p = prepare_source1_hourly_for_merge(df_s1)
    df_s2p = prepare_source2_monthly_for_merge(df_s2)

    df_12 = merge_source1_hourly_with_source2_monthly(df_s1p, df_s2p)
    out = data_dir / "source1_source2_merged_hourly.csv"
    df_12.to_csv(out, index=False)
    return out


# -------------------------
# city_catalog
# -------------------------
def build_and_save_city_catalog(data_dir: Path) -> Path:
    wc_raw = pd.read_csv(data_dir / "worldcities.csv")
    city_catalog = build_city_catalog(wc_raw)
    out = data_dir / "city_catalog.csv"
    city_catalog.to_csv(out, index=False)
    return out


# -------------------------
# MERGE (Source 1 + 2 + 3) 
# -------------------------
def merge_with_city_catalog(data_dir: Path) -> Path:
    df_12 = pd.read_csv(data_dir / "source1_source2_merged_hourly.csv")
    city_catalog = pd.read_csv(data_dir / "city_catalog.csv")

    df_123 = merge_hourly_with_city_catalog(df_12, city_catalog)
    out = data_dir / "source123_hourly.csv"
    df_123.to_csv(out, index=False)
    return out
