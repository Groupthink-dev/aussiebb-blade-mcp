# aussiebb-blade-mcp

Aussie Broadband MCP server wrapping pyaussiebb. Part of the Sidereal marketplace.

## Quick reference

- **Runtime:** Python >=3.12, FastMCP, uv
- **Contract:** isp-v1
- **Tier:** certified
- **Repo:** groupthink-dev/aussiebb-blade-mcp

## Development

```bash
make install-dev    # Install deps
make test           # Run unit tests (51 tests, mocked)
make check          # Lint + format + type-check
make run            # Start server (stdio)
```

## Architecture

```
src/aussiebb_blade_mcp/
├── server.py       — 12 tools, FastMCP 2.0
├── client.py       — Multi-account wrapper over pyaussiebb
├── formatters.py   — Token-efficient output
├── models.py       — Config parsing, diagnostics gate
└── auth.py         — Bearer token middleware (HTTP transport)
```

## Multi-account

Supports `ABB_ACCOUNTS=home,office` with per-account `ABB_{NAME}_USERNAME` / `ABB_{NAME}_PASSWORD` env vars. Tools accept optional `account=` parameter. Falls back to single-account mode with `ABB_USERNAME` / `ABB_PASSWORD`.

## Diagnostics gate

Line tests require `ABB_DIAGNOSTICS_ENABLED=true` (env var) AND `confirm=true` (per-call). Some tests briefly interrupt connectivity.
