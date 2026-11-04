"""Testes unitários para o módulo de visão computacional (FrameExtractor e VisualHookAnalyzer)."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.models.instagram import VisualHookAnalysis
from src.vision.frame_extractor import FrameExtractor
from src.vision.visual_analyzer import VisualHookAnalyzer


class TestVision(unittest.TestCase):
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_frame_extractor(self, mock_run, mock_which):
        mock_which.return_value = "ffmpeg"
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        extractor = FrameExtractor()
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=15000)
                frames = extractor.extract_hook_frames(
                    video_path=Path("sample.mp4"),
                    output_dir=Path("tmp_frames"),
                    timestamps=[0.8, 1.8, 2.8],
                )
                self.assertEqual(len(frames), 3)
                self.assertEqual(mock_run.call_count, 3)
                # Verifica passagem de parâmetros FFmpeg
                call_args = mock_run.call_args[0][0]
                self.assertIn("-vframes", call_args)
                self.assertIn("1", call_args)
                self.assertIn("-q:v", call_args)

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_bytes", return_value=b"fake_jpeg_bytes_header")
    def test_visual_hook_analyzer(self, mock_read, mock_exists):
        mock_gemini = MagicMock()
        mock_expected = VisualHookAnalysis(
            visual_summary="Criador corta um bolo recheado em close dramático",
            scene_elements="Cozinha bem iluminada, bancada de mármore",
            on_screen_text="NÃO FAÇA BOLO ANTES DE VER ISSO!",
            pattern_interrupt="Corte rápido no segundo 1.8 com zoom nos detalhes",
            timestamps_captured=[0.8, 1.8, 2.8],
        )
        mock_gemini.generate_structured.return_value = mock_expected

        analyzer = VisualHookAnalyzer(gemini_client=mock_gemini)
        frames = [Path("f1.jpg"), Path("f2.jpg"), Path("f3.jpg")]
        result = analyzer.analyze_hook_frames(frames, reel_code="DdrW4GDAnjS", caption="Receita fácil")

        mock_gemini.generate_structured.assert_called_once()
        self.assertEqual(result.visual_summary, "Criador corta um bolo recheado em close dramático")
        self.assertEqual(result.on_screen_text, "NÃO FAÇA BOLO ANTES DE VER ISSO!")
        self.assertEqual(result.pattern_interrupt, "Corte rápido no segundo 1.8 com zoom nos detalhes")


if __name__ == "__main__":
    unittest.main()
