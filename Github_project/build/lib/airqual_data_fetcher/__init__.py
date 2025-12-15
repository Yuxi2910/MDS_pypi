from airqual_data_fetcher.api_client import build_source1_dataset, fetch_hourly_history_30d
from airqual_data_fetcher.cleaning import (
    clean_source1_to_hourly_panel,
    summarize_city_30d,
    climate_table_to_monthly_panel,
    drop_nan_metric_cols,
)
from airqual_data_fetcher.data_pipeline import run_source1_pipeline, run_source2_pipeline
from airqual_data_fetcher.web_scraping import (
    build_source2_wiki_climate,
    fetch_wiki_climate_table,
    city_label_to_wiki_slug,
)

__all__ = [
    # Source 1
    "build_source1_dataset",
    "fetch_hourly_history_30d",
    "clean_source1_to_hourly_panel",
    "summarize_city_30d",
    "run_source1_pipeline",

    # Source 2
    "fetch_wiki_climate_table",
    "city_label_to_wiki_slug",
    "build_source2_wiki_climate",
    "climate_table_to_monthly_panel",
    "drop_nan_metric_cols",
    "run_source2_pipeline",
]
