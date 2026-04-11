"""Token-efficient output formatters for Aussie Broadband Blade MCP server.

All formatters return compact strings optimised for LLM consumption:
- One line per item
- Pipe-delimited fields
- Null-field omission
- Human-readable units (GB, MB, %)
"""

from __future__ import annotations

from typing import Any


def _bytes_to_human(value: Any) -> str:
    """Convert bytes/MB to human-readable format."""
    if value is None:
        return "?"
    try:
        mb = float(value)
    except (ValueError, TypeError):
        return str(value)
    if mb >= 1024:
        return f"{mb / 1024:.1f}GB"
    return f"{mb:.0f}MB"


def _pct(used: Any, total: Any) -> str:
    """Calculate percentage used."""
    try:
        u, t = float(used), float(total)
        if t <= 0:
            return "unlimited"
        return f"{(u / t) * 100:.0f}%"
    except (ValueError, TypeError, ZeroDivisionError):
        return "?"


# ------------------------------------------------------------------
# Info
# ------------------------------------------------------------------


def format_info(info: dict[str, Any]) -> str:
    """Format health check info."""
    lines = []
    for a in info.get("accounts", []):
        status = a.get("status", "unknown")
        name = a.get("account", "?")
        if status == "connected":
            lines.append(f"{name}: connected | customer={a.get('customer', '?')} | services={a.get('services', 0)}")
        else:
            lines.append(f"{name}: {status} — {a.get('error', 'unknown error')}")
    lines.append(f"Total services: {info.get('total_services', 0)}")
    lines.append(f"Diagnostics enabled: {info.get('diagnostics_enabled', False)}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Services
# ------------------------------------------------------------------


def format_service_line(svc: dict[str, Any]) -> str:
    """Format a single service as a compact one-line string."""
    parts = []

    svc_id = svc.get("service_id")
    if svc_id:
        parts.append(f"id={svc_id}")

    stype = svc.get("type", "")
    name = svc.get("name") or svc.get("description") or "(unnamed)"
    parts.append(f"{stype}: {name}" if stype else name)

    plan = svc.get("plan", {})
    if isinstance(plan, dict):
        plan_name = plan.get("name")
        if plan_name:
            parts.append(f"plan={plan_name}")

    address = svc.get("address", {})
    if isinstance(address, dict):
        suburb = address.get("suburb")
        if suburb:
            parts.append(f"loc={suburb}")

    tech = svc.get("nbnDetails", {})
    if isinstance(tech, dict):
        tech_type = tech.get("techType")
        speed = tech.get("speedTier")
        if tech_type:
            parts.append(f"tech={tech_type}")
        if speed:
            parts.append(f"speed={speed}")

    status = svc.get("status")
    if status and status != "active":
        parts.append(f"status={status}")

    return " | ".join(parts)


def format_service_list(services: list[dict[str, Any]]) -> str:
    """Format a list of services as compact lines."""
    if not services:
        return "(no services)"
    return "\n".join(format_service_line(s) for s in services)


def format_service_detail(svc: dict[str, Any]) -> str:
    """Format a single service with full details."""
    lines = []
    lines.append(f"Service ID: {svc.get('service_id', '?')}")
    lines.append(f"Type: {svc.get('type', '?')}")
    lines.append(f"Name: {svc.get('name') or svc.get('description') or '(unnamed)'}")

    plan = svc.get("plan", {})
    if isinstance(plan, dict):
        if plan.get("name"):
            lines.append(f"Plan: {plan['name']}")
        if plan.get("speed"):
            lines.append(f"Speed: {plan['speed']}")

    address = svc.get("address", {})
    if isinstance(address, dict):
        parts = [
            address.get("streetNumber", ""),
            address.get("street", ""),
            address.get("suburb", ""),
            address.get("state", ""),
            address.get("postcode", ""),
        ]
        addr_str = " ".join(p for p in parts if p)
        if addr_str.strip():
            lines.append(f"Address: {addr_str}")

    nbn = svc.get("nbnDetails", {})
    if isinstance(nbn, dict):
        if nbn.get("techType"):
            lines.append(f"Technology: {nbn['techType']}")
        if nbn.get("speedTier"):
            lines.append(f"Speed tier: {nbn['speedTier']}")
        if nbn.get("poiName"):
            lines.append(f"POI: {nbn['poiName']}")

    lines.append(f"Status: {svc.get('status', '?')}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Usage
# ------------------------------------------------------------------


def format_usage(usage: dict[str, Any]) -> str:
    """Format broadband usage as compact output."""
    if not usage:
        return "(no usage data)"

    lines = []
    dl = usage.get("downloadedMb")
    ul = usage.get("uploadedMb")
    remaining = usage.get("remainingMb")
    allowance = usage.get("allowance1Mb") or usage.get("allowanceMb")

    if dl is not None:
        total_used = (float(dl) if dl else 0) + (float(ul) if ul else 0)
        lines.append(f"Downloaded: {_bytes_to_human(dl)}")
        lines.append(f"Uploaded: {_bytes_to_human(ul)}")
        lines.append(f"Total used: {_bytes_to_human(total_used)}")

    if allowance is not None:
        lines.append(f"Allowance: {_bytes_to_human(allowance)}")
        if dl is not None:
            total = (float(dl) if dl else 0) + (float(ul) if ul else 0)
            lines.append(f"Used: {_pct(total, allowance)}")

    if remaining is not None:
        lines.append(f"Remaining: {_bytes_to_human(remaining)}")

    days_total = usage.get("daysTotal")
    days_remaining = usage.get("daysRemaining")
    if days_total is not None:
        lines.append(f"Billing period: {days_remaining or '?'}/{days_total} days remaining")

    last_updated = usage.get("lastUpdated")
    if last_updated:
        lines.append(f"Last updated: {last_updated}")

    return "\n".join(lines) if lines else "(no usage data)"


def format_telephony_usage(usage: dict[str, Any]) -> str:
    """Format telephony usage as compact output."""
    if not usage:
        return "(no telephony data)"

    lines = []
    for key, label in [
        ("national", "National"),
        ("mobile", "Mobile"),
        ("international", "International"),
        ("sms", "SMS"),
        ("voicemail", "Voicemail"),
    ]:
        data = usage.get(key, {})
        if isinstance(data, dict) and data:
            cost = data.get("cost", data.get("totalCost", ""))
            count = data.get("count", data.get("totalCount", ""))
            if cost or count:
                lines.append(f"{label}: {count} calls, ${cost}" if count else f"{label}: ${cost}")

    return "\n".join(lines) if lines else "(no telephony data)"


# ------------------------------------------------------------------
# Outages
# ------------------------------------------------------------------


def _format_outage(outage: dict[str, Any], prefix: str = "") -> str:
    """Format a single outage as a compact line."""
    parts = []
    if prefix:
        parts.append(prefix)

    otype = outage.get("type", "")
    if otype:
        parts.append(otype)

    start = outage.get("start") or outage.get("startDate", "")
    end = outage.get("end") or outage.get("endDate", "")
    if start:
        time_str = f"{start}"
        if end:
            time_str += f" → {end}"
        parts.append(time_str)

    desc = outage.get("description") or outage.get("summary", "")
    if desc:
        # Truncate long descriptions for token efficiency
        parts.append(desc[:200])

    return " | ".join(parts)


def format_outages(outages: dict[str, Any]) -> str:
    """Format outages grouped by source."""
    if not outages:
        return "(no outage data)"

    lines = []
    sections = [
        ("networkEvents", "Network Events"),
        ("aussieOutages", "ABB Outages"),
        ("currentNbnOutages", "NBN Current"),
        ("scheduledNbnOutages", "NBN Scheduled"),
        ("resolvedNbnOutages", "NBN Resolved"),
    ]

    any_found = False
    for key, label in sections:
        items = outages.get(key, [])
        if not items:
            continue
        any_found = True
        lines.append(f"## {label} ({len(items)})")
        if isinstance(items, list):
            for item in items[:10]:  # Cap at 10 per section for token efficiency
                lines.append(_format_outage(item))
        lines.append("")

    if not any_found:
        return "(no outages — all clear)"
    return "\n".join(lines).rstrip()


# ------------------------------------------------------------------
# Billing
# ------------------------------------------------------------------


def format_transactions(transactions: dict[str, Any], limit: int = 10) -> str:
    """Format billing transactions grouped by month."""
    if not transactions:
        return "(no transactions)"

    lines = []
    count = 0
    for month, items in transactions.items():
        if count >= limit:
            lines.append(f"... ({len(transactions) - limit} more months)")
            break
        lines.append(f"## {month}")
        if isinstance(items, list):
            for txn in items:
                amount = txn.get("amount", "?")
                desc = txn.get("description", "")
                date = txn.get("date", "")
                ttype = txn.get("type", "")
                parts = [date, f"${amount}", desc]
                if ttype:
                    parts.append(f"type={ttype}")
                lines.append(" | ".join(p for p in parts if p))
        lines.append("")
        count += 1

    return "\n".join(lines).rstrip() if lines else "(no transactions)"


# ------------------------------------------------------------------
# Support
# ------------------------------------------------------------------


def format_tickets(tickets: dict[str, Any] | list[Any]) -> str:
    """Format support tickets as compact lines."""
    items = tickets if isinstance(tickets, list) else tickets.get("tickets", tickets.get("data", []))
    if not items:
        return "(no tickets)"

    lines = []
    for t in items:
        parts = []
        ref = t.get("ref") or t.get("id", "?")
        parts.append(f"ref={ref}")
        status = t.get("status", "")
        if status:
            parts.append(f"status={status}")
        subject = t.get("subject", "")
        if subject:
            parts.append(subject[:100])
        created = t.get("created") or t.get("date", "")
        if created:
            parts.append(f"date={created}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------


def format_orders(orders: dict[str, Any] | list[Any]) -> str:
    """Format pending orders as compact lines."""
    items = orders if isinstance(orders, list) else orders.get("orders", orders.get("data", []))
    if not items:
        return "(no pending orders)"

    lines = []
    for o in items:
        parts = []
        order_id = o.get("id") or o.get("orderId", "?")
        parts.append(f"id={order_id}")
        status = o.get("status", "")
        if status:
            parts.append(f"status={status}")
        otype = o.get("type", "")
        if otype:
            parts.append(f"type={otype}")
        desc = o.get("description", "")
        if desc:
            parts.append(desc[:100])
        lines.append(" | ".join(parts))

    return "\n".join(lines)


# ------------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------------


def format_available_tests(tests: list[Any]) -> str:
    """Format available diagnostic tests."""
    if not tests:
        return "(no diagnostic tests available)"

    lines = []
    for t in tests:
        if hasattr(t, "name"):
            name = t.name
            desc = getattr(t, "description", "")
        elif isinstance(t, dict):
            name = t.get("name", "?")
            desc = t.get("description", "")
        else:
            name = str(t)
            desc = ""
        line = f"- {name}"
        if desc:
            line += f": {desc}"
        lines.append(line)

    return "\n".join(lines)


def format_test_result(result: dict[str, Any]) -> str:
    """Format a diagnostic test result."""
    if not result:
        return "(no test result)"

    lines = []
    test_name = result.get("name") or result.get("test", "?")
    lines.append(f"Test: {test_name}")

    status = result.get("status", "?")
    lines.append(f"Status: {status}")

    for key in ["syncUp", "syncDown", "attainableUp", "attainableDown", "lineAttenuation", "noiseMargin"]:
        val = result.get(key)
        if val is not None:
            lines.append(f"{key}: {val}")

    message = result.get("message") or result.get("result", "")
    if message:
        lines.append(f"Message: {message}")

    return "\n".join(lines)


def format_test_history(history: dict[str, Any]) -> str:
    """Format diagnostic test history."""
    tests = history if isinstance(history, list) else history.get("tests", history.get("data", []))
    if not tests:
        return "(no test history)"

    lines = []
    for t in tests[:20]:  # Cap for token efficiency
        parts = []
        name = t.get("name") or t.get("test", "?")
        parts.append(name)
        status = t.get("status", "")
        if status:
            parts.append(f"status={status}")
        date = t.get("date") or t.get("created", "")
        if date:
            parts.append(f"date={date}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


# ------------------------------------------------------------------
# Boltons
# ------------------------------------------------------------------


def format_boltons(boltons: dict[str, Any]) -> str:
    """Format service add-ons (boltons)."""
    items = boltons if isinstance(boltons, list) else boltons.get("boltons", boltons.get("data", []))
    if not items:
        return "(no add-ons)"

    lines = []
    for b in items:
        parts = []
        name = b.get("name", "?")
        parts.append(name)
        cost = b.get("cost") or b.get("price", "")
        if cost:
            parts.append(f"${cost}")
        status = b.get("status", "")
        if status:
            parts.append(f"status={status}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)
