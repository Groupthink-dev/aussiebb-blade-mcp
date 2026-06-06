"""CONV-29 ``_meta`` audit-tail envelope tests (S-AUD-001).

Every successful tool return carries the canonical ``_meta: {...}`` JSON tail
appended after a blank line; error / gate returns stay plain.
"""

from __future__ import annotations

import json
import re
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aussiebb_blade_mcp import server
from aussiebb_blade_mcp.client import ABBError

_META_RE = re.compile(r"\n\n_meta: (\{.*\})\s*$", re.DOTALL)


def _split_meta(out: str) -> tuple[str, dict[str, Any]]:
    m = _META_RE.search(out)
    assert m is not None, f"expected a _meta tail, got: {out!r}"
    return out[: m.start()], json.loads(m.group(1))


def _assert_no_meta(out: str) -> None:
    assert _META_RE.search(out) is None, f"did not expect a _meta tail, got: {out!r}"


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    with patch("aussiebb_blade_mcp.server._get_client", return_value=client):
        yield client


class TestMetaTail:
    async def test_info_carries_meta(self, mock_client: MagicMock) -> None:
        mock_client.info.return_value = {
            "accounts": [{"account": "default", "status": "connected", "customer": "C1", "services": 2}],
            "total_services": 2,
            "diagnostics_enabled": False,
        }
        payload, meta = _split_meta(await server.abb_info())
        assert "connected" in payload
        assert meta["matched_total"] == 1

    async def test_services_carries_meta(self, mock_client: MagicMock) -> None:
        mock_client.get_services.return_value = [{"service_id": 1}, {"service_id": 2}]
        _, meta = _split_meta(await server.abb_services())
        assert meta["matched_total"] == 2

    async def test_usage_carries_meta_with_target(self, mock_client: MagicMock) -> None:
        mock_client.get_usage.return_value = {"downloaded": 1000, "uploaded": 50}
        _, meta = _split_meta(await server.abb_usage(service_id=42))
        assert meta["target_id"] == "42"

    async def test_run_test_carries_meta(self, mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ABB_DIAGNOSTICS_ENABLED", "true")
        mock_client.test_line_state.return_value = {"result": "ok"}
        _, meta = _split_meta(await server.abb_run_test(service_id=7, test_name="linestate", confirm=True))
        assert meta["target_id"] == "7"
        assert meta["rows_affected"] == 1


class TestPlainPaths:
    async def test_diagnostics_gate_is_plain(self, mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ABB_DIAGNOSTICS_ENABLED", raising=False)
        out = await server.abb_run_test(service_id=7, test_name="loopback", confirm=True)
        assert out.startswith("Error: Diagnostic tests are disabled")
        _assert_no_meta(out)

    async def test_confirm_gate_is_plain(self, mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ABB_DIAGNOSTICS_ENABLED", "true")
        out = await server.abb_run_test(service_id=7, test_name="loopback", confirm=False)
        assert "confirm=true" in out
        _assert_no_meta(out)

    async def test_error_path_is_plain(self, mock_client: MagicMock) -> None:
        mock_client.get_services.side_effect = ABBError("boom")
        out = await server.abb_services()
        assert out.startswith("Error:")
        _assert_no_meta(out)

    async def test_service_not_found_is_plain(self, mock_client: MagicMock) -> None:
        mock_client.get_services.return_value = [{"service_id": 1}]
        out = await server.abb_service(service_id=999)
        assert "not found" in out
        _assert_no_meta(out)
