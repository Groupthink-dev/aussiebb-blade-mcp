"""Aussie Broadband Blade MCP Server — usage monitoring, outage tracking, and line diagnostics.

Wraps the ``pyaussiebb`` library as MCP tools. Token-efficient by default:
compact output, null-field omission, one line per item.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from aussiebb_blade_mcp.client import ABBClient, ABBError
from aussiebb_blade_mcp.formatters import (
    format_available_tests,
    format_boltons,
    format_info,
    format_orders,
    format_outages,
    format_service_detail,
    format_service_list,
    format_telephony_usage,
    format_test_history,
    format_test_result,
    format_tickets,
    format_transactions,
    format_usage,
)
from aussiebb_blade_mcp.models import require_diagnostics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

log_level = os.environ.get("ABB_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.WARNING))

# ---------------------------------------------------------------------------
# Transport configuration
# ---------------------------------------------------------------------------

TRANSPORT = os.environ.get("ABB_MCP_TRANSPORT", "stdio")
HTTP_HOST = os.environ.get("ABB_MCP_HOST", "127.0.0.1")
HTTP_PORT = int(os.environ.get("ABB_MCP_PORT", "8780"))

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "AussieBBBlade",
    instructions=(
        "Aussie Broadband ISP operations. Monitor broadband usage, track outages, "
        "check billing, view support tickets, and run line diagnostics. "
        "Multi-account support — pass account= to target a specific account. "
        "Diagnostic tests require ABB_DIAGNOSTICS_ENABLED=true."
    ),
)

# Lazy-initialized client
_client: ABBClient | None = None


def _get_client() -> ABBClient:
    """Get or create the ABBClient singleton."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = ABBClient()
    return _client


def _error_response(e: ABBError) -> str:
    """Format a client error as a user-friendly string."""
    return f"Error: {e}"


async def _run(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking client method in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)


# ===========================================================================
# ACCOUNT & INFO
# ===========================================================================


@mcp.tool()
async def abb_info(
    account: Annotated[str | None, Field(description="Account name (omit for all accounts)")] = None,
) -> str:
    """Health check: connection status, customer details, service count, diagnostics gate status."""
    try:
        info = await _run(_get_client().info, account)
        return format_info(info)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# SERVICES
# ===========================================================================


@mcp.tool()
async def abb_services(
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """List all services (broadband, VOIP, Fetch TV). Compact one-line-per-service output with ID, type, plan, tech, speed."""
    try:
        services = await _run(_get_client().get_services, account)
        return format_service_list(services)
    except ABBError as e:
        return _error_response(e)


@mcp.tool()
async def abb_service(
    service_id: Annotated[int, Field(description="Service ID (from abb_services)")],
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Get full details for a single service including address, plan, technology type, speed tier, and POI."""
    try:
        services = await _run(_get_client().get_services, account)
        svc = next((s for s in services if s.get("service_id") == service_id), None)
        if svc is None:
            return f"Error: Service {service_id} not found"
        return format_service_detail(svc)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# USAGE MONITORING
# ===========================================================================


@mcp.tool()
async def abb_usage(
    service_id: Annotated[int, Field(description="Service ID (from abb_services)")],
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Broadband usage for a service: download, upload, remaining, billing period, percentage used."""
    try:
        usage = await _run(_get_client().get_usage, service_id, account)
        return format_usage(usage)
    except ABBError as e:
        return _error_response(e)


@mcp.tool()
async def abb_telephony(
    service_id: Annotated[int, Field(description="Service ID (from abb_services)")],
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Telephony usage breakdown: national, mobile, international, SMS, voicemail with call counts and costs."""
    try:
        usage = await _run(_get_client().get_telephony_usage, service_id, account)
        return format_telephony_usage(usage)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# OUTAGES
# ===========================================================================


@mcp.tool()
async def abb_outages(
    service_id: Annotated[int, Field(description="Service ID (from abb_services)")],
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Outages for a service: network events, ABB outages, NBN outages (current, scheduled, resolved)."""
    try:
        outages = await _run(_get_client().get_outages, service_id, account)
        return format_outages(outages)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# BILLING
# ===========================================================================


@mcp.tool()
async def abb_billing(
    limit: Annotated[int, Field(description="Max months to return (default 3)")] = 3,
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Billing transactions grouped by month: date, amount, description, type."""
    try:
        transactions = await _run(_get_client().get_transactions, account)
        return format_transactions(transactions, limit=limit)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# SUPPORT
# ===========================================================================


@mcp.tool()
async def abb_tickets(
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Support tickets: reference, status, subject, date."""
    try:
        tickets = await _run(_get_client().get_tickets, account)
        return format_tickets(tickets)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# ORDERS
# ===========================================================================


@mcp.tool()
async def abb_orders(
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Pending orders: order ID, status, type, description."""
    try:
        orders = await _run(_get_client().get_orders, account)
        return format_orders(orders)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# SERVICE ADD-ONS
# ===========================================================================


@mcp.tool()
async def abb_boltons(
    service_id: Annotated[int, Field(description="Service ID (from abb_services)")],
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
) -> str:
    """Add-ons (boltons) for a service: name, cost, status."""
    try:
        boltons = await _run(_get_client().get_boltons, service_id, account)
        return format_boltons(boltons)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# DIAGNOSTICS (gated by ABB_DIAGNOSTICS_ENABLED=true)
# ===========================================================================


@mcp.tool()
async def abb_tests(
    service_id: Annotated[int, Field(description="Service ID (from abb_services)")],
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
    show_history: Annotated[bool, Field(description="Include test history (default: false)")] = False,
) -> str:
    """Available diagnostic tests for a service, optionally with test history.

    Tests vary by technology: FTTC (DPU/NCD reset), FTTN (stability profile),
    FTTP (UNI-D status), HFC (NTD status). All include connection check, kick, loopback.
    """
    try:
        available = await _run(_get_client().get_available_tests, service_id, account)
        result = format_available_tests(available)

        if show_history:
            history = await _run(_get_client().get_test_history, service_id, account)
            result += "\n\n## Test History\n" + format_test_history(history)

        return result
    except ABBError as e:
        return _error_response(e)


@mcp.tool()
async def abb_run_test(
    service_id: Annotated[int, Field(description="Service ID (from abb_services)")],
    test_name: Annotated[str, Field(description="Test name (from abb_tests, e.g. 'loopback', 'linestate')")],
    account: Annotated[str | None, Field(description="Account name (omit for default)")] = None,
    confirm: Annotated[bool, Field(description="Must be true to confirm — some tests briefly interrupt connectivity")] = False,
) -> str:
    """Run a diagnostic test on a service. Requires ABB_DIAGNOSTICS_ENABLED=true and confirm=true.

    Some tests (port reset, kick connection) will briefly interrupt your internet connection.
    """
    gate = require_diagnostics()
    if gate:
        return gate
    if not confirm:
        return "Error: Set confirm=true to run diagnostic. Some tests briefly interrupt connectivity."
    try:
        if test_name == "linestate":
            result = await _run(_get_client().test_line_state, service_id, account)
        else:
            result = await _run(_get_client().run_test, service_id, test_name, account)
        return format_test_result(result)
    except ABBError as e:
        return _error_response(e)


# ===========================================================================
# Entry point
# ===========================================================================


def main() -> None:
    """Run the MCP server."""
    if TRANSPORT == "http":
        from aussiebb_blade_mcp.auth import BearerAuthMiddleware

        mcp.settings.http_app_kwargs = {"middleware": [BearerAuthMiddleware]}
        mcp.run(transport="streamable-http", host=HTTP_HOST, port=HTTP_PORT)
    else:
        mcp.run(transport="stdio")
