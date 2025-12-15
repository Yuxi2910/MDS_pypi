# 🌏 AirQual-Data-Fetcher

**AirQual-Data-Fetcher** is a Python package that lets you:
- 📡 Fetch **hourly air-quality data** via the Google Air Quality API  
- 🌦 Scrape **monthly climate tables** from Wikipedia  
- 🏙 Build a **city catalog** from the SimpleMaps World Cities dataset  
- 🧩 Merge all three sources into a clean, analysis-ready dataset  
- 📊 Perform quick **descriptive analysis** (AQI vs climate)

---

## 🧠 What This Project Does

It automates the end-to-end process of combining **environmental and city-level data** into one dataset for exploration.

**Outputs:**
| Step | Output file | Description |
|------|--------------|-------------|
| 1 | `source1_hourly_panel.csv` | Hourly AQI + pollutant readings |
| 2 | `source2_wikipedia_climate_monthly.csv` | Monthly climate features (temperature, humidity, precipitation, etc.) |
| 3 | `source1_source2_merged_hourly.csv` | Hourly panel joined with monthly climate data |
| 4 | `city_catalog.csv` | City metadata (population, capital type, admin name) |
| 5 | `source123_hourly.csv` | Final merged dataset (air quality + climate + city catalog) |

---

## 🌍 Data Sources

### 🩵 Source 1 — Air Quality (Hourly)
- **Google Maps Platform Air Quality API**  
  <https://developers.google.com/maps/documentation/air-quality>  
  → provides hourly air-quality indices (UAQI, local AQI standards)  
  ⚠️ *History endpoint limited to the last 30 days (≈ 720 hours).*  

### 🌤 Source 2 — Climate (Monthly)
- **Wikipedia “Climate” tables** from each city page  
  Example: <https://en.wikipedia.org/wiki/Tokyo#Climate>  
  → provides monthly mean temperatures, humidity, precipitation, sunshine hours, etc.

### 🏙 Source 3 — City Catalog (Metadata)
- **SimpleMaps World Cities Database**  
  <https://simplemaps.com/data/world-cities>  
  → provides city name, admin name, capital type, and population.
  ⚠️ *Free dataset is limited to about 48 thousand entries. However, 2 advanced versions contain millions of entries *  

---

## Descriptive Analysis
Use the provided notebook vignette.ipynb or your own scripts.

Typical analyses include:

1. City-wise AQI description table (e.g. average & extreme)
2. AQI time series plot with cities selected
3. Climate–AQI correlations (e.g., aqi_uaqi vs clim_daily_mean_c)
4. Hourly AQI variation by month
5. Boxplots and heatmaps for AQI–climate relations

Example:
```python
import seaborn as sns, matplotlib.pyplot as plt

cols = ["aqi_uaqi", "clim_daily_mean_c", "clim_avg_rel_humidity_pct"]
sns.heatmap(df_123[cols].corr(), annot=True, cmap="coolwarm")
plt.title("Correlation: AQI vs Climate Features")
plt.show()

```

---

## 🧰 Installation

- Available on *[PyPI](https://pypi.org/project/airqual-data-fetcher/)*:

  ```bash
  pip install airqual-data-fetcher
  ```

- Clone and install locally:
  ```bash
  git clone https://github.com/<Yuxi2910>/airqual-data-fetcher.git
  cd airqual-data-fetcher
  pip install -e .


## ⚠️ Limitations

1. Google Air Quality API provides max 30-day historical data; older periods aren’t accessible without paid data archives.
2. Wikipedia scraping may fail for cities with non-standard climate tables or formatting.
3. Merging relies on exact "City, Country" label consistency (NFKC normalization is applied internally).
4. Climate data is monthly; when merged to hourly, it repeats within each month.

## Project structure
Final_Project/
├── data_fetcher/           # The Python package directory
│   ├── __init__.py                 # Makes the directory a Python package
│   ├── api_client.py               # Contains API_KEY setup and fetch_air_quality_data()
│   ├── web_scraper.py              # Contains scrape_indian_cities_data() and other scrapers
│   ├── merge_utils.py                   # Contains geocode_city_name() and the logic to merge AQ & Demo data
│   └── data_pipeline.py            # Contains acquire_full_air_quality_dataset() (the orchestrator)
├── tests/
│   ├── test_api_client.py          # Contains tests for fetch_air_quality_data()
│   └── test_web_scraper.py         # Contains tests for scraping functions (crucial requirement)

├── docs/                           # Sphinx documentation output
├── vignette_analysis.ipynb         # Jupyter Notebook (how to use the package & summary analysis(+basic graphs))
├── setup.py                        # Required for packaging (to publish to PyPI/TestPyPI)
├── README.md                       # Required: Overview, installation, usage
└── LICENSE