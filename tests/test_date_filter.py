"""Testes para o utilitário de filtragem por período de tempo (timeframe)."""
import unittest
from datetime import datetime, timedelta, timezone
from src.instagram.date_filter import is_within_timeframe, parse_timeframe


class TestDateFilter(unittest.TestCase):
    def test_parse_timeframe_weeks(self):
        dt, desc = parse_timeframe("1w")
        self.assertIsNotNone(dt)
        self.assertIn("semana", desc.lower())
        # Deve estar a aproximadamente 7 dias no passado
        delta = datetime.now(timezone.utc) - dt
        self.assertAlmostEqual(delta.total_seconds(), 7 * 86400, delta=10)

        dt2, desc2 = parse_timeframe("2semanas")
        delta2 = datetime.now(timezone.utc) - dt2
        self.assertAlmostEqual(delta2.total_seconds(), 14 * 86400, delta=10)

    def test_parse_timeframe_months(self):
        dt, desc = parse_timeframe("1m")
        self.assertIsNotNone(dt)
        self.assertIn("mês", desc.lower())
        delta = datetime.now(timezone.utc) - dt
        self.assertAlmostEqual(delta.total_seconds(), 30 * 86400, delta=10)

        dt3, desc3 = parse_timeframe("3m")
        self.assertIn("3 meses", desc3.lower())
        delta3 = datetime.now(timezone.utc) - dt3
        self.assertAlmostEqual(delta3.total_seconds(), 90 * 86400, delta=10)

    def test_parse_timeframe_years(self):
        dt, desc = parse_timeframe("1y")
        self.assertIsNotNone(dt)
        self.assertIn("ano", desc.lower())
        delta = datetime.now(timezone.utc) - dt
        self.assertAlmostEqual(delta.total_seconds(), 365 * 86400, delta=10)

        dt2, desc2 = parse_timeframe("2anos")
        delta2 = datetime.now(timezone.utc) - dt2
        self.assertAlmostEqual(delta2.total_seconds(), 730 * 86400, delta=10)

    def test_parse_timeframe_days(self):
        dt, desc = parse_timeframe("15d")
        delta = datetime.now(timezone.utc) - dt
        self.assertAlmostEqual(delta.total_seconds(), 15 * 86400, delta=10)

    def test_parse_timeframe_all_or_none(self):
        dt1, desc1 = parse_timeframe("all")
        self.assertIsNone(dt1)
        self.assertEqual(desc1, "Todo o período")

        dt2, desc2 = parse_timeframe(None)
        self.assertIsNone(dt2)

        dt3, desc3 = parse_timeframe("")
        self.assertIsNone(dt3)

    def test_parse_timeframe_invalid(self):
        with self.assertRaises(ValueError):
            parse_timeframe("invalido_xyz")

    def test_is_within_timeframe(self):
        now = datetime.now(timezone.utc)
        min_date = now - timedelta(days=7)

        # Post de 2 dias atrás -> dentro do período
        post_recent = now - timedelta(days=2)
        self.assertTrue(is_within_timeframe(post_recent, min_date))

        # Post de 10 dias atrás -> fora do período
        post_old = now - timedelta(days=10)
        self.assertFalse(is_within_timeframe(post_old, min_date))

        # Post sem data -> não descarta
        self.assertTrue(is_within_timeframe(None, min_date))

        # Sem filtro de data mínima -> sempre True
        self.assertTrue(is_within_timeframe(post_old, None))

        # Suporte a timestamp numérico
        ts_recent = (now - timedelta(days=3)).timestamp()
        self.assertTrue(is_within_timeframe(ts_recent, min_date))

        ts_old = (now - timedelta(days=20)).timestamp()
        self.assertFalse(is_within_timeframe(ts_old, min_date))


if __name__ == "__main__":
    unittest.main()
