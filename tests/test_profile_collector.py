"""Testes unitários para a coleta de perfis e reels do usuário."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from src.instagram.collector import InstagramCollector


class TestProfileCollector(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_rate_limiter = MagicMock()
        self.collector = InstagramCollector(client=self.mock_client, rate_limiter=self.mock_rate_limiter)

    def test_get_user_profile(self):
        mock_user = SimpleNamespace(
            pk=1234567,
            username="criador_famoso",
            full_name="Criador Famoso Oficial",
            biography="Aprenda confeitaria do zero | Link abaixo",
            follower_count=250000,
            following_count=180,
            media_count=420,
            is_verified=True,
            is_business=True,
            external_url="https://curso.com",
            category_name="Criador de Conteúdo",
            profile_pic_url="https://cdn.instagram.com/pic.jpg",
        )
        self.mock_client.user_info_by_username.return_value = mock_user

        profile = self.collector.get_user_profile("@criador_famoso")

        self.mock_client.user_info_by_username.assert_called_once_with("criador_famoso")
        self.assertEqual(profile.username, "criador_famoso")
        self.assertEqual(profile.follower_count, 250000)
        self.assertEqual(profile.media_count, 420)
        self.assertTrue(profile.is_verified)
        self.assertEqual(profile.external_url, "https://curso.com")

    def test_get_user_reels(self):
        mock_media = SimpleNamespace(
            pk="112233",
            code="Cl1pCode",
            caption_text="Reel viral do criador",
            video_duration=28.0,
            taken_at=None,
            media_type=2,
            product_type="clips",
            video_url="https://cdn.instagram.com/video.mp4",
            user=SimpleNamespace(username="criador_famoso"),
            play_count=500000,
            like_count=45000,
            comment_count=3200,
        )
        self.mock_client.user_clips_v1.return_value = [mock_media]

        reels = self.collector.get_user_reels(user_id="1234567", amount=10)

        self.mock_client.user_clips_v1.assert_called_once_with(user_id="1234567", amount=10)
        self.assertEqual(len(reels), 1)
        self.assertEqual(reels[0].code, "Cl1pCode")
        self.assertEqual(reels[0].video_url, "https://cdn.instagram.com/video.mp4")
        self.assertEqual(reels[0].metrics.views, 500000)
        self.assertGreater(reels[0].metrics.viral_score, 0)


if __name__ == "__main__":
    unittest.main()
