"""End-to-end and unit tests. Run with:  python -m unittest -v"""
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from pipeline import config
from pipeline.quality import DataQualityError
from pipeline.run import run
from pipeline.transform import clean


class PipelineTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db_path = root / "warehouse.db"
        self.bronze = root / "bronze"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, end, start=None):
        return run(sample=True, start=start, end=end, db_path=self.db_path, bronze_dir=self.bronze)

    def _query(self, sql):
        con = sqlite3.connect(self.db_path)
        try:
            return con.execute(sql).fetchall()
        finally:
            con.close()


class TestEndToEnd(PipelineTestCase):
    def test_first_run_loads_all_layers(self):
        summary = self._run(end=date(2026, 1, 10))
        n_cities = len(config.CITIES)
        self.assertEqual(summary["status"], "success")
        self.assertEqual(len(list(self.bronze.rglob("*.json"))), n_cities)
        self.assertEqual(self._query("SELECT COUNT(*) FROM fact_weather_daily")[0][0], 10 * n_cities)
        self.assertEqual(self._query("SELECT COUNT(*) FROM dim_date")[0][0], 10)
        self.assertEqual(self._query("SELECT COUNT(*) FROM dim_city")[0][0], n_cities)
        self.assertTrue((self.db_path.parent / "gold_csv" / "fact_weather_daily.csv").exists())

    def test_rerun_is_idempotent(self):
        self._run(end=date(2026, 1, 10))
        before = self._query("SELECT COUNT(*), SUM(avg_temperature_c) FROM fact_weather_daily")
        summary = self._run(end=date(2026, 1, 10))
        after = self._query("SELECT COUNT(*), SUM(avg_temperature_c) FROM fact_weather_daily")
        self.assertEqual(summary["rows_bronze"], 0)
        self.assertEqual(before, after)

    def test_incremental_run_only_loads_new_days(self):
        self._run(end=date(2026, 1, 10))
        summary = self._run(end=date(2026, 1, 12))
        self.assertEqual(summary["rows_gold"], 2 * len(config.CITIES))
        wm = self._query("SELECT DISTINCT last_loaded_date FROM pipeline_watermark")
        self.assertEqual(wm, [("2026-01-12",)])

    def test_backfill_overwrites_without_duplicates(self):
        self._run(end=date(2026, 1, 10))
        self._run(start=date(2026, 1, 5), end=date(2026, 1, 10))
        dupes = self._query("""SELECT COUNT(*) FROM (SELECT date_key, city_id, COUNT(*) c
                               FROM fact_weather_daily GROUP BY 1, 2 HAVING c > 1)""")
        self.assertEqual(dupes[0][0], 0)

    def test_failed_quality_check_rolls_back_everything(self):
        self._run(end=date(2026, 1, 10))
        with mock.patch("pipeline.run.run_checks", side_effect=DataQualityError("boom")):
            with self.assertRaises(DataQualityError):
                self._run(end=date(2026, 1, 12))
        # watermark and gold must be unchanged; the failure must be logged
        self.assertEqual(self._query("SELECT DISTINCT last_loaded_date FROM pipeline_watermark"),
                         [("2026-01-10",)])
        self.assertEqual(self._query("SELECT MAX(date_key) FROM fact_weather_daily")[0][0], 20260110)
        self.assertEqual(self._query("SELECT status FROM pipeline_runs ORDER BY run_id DESC LIMIT 1"),
                         [("failed",)])


class TestApiExtract(PipelineTestCase):
    def test_api_mode_with_mocked_http(self):
        def fake_get(url, params, timeout):
            self.assertEqual(url, config.API_URL)
            self.assertEqual(params["timezone"], "Asia/Baku")
            resp = mock.Mock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"hourly": {
                "time": ["2026-02-01T00:00", "2026-02-01T01:00"],
                "temperature_2m": [3.1, None], "relative_humidity_2m": [80, 82],
                "precipitation": [0.0, 0.3], "wind_speed_10m": [12.4, 15.0]}}
            return resp

        with mock.patch("pipeline.extract.requests.get", side_effect=fake_get):
            summary = run(sample=False, start=date(2026, 2, 1), end=date(2026, 2, 1),
                          db_path=self.db_path, bronze_dir=self.bronze)
        self.assertEqual(summary["rows_silver"], 2 * len(config.CITIES))
        self.assertEqual(self._query("SELECT rainy_hours, hours_recorded FROM fact_weather_daily "
                                     "WHERE city_id = 1"), [(1, 2)])


class TestCleaning(unittest.TestCase):
    def _frame(self, **overrides):
        row = {"time": "2026-03-01T10:00", "temperature_c": 12.0, "relative_humidity_pct": 60.0,
               "precipitation_mm": 0.0, "wind_speed_kmh": 10.0, "city_id": 1,
               "source_file": "a.json", "_extracted_at": "2026-03-05T00:00:00"}
        row.update(overrides)
        return pd.DataFrame([row])

    def test_out_of_range_values_become_null(self):
        out = clean(self._frame(temperature_c=999.0, relative_humidity_pct=-5.0))
        self.assertTrue(pd.isna(out.loc[0, "temperature_c"]))
        self.assertTrue(pd.isna(out.loc[0, "relative_humidity_pct"]))
        self.assertEqual(out.loc[0, "wind_speed_kmh"], 10.0)

    def test_rows_with_no_measurements_are_dropped(self):
        out = clean(self._frame(temperature_c=None, relative_humidity_pct=None,
                                precipitation_mm=None, wind_speed_kmh=None))
        self.assertEqual(len(out), 0)

    def test_duplicates_keep_latest_extraction(self):
        old = self._frame(temperature_c=10.0, _extracted_at="2026-03-02T00:00:00")
        new = self._frame(temperature_c=11.0, _extracted_at="2026-03-09T00:00:00")
        out = clean(pd.concat([old, new], ignore_index=True))
        self.assertEqual(len(out), 1)
        self.assertEqual(out.loc[0, "temperature_c"], 11.0)

    def test_bad_timestamps_are_dropped(self):
        out = clean(self._frame(time="not-a-date"))
        self.assertEqual(len(out), 0)


if __name__ == "__main__":
    unittest.main()
