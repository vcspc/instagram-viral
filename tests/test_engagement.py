"""Testes das funções de engajamento e cálculo de viral score."""
import unittest
from src.instagram.engagement import calculate_metrics, sort_reels_by_viral_score
from src.models.instagram import ReelItem, ReelMetrics


class TestEngagement(unittest.TestCase):
    def test_calculate_metrics_normal(self):
        # 10.000 views, 500 likes, 100 comments
        metrics = calculate_metrics(views=10000, likes=500, comments=100)
        self.assertEqual(metrics.views, 10000)
        self.assertEqual(metrics.likes, 500)
        self.assertEqual(metrics.comments, 100)
        # Taxa de engajamento = ((500 + 100) / 10000) * 100 = 6.0%
        self.assertEqual(metrics.engagement_rate, 6.0)
        # Razão comentários/likes = 100 / 500 = 0.2
        self.assertEqual(metrics.discussion_ratio, 0.2)
        self.assertGreater(metrics.viral_score, 0)

    def test_calculate_metrics_zero_views(self):
        # Vídeo sem views registradas
        metrics = calculate_metrics(views=0, likes=10, comments=2)
        self.assertEqual(metrics.views, 0)
        # safe_views evita divisão por zero
        self.assertGreater(metrics.engagement_rate, 0)
        self.assertGreater(metrics.viral_score, 0)

    def test_calculate_metrics_high_comments_boost(self):
        # Dois vídeos com mesmas views e likes, mas um com muito mais comentários
        m1 = calculate_metrics(views=50000, likes=2000, comments=50)
        m2 = calculate_metrics(views=50000, likes=2000, comments=800)
        # m2 deve ter Viral Score significativamente maior devido ao peso do debate
        self.assertGreater(m2.viral_score, m1.viral_score)

    def test_sort_reels_by_viral_score(self):
        r1 = ReelItem(
            pk="1",
            code="code1",
            url="https://www.instagram.com/reel/code1/",
            metrics=ReelMetrics(views=1000, likes=50, comments=5, viral_score=15.0),
        )
        r2 = ReelItem(
            pk="2",
            code="code2",
            url="https://www.instagram.com/reel/code2/",
            metrics=ReelMetrics(views=50000, likes=4000, comments=500, viral_score=950.0),
        )
        r3 = ReelItem(
            pk="3",
            code="code3",
            url="https://www.instagram.com/reel/code3/",
            metrics=ReelMetrics(views=5000, likes=200, comments=20, viral_score=80.0),
        )

        sorted_list = sort_reels_by_viral_score([r1, r2, r3])
        self.assertEqual(sorted_list[0].code, "code2")
        self.assertEqual(sorted_list[1].code, "code3")
        self.assertEqual(sorted_list[2].code, "code1")


if __name__ == "__main__":
    unittest.main()
