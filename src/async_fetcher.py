#!/usr/bin/env python3
"""Async concurrent HTTP fetcher with retries (stdlib asyncio)."""
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


def validate_options(timeout: float, retries: int, concurrency: int) -> None:
    """Raise ValueError when fetch options are out of range."""
    if timeout <= 0:
        raise ValueError("--timeout must be > 0")
    if retries < 0:
        raise ValueError("--retries must be >= 0")
    if concurrency <= 0:
        raise ValueError("--concurrency must be > 0")


def _fetch_once(url: str, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


async def fetch_url(url: str, timeout: float, retries: int, delay: float) -> FetchResult:
    attempts = 0
    started = time.perf_counter()
    last_error: str | None = None
    last_status: int | None = None
    for attempt in range(retries + 1):
        attempts = attempt + 1
        try:
            status, body = await asyncio.to_thread(_fetch_once, url, timeout)
            elapsed = (time.perf_counter() - started) * 1000.0
            return FetchResult(
                url=url,
                ok=200 <= status < 400,
                status=status,
                elapsed_ms=round(elapsed, 2),
                attempts=attempts,
                bytes=len(body),
            )
        except urllib.error.HTTPError as ex:
            last_status = ex.code
            last_error = f"HTTP {ex.code}"
            try:
                ex.close()
            except Exception:  # noqa: BLE001
                pass
            # Client errors are not retried; server errors may be.
            if 400 <= ex.code < 500:
                break
        except Exception as ex:  # noqa: BLE001
            last_error = str(ex)
        if attempt < retries:
            await asyncio.sleep(delay * (attempt + 1))
    elapsed = (time.perf_counter() - started) * 1000.0
    return FetchResult(
        url=url,
        ok=False,
        status=last_status,
        elapsed_ms=round(elapsed, 2),
        attempts=attempts,
        error=last_error,
    )


async def run(urls: list[str], timeout: float, retries: int, concurrency: int) -> list[FetchResult]:
    validate_options(timeout, retries, concurrency)
    sem = asyncio.Semaphore(concurrency)

    async def wrapped(url: str) -> FetchResult:
        async with sem:
            return await fetch_url(url, timeout, retries, delay=0.2)

    return list(await asyncio.gather(*(wrapped(u) for u in urls)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch many URLs concurrently with retries")
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        validate_options(args.timeout, args.retries, args.concurrency)
    except ValueError as ex:
        parser.error(str(ex))

    results = asyncio.run(run(args.urls, args.timeout, args.retries, args.concurrency))
    if args.json:
        print(json.dumps({"results": [asdict(r) for r in results]}, indent=2))
    else:
        for r in results:
            flag = "OK" if r.ok else "FAIL"
            status = r.status if r.status is not None else "-"
            extra = f" error={r.error}" if r.error else f" bytes={r.bytes}"
            print(f"[{flag}] {r.url} status={status} {r.elapsed_ms}ms attempts={r.attempts}{extra}")
    return 0 if all(r.ok for r in results) else 1


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
