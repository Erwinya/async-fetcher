#!/usr/bin/env python3
"""Async HTTP fetch CLI (retries / concurrency land next)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None
    elapsed_ms: float
    attempts: int
    error: str | None = None
    bytes: int | None = None


def _fetch_once(url: str, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


async def fetch_url(url: str, timeout: float) -> FetchResult:
    started = time.perf_counter()
    try:
        status, body = await asyncio.to_thread(_fetch_once, url, timeout)
        elapsed = (time.perf_counter() - started) * 1000.0
        return FetchResult(
            url=url,
            ok=200 <= status < 400,
            status=status,
            elapsed_ms=round(elapsed, 2),
            attempts=1,
            bytes=len(body),
        )
    except urllib.error.HTTPError as ex:
        elapsed = (time.perf_counter() - started) * 1000.0
        return FetchResult(
            url=url,
            ok=False,
            status=ex.code,
            elapsed_ms=round(elapsed, 2),
            attempts=1,
            error=f"HTTP {ex.code}",
        )
    except Exception as ex:  # noqa: BLE001
        elapsed = (time.perf_counter() - started) * 1000.0
        return FetchResult(
            url=url,
            ok=False,
            status=None,
            elapsed_ms=round(elapsed, 2),
            attempts=1,
            error=str(ex),
        )


async def run(urls: list[str], timeout: float) -> list[FetchResult]:
    return list(await asyncio.gather(*(fetch_url(u, timeout) for u in urls)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch URLs concurrently (stdlib asyncio)")
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    results = asyncio.run(run(args.urls, args.timeout))
    if args.json:
        print(json.dumps({"results": [asdict(r) for r in results]}, indent=2))
    else:
        for r in results:
            flag = "OK" if r.ok else "FAIL"
            status = r.status if r.status is not None else "-"
            extra = f" error={r.error}" if r.error else f" bytes={r.bytes}"
            print(f"[{flag}] {r.url} status={status} {r.elapsed_ms}ms attempts={r.attempts}{extra}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
