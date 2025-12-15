from airqual_data_fetcher.api_client import build_source1_dataset

from airqual_data_fetcher.data_pipeline import run_source1_pipeline, run_source2_pipeline
from airqual_data_fetcher.web_scraping import build_source2_wiki_climate

from airqual_data_fetcher.city_catalog import build_city_catalog
from airqual_data_fetcher.merge_utils import (
    merge_source1_hourly_with_source2_monthly,
    merge_hourly_with_city_catalog,
)

__all__ = [
    # Source 1
    "build_source1_dataset",
    "run_source1_pipeline",

    # Source 2
    "build_source2_wiki_climate",
    "run_source2_pipeline",

    # Source 3
    "build_city_catalog",

    # Merging
    "merge_source1_hourly_with_source2_monthly",
    "merge_hourly_with_city_catalog",
    ]
