"""Testes unitários para o servidor web e rotas da API."""
import unittest
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from src.web.server import AppServer


class TestWebServer(AioHTTPTestCase):
    async def get_application(self):
        server = AppServer(host="127.0.0.1", port=8000)
        return server.app

    @unittest_run_loop
    async def test_index_page(self):
        resp = await self.client.get("/")
        self.assertEqual(resp.status, 200)
        text = await resp.text()
        self.assertIn("Instagram Viral Reels", text)
        self.assertIn("AI Agent", text)

    @unittest_run_loop
    async def test_api_status(self):
        resp = await self.client.get("/api/status")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertIn("gemini_ready", data)
        self.assertIn("instagram_ready", data)

    @unittest_run_loop
    async def test_api_reports_list(self):
        resp = await self.client.get("/api/reports")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertIsInstance(data, list)

    @unittest_run_loop
    async def test_api_download_not_found(self):
        resp = await self.client.get("/api/reports/download/inexistente.md")
        self.assertEqual(resp.status, 404)


if __name__ == "__main__":
    unittest.main()
