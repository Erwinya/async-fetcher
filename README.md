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


## Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--timeout` | `5.0` | Per-request timeout in seconds |
| `--retries` | `2` | Extra attempts after a failed request |
| `--concurrency` | `8` | Max in-flight fetches |
| `--json` | off | Emit JSON results instead of plain text |

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
