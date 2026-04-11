"""Tests for models and configuration parsing."""

from __future__ import annotations

import pytest

from aussiebb_blade_mcp.models import (
    AccountConfig,
    is_diagnostics_enabled,
    parse_accounts,
    require_diagnostics,
)


class TestParseAccounts:
    def test_single_account(self, mock_env: None) -> None:
        accounts = parse_accounts()
        assert len(accounts) == 1
        assert accounts[0].name == "default"
        assert accounts[0].username == "test@example.com"
        assert accounts[0].password == "test-password"

    def test_multi_account(self, mock_env_multi: None) -> None:
        accounts = parse_accounts()
        assert len(accounts) == 2
        assert accounts[0].name == "home"
        assert accounts[0].username == "home@example.com"
        assert accounts[1].name == "office"
        assert accounts[1].username == "office@example.com"

    def test_missing_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ABB_USERNAME", raising=False)
        monkeypatch.delenv("ABB_PASSWORD", raising=False)
        monkeypatch.delenv("ABB_ACCOUNTS", raising=False)
        with pytest.raises(ValueError, match="ABB credentials not configured"):
            parse_accounts()

    def test_multi_account_incomplete(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ABB_ACCOUNTS", "home,office")
        monkeypatch.setenv("ABB_HOME_USERNAME", "home@example.com")
        # Missing ABB_HOME_PASSWORD and all office vars
        monkeypatch.delenv("ABB_HOME_PASSWORD", raising=False)
        monkeypatch.delenv("ABB_OFFICE_USERNAME", raising=False)
        monkeypatch.delenv("ABB_OFFICE_PASSWORD", raising=False)
        with pytest.raises(ValueError, match="no accounts configured"):
            parse_accounts()


class TestDiagnosticsGate:
    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ABB_DIAGNOSTICS_ENABLED", raising=False)
        assert not is_diagnostics_enabled()
        assert require_diagnostics() is not None
        assert "disabled" in require_diagnostics().lower()  # type: ignore[union-attr]

    def test_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ABB_DIAGNOSTICS_ENABLED", "true")
        assert is_diagnostics_enabled()
        assert require_diagnostics() is None

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ABB_DIAGNOSTICS_ENABLED", "TRUE")
        assert is_diagnostics_enabled()

    def test_not_enabled_with_other_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ABB_DIAGNOSTICS_ENABLED", "yes")
        assert not is_diagnostics_enabled()
