"""
Authentication module for ERP connectors.

Handles OAuth 2.0, API Key, Basic Auth, and Bearer Token authentication.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import logging

import httpx


logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """OAuth token information"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """
        Check if token is expired or will expire soon.

        Args:
            buffer_seconds: Refresh buffer time before actual expiry

        Returns:
            True if token is expired or about to expire
        """
        expiry_time = self.issued_at + timedelta(seconds=self.expires_in - buffer_seconds)
        return datetime.now(timezone.utc) >= expiry_time

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for serialization"""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": str(self.expires_in),
            "refresh_token": self.refresh_token or "",
            "scope": self.scope or "",
            "issued_at": self.issued_at.isoformat(),
        }


class AuthHandler(ABC):
    """Abstract base class for authentication handlers"""

    def __init__(self, credentials: Dict[str, str], config: Optional[Dict[str, str]] = None):
        """
        Initialize auth handler.

        Args:
            credentials: Authentication credentials
            config: Optional configuration (URLs, scopes, etc.)
        """
        self.credentials = credentials
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def get_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Returns:
            Dictionary of HTTP headers
        """
        pass

    @abstractmethod
    async def refresh(self) -> bool:
        """
        Refresh authentication if needed.

        Returns:
            True if refresh successful or not needed
        """
        pass


class OAuth2Handler(AuthHandler):
    """OAuth 2.0 authentication handler with automatic token refresh"""

    def __init__(
        self,
        credentials: Dict[str, str],
        config: Optional[Dict[str, str]] = None
    ):
        super().__init__(credentials, config)
        self._token_info: Optional[TokenInfo] = None
        self._lock = asyncio.Lock()

    async def get_headers(self) -> Dict[str, str]:
        """Get headers with valid access token"""
        await self._ensure_valid_token()

        if not self._token_info:
            raise RuntimeError("Failed to obtain access token")

        return {
            "Authorization": f"{self._token_info.token_type} {self._token_info.access_token}",
            "Content-Type": "application/json",
        }

    async def refresh(self) -> bool:
        """Refresh token if expired"""
        if not self._token_info or not self._token_info.is_expired():
            return True

        return await self._refresh_token()

    async def _ensure_valid_token(self):
        """Ensure we have a valid access token"""
        async with self._lock:
            if self._token_info and not self._token_info.is_expired():
                return

            if self._token_info and self._token_info.refresh_token:
                success = await self._refresh_token()
                if success:
                    return

            # Get new token
            await self._get_new_token()

    async def _get_new_token(self):
        """Request new access token"""
        token_url = self.config.get("token_url")
        if not token_url:
            raise ValueError("token_url not provided in config")

        client_id = self.credentials.get("client_id")
        client_secret = self.credentials.get("client_secret")
        scope = self.config.get("scope", "")

        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": scope,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                data = response.json()
                self._token_info = TokenInfo(
                    access_token=data["access_token"],
                    token_type=data.get("token_type", "Bearer"),
                    expires_in=data.get("expires_in", 3600),
                    refresh_token=data.get("refresh_token"),
                    scope=data.get("scope"),
                )
                self.logger.info("Successfully obtained new access token")

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to get access token: {e}")
            raise

    async def _refresh_token(self) -> bool:
        """Refresh access token using refresh token"""
        if not self._token_info or not self._token_info.refresh_token:
            return False

        token_url = self.config.get("token_url")
        if not token_url:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._token_info.refresh_token,
                        "client_id": self.credentials.get("client_id"),
                        "client_secret": self.credentials.get("client_secret"),
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                data = response.json()
                self._token_info = TokenInfo(
                    access_token=data["access_token"],
                    token_type=data.get("token_type", "Bearer"),
                    expires_in=data.get("expires_in", 3600),
                    refresh_token=data.get("refresh_token", self._token_info.refresh_token),
                    scope=data.get("scope"),
                )
                self.logger.info("Successfully refreshed access token")
                return True

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to refresh token: {e}")
            return False


class APIKeyHandler(AuthHandler):
    """API Key authentication handler"""

    async def get_headers(self) -> Dict[str, str]:
        """Get headers with API key"""
        api_key = self.credentials.get("api_key")
        if not api_key:
            raise ValueError("api_key required")

        # Different ERPs use different header names
        key_header = self.config.get("key_header", "X-API-Key")

        return {
            key_header: api_key,
            "Content-Type": "application/json",
        }

    async def refresh(self) -> bool:
        """API keys don't need refresh"""
        return True


class BasicAuthHandler(AuthHandler):
    """HTTP Basic Authentication handler"""

    async def get_headers(self) -> Dict[str, str]:
        """Get headers with Basic auth"""
        username = self.credentials.get("username")
        password = self.credentials.get("password")

        if not username or not password:
            raise ValueError("username and password required")

        # httpx will handle base64 encoding
        import base64
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()

        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    async def refresh(self) -> bool:
        """Basic auth doesn't need refresh"""
        return True


class BearerTokenHandler(AuthHandler):
    """Bearer Token authentication handler"""

    async def get_headers(self) -> Dict[str, str]:
        """Get headers with bearer token"""
        token = self.credentials.get("token")
        if not token:
            raise ValueError("token required")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def refresh(self) -> bool:
        """Bearer tokens don't auto-refresh"""
        return True


def create_auth_handler(
    auth_type: str,
    credentials: Dict[str, str],
    config: Optional[Dict[str, str]] = None
) -> AuthHandler:
    """
    Factory function to create appropriate auth handler.

    Args:
        auth_type: Type of authentication (oauth2, api_key, basic_auth, bearer_token)
        credentials: Authentication credentials
        config: Optional configuration

    Returns:
        Configured AuthHandler instance
    """
    handlers = {
        "oauth2": OAuth2Handler,
        "api_key": APIKeyHandler,
        "basic_auth": BasicAuthHandler,
        "bearer_token": BearerTokenHandler,
    }

    handler_class = handlers.get(auth_type.lower())
    if not handler_class:
        raise ValueError(f"Unsupported auth type: {auth_type}")

    return handler_class(credentials, config)
