"""OAuth helpers for the SwitchBot account API."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from time import monotonic
from typing import Any
from urllib.parse import urlencode, urlsplit

import aiohttp

from .const import (
    SwitchbotAccountConnectionError,
    SwitchbotApiError,
    SwitchbotAuthenticationError,
)
from .utils import extract_request_id

_LOGGER = logging.getLogger(__name__)

OAUTH_AUTHORIZE_URL = "https://sp.oauth.switchbot.net"
OAUTH_TOKEN_URL = "https://account.api.switchbot.net/merchant/v1/oauth/token"
OAUTH_SCOPE = "api_login"


def _oauth_error_field(
    error_data: Any, field: str, authorization_code: str
) -> str | None:
    """Return a bounded OAuth error field with the authorization code redacted."""
    if not isinstance(error_data, Mapping):
        return None
    value = error_data.get(field)
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    if authorization_code:
        value = value.replace(authorization_code, "<redacted>")
    return value[:256] or None


def _raise_for_oauth_error(status: int, error: str | None, error_suffix: str) -> None:
    """Raise the appropriate exception for an OAuth error response."""
    if status in (401, 403) or (
        status == 400 and error in {"invalid_client", "invalid_grant"}
    ):
        raise SwitchbotAuthenticationError(
            f"SwitchBot OAuth token request rejected ({status}){error_suffix}"
        )
    if 400 <= status < 500 and status != 429:
        raise SwitchbotApiError(
            f"SwitchBot OAuth token request failed ({status}){error_suffix}"
        )
    if status == 429 or status >= 500:
        raise SwitchbotAccountConnectionError(
            f"SwitchBot OAuth token service unavailable ({status}){error_suffix}"
        )


def build_oauth_authorize_url(
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Build a SwitchBot OAuth authorization URL."""
    _LOGGER.debug(
        "Building SwitchBot OAuth authorization request; authorize_host=%s "
        "redirect_host=%s",
        urlsplit(OAUTH_AUTHORIZE_URL).hostname,
        urlsplit(redirect_uri).hostname,
    )
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": OAUTH_SCOPE,
            "state": state,
        }
    )
    return f"{OAUTH_AUTHORIZE_URL}?{query}"


async def exchange_oauth_code(
    session: aiohttp.ClientSession,
    client_id: str,
    redirect_uri: str,
    code: str,
) -> dict[str, Any]:
    """Exchange an OAuth authorization code for a SwitchBot access token."""
    started = monotonic()
    _LOGGER.debug(
        "Exchanging SwitchBot OAuth authorization code; token_host=%s",
        urlsplit(OAUTH_TOKEN_URL).hostname,
    )
    error: str | None = None
    error_description: str | None = None
    token_data: Any = None
    try:
        async with session.post(
            OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            status = response.status
            _LOGGER.debug(
                "SwitchBot OAuth token endpoint returned HTTP status %s; "
                "duration_ms=%s request_id=%s",
                status,
                round((monotonic() - started) * 1000),
                extract_request_id(response.headers) or "unavailable",
            )
            if status >= 400:
                try:
                    error_data = await response.json()
                except (aiohttp.ClientError, ValueError, TypeError) as err:
                    _LOGGER.debug(
                        "SwitchBot OAuth token error response could not be parsed; "
                        "error_type=%s",
                        type(err).__name__,
                    )
                    error_data = None
                error = _oauth_error_field(error_data, "error", code)
                error_description = _oauth_error_field(
                    error_data, "error_description", code
                )
                _LOGGER.debug(
                    "SwitchBot OAuth token endpoint returned an error response; "
                    "error=%s error_description=%s",
                    error or "unavailable",
                    error_description or "unavailable",
                )
            else:
                try:
                    token_data = await response.json()
                except (aiohttp.ClientError, ValueError, TypeError) as err:
                    raise SwitchbotApiError(
                        "Invalid response from SwitchBot OAuth token API"
                    ) from err
    except (aiohttp.ClientError, TimeoutError) as err:
        raise SwitchbotAccountConnectionError(
            f"Failed to connect to SwitchBot OAuth token API: {err}"
        ) from err

    error_detail = ": ".join(
        value for value in (error, error_description) if value is not None
    )
    error_suffix = f": {error_detail}" if error_detail else ""
    _raise_for_oauth_error(status, error, error_suffix)
    if not isinstance(token_data, dict):
        raise SwitchbotApiError("Invalid response from SwitchBot OAuth token API")

    token: dict[str, Any] = token_data.copy()
    _LOGGER.debug("SwitchBot OAuth token response fields: %s", sorted(token))
    access_token = token.get("access_token")
    expires_in = token.get("expires_in")
    if (
        not isinstance(access_token, str)
        or not access_token
        or isinstance(expires_in, bool)
        or not isinstance(expires_in, int | str)
    ):
        raise SwitchbotApiError("Invalid token data from SwitchBot OAuth token API")
    try:
        normalized_expires_in = int(expires_in)
    except ValueError as err:
        raise SwitchbotApiError(
            "Invalid token data from SwitchBot OAuth token API"
        ) from err
    token["expires_in"] = normalized_expires_in
    _LOGGER.debug(
        "SwitchBot OAuth token response validated; expires_in=%s "
        "refresh_token_present=%s refresh_expires_in_present=%s",
        normalized_expires_in,
        bool(token.get("refresh_token")),
        "refresh_expires_in" in token,
    )
    return token
