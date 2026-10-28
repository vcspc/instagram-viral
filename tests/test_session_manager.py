"""Testes do gerenciador de sessão do Instagram."""
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.instagram.session_manager import InstagramSessionManager


class TestSessionManager(unittest.TestCase):
    def test_session_manager_init(self):
        mgr = InstagramSessionManager(
            username="test_user",
            password="secret_password",
            session_dir=Path("test_sessions"),
            sessionid="123456789%3Aabcdefghijklmnopqrstuvwxyz",
        )
        self.assertEqual(mgr.username, "test_user")
        self.assertEqual(mgr.password, "secret_password")
        self.assertEqual(mgr.sessionid, "123456789%3Aabcdefghijklmnopqrstuvwxyz")
        self.assertEqual(mgr.session_file, Path("test_sessions/test_user.session.json"))

    @patch("src.instagram.session_manager.Client")
    def test_authenticated_client_with_sessionid(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mgr = InstagramSessionManager(
            username="test_user",
            session_dir=Path("test_sessions_tmp"),
            sessionid="123456789%3Aabcdefghijklmnopqrstuvwxyz",
        )
        # Garante que session_file não existe
        mgr.session_file = Path("test_sessions_tmp/non_existent.json")

        client = mgr.get_authenticated_client()
        mock_client.get_timeline_feed.assert_called_once()
        mock_client.dump_settings.assert_called_once()
        self.assertEqual(client, mock_client)


    def test_parse_full_document_cookie(self):
        mgr = InstagramSessionManager(
            username="test_user",
            sessionid='mid=Z123; ds_user_id=66045681570; sessionid=66045681570%3Aabcxyz; csrftoken=csrftest123',
        )
        mgr._apply_session_cookies(mgr.sessionid)
        # Verifica se o User-Agent foi ajustado para Desktop e os cabeçalhos de Android foram removidos
        self.assertIn("Chrome", mgr.client.private.headers.get("User-Agent", ""))
        self.assertNotIn("X-IG-Android-ID", mgr.client.private.headers)
        self.assertEqual(mgr.client.private.headers.get("X-IG-App-ID"), "936619743392459")


if __name__ == "__main__":
    unittest.main()
