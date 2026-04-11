"""Shared constants, types, and gates for Aussie Broadband Blade MCP server."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default limits for list operations (token efficiency)
DEFAULT_SERVICE_LIMIT = 20
DEFAULT_TRANSACTION_LIMIT = 10
DEFAULT_TICKET_LIMIT = 10

# Technology types for diagnostic test routing
NBN_TECHNOLOGIES = frozenset({"FTTC", "FTTN", "FTTP", "HFC"})


@dataclass
class AccountConfig:
    """Configuration for a single ABB account."""

    name: str
    username: str
    password: str


def parse_accounts() -> list[AccountConfig]:
    """Parse ABB account configuration from environment variables.

    Supports two modes:

    1. Multi-account: ``ABB_ACCOUNTS=home,office`` with per-account
       ``ABB_HOME_USERNAME``, ``ABB_HOME_PASSWORD``

    2. Single-account (default): ``ABB_USERNAME``, ``ABB_PASSWORD``
       treated as account "default".
    """
    accounts_str = os.environ.get("ABB_ACCOUNTS", "").strip()
    if accounts_str:
        accounts = []
        for name in accounts_str.split(","):
            name = name.strip()
            prefix = f"ABB_{name.upper()}_"
            username = os.environ.get(f"{prefix}USERNAME", "")
            password = os.environ.get(f"{prefix}PASSWORD", "")
            if not all([username, password]):
                logger.warning("Incomplete config for account %s — skipping", name)
                continue
            accounts.append(AccountConfig(name=name, username=username, password=password))
        if not accounts:
            raise ValueError("ABB_ACCOUNTS set but no accounts configured correctly")
        return accounts

    # Single-account mode
    username = os.environ.get("ABB_USERNAME", "")
    password = os.environ.get("ABB_PASSWORD", "")
    if not all([username, password]):
        raise ValueError("ABB credentials not configured. Set ABB_USERNAME and ABB_PASSWORD")
    return [AccountConfig(name="default", username=username, password=password)]


def is_diagnostics_enabled() -> bool:
    """Check if diagnostic tests are enabled via env var."""
    return os.environ.get("ABB_DIAGNOSTICS_ENABLED", "").lower() == "true"


def require_diagnostics() -> str | None:
    """Return an error message if diagnostics are disabled, else None."""
    if not is_diagnostics_enabled():
        return "Error: Diagnostic tests are disabled. Set ABB_DIAGNOSTICS_ENABLED=true to enable."
    return None
