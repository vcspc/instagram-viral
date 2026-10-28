"""Testes dos exportadores de relatórios."""
import tempfile
import unittest
from pathlib import Path
from src.models.agent import SearchStrategy, ViralAnalysis
from src.models.instagram import ReelItem, ReelMetrics
from src.reports.exporter import ReportExporter


class TestExporter(unittest.TestCase):
    def test_exporter_creates_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            exporter = ReportExporter(output_dir=tmp_path)

            strategy = SearchStrategy(
                intent_summary="Teste de confeitaria",
                primary_hashtags=["confeitaria", "bolos"],
                long_tail_hashtags=["bolosdecoradoscaseiros"],
                search_keywords=["como fazer bolo"],
                reasoning="Estratégia focada em iniciantes",
            )

            reels = [
                ReelItem(
                    pk="12345",
                    code="CxYz123",
                    url="https://www.instagram.com/reel/CxYz123/",
                    caption="Receita fácil de bolo de cenoura fofinho!",
                    duration=35.0,
                    author_username="chef_maria",
                    metrics=ReelMetrics(
                        views=120000,
                        likes=8500,
                        comments=420,
                        engagement_rate=7.43,
                        viral_score=1850.5,
                    ),
                    source_term="#confeitaria",
                )
            ]

            analysis = ViralAnalysis(
                common_hook_patterns=["Não faça bolo antes de ver isso"],
                content_themes=["Passo a passo rápido"],
                audio_insights="Áudio acústico relaxante",
                caption_strategy="Ingredientes na legenda com CTA para salvar",
                actionable_recommendations=["Filme a textura cortando o bolo nos primeiros 2s"],
            )

            paths = exporter.export_all(
                query="bolos de cenoura fáceis",
                strategy=strategy,
                reels=reels,
                analysis=analysis,
            )

            self.assertTrue(paths["markdown"].exists())
            self.assertTrue(paths["csv"].exists())
            self.assertTrue(paths["json"].exists())

            md_content = paths["markdown"].read_text(encoding="utf-8")
            self.assertIn("chef_maria", md_content)
            self.assertIn("CxYz123", md_content)
            self.assertIn("Não faça bolo antes de ver isso", md_content)


if __name__ == "__main__":
    unittest.main()
