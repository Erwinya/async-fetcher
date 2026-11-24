import asyncio
import unittest
import urllib.error
from io import BytesIO
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

    def test_validate_options_rejects_bad_values(self) -> None:
        with self.assertRaises(ValueError):
            async_fetcher.validate_options(0, 1, 1)
        with self.assertRaises(ValueError):
            async_fetcher.validate_options(1, -1, 1)
        with self.assertRaises(ValueError):
            async_fetcher.validate_options(1, 0, 0)

    def test_cli_rejects_invalid_timeout(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            async_fetcher.main(["https://example.com", "--timeout", "0"])
        self.assertEqual(ctx.exception.code, 2)

    def test_http_error_preserves_status_and_skips_4xx_retry(self) -> None:
        err = urllib.error.HTTPError(
            "https://x.test", 404, "Not Found", hdrs={}, fp=BytesIO(b"missing")
        )
        with patch.object(async_fetcher, "_fetch_once", side_effect=err):
            result = asyncio.run(async_fetcher.fetch_url("https://x.test", 1.0, retries=3, delay=0.0))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 404)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.error, "HTTP 404")

    def test_http_5xx_retries_and_keeps_status(self) -> None:
        def raise_503(*_args, **_kwargs):
            raise urllib.error.HTTPError(
                "https://x.test", 503, "Unavailable", hdrs={}, fp=BytesIO(b"down")
            )

        with patch.object(async_fetcher, "_fetch_once", side_effect=raise_503):
            result = asyncio.run(async_fetcher.fetch_url("https://x.test", 1.0, retries=2, delay=0.0))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 503)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(result.error, "HTTP 503")


if __name__ == "__main__":
    unittest.main()
