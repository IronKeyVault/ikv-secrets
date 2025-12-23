"""
Secure token storage using OS keyring.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional

import keyring


KEYRING_SERVICE = "ikv-secrets"


@dataclass
class TokenInfo:
    """Token information stored in keyring."""
    access_token: str
    expires_at: int  # Unix timestamp
    tenant: str
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 5 min buffer)."""
        return time.time() > (self.expires_at - 300)
    
    @property
    def expires_in(self) -> int:
        """Seconds until expiration."""
        return max(0, self.expires_at - int(time.time()))
    
    def to_json(self) -> str:
        """Serialize to JSON for storage."""
        return json.dumps({
            "access_token": self.access_token,
            "expires_at": self.expires_at,
            "tenant": self.tenant,
        })
    
    @classmethod
    def from_json(cls, data: str) -> "TokenInfo":
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(
            access_token=obj["access_token"],
            expires_at=obj["expires_at"],
            tenant=obj["tenant"],
        )


def get_token(tenant: str) -> Optional[TokenInfo]:
    """
    Retrieve token from OS keyring.
    
    Args:
        tenant: Tenant name
        
    Returns:
        TokenInfo if found, None otherwise
    """
    try:
        data = keyring.get_password(KEYRING_SERVICE, tenant)
        if data:
            return TokenInfo.from_json(data)
    except Exception:
        pass
    return None


def save_token(tenant: str, token: TokenInfo) -> None:
    """
    Save token to OS keyring.
    
    Args:
        tenant: Tenant name
        token: Token information
    """
    keyring.set_password(KEYRING_SERVICE, tenant, token.to_json())


def delete_token(tenant: str) -> None:
    """
    Delete token from OS keyring.
    
    Args:
        tenant: Tenant name
    """
    try:
        keyring.delete_password(KEYRING_SERVICE, tenant)
    except keyring.errors.PasswordDeleteError:
        pass  # Already deleted
