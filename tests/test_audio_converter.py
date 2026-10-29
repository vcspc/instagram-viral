"""Testes unitários para o conversor de áudio FFmpeg."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.audio.converter import AudioConverter


class TestAudioConverter(unittest.TestCase):
    @patch("shutil.which")
    def test_resolve_ffmpeg_found(self, mock_which):
        mock_which.return_value = "C:\\ffmpeg\\bin\\ffmpeg.exe"
        converter = AudioConverter()
        self.assertEqual(converter.ffmpeg_bin, "C:\\ffmpeg\\bin\\ffmpeg.exe")

    @patch("shutil.which")
    def test_resolve_ffmpeg_not_found(self, mock_which):
        mock_which.return_value = None
        with patch.object(Path, "exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                AudioConverter()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_video_to_whisper_audio(self, mock_run, mock_which):
        mock_which.return_value = "ffmpeg"
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        converter = AudioConverter()
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=50000)
                out = converter.video_to_whisper_audio(Path("video.mp4"))
                self.assertEqual(out, Path("video.wav"))
                mock_run.assert_called_once()
                args_called = mock_run.call_args[0][0]
                self.assertIn("-acodec", args_called)
                self.assertIn("pcm_s16le", args_called)
                self.assertIn("16000", args_called)


if __name__ == "__main__":
    unittest.main()
