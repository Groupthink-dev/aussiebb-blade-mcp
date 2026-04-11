"""Aussie Broadband API client wrapper.

Wraps ``pyaussiebb`` sync client with credential scrubbing, session management,
and multi-account support. All methods are synchronous — the server layer
wraps them via ``asyncio.to_thread`` to avoid blocking the event loop.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from aussiebb import AussieBB

from aussiebb_blade_mcp.models import AccountConfig, parse_accounts

logger = logging.getLogger(__name__)

# Patterns to scrub from error messages
_CREDENTIAL_PATTERNS = [
    re.compile(r"password[=:]\S+", re.IGNORECASE),
    re.compile(r"cookie[=:]\S+", re.IGNORECASE),
    re.compile(r"myaussie_cookie[=:]\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
]


class ABBError(Exception):
    """Base error for ABB client operations."""


class AuthError(ABBError):
    """Authentication failed."""


class NotFoundError(ABBError):
    """Requested resource not found."""


class ConnectionError(ABBError):
    """Network or API connection error."""


class RateLimitError(ABBError):
    """API rate limit hit."""


def _scrub(message: str) -> str:
    """Remove credentials from error messages."""
    for pattern in _CREDENTIAL_PATTERNS:
        message = pattern.sub("[REDACTED]", message)
    return message


class ABBClient:
    """Multi-account Aussie Broadband API client.

    Wraps pyaussiebb with:
    - Lazy login (on first API call per account)
    - Credential scrubbing on all errors
    - Multi-account routing (account param on all methods)
    - Service ID validation
    """

    def __init__(self) -> None:
        self._configs = parse_accounts()
        self._clients: dict[str, AussieBB] = {}
        self._logged_in: set[str] = set()

    @property
    def account_names(self) -> list[str]:
        """Return configured account names."""
        return [c.name for c in self._configs]

    def _get_api(self, account: str | None = None) -> AussieBB:
        """Get or create an AussieBB client for the given account."""
        name = account or self._configs[0].name
        if name in self._clients:
            return self._clients[name]

        config = next((c for c in self._configs if c.name == name), None)
        if config is None:
            raise ABBError(f"Unknown account: {name}. Available: {', '.join(self.account_names)}")

        client = AussieBB(config.username, config.password)
        self._clients[name] = client
        return client

    def _ensure_login(self, account: str | None = None) -> AussieBB:
        """Ensure the client is logged in, performing login if needed."""
        name = account or self._configs[0].name
        api = self._get_api(name)

        if name not in self._logged_in:
            try:
                result = api.login()
                if not result:
                    raise AuthError(f"Login failed for account '{name}'. Check credentials.")
                self._logged_in.add(name)
                logger.info("Logged in to ABB account '%s'", name)
            except AuthError:
                raise
            except Exception as e:
                raise AuthError(_scrub(f"Login error for account '{name}': {e}")) from e

        return api

    def _call(self, method_name: str, account: str | None = None, **kwargs: Any) -> Any:
        """Call an API method with error handling and credential scrubbing."""
        api = self._ensure_login(account)
        method = getattr(api, method_name)
        try:
            return method(**kwargs)
        except Exception as e:
            error_str = _scrub(str(e))
            error_type = type(e).__name__

            if "rate" in error_str.lower() or "429" in error_str:
                raise RateLimitError(f"Rate limited: {error_str}") from e
            if "404" in error_str or "not found" in error_str.lower():
                raise NotFoundError(error_str) from e
            if "401" in error_str or "auth" in error_str.lower() or "login" in error_str.lower():
                # Session may have expired — clear login state and retry once
                name = account or self._configs[0].name
                if name in self._logged_in:
                    self._logged_in.discard(name)
                    return self._call(method_name, account, **kwargs)
                raise AuthError(error_str) from e

            raise ABBError(f"{error_type}: {error_str}") from e

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def info(self, account: str | None = None) -> dict[str, Any]:
        """Health check: account details, service count, diagnostics gate."""
        from aussiebb_blade_mcp.models import is_diagnostics_enabled

        results: list[dict[str, Any]] = []
        accounts_to_check = [account] if account else [c.name for c in self._configs]

        for acct in accounts_to_check:
            try:
                customer = self._call("get_customer_details", acct)
                services = self._call("get_services", acct)
                results.append({
                    "account": acct,
                    "status": "connected",
                    "customer": customer.get("customer_number", ""),
                    "name": customer.get("billing_name", ""),
                    "services": len(services) if isinstance(services, list) else 0,
                })
            except ABBError as e:
                results.append({"account": acct, "status": "error", "error": str(e)})

        return {
            "accounts": results,
            "total_services": sum(a.get("services", 0) for a in results),
            "diagnostics_enabled": is_diagnostics_enabled(),
        }

    def get_customer(self, account: str | None = None) -> dict[str, Any]:
        """Get customer details."""
        return self._call("get_customer_details", account)

    def get_contacts(self, account: str | None = None) -> list[Any]:
        """Get account contacts."""
        return self._call("account_contacts", account)

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    def get_services(self, account: str | None = None) -> list[dict[str, Any]]:
        """Get all services across pages."""
        api = self._ensure_login(account)
        all_services: list[dict[str, Any]] = []
        page = 1
        try:
            while True:
                batch = api.get_services(page=page)
                if not batch:
                    break
                all_services.extend(batch)
                page += 1
        except Exception as e:
            if all_services:
                logger.warning("Pagination stopped at page %d: %s", page, _scrub(str(e)))
            else:
                raise ABBError(_scrub(f"Failed to fetch services: {e}")) from e
        return all_services

    # ------------------------------------------------------------------
    # Usage
    # ------------------------------------------------------------------

    def get_usage(self, service_id: int, account: str | None = None) -> dict[str, Any]:
        """Get broadband usage for a service."""
        return self._call("get_usage", account, service_id=service_id)

    def get_telephony_usage(self, service_id: int, account: str | None = None) -> dict[str, Any]:
        """Get telephony usage for a service."""
        return self._call("telephony_usage", account, service_id=service_id)

    # ------------------------------------------------------------------
    # Outages
    # ------------------------------------------------------------------

    def get_outages(self, service_id: int, account: str | None = None) -> dict[str, Any]:
        """Get outages for a service (network events, ABB, NBN)."""
        return self._call("service_outages", account, service_id=service_id)

    # ------------------------------------------------------------------
    # Billing
    # ------------------------------------------------------------------

    def get_transactions(self, account: str | None = None) -> dict[str, Any]:
        """Get billing transactions grouped by month."""
        return self._call("account_transactions", account)

    def get_payment_plans(self, account: str | None = None) -> dict[str, Any]:
        """Get payment plans."""
        return self._call("account_paymentplans", account)

    # ------------------------------------------------------------------
    # Support
    # ------------------------------------------------------------------

    def get_tickets(self, account: str | None = None) -> dict[str, Any]:
        """Get support tickets."""
        return self._call("support_tickets", account)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def get_orders(self, account: str | None = None) -> dict[str, Any]:
        """Get pending orders."""
        return self._call("get_orders", account)

    # ------------------------------------------------------------------
    # Service details
    # ------------------------------------------------------------------

    def get_boltons(self, service_id: int, account: str | None = None) -> dict[str, Any]:
        """Get add-ons (boltons) for a service."""
        return self._call("service_boltons", account, service_id=service_id)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_available_tests(self, service_id: int, account: str | None = None) -> list[Any]:
        """Get available diagnostic tests for a service."""
        return self._call("get_service_tests", account, service_id=service_id)

    def get_test_history(self, service_id: int, account: str | None = None) -> dict[str, Any]:
        """Get diagnostic test history for a service."""
        return self._call("get_test_history", account, service_id=service_id)

    def run_test(self, service_id: int, test_name: str, account: str | None = None) -> dict[str, Any]:
        """Run a diagnostic test on a service."""
        return self._call("run_test", account, service_id=service_id, test_name=test_name)

    def test_line_state(self, service_id: int, account: str | None = None) -> dict[str, Any]:
        """Run a line state test on a service."""
        return self._call("test_line_state", account, service_id=service_id)
