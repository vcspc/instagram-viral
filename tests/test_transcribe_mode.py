"""Testes unitários para o modo de transcrição direta de Reels."""
import tempfile
import unittest
from pathlib import Path
from src.instagram.collector import InstagramCollector
from src.models.instagram import ReelItem, ReelTranscript, TranscriptSegment
from src.reports.exporter import ReportExporter


class TestTranscribeMode(unittest.TestCase):
    def test_extract_code_from_url_formats(self):
        # 1. URL padrão de reel com barra final
        url1 = "https://www.instagram.com/reel/DdrW4GDAnjS/"
        self.assertEqual(InstagramCollector.extract_code_from_url(url1), "DdrW4GDAnjS")

        # 2. URL com parâmetros de tracking (igsh, etc.)
        url2 = "https://www.instagram.com/reel/C8xY12zAbc/?igsh=MWx123&utm_source=ig_web"
        self.assertEqual(InstagramCollector.extract_code_from_url(url2), "C8xY12zAbc")

        # 3. URL com /p/ (post)
        url3 = "https://instagram.com/p/B1LbfVPlwIA"
        self.assertEqual(InstagramCollector.extract_code_from_url(url3), "B1LbfVPlwIA")

        # 4. Apenas o código puro
        code4 = "DdrW4GDAnjS"
        self.assertEqual(InstagramCollector.extract_code_from_url(code4), "DdrW4GDAnjS")

    def test_export_transcriptions_markdown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exporter = ReportExporter(output_dir=Path(tmp_dir))

            reels = [
                ReelItem(
                    pk="111",
                    code="Reel1",
                    url="https://www.instagram.com/reel/Reel1/",
                    author_username="criador_teste",
                    duration=45.0,
                    caption="Legenda do primeiro reel",
                    transcript=ReelTranscript(
                        text="Olá pessoal, hoje eu vou ensinar como fazer a receita mais fácil do mundo.",
                        segments=[
                            TranscriptSegment(
                                start=0.0,
                                end=2.8,
                                text="Olá pessoal, hoje eu vou ensinar",
                                timestamp_formatted="[00:00 - 00:02]",
                            ),
                            TranscriptSegment(
                                start=2.8,
                                end=5.5,
                                text="como fazer a receita mais fácil do mundo.",
                                timestamp_formatted="[00:02 - 00:05]",
                            ),
                        ],
                        language="pt",
                        duration=45.0,
                        hook_text_3s="Olá pessoal, hoje eu vou ensinar",
                    ),
                ),
                ReelItem(
                    pk="222",
                    code="Reel2",
                    url="https://www.instagram.com/reel/Reel2/",
                    author_username="outro_criador",
                    duration=30.0,
                    transcript=None,  # Reel sem fala audível
                ),
            ]

            md_path = exporter.export_transcriptions_markdown(
                reels=reels,
                language="pt",
                whisper_model="base",
            )

            self.assertTrue(md_path.exists())
            content = md_path.read_text(encoding="utf-8")

            # Verifica seções do documento
            self.assertIn("# Transcrições Literais de Reels do Instagram", content)
            self.assertIn("Total de Vídeos Enviados:** 2", content)
            self.assertIn("Reel: [Reel1]", content)
            self.assertIn("criador_teste", content)
            # Transcrição literal completa
            self.assertIn("#### Transcrição Literal Completa:", content)
            self.assertIn("Olá pessoal, hoje eu vou ensinar como fazer a receita mais fácil do mundo.", content)
            # Timestamps
            self.assertIn("[00:00 - 00:02] Olá pessoal, hoje eu vou ensinar", content)
            # Reel sem áudio
            self.assertIn("Não foi possível extrair a faixa de áudio", content)


if __name__ == "__main__":
    unittest.main()
