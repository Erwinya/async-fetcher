# async-fetcher

Concurrent HTTP fetcher using `asyncio` + retries (stdlib only).

## Status

CLI, concurrent fetches, and retry backoff (`--retries`) are in place. Concurrency limits will land in a follow-up commit.

## Run

```powershell
python src\async_fetcher.py https://example.com https://httpbin.org/status/200 --retries 2 --json
```

## Requirements

- Python 3.10+
- Standard library only

## License

MIT
