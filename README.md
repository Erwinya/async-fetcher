# async-fetcher

Concurrent HTTP fetcher using `asyncio` + retries (stdlib only).

## Status

Project scaffolding is in place. Fetcher CLI and retry logic will land in follow-up commits.

## Planned run

```powershell
python src\async_fetcher.py https://example.com https://httpbin.org/status/200 --json
```

## Requirements

- Python 3.10+
- Standard library only

## License

MIT
