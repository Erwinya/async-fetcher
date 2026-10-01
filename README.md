# async-fetcher

Concurrent HTTP fetcher using `asyncio` + retries (stdlib only).

## Status

CLI and concurrent single-attempt fetches are in place. Retry backoff and concurrency limits will land in follow-up commits.

## Run

```powershell
python src\async_fetcher.py https://example.com https://httpbin.org/status/200 --json
```

## Requirements

- Python 3.10+
- Standard library only

## License

MIT
