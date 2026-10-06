# async-fetcher

Concurrent HTTP fetcher using `asyncio` + retries (stdlib only).

## Status

CLI, concurrent fetches, retry backoff (`--retries`), and an in-flight concurrency limit (`--concurrency`) are in place.

## Run

```powershell
python src\async_fetcher.py https://example.com https://httpbin.org/status/200 --concurrency 2 --retries 2 --json
```

## Requirements

- Python 3.10+
- Standard library only

## License

MIT
