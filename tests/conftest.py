"""Shared fixtures for aussiebb-blade-mcp tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set minimal ABB environment variables."""
    monkeypatch.setenv("ABB_USERNAME", "test@example.com")
    monkeypatch.setenv("ABB_PASSWORD", "test-password")


@pytest.fixture()
def mock_env_multi(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set multi-account ABB environment variables."""
    monkeypatch.setenv("ABB_ACCOUNTS", "home,office")
    monkeypatch.setenv("ABB_HOME_USERNAME", "home@example.com")
    monkeypatch.setenv("ABB_HOME_PASSWORD", "home-password")
    monkeypatch.setenv("ABB_OFFICE_USERNAME", "office@example.com")
    monkeypatch.setenv("ABB_OFFICE_PASSWORD", "office-password")


@pytest.fixture()
def mock_env_diagnostics(monkeypatch: pytest.MonkeyPatch, mock_env: None) -> None:
    """Enable diagnostics."""
    monkeypatch.setenv("ABB_DIAGNOSTICS_ENABLED", "true")


@pytest.fixture()
def mock_aussiebb() -> MagicMock:
    """Create a mock AussieBB client."""
    mock = MagicMock()
    mock.login.return_value = True
    return mock


@pytest.fixture()
def sample_services() -> list[dict[str, Any]]:
    """Sample services response."""
    return [
        {
            "service_id": 12345,
            "type": "NBN",
            "name": "Home Broadband",
            "description": "NBN Internet",
            "status": "active",
            "plan": {"name": "250/25 Mbps", "speed": "250/25"},
            "address": {
                "streetNumber": "42",
                "street": "Wallaby Way",
                "suburb": "Sydney",
                "state": "NSW",
                "postcode": "2000",
            },
            "nbnDetails": {
                "techType": "FTTP",
                "speedTier": "TC4",
                "poiName": "Sydney CBD",
            },
        },
        {
            "service_id": 67890,
            "type": "VOIP",
            "name": "Home Phone",
            "description": "VOIP Service",
            "status": "active",
            "plan": {"name": "VOIP Basic"},
        },
    ]


@pytest.fixture()
def sample_usage() -> dict[str, Any]:
    """Sample usage response."""
    return {
        "downloadedMb": 150000,
        "uploadedMb": 25000,
        "remainingMb": 825000,
        "allowance1Mb": 1000000,
        "daysTotal": 30,
        "daysRemaining": 12,
        "lastUpdated": "2026-04-11T14:30:00+10:00",
    }


@pytest.fixture()
def sample_outages() -> dict[str, Any]:
    """Sample outages response."""
    return {
        "networkEvents": [],
        "aussieOutages": [
            {
                "type": "Planned Maintenance",
                "start": "2026-04-12T02:00:00+10:00",
                "end": "2026-04-12T06:00:00+10:00",
                "description": "Scheduled maintenance on Sydney POI",
            }
        ],
        "currentNbnOutages": [],
        "scheduledNbnOutages": [],
        "resolvedNbnOutages": [],
    }


@pytest.fixture()
def sample_transactions() -> dict[str, Any]:
    """Sample transactions response."""
    return {
        "April 2026": [
            {
                "date": "2026-04-01",
                "amount": "89.00",
                "description": "Monthly plan — 250/25 Mbps",
                "type": "invoice",
            }
        ],
        "March 2026": [
            {
                "date": "2026-03-01",
                "amount": "89.00",
                "description": "Monthly plan — 250/25 Mbps",
                "type": "invoice",
            },
            {
                "date": "2026-03-15",
                "amount": "-89.00",
                "description": "Payment received",
                "type": "payment",
            },
        ],
    }
