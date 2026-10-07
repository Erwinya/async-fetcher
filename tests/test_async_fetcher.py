import asyncio
import unittest
from unittest.mock import patch

import async_fetcher


class FetchTests(unittest.TestCase):
    def test_fetch_once_success(self) -> None:
        class Resp:
            status = 200

            def read(self) -> bytes:
                return b"ok"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("async_fetcher.urllib.request.urlopen", return_value=Resp()):
            status, body = async_fetcher._fetch_once("https://example.com", 5.0)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"ok")

    def test_cli_requires_urls(self) -> None:
        with self.assertRaises(SystemExit):
            async_fetcher.main([])

    def test_run_gather_mocked(self) -> None:
        async def fake_fetch(url: str, timeout: float, retries: int, delay: float = 0.2):
            return async_fetcher.FetchResult(
                url=url,
                ok=True,
                status=200,
                elapsed_ms=1.0,
                attempts=1,
                bytes=2,
            )

        with patch.object(async_fetcher, "fetch_url", side_effect=fake_fetch):
            results = asyncio.run(async_fetcher.run(["https://a.test", "https://b.test"], 5.0, 0, 2))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.ok for r in results))


if __name__ == "__main__":
    unittest.main()
