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

    def test_target_job_is_classified(self):
        category, score, hits = radar.classify_job(
            "Excel automation task",
            "Small freelance project to clean CSV and organize spreadsheet data",
            ["remote", "contract"],
        )
        self.assertIn(category, {"Excel e planilhas", "Automações simples"})
        self.assertGreaterEqual(score, 45)
        self.assertTrue(any(x in hits for x in ("excel", "automation")))

    def test_traditional_role_is_blocked(self):
        category, score, hits = radar.classify_job(
            "Senior Data Engineer",
            "Excel automation and scraping",
            ["full-time"],
        )
        self.assertIsNone(category)
        self.assertEqual(score, 0)

    def test_missing_url_is_ignored(self):
        jobs = []
        radar.add_job(jobs, source="Test", title="Excel task", desc="automation", url="")
        self.assertEqual(jobs, [])

    def test_sources_and_filtering(self):
        original = radar.get_json
        try:
            radar.get_json = lambda url: (
                [{"meta": True}, {"position":"Excel automation task","description":"small freelance csv cleanup","url":"https://a","epoch":1700000000,"tags":["remote"]}]
                if "remoteok" in url else
                {"data":[
                    {"title":"PDF data entry task","description":"convert pdf to excel","url":"https://b","created_at":"2026-09-30","tags":["contract"]},
                    {"title":"Senior Data Engineer","description":"excel scraping automation","url":"https://blocked","created_at":"2026-09-30","tags":[]}
                ]}
                if "arbeitnow" in url else
                {"jobs":[{"jobTitle":"Browser extension task","jobDescription":"small chrome extension automation","url":"https://c","pubDate":"2026-09-30","jobType":"contract"}]}
            )
            payload = radar.collect()
            self.assertEqual(payload["count"], 3)
            self.assertEqual(payload["errors"], [])
            self.assertTrue(all(j.get("category") for j in payload["jobs"]))
            self.assertTrue(all(isinstance(j["date"], (str, type(None))) for j in payload["jobs"]))
            self.assertFalse(any(j["url"] == "https://blocked" for j in payload["jobs"]))
        finally:
            radar.get_json = original

if __name__ == "__main__":
    unittest.main()
