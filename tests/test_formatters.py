"""Tests for output formatters."""

from __future__ import annotations

from typing import Any

from aussiebb_blade_mcp.formatters import (
    format_available_tests,
    format_boltons,
    format_info,
    format_orders,
    format_outages,
    format_service_detail,
    format_service_line,
    format_service_list,
    format_telephony_usage,
    format_test_history,
    format_test_result,
    format_tickets,
    format_transactions,
    format_usage,
)


class TestServiceFormatters:
    def test_service_line_basic(self, sample_services: list[dict[str, Any]]) -> None:
        line = format_service_line(sample_services[0])
        assert "id=12345" in line
        assert "NBN" in line
        assert "FTTP" in line
        assert "TC4" in line

    def test_service_line_voip(self, sample_services: list[dict[str, Any]]) -> None:
        line = format_service_line(sample_services[1])
        assert "id=67890" in line
        assert "VOIP" in line

    def test_service_list_empty(self) -> None:
        assert format_service_list([]) == "(no services)"

    def test_service_list(self, sample_services: list[dict[str, Any]]) -> None:
        result = format_service_list(sample_services)
        assert "12345" in result
        assert "67890" in result
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_service_detail(self, sample_services: list[dict[str, Any]]) -> None:
        result = format_service_detail(sample_services[0])
        assert "Service ID: 12345" in result
        assert "FTTP" in result
        assert "42 Wallaby Way Sydney NSW 2000" in result
        assert "Sydney CBD" in result

    def test_service_inactive_status(self) -> None:
        svc = {"service_id": 1, "type": "NBN", "name": "Test", "status": "suspended"}
        line = format_service_line(svc)
        assert "status=suspended" in line

    def test_service_active_status_omitted(self) -> None:
        svc = {"service_id": 1, "type": "NBN", "name": "Test", "status": "active"}
        line = format_service_line(svc)
        assert "status=" not in line


class TestUsageFormatters:
    def test_usage_basic(self, sample_usage: dict[str, Any]) -> None:
        result = format_usage(sample_usage)
        assert "146.5GB" in result  # 150000 MB
        assert "24.4GB" in result  # 25000 MB
        assert "976.6GB" in result  # allowance
        assert "12/30 days" in result
        assert "17%" in result  # ~175000/1000000

    def test_usage_empty(self) -> None:
        assert format_usage({}) == "(no usage data)"

    def test_usage_unlimited(self) -> None:
        usage = {"downloadedMb": 500000, "uploadedMb": 100000, "allowanceMb": 0}
        result = format_usage(usage)
        assert "unlimited" in result

    def test_telephony_empty(self) -> None:
        assert format_telephony_usage({}) == "(no telephony data)"

    def test_telephony_basic(self) -> None:
        usage = {
            "national": {"count": 15, "cost": "3.50"},
            "mobile": {"count": 8, "cost": "12.00"},
            "international": {},
        }
        result = format_telephony_usage(usage)
        assert "National: 15 calls, $3.50" in result
        assert "Mobile: 8 calls, $12.00" in result
        assert "International" not in result


class TestOutageFormatters:
    def test_outages_all_clear(self) -> None:
        outages = {
            "networkEvents": [],
            "aussieOutages": [],
            "currentNbnOutages": [],
            "scheduledNbnOutages": [],
            "resolvedNbnOutages": [],
        }
        assert "all clear" in format_outages(outages)

    def test_outages_with_data(self, sample_outages: dict[str, Any]) -> None:
        result = format_outages(sample_outages)
        assert "ABB Outages (1)" in result
        assert "Planned Maintenance" in result
        assert "Sydney POI" in result

    def test_outages_empty(self) -> None:
        assert format_outages({}) == "(no outage data)"


class TestBillingFormatters:
    def test_transactions_basic(self, sample_transactions: dict[str, Any]) -> None:
        result = format_transactions(sample_transactions)
        assert "April 2026" in result
        assert "$89.00" in result
        assert "250/25 Mbps" in result

    def test_transactions_limit(self, sample_transactions: dict[str, Any]) -> None:
        result = format_transactions(sample_transactions, limit=1)
        assert "April 2026" in result
        assert "1 more months" in result

    def test_transactions_empty(self) -> None:
        assert format_transactions({}) == "(no transactions)"


class TestSupportFormatters:
    def test_tickets_empty(self) -> None:
        assert format_tickets([]) == "(no tickets)"

    def test_tickets_basic(self) -> None:
        tickets = [
            {"ref": "TK-12345", "status": "open", "subject": "Slow speeds", "created": "2026-04-10"},
            {"ref": "TK-12346", "status": "closed", "subject": "Billing query", "created": "2026-04-01"},
        ]
        result = format_tickets(tickets)
        assert "ref=TK-12345" in result
        assert "status=open" in result
        assert "Slow speeds" in result

    def test_orders_empty(self) -> None:
        assert format_orders([]) == "(no pending orders)"


class TestDiagnosticsFormatters:
    def test_available_tests_empty(self) -> None:
        assert format_available_tests([]) == "(no diagnostic tests available)"

    def test_available_tests_dict(self) -> None:
        tests = [
            {"name": "loopback", "description": "Test loopback connectivity"},
            {"name": "linestate", "description": "Check line sync state"},
        ]
        result = format_available_tests(tests)
        assert "loopback" in result
        assert "linestate" in result

    def test_test_result(self) -> None:
        result_data = {
            "name": "linestate",
            "status": "completed",
            "syncDown": "100000",
            "syncUp": "40000",
            "message": "Line synced at full speed",
        }
        result = format_test_result(result_data)
        assert "Test: linestate" in result
        assert "Status: completed" in result
        assert "syncDown: 100000" in result

    def test_test_history_empty(self) -> None:
        assert format_test_history({}) == "(no test history)"

    def test_boltons_empty(self) -> None:
        assert format_boltons([]) == "(no add-ons)"


class TestInfoFormatter:
    def test_info_connected(self) -> None:
        info = {
            "accounts": [{"account": "default", "status": "connected", "customer": "C-123", "services": 2}],
            "total_services": 2,
            "diagnostics_enabled": False,
        }
        result = format_info(info)
        assert "default: connected" in result
        assert "customer=C-123" in result
        assert "Total services: 2" in result
        assert "Diagnostics enabled: False" in result

    def test_info_error(self) -> None:
        info = {
            "accounts": [{"account": "home", "status": "error", "error": "Auth failed"}],
            "total_services": 0,
            "diagnostics_enabled": False,
        }
        result = format_info(info)
        assert "error" in result
        assert "Auth failed" in result
