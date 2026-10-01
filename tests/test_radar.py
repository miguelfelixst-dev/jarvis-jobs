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

    def test_marketplace_excel_project_is_accepted(self):
        category, score, hits = radar.classify_job(
            "Automação em Excel",
            "Preciso automatizar planilha, criar macros simples e organizar dados.",
            ["projeto"],
            "99Freelas",
        )
        self.assertEqual(category, "Excel e planilhas")
        self.assertGreaterEqual(score, 50)
        self.assertIn("excel", hits)

    def test_marketplace_scraping_project_is_accepted(self):
        category, score, hits = radar.classify_job(
            "Web scraping para Excel",
            "Extrair dados de sites e entregar em CSV.",
            ["freelance"],
            "Workana",
        )
        self.assertIsNotNone(category)
        self.assertGreaterEqual(score, 50)

    def test_traditional_senior_role_is_blocked(self):
        category, score, hits = radar.classify_job(
            "Senior Data Engineer",
            "Excel automation and scraping",
            ["full-time"],
            "Upwork",
        )
        self.assertIsNone(category)
        self.assertEqual(score, 0)

    def test_missing_url_is_ignored(self):
        jobs=[]
        radar.add_job(
            jobs, source="99Freelas", title="Automação em Excel",
            desc="Projeto de planilha", url="", tags=["projeto"]
        )
        self.assertEqual(jobs, [])

    def test_add_job_records_category(self):
        jobs=[]
        radar.add_job(
            jobs, source="Freelancer", title="Excel Data Cleaning",
            desc="Clean an Excel spreadsheet and remove duplicates",
            url="https://example.com/job", tags=["project"]
        )
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0]["category"])
        self.assertGreaterEqual(jobs[0]["score"], 50)

if __name__ == "__main__":
    unittest.main()
