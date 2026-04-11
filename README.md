# aussiebb-blade-mcp

An MCP server that gives AI agents structured access to Aussie Broadband accounts. Built for the [Model Context Protocol](https://modelcontextprotocol.io) with token efficiency and operational security as first-class design goals.

## Why this exists

Aussie Broadband has no public API program. The MyAussie portal API is undocumented and session-authenticated — not designed for programmatic access. The community-maintained [pyaussiebb](https://github.com/yaleman/pyaussiebb) library (MIT, 6 years, powers the Home Assistant integration) has done the reverse-engineering work. This MCP wraps it with the guardrails that automated agents need:

- **Token-efficient output** — compact pipe-delimited format. A full service listing in ~50 tokens per service. Usage summaries with human-readable units (GB, %) and billing period context.
- **Credential isolation** — passwords and session cookies scrubbed from all error output. Bearer token auth for HTTP transport. No credential caching beyond the session.
- **Diagnostic safety gate** — line tests (connection check, port reset, loopback) require explicit opt-in via `ABB_DIAGNOSTICS_ENABLED=true` *and* per-call `confirm=true`. Port resets and connection kicks briefly interrupt service.
- **Multi-account** — manage home and business accounts from a single MCP instance. Each account authenticates independently.

## How this differs from other ISP tools

| | aussiebb-blade-mcp | Home Assistant integration | Raw pyaussiebb |
|---|---|---|---|
| **Interface** | MCP tools (any LLM agent) | HA entities + automations | Python library |
| **Output** | Token-optimised text | Sensor values | Raw dicts |
| **Multi-account** | Native (env var config) | One account per integration | Manual |
| **Diagnostic safety** | Double-gated (env + confirm) | Exposed as buttons | No gate |
| **Auth transport** | Bearer token + stdio | HA auth | None |
| **Credential handling** | Scrubbed from all output | HA secrets | Caller's responsibility |

## Quick start

```bash
# Install
uv pip install -e .

# Configure
export ABB_USERNAME="your.email@example.com"
export ABB_PASSWORD="your-myaussie-password"

# Run
aussiebb-blade-mcp
```

## 12 tools, 5 categories

### Account & Services (3 tools)

| Tool | Purpose | Token cost |
|------|---------|------------|
| `abb_info` | Health check — accounts, connection status, service count, diagnostics gate | ~40 |
| `abb_services` | List all services (broadband, VOIP, Fetch TV) with plan, tech, speed | ~50/svc |
| `abb_service` | Full detail for one service — address, POI, technology type | ~120 |

### Usage Monitoring (2 tools)

| Tool | Purpose | Token cost |
|------|---------|------------|
| `abb_usage` | Broadband usage: download, upload, remaining, billing period, % used | ~80 |
| `abb_telephony` | Telephony breakdown: national, mobile, international, SMS, voicemail | ~60 |

### Network & Outages (1 tool)

| Tool | Purpose | Token cost |
|------|---------|------------|
| `abb_outages` | Network events, ABB outages, NBN outages (current, scheduled, resolved) | ~40/outage |

### Billing & Support (3 tools)

| Tool | Purpose | Token cost |
|------|---------|------------|
| `abb_billing` | Transactions by month (configurable depth) | ~30/txn |
| `abb_tickets` | Support tickets: ref, status, subject, date | ~30/ticket |
| `abb_orders` | Pending orders: ID, status, type | ~30/order |

### Diagnostics (3 tools, gated)

| Tool | Purpose | Token cost |
|------|---------|------------|
| `abb_boltons` | Service add-ons (data blocks, extras) | ~25/bolton |
| `abb_tests` | Available diagnostic tests + optional history | ~20/test |
| `abb_run_test` | Execute a test (loopback, linestate, port reset, etc.) | ~80 |

### Output format

```
id=12345 | NBN: Home Broadband | plan=250/25 Mbps | loc=Sydney | tech=FTTP | speed=TC4
id=67890 | VOIP: Home Phone | plan=VOIP Basic
```

```
Downloaded: 146.5GB
Uploaded: 24.4GB
Total used: 170.9GB
Allowance: 976.6GB
Used: 17%
Remaining: 805.7GB
Billing period: 12/30 days remaining
```

## Multi-account support

Manage multiple ABB accounts (household + business, parent + child) from a single MCP instance:

```bash
export ABB_ACCOUNTS="home,office"
export ABB_HOME_USERNAME="home@example.com"
export ABB_HOME_PASSWORD="home-password"
export ABB_OFFICE_USERNAME="office@example.com"
export ABB_OFFICE_PASSWORD="office-password"
```

Pass `account="office"` to any tool to target a specific account. Omit for the first configured account.

Single-account mode (plain `ABB_USERNAME`/`ABB_PASSWORD`) remains fully supported.

## Security model

| Layer | Mechanism |
|-------|-----------|
| **Credential scrubbing** | Passwords, cookies, and tokens stripped from all error output |
| **Diagnostics gate** | `ABB_DIAGNOSTICS_ENABLED=true` required for any line test |
| **Test confirmation** | `abb_run_test` additionally requires `confirm=true` |
| **Bearer auth** | Optional `ABB_MCP_API_TOKEN` for HTTP transport |
| **Session isolation** | Each account authenticates independently; no credential sharing |
| **No persistence** | Credentials read from env at startup, never written to disk |
| **Rate limiting** | Automatic backoff on 429 responses from ABB API |
| **MFA awareness** | Documents MFA requirement for plan changes; does not bypass |

## Sidereal integration

Add to your MCP config:

```json
{
  "mcpServers": {
    "aussiebb": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "~/src/aussiebb-blade-mcp", "run", "aussiebb-blade-mcp"],
      "env": {
        "ABB_USERNAME": "...",
        "ABB_PASSWORD": "...",
        "ABB_DIAGNOSTICS_ENABLED": "false"
      }
    }
  }
}
```

### Webhook trigger patterns

The outage and usage tools are designed for downstream automation:

- **Outage monitoring** — `abb_outages` returns structured outage data suitable for Sidereal WatchPaths triggers or scheduled polling. Detect new outages, scheduled maintenance windows, and resolution events.
- **Usage threshold alerts** — `abb_usage` returns percentage-used and days-remaining, enabling threshold-based alerting (e.g. "notify at 80% usage with 10+ days remaining").
- **Service status changes** — `abb_services` returns service status, enabling detection of suspensions, activations, or plan changes.

## Development

```bash
make install-dev    # Install with dev + test dependencies
make test           # Unit tests (mocked API, no ABB account needed)
make check          # Lint + format + type-check
make run            # Start MCP server (stdio)
```

### Architecture

```
src/aussiebb_blade_mcp/
├── server.py       — FastMCP 2.0 server, 12 @mcp.tool decorators
├── client.py       — ABBClient with multi-account, credential scrubbing, session management
├── formatters.py   — Token-efficient output (pipe-delimited, null omission, human units)
├── models.py       — Account config, diagnostics gate, constants
└── auth.py         — Bearer token middleware for HTTP transport
```

Built with [FastMCP 2.0](https://github.com/jlowin/fastmcp) and [pyaussiebb](https://github.com/yaleman/pyaussiebb).

### Testing

```bash
make test           # Unit tests (mocked)
make test-cov       # With coverage report
make test-e2e       # Live account tests (requires ABB_E2E=1 + real credentials)
```

## Acknowledgements

- [yaleman/pyaussiebb](https://github.com/yaleman/pyaussiebb) — the reverse-engineering work that makes this possible
- [Home Assistant aussie_broadband](https://www.home-assistant.io/integrations/aussie_broadband/) — production validation of the underlying API surface

## License

MIT
