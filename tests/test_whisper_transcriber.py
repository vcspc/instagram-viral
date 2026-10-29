"""Testes unitários para o transcritor Whisper."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from src.audio.transcriber import WhisperTranscriber, format_seconds_to_timestamp


class TestWhisperTranscriber(unittest.TestCase):
    def test_format_seconds_to_timestamp(self):
        self.assertEqual(format_seconds_to_timestamp(0.0), "00:00")
        self.assertEqual(format_seconds_to_timestamp(3.5), "00:03")
        self.assertEqual(format_seconds_to_timestamp(65.0), "01:05")
        self.assertEqual(format_seconds_to_timestamp(125.9), "02:05")

    @patch("pathlib.Path.exists")
    def test_transcribe_segments_and_hook(self, mock_exists):
        mock_exists.return_value = True

        mock_segments = [
            SimpleNamespace(start=0.5, end=2.8, text="Você nunca mais vai errar este bolo!"),
            SimpleNamespace(start=2.9, end=5.2, text="O segredo está em bater os ovos."),
            SimpleNamespace(start=5.5, end=9.0, text="Siga o perfil para mais dicas."),
        ]
        mock_info = SimpleNamespace(duration=9.0, language="pt")

        transcriber = WhisperTranscriber(model_size="base")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (mock_segments, mock_info)
        transcriber._model = mock_model

        result = transcriber.transcribe(Path("audio.wav"))

        self.assertEqual(len(result.segments), 3)
        self.assertEqual(result.segments[0].timestamp_formatted, "[00:00 - 00:02]")
        self.assertEqual(result.segments[1].timestamp_formatted, "[00:02 - 00:05]")
        self.assertEqual(result.duration, 9.0)
        self.assertEqual(result.language, "pt")
        # Gancho dos primeiros 3s deve conter as falas que começaram antes de 3.0s
        self.assertIn("Você nunca mais vai errar este bolo!", result.hook_text_3s)
        self.assertIn("O segredo está em bater os ovos.", result.hook_text_3s)


if __name__ == "__main__":
    unittest.main()
