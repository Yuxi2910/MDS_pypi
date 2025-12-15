from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd
import matplotlib.pyplot as plt


@dataclass
class EDAConfig:
    city_col: str = "city"
    dt_col: str = "dateTime"
    aqi_col: str = "aqi_uaqi"
    clim_prefix: str = "clim_"
    aqi_prefix: str = "aqi_"
    merge_citycat_indicator: str = "_merge_citycat"


def load_and_prepare(
    csv_path: str,
    cfg: EDAConfig = EDAConfig(),
    cities: Optional[Iterable[str]] = None,
    sample_only: bool = False,
    keep_citycat_matched_only: bool = True,
) -> pd.DataFrame:

    df = pd.read_csv(csv_path)

    df[cfg.dt_col] = pd.to_datetime(df[cfg.dt_col], utc=True, errors="coerce")
    df = df[df[cfg.dt_col].notna()].copy()

    if keep_citycat_matched_only and cfg.merge_citycat_indicator in df.columns:
        df = df[df[cfg.merge_citycat_indicator] == "both"].copy()

    if sample_only and cities is not None:
        cities = list(cities)
        df = df[df[cfg.city_col].isin(cities)].copy()

    return df


def get_feature_columns(
    df: pd.DataFrame,
    cfg: EDAConfig = EDAConfig(),
    clim_keep: Optional[list[str]] = None,
) -> dict:
    """
    Return a dict of column lists: AQI columns, climate columns, and selected climate subset.
    """
    aqi_cols = [c for c in df.columns if c.startswith(cfg.aqi_prefix)]
    clim_cols = [c for c in df.columns if c.startswith(cfg.clim_prefix)]

    if clim_keep is None:
        clim_keep = [
            "clim_avg_rel_humidity_pct",
            "clim_daily_mean_c",
            "clim_mean_daily_max_c",
            "clim_mean_daily_min_c",
            "clim_mean_monthly_sunshine_hours",
            "clim_record_high_c",
            "clim_record_low_c",
        ]
    clim_keep = [c for c in clim_keep if c in df.columns]

    return {"aqi_cols": aqi_cols, "clim_cols": clim_cols, "clim_keep": clim_keep}


def dataset_overview(df: pd.DataFrame, cfg: EDAConfig = EDAConfig()) -> dict:
    out = {
        "shape": df.shape,
        "n_cities": int(df[cfg.city_col].nunique()),
        "date_min": df[cfg.dt_col].min(),
        "date_max": df[cfg.dt_col].max(),
        "rows_per_city": df[cfg.city_col].value_counts().to_dict(),
    }
    return out


def missingness_report(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    """
    Missing-value counts for a given set of columns.
    """
    if not cols:
        return pd.Series(dtype="int64")
    return df[cols].isna().sum().sort_values(ascending=False)


def describe_selected(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return pd.DataFrame()
    return df[cols].describe()


def city_summary_aqi(df: pd.DataFrame, cfg: EDAConfig = EDAConfig()) -> pd.DataFrame:
    """
    City-level summary table for AQI.
    """
    g = (
        df.groupby(cfg.city_col)[cfg.aqi_col]
        .agg(count="count", mean="mean", median="median", std="std", min="min", max="max")
        .sort_values("mean", ascending=False)
    )
    return g


def plot_aqi_daily_timeseries(
    df: pd.DataFrame,
    cfg: EDAConfig = EDAConfig(),
    figsize: tuple[int, int] = (12, 6),
) -> None:
    """
    Plot daily mean AQI per city to smooth hourly noise.
    """
    df_daily = (
        df.set_index(cfg.dt_col)
        .groupby(cfg.city_col)[cfg.aqi_col]
        .resample("D")
        .mean()
        .reset_index()
    )

    plt.figure(figsize=figsize)
    for city, g in df_daily.groupby(cfg.city_col):
        plt.plot(g[cfg.dt_col], g[cfg.aqi_col], label=city)

    plt.title("Daily mean AQI over time")
    plt.xlabel("Date (UTC)")
    plt.ylabel(cfg.aqi_col)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_aqi_box_by_city(
    df: pd.DataFrame,
    cfg: EDAConfig = EDAConfig(),
    figsize: tuple[int, int] = (12, 6),
) -> None:
    """
    Boxplot of hourly AQI distribution by city (outliers hidden).
    """
    d = df[[cfg.city_col, cfg.aqi_col]].dropna().copy()
    if d.empty:
        return

    city_order = (
        d.groupby(cfg.city_col)[cfg.aqi_col].median().sort_values(ascending=False).index.tolist()
    )
    data = [d.loc[d[cfg.city_col] == c, cfg.aqi_col].values for c in city_order]

    plt.figure(figsize=figsize)
    plt.boxplot(data, labels=city_order, showfliers=False)
    plt.xticks(rotation=45, ha="right")
    plt.title("AQI distribution by city (hourly)")
    plt.ylabel(cfg.aqi_col)
    plt.grid(True, axis="y")
    plt.tight_layout()
    plt.show()


def corr_matrix(
    df: pd.DataFrame,
    cols: list[str],
    min_complete_rows: int = 50,
) -> pd.DataFrame:
    """
    Return correlation matrix for selected columns using only complete rows.
    """
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 2:
        return pd.DataFrame()

    d = df[cols].dropna()
    if len(d) < min_complete_rows:
        return pd.DataFrame()

    return d.corr(numeric_only=True)


def plot_corr_heatmap_matplotlib(corr: pd.DataFrame, figsize: tuple[int, int] = (10, 6)) -> None:
    """
    Pure matplotlib heatmap (no seaborn dependency).
    """
    if corr.empty:
        return

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(corr.values)

    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.index)

    # annotate numbers
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center")

    ax.set_title("Correlation: AQI vs climate features")
    fig.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.show()
