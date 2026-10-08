# async-fetcher

Concurrent HTTP fetcher using `asyncio` + retries (stdlib only).

## Status

Complete: CLI, retries, concurrency limits, packaging, unit tests, and CI.

## Run

```powershell
python src\async_fetcher.py https://example.com https://httpbin.org/status/200 --retries 2 --concurrency 4 --json
```

Install locally (optional):

```powershell
pip install -e .
async-fetcher https://example.com --json
```

## Development

```powershell
pip install -e ".[dev]"
pytest
```

## Requirements

- Python 3.10+
- Standard library only (pytest optional for tests)

## License

MIT
