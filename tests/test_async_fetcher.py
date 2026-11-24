import asyncio
import io
import json
import unittest
import urllib.error
from contextlib import redirect_stdout
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

    def test_retry_backoff_sleeps_between_attempts(self) -> None:
        sleeps: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        with patch.object(async_fetcher, "_fetch_once", side_effect=TimeoutError("boom")):
            with patch.object(async_fetcher.asyncio, "sleep", side_effect=fake_sleep):
                result = asyncio.run(
                    async_fetcher.fetch_url("https://x.test", 1.0, retries=2, delay=0.5)
                )
        self.assertFalse(result.ok)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_concurrency_limits_inflight_fetches(self) -> None:
        inflight = 0
        peak = 0

        async def fake_fetch(url: str, timeout: float, retries: int, delay: float = 0.2):
            nonlocal inflight, peak
            inflight += 1
            peak = max(peak, inflight)
            await asyncio.sleep(0.01)
            inflight -= 1
            return async_fetcher.FetchResult(
                url=url,
                ok=True,
                status=200,
                elapsed_ms=1.0,
                attempts=1,
                bytes=1,
            )

        urls = [f"https://u{i}.test" for i in range(6)]
        with patch.object(async_fetcher, "fetch_url", side_effect=fake_fetch):
            results = asyncio.run(async_fetcher.run(urls, 5.0, 0, 2))
        self.assertEqual(len(results), 6)
        self.assertLessEqual(peak, 2)

    def test_cli_json_output_and_exit_codes(self) -> None:
        ok = async_fetcher.FetchResult(
            url="https://ok.test",
            ok=True,
            status=200,
            elapsed_ms=1.0,
            attempts=1,
            bytes=2,
        )
        bad = async_fetcher.FetchResult(
            url="https://bad.test",
            ok=False,
            status=500,
            elapsed_ms=2.0,
            attempts=2,
            error="HTTP 500",
        )

        async def fake_run(urls, timeout, retries, concurrency):
            return [ok if "ok" in u else bad for u in urls]

        buf = io.StringIO()
        with patch.object(async_fetcher, "run", side_effect=fake_run):
            with redirect_stdout(buf):
                code = async_fetcher.main(["https://ok.test", "https://bad.test", "--json"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(len(payload["results"]), 2)
        self.assertTrue(payload["results"][0]["ok"])
        self.assertFalse(payload["results"][1]["ok"])

        buf2 = io.StringIO()
        with patch.object(async_fetcher, "run", side_effect=fake_run):
            with redirect_stdout(buf2):
                code_ok = async_fetcher.main(["https://ok.test", "--json"])
        self.assertEqual(code_ok, 0)
        self.assertTrue(json.loads(buf2.getvalue())["results"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
