"""
IronKeyVault API client for fetching secrets.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Optional

import httpx

from ikv_secrets.keyring_store import get_token, TokenInfo


class IKVClientError(Exception):
    """Base exception for IKV client errors."""
    pass


class AuthenticationError(IKVClientError):
    """Authentication failed or token expired."""
    pass


class TierError(IKVClientError):
    """Feature requires higher tier."""
    
    def __init__(self, message: str, required_tier: str, current_tier: str):
        super().__init__(message)
        self.required_tier = required_tier
        self.current_tier = current_tier


class IKVClient:
    """
    Client for IronKeyVault API.
    
    Usage:
        # From environment variables
        client = IKVClient.from_env()
        
        # Explicit configuration
        client = IKVClient(
            vault_url="https://vault.example.com",
            tenant="acme"
        )
    """
    
    def __init__(
        self,
        vault_url: str,
        tenant: str,
        api_key: Optional[str] = None,
        master_key: Optional[str] = None,
    ) -> None:
        self.vault_url = vault_url.rstrip("/")
        self.tenant = tenant
        self._api_key = api_key
        self._master_key = master_key
        self._token: Optional[TokenInfo] = None
        self._http = httpx.Client(timeout=30.0)
    
    @classmethod
    def from_env(cls) -> "IKVClient":
        """Create client from environment variables."""
        vault_url = os.environ.get("IKV_VAULT_URL")
        tenant = os.environ.get("IKV_TENANT")
        
        if not vault_url:
            raise IKVClientError(
                "IKV_VAULT_URL not set. Run 'ikv-secrets login --tenant <name>' first."
            )
        if not tenant:
            raise IKVClientError(
                "IKV_TENANT not set. Run 'ikv-secrets login --tenant <name>' first."
            )
        
        return cls(
            vault_url=vault_url,
            tenant=tenant,
            api_key=os.environ.get("IKV_API_KEY"),
            master_key=os.environ.get("IKV_MASTER_KEY"),
        )
    
    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        # Service account mode (CI/CD)
        if self._api_key and self._master_key:
            timestamp = str(int(time.time()))
            nonce = os.urandom(16).hex()
            
            # Create signature
            message = f"{timestamp}:{nonce}:{self.tenant}"
            signature = hmac.new(
                self._api_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return {
                "X-API-Key": self._api_key,
                "X-Master-Key": self._master_key,
                "X-Timestamp": timestamp,
                "X-Nonce": nonce,
                "X-Signature": signature,
            }
        
        # Interactive mode (token from keyring)
        token = get_token(self.tenant)
        if not token:
            raise AuthenticationError(
                f"Not logged in to tenant '{self.tenant}'. "
                f"Run 'ikv-secrets login --tenant {self.tenant}' first."
            )
        
        if token.is_expired:
            raise AuthenticationError(
                f"Token expired for tenant '{self.tenant}'. "
                f"Run 'ikv-secrets login --tenant {self.tenant}' to re-authenticate."
            )
        
        return {
            "Authorization": f"Bearer {token.access_token}",
        }
    
    def get_env(self, record_id: str) -> dict[str, str]:
        """
        Fetch environment variables from a record.
        
        Args:
            record_id: Record ID or name
            
        Returns:
            Dictionary of environment variable name -> value
        """
        headers = self._get_auth_headers()
        
        response = self._http.get(
            f"{self.vault_url}/api/v1/env/{record_id}",
            headers=headers,
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed. Please login again.")
        
        if response.status_code == 403:
            data = response.json()
            raise TierError(
                data.get("error", "Feature requires higher tier"),
                required_tier=data.get("required_tier", "premium"),
                current_tier=data.get("current_tier", "unknown"),
            )
        
        if response.status_code == 404:
            raise IKVClientError(f"Env record '{record_id}' not found")
        
        response.raise_for_status()
        
        data = response.json()
        return data.get("variables", {})
    
    def list_env_records(self) -> list[dict[str, Any]]:
        """
        List available env records.
        
        Returns:
            List of record metadata (id, name, updated_at)
        """
        headers = self._get_auth_headers()
        
        response = self._http.get(
            f"{self.vault_url}/api/v1/env",
            headers=headers,
        )
        
        response.raise_for_status()
        return response.json().get("records", [])
    
    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()
    
    def __enter__(self) -> "IKVClient":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()
