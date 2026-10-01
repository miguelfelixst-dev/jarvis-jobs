import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("radar", ROOT / "scripts" / "radar.py")
radar = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(radar)

class RadarTests(unittest.TestCase):
    def test_clean_html(self):
        self.assertEqual(radar.clean("<b>Excel</b>   automation"), "Excel automation")
        self.assertEqual(radar.clean("&lt;b&gt;PDF&lt;/b&gt; data"), "PDF data")

    def test_epoch_date_becomes_text(self):
        value = radar.normalize_date(1700000000)
        self.assertIsInstance(value, str)
        self.assertIn("T", value)

    def test_good_job_scores_high(self):
        score, hits = radar.score_job(
            "Excel automation and web scraping",
            "Small Python script to clean CSV and extract data",
            ["freelance", "remote"],
        )
        self.assertGreaterEqual(score, 60)
        self.assertIn("excel", hits)

    def test_missing_url_is_ignored(self):
        jobs = []
        radar.add_job(jobs, source="Test", title="Excel task", desc="automation", url="")
        self.assertEqual(jobs, [])

    def test_duplicate_sort_types_are_safe(self):
        original = radar.get_json
        try:
            radar.get_json = lambda url: (
                [{"meta": True}, {"position":"Excel automation","description":"python csv","url":"https://a","epoch":1700000000,"tags":["remote"]}]
                if "remoteok" in url else
                {"data":[{"title":"PDF data entry","description":"excel","url":"https://b","created_at":"2026-09-30","tags":[]}]}
                if "arbeitnow" in url else
                {"jobs":[{"jobTitle":"Browser extension","jobDescription":"javascript automation","url":"https://c","pubDate":"2026-09-30","jobType":"contract"}]}
            )
            payload = radar.collect()
            self.assertEqual(payload["count"], 3)
            self.assertEqual(payload["errors"], [])
            self.assertTrue(all(isinstance(j["date"], (str, type(None))) for j in payload["jobs"]))
        finally:
            radar.get_json = original

if __name__ == "__main__":
    unittest.main()
