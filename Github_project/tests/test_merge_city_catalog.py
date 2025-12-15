import unittest
import pandas as pd

from airqual_data_fetcher.merge_utils import merge_hourly_with_city_catalog


class TestMergeCityCatalog(unittest.TestCase):
    def test_merge_adds_indicator_and_preserves_rows(self):
        # df_12 should look like your already-merged Source1+Source2 hourly output
        # (it often already has a "_merge" column from the previous merge)
        df_12 = pd.DataFrame({
            "city": [
                "Shenzhen, China",
                "Bangkok, Thailand",
                "Tokyo, Japan",
                "Delhi, India",
                "Paris, France",          # intentionally NOT in city_catalog
            ],
            "dateTime": [
                "2025-11-01T00:00:00Z",
                "2025-11-01T01:00:00Z",
                "2025-11-01T02:00:00Z",
                "2025-11-01T03:00:00Z",
                "2025-11-01T04:00:00Z",
            ],
            "_merge": ["both"] * 5,  
        })

        city_catalog = pd.DataFrame({
            "city": ["Shenzhen, China", "Bangkok, Thailand", "Tokyo, Japan", "Delhi, India"],
            "admin_name": ["Guangdong", "Bangkok", "Tokyo", "Delhi"],
            "capital": ["admin", "primary", "primary", "admin"],
            "population": [17560000, 10539000, 37785000, 32226000],
        })

        out = merge_hourly_with_city_catalog(
            df_12,
            city_catalog,
            city_col="city",
            prefix="citycat_",
            keep_indicator=True,
            indicator_name="_merge_citycat",
        )

        self.assertEqual(len(out), len(df_12))

        self.assertIn("_merge", out.columns)
        self.assertIn("_merge_citycat", out.columns)

        self.assertIn("citycat_admin_name", out.columns)
        self.assertIn("citycat_capital", out.columns)
        self.assertIn("citycat_population", out.columns)

        # 4 cities match, 1 city (Paris) should be left_only
        counts = out["_merge_citycat"].value_counts().to_dict()
        self.assertEqual(counts.get("both", 0), 4)
        self.assertEqual(counts.get("left_only", 0), 1)

    def test_indicator_name_collision_is_handled(self):
        df_12 = pd.DataFrame({
            "city": ["Tokyo, Japan"],
            "dateTime": ["2025-11-01T00:00:00Z"],
            "_merge_citycat": ["old_value"], 
        })

        city_catalog = pd.DataFrame({
            "city": ["Tokyo, Japan"],
            "admin_name": ["Tokyo"],
            "capital": ["primary"],
            "population": [37785000],
        })

        out = merge_hourly_with_city_catalog(
            df_12,
            city_catalog,
            keep_indicator=True,
            indicator_name="_merge_citycat",
        )

        self.assertIn("_merge_citycat", out.columns)

        self.assertTrue(any(c.startswith("_merge_citycat_") for c in out.columns))


if __name__ == "__main__":
    unittest.main()

