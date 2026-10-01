import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("radar", ROOT / "scripts" / "radar.py")
radar = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(radar)

class RadarTests(unittest.TestCase):
    def test_classifica_excel(self):
        category,score,hits=radar.classify_job(
            "Automação de planilha Excel",
            "Preciso automatizar controles e criar dashboard.",
            "99Freelas"
        )
        self.assertEqual(category,"Excel e planilhas")
        self.assertGreaterEqual(score,50)

    def test_bloqueia_cargo_tradicional(self):
        category,score,hits=radar.classify_job(
            "Senior Data Engineer",
            "Automação em Excel e scraping.",
            "Workana"
        )
        self.assertIsNone(category)

    def test_competicao_alta_nao_entra(self):
        jobs=[]
        radar.add_job(
            jobs,source="99Freelas",title="Automação de planilha Excel",
            desc="Projeto de automação e dashboard",url="https://x",
            competition=231,status="Aberto"
        )
        self.assertEqual(jobs,[])

    def test_competicao_baixa_ganha_bonus(self):
        self.assertGreater(radar.competition_bonus(2),radar.competition_bonus(18))

    def test_projeto_baixa_competicao_entra(self):
        jobs=[]
        radar.add_job(
            jobs,source="Workana",title="Automação de planilha Excel",
            desc="Projeto simples com VBA",url="https://x",
            competition=3,status="Aberto"
        )
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]["meta"]["competition"],3)

if __name__=="__main__":
    unittest.main()
