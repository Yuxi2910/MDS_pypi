import unittest
import pandas as pd

from airqual_data_fetcher.merge_utils import (
    prepare_source1_hourly_for_merge,
    prepare_source2_monthly_for_merge,
    merge_source1_hourly_with_source2_monthly,
)


class TestMergeUtils(unittest.TestCase):
    def setUp(self):
        # 4 cities, all in November so month_num should be 11
        self.df_hourly = pd.DataFrame({
            "city": ["Tokyo, Japan", "Shenzhen, China", "Bangkok, Thailand", "Delhi, India"],
            "dateTime": [
                "2025-11-15T06:00:00Z",
                "2025-11-15T07:00:00Z",
                "2025-11-15T08:00:00Z",
                "2025-11-15T09:00:00Z",
            ],
            "aqi_uaqi": [50, 55, 70, 160],
        })

        self.df_monthly = pd.DataFrame({
            "city": ["Tokyo, Japan", "Shenzhen, China", "Bangkok, Thailand", "Delhi, India"],
            "month_num": [11, 11, 11, 11],
            "daily_mean_c": [15.0, 25.0, 28.0, 20.0],
        })

    def test_prepare_and_merge(self):
        h = prepare_source1_hourly_for_merge(self.df_hourly, datetime_col="dateTime", city_col="city")
        m = prepare_source2_monthly_for_merge(self.df_monthly, city_col="city", month_col="month_num")

        merged = merge_source1_hourly_with_source2_monthly(
            h,
            m,
            on=("city", "month_num"),
            prefix_source2="clim_",
            how="left",
            keep_indicator=True,
        )

        self.assertEqual(len(merged), len(h))

        self.assertTrue((merged["month_num"] == 11).all())

        self.assertIn("clim_daily_mean_c", merged.columns)

        self.assertIn("_merge", merged.columns)
        self.assertTrue((merged["_merge"] == "both").all())

    def test_source2_duplicates_raise(self):
        dup = pd.concat([self.df_monthly, self.df_monthly.iloc[[0]]], ignore_index=True)

        with self.assertRaises(ValueError):
            prepare_source2_monthly_for_merge(dup, city_col="city", month_col="month_num")


if __name__ == "__main__":
    unittest.main()