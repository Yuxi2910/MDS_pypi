import pandas as pd
from airqual_data_fetcher.cleaning import normalize_text_nfkc

def build_city_catalog(worldcities: pd.DataFrame) -> pd.DataFrame:
    """
    Build city_catalog from worldcities.csv.

    Output columns:
      - city (shared join key like "Tokyo, Japan")
      - admin_name
      - capital
      - population (numeric)
    """
    wc = worldcities.copy()

    # create shared "city" label
    wc["city"] = wc["city_ascii"].fillna(wc["city"]).astype(str) + ", " + wc["country"].astype(str)
    wc["city"] = wc["city"].map(normalize_text_nfkc)

    keep = ["city", "admin_name", "capital", "population"]
    wc = wc[keep].copy()

    wc["admin_name"] = wc["admin_name"].map(normalize_text_nfkc)
    wc["capital"] = wc["capital"].map(normalize_text_nfkc)
    wc["population"] = pd.to_numeric(wc["population"], errors="coerce")

    # dedupe: keep the largest population per city label
    wc = wc.sort_values(["city", "population"], ascending=[True, False])
    wc = wc.drop_duplicates(subset=["city"], keep="first").reset_index(drop=True)

    return wc


def prepare_city_catalog_for_merge(
    city_catalog: pd.DataFrame,
    city_col: str = "city",
) -> pd.DataFrame:
    """
    Ensure city_catalog has unique city key for a clean m:1 merge.
    """
    out = city_catalog.copy()
    out[city_col] = out[city_col].map(normalize_text_nfkc)

    # must be unique on city
    if out.duplicated(subset=[city_col]).any():
        dups = out[out.duplicated(subset=[city_col], keep=False)].sort_values(city_col)
        raise ValueError(f"city_catalog has duplicate city keys. Examples:\n{dups.head(10)}")

    return out