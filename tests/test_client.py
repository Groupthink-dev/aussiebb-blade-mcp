"""Tests for ABB client wrapper."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aussiebb_blade_mcp.client import ABBClient, ABBError, AuthError, _scrub


class TestCredentialScrubbing:
    def test_scrub_password(self) -> None:
        assert "REDACTED" in _scrub("password=mysecret123")

    def test_scrub_cookie(self) -> None:
        assert "REDACTED" in _scrub("cookie=abc123def456")

    def test_scrub_bearer(self) -> None:
        assert "REDACTED" in _scrub("Bearer sk-abc123")

    def test_scrub_preserves_safe_text(self) -> None:
        safe = "Connection timeout after 30s"
        assert _scrub(safe) == safe


class TestABBClientInit:
    def test_single_account(self, mock_env: None) -> None:
        with patch("aussiebb_blade_mcp.client.AussieBB"):
            client = ABBClient()
            assert client.account_names == ["default"]

    def test_multi_account(self, mock_env_multi: None) -> None:
        with patch("aussiebb_blade_mcp.client.AussieBB"):
            client = ABBClient()
            assert client.account_names == ["home", "office"]

    def test_unknown_account_raises(self, mock_env: None) -> None:
        with patch("aussiebb_blade_mcp.client.AussieBB"):
            client = ABBClient()
            with pytest.raises(ABBError, match="Unknown account"):
                client._get_api("nonexistent")


class TestABBClientLogin:
    def test_login_success(self, mock_env: None) -> None:
        mock_api = MagicMock()
        mock_api.login.return_value = True
        with patch("aussiebb_blade_mcp.client.AussieBB", return_value=mock_api):
            client = ABBClient()
            api = client._ensure_login()
            mock_api.login.assert_called_once()
            assert api is mock_api

    def test_login_failure(self, mock_env: None) -> None:
        mock_api = MagicMock()
        mock_api.login.return_value = False
        with patch("aussiebb_blade_mcp.client.AussieBB", return_value=mock_api):
            client = ABBClient()
            with pytest.raises(AuthError, match="Login failed"):
                client._ensure_login()

    def test_login_cached(self, mock_env: None) -> None:
        mock_api = MagicMock()
        mock_api.login.return_value = True
        with patch("aussiebb_blade_mcp.client.AussieBB", return_value=mock_api):
            client = ABBClient()
            client._ensure_login()
            client._ensure_login()
            # Only called once
            mock_api.login.assert_called_once()


class TestABBClientMethods:
    def test_get_services(self, mock_env: None, sample_services: list[dict[str, Any]]) -> None:
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_services.side_effect = [sample_services, []]
        with patch("aussiebb_blade_mcp.client.AussieBB", return_value=mock_api):
            client = ABBClient()
            services = client.get_services()
            assert len(services) == 2
            assert services[0]["service_id"] == 12345

    def test_get_usage(self, mock_env: None, sample_usage: dict[str, Any]) -> None:
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_usage.return_value = sample_usage
        with patch("aussiebb_blade_mcp.client.AussieBB", return_value=mock_api):
            client = ABBClient()
            usage = client.get_usage(12345)
            assert usage["downloadedMb"] == 150000
            mock_api.get_usage.assert_called_once_with(service_id=12345)

    def test_get_outages(self, mock_env: None, sample_outages: dict[str, Any]) -> None:
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.service_outages.return_value = sample_outages
        with patch("aussiebb_blade_mcp.client.AussieBB", return_value=mock_api):
            client = ABBClient()
            outages = client.get_outages(12345)
            assert len(outages["aussieOutages"]) == 1

    def test_info_multi_account(self, mock_env_multi: None) -> None:
        mock_api_home = MagicMock()
        mock_api_home.login.return_value = True
        mock_api_home.get_customer_details.return_value = {"customer_number": "C-100", "billing_name": "Home"}
        mock_api_home.get_services.return_value = [{"service_id": 1}, {"service_id": 2}]

        mock_api_office = MagicMock()
        mock_api_office.login.return_value = True
        mock_api_office.get_customer_details.return_value = {"customer_number": "C-200", "billing_name": "Office"}
        mock_api_office.get_services.return_value = [{"service_id": 3}]

        call_count = 0

        def create_mock(username: str, password: str) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return mock_api_home if call_count == 1 else mock_api_office

        with patch("aussiebb_blade_mcp.client.AussieBB", side_effect=create_mock):
            client = ABBClient()
            info = client.info()
            assert info["total_services"] == 3
            assert len(info["accounts"]) == 2
            assert info["accounts"][0]["customer"] == "C-100"
            assert info["accounts"][1]["customer"] == "C-200"

    def test_credential_scrubbing_on_error(self, mock_env: None) -> None:
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_usage.side_effect = Exception("password=secret123 failed")
        with patch("aussiebb_blade_mcp.client.AussieBB", return_value=mock_api):
            client = ABBClient()
            with pytest.raises(ABBError) as exc_info:
                client.get_usage(12345)
            assert "secret123" not in str(exc_info.value)
            assert "REDACTED" in str(exc_info.value)
