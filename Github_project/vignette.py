"""
Set up environment
"""
import os
API_KEY = os.getenv("GOOGLE_AIR_QUALITY_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing GOOGLE_AIR_QUALITY_API_KEY. Set it in your shell or in a .env file.")


"""
Source 1: Google Air Quality API data
"""
from airqual_data_fetcher.config import SAMPLE_CITIES
from airqual_data_fetcher.data_pipeline import run_source1_pipeline

dfs = run_source1_pipeline(SAMPLE_CITIES, out_dir="data")
dfs["raw"].shape, dfs["hourly_panel"].shape, dfs["city_summary"].shape

"""
check the three output files
"""
import os
os.listdir("data")


"""
Source 2: Wikipedia climate data
"""
from airqual_data_fetcher.data_pipeline import run_source2_pipeline
from airqual_data_fetcher.config import cities

df_source2 = run_source2_pipeline(cities, out_dir="data", drop_nan_cols_how="any")
df_source2.head(), df_source2.shape


"""
Merged Source 1 & Source 2 and Source 1 & 2 & city_catalog datasets
"""
from pathlib import Path
from airqual_data_fetcher.data_pipeline import (
    build_and_save_city_catalog, merge_source1_source2, merge_with_city_catalog
)

DATA_DIR = Path("data")
build_and_save_city_catalog(DATA_DIR)
merge_source1_source2(DATA_DIR)
merge_with_city_catalog(DATA_DIR)


"""
summary analysis
"""
from airqual_data_fetcher.eda_utils import (
    EDAConfig,
    load_and_prepare,
    get_feature_columns,
    dataset_overview,
    missingness_report,
    describe_selected,
    city_summary_aqi,
    plot_aqi_daily_timeseries,
    plot_aqi_box_by_city,
    corr_matrix,
    plot_corr_heatmap_matplotlib,
)

cfg = EDAConfig(
    city_col="city",
    dt_col="dateTime",
    aqi_col="aqi_uaqi",
)

cities_1 = [
    "Delhi, India",
    "Shenzhen, China",
    "Bangkok, Thailand",
    "Tokyo, Japan",
]

df = load_and_prepare(
    csv_path="data/source123_hourly.csv",
    cfg=cfg,
    cities=cities_1,
    sample_only=True,             
    keep_citycat_matched_only=True
)

# Overview
ov = dataset_overview(df, cfg)
print(ov["shape"], ov["n_cities"], ov["date_min"], ov["date_max"])
print(pd.Series(ov["rows_per_city"]))

# Columns
cols = get_feature_columns(df, cfg)
aqi_cols = cols["aqi_cols"]
clim_cols = cols["clim_cols"]
clim_keep = cols["clim_keep"]

# Missingness
print("\nAQI missingness:\n", missingness_report(df, aqi_cols))
print("\nClimate missingness (top 20):\n", missingness_report(df, clim_cols).head(20))

# Describe (selected)
from IPython.display import display

selected = [cfg.aqi_col] + clim_keep
display(describe_selected(df, selected))

# City AQI summary table
display(city_summary_aqi(df, cfg))

# Plots
plot_aqi_daily_timeseries(df, cfg)
plot_aqi_box_by_city(df, cfg)

# Correlation heatmap (AQI vs climate keep)
corr = corr_matrix(df, selected, min_complete_rows=50)
plot_corr_heatmap_matplotlib(corr)
