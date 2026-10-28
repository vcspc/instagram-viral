"""Testes do coletor de publicações do Instagram."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from src.instagram.collector import InstagramCollector


class TestInstagramCollector(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_rate_limiter = MagicMock()
        self.collector = InstagramCollector(client=self.mock_client, rate_limiter=self.mock_rate_limiter)

    def test_is_reel_or_video_variations(self):
        # 1. media_type == 2 com product_type == "clips"
        m1 = SimpleNamespace(media_type=2, product_type="clips", video_duration=30.0)
        self.assertTrue(self.collector._is_reel_or_video(m1))

        # 2. media_type == 2 com product_type == "feed" (vídeo regular que no Instagram roda como Reel)
        m2 = SimpleNamespace(media_type=2, product_type="feed", video_duration=15.0)
        self.assertTrue(self.collector._is_reel_or_video(m2))

        # 3. media_type == 1 (foto) -> não é vídeo
        m3 = SimpleNamespace(media_type=1, product_type="feed", video_duration=0.0)
        self.assertFalse(self.collector._is_reel_or_video(m3))

        # 4. media com duração positiva
        m4 = SimpleNamespace(media_type=None, product_type="unknown", video_duration=45.0)
        self.assertTrue(self.collector._is_reel_or_video(m4))

    def test_search_reels_by_keyword(self):
        sample_media = SimpleNamespace(
            pk="999111",
            code="ReelCode123",
            caption_text="Vídeo viral de teste",
            video_duration=22.0,
            taken_at=None,
            media_type=2,
            product_type="clips",
            user=SimpleNamespace(username="criador_viral"),
            play_count=150000,
            like_count=12000,
            comment_count=850,
        )
        self.mock_client.media_search.return_value = [sample_media]

        reels = self.collector.search_reels_by_keyword("confeitaria caseira", amount=10)
        self.mock_client.media_search.assert_called_once_with("confeitaria caseira", amount=10)
        self.assertEqual(len(reels), 1)
        self.assertEqual(reels[0].code, "ReelCode123")
        self.assertEqual(reels[0].author_username, "criador_viral")
        self.assertEqual(reels[0].metrics.views, 150000)

    def test_search_reels_by_hashtag_fallback(self):
        # Simula hashtag_medias_reels_v1 retornando vazio e hashtag_medias_recent_v1 trazendo o reel
        self.mock_client.hashtag_medias_reels_v1.return_value = []
        sample_media = SimpleNamespace(
            pk="888222",
            code="ReelRecent456",
            caption_text="Bolo fofinho",
            video_duration=18.0,
            taken_at=None,
            media_type=2,
            product_type="clips",
            user=SimpleNamespace(username="chef_paula"),
            view_count=80000,
            like_count=5000,
            comment_count=320,
        )
        self.mock_client.hashtag_medias_recent_v1.return_value = [sample_media]

        reels = self.collector.search_reels_by_hashtag("#boloscaseiros", amount=10)
        self.mock_client.hashtag_medias_reels_v1.assert_called_once_with("boloscaseiros", amount=10)
        self.mock_client.hashtag_medias_recent_v1.assert_called_once_with("boloscaseiros", amount=10)
        self.assertEqual(len(reels), 1)
        self.assertEqual(reels[0].code, "ReelRecent456")


    def test_search_reels_filters_by_date(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        min_date = now - timedelta(days=7)

        # 1 mídia recente (dentro dos 7 dias)
        media_recent = SimpleNamespace(
            pk="111",
            code="RecentCode",
            caption_text="Vídeo recente",
            video_duration=20.0,
            taken_at=now - timedelta(days=2),
            media_type=2,
            product_type="clips",
            user=SimpleNamespace(username="user1"),
            play_count=1000,
            like_count=100,
            comment_count=10,
        )

        # 1 mídia antiga (de 30 dias atrás)
        media_old = SimpleNamespace(
            pk="222",
            code="OldCode",
            caption_text="Vídeo antigo",
            video_duration=25.0,
            taken_at=now - timedelta(days=30),
            media_type=2,
            product_type="clips",
            user=SimpleNamespace(username="user2"),
            play_count=5000,
            like_count=500,
            comment_count=50,
        )

        self.mock_client.media_search.return_value = [media_recent, media_old]

        reels = self.collector.search_reels_by_keyword("marketing", amount=10, min_taken_at=min_date)
        # Deve reter apenas o recente
        self.assertEqual(len(reels), 1)
        self.assertEqual(reels[0].code, "RecentCode")


if __name__ == "__main__":
    unittest.main()
