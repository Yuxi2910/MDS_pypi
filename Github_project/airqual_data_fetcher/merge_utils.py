from typing import Tuple
import pandas as pd
from airqual_data_fetcher.cleaning import normalize_text_nfkc
from airqual_data_fetcher.city_catalog import prepare_city_catalog_for_merge

def prepare_source1_hourly_for_merge(df: pd.DataFrame, datetime_col="dateTime", city_col="city") -> pd.DataFrame:
    out = df.copy()
    out[city_col] = out[city_col].astype(str).map(normalize_text_nfkc)

    out[datetime_col] = pd.to_datetime(out[datetime_col], utc=True, errors="coerce")
    out = out[out[datetime_col].notna()].copy()

    out["month_num"] = out[datetime_col].dt.month.astype(int)
    return out


def prepare_source2_monthly_for_merge(df: pd.DataFrame, city_col="city", month_col="month_num") -> pd.DataFrame:
    out = df.copy()
    out[city_col] = out[city_col].astype(str).map(normalize_text_nfkc)

    out[month_col] = pd.to_numeric(out[month_col], errors="coerce").astype("Int64")
    out = out[out[month_col].notna()].copy()
    out[month_col] = out[month_col].astype(int)

    if out.duplicated(subset=[city_col, month_col]).any():
        dups = out[out.duplicated(subset=[city_col, month_col], keep=False)].sort_values([city_col, month_col])
        raise ValueError(f"Source2 keys are not unique. Examples:\n{dups.head(10)}")

    return out


def merge_source1_hourly_with_source2_monthly(
    df_hourly: pd.DataFrame,
    df_monthly: pd.DataFrame,
    on: Tuple[str, str] = ("city", "month_num"),
    prefix_source2: str = "clim_",
    how: str = "left",
    indicator_name: str = "_merge_s1s2",
) -> pd.DataFrame:
    left = df_hourly.copy()
    right = df_monthly.copy()

    key_cols = list(on)
    rename = {c: f"{prefix_source2}{c}" for c in right.columns if c not in key_cols}
    right = right.rename(columns=rename)

    # IMPORTANT: use a custom indicator name so later merges don't collide
    if indicator_name in left.columns:
        left = left.drop(columns=[indicator_name])

    return left.merge(
        right,
        on=key_cols,
        how=how,
        validate="m:1",
        indicator=indicator_name,
    )


def merge_hourly_with_city_catalog(
    df_hourly: pd.DataFrame,
    city_catalog: pd.DataFrame,
    city_col: str = "city",
    prefix: str = "citycat_",
    how: str = "left",
    indicator_name: str = "_merge_citycat",
) -> pd.DataFrame:
    left = df_hourly.copy()
    left[city_col] = left[city_col].map(normalize_text_nfkc)

    right = prepare_city_catalog_for_merge(city_catalog, city_col=city_col)
    rename = {c: f"{prefix}{c}" for c in right.columns if c != city_col}
    right = right.rename(columns=rename)

    # fix your error: if df already has _merge (from previous merge), don't reuse it
    if indicator_name in left.columns:
        left = left.drop(columns=[indicator_name])

    return left.merge(
        right,
        on=city_col,
        how=how,
        validate="m:1",
        indicator=indicator_name,
    )


def cities_not_matching(df1: pd.DataFrame, df2: pd.DataFrame, city_col: str = "city") -> dict:
    c1 = set(df1[city_col].astype(str).map(normalize_text_nfkc).unique())
    c2 = set(df2[city_col].astype(str).map(normalize_text_nfkc).unique())
    return {
        "in_left_not_right": sorted(c1 - c2),
        "in_right_not_left": sorted(c2 - c1),
    }
