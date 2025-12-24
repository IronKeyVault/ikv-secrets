"""
Secure token storage using OS keyring with file fallback.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import keyring
    from keyring.errors import NoKeyringError
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    NoKeyringError = Exception


KEYRING_SERVICE = "ikv-secrets"
CONFIG_DIR = Path.home() / ".config" / "ikv-secrets"
TOKENS_FILE = CONFIG_DIR / "tokens.json"


def _use_file_fallback() -> bool:
    """Check if we need to use file fallback instead of keyring."""
    if not KEYRING_AVAILABLE:
        return True
    try:
        # Test if keyring works
        keyring.get_keyring()
        # Try a test operation
        keyring.get_password(KEYRING_SERVICE, "__test__")
        return False
    except (NoKeyringError, RuntimeError, Exception):
        return True


def _load_tokens_file() -> dict:
    """Load tokens from file."""
    if TOKENS_FILE.exists():
        try:
            return json.loads(TOKENS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_tokens_file(tokens: dict) -> None:
    """Save tokens to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))
    # Secure permissions
    os.chmod(TOKENS_FILE, 0o600)


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
    Retrieve token from OS keyring or file fallback.
    
    Args:
        tenant: Tenant name
        
    Returns:
        TokenInfo if found, None otherwise
    """
    try:
        if _use_file_fallback():
            tokens = _load_tokens_file()
            data = tokens.get(tenant)
        else:
            data = keyring.get_password(KEYRING_SERVICE, tenant)
        
        if data:
            return TokenInfo.from_json(data) if isinstance(data, str) else TokenInfo.from_json(json.dumps(data))
    except Exception:
        pass
    return None


def save_token(tenant: str, token: TokenInfo) -> None:
    """
    Save token to OS keyring or file fallback.
    
    Args:
        tenant: Tenant name
        token: Token information
    """
    if _use_file_fallback():
        tokens = _load_tokens_file()
        tokens[tenant] = json.loads(token.to_json())
        _save_tokens_file(tokens)
    else:
        keyring.set_password(KEYRING_SERVICE, tenant, token.to_json())


def delete_token(tenant: str) -> None:
    """
    Delete token from OS keyring or file fallback.
    
    Args:
        tenant: Tenant name
    """
    try:
        if _use_file_fallback():
            tokens = _load_tokens_file()
            tokens.pop(tenant, None)
            _save_tokens_file(tokens)
        else:
            keyring.delete_password(KEYRING_SERVICE, tenant)
    except Exception:
        pass  # Already deleted or doesn't exist
