"""
Environment variable proxy for lazy-loading secrets from IronKeyVault.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ikv_secrets.client import IKVClient


class EnvProxy:
    """
    Lazy-loading proxy for environment variables stored in IronKeyVault.
    
    Usage:
        from ikv_secrets import env
        
        # Access as attributes
        db_url = env.DATABASE_URL
        
        # Access with default
        debug = env.get("DEBUG", "false")
        
        # Check existence
        if env.has("OPTIONAL_VAR"):
            use_it(env.OPTIONAL_VAR)
    """
    
    def __init__(self) -> None:
        self._client: Optional[IKVClient] = None
        self._cache: dict[str, str] = {}
        self._loaded: bool = False
        self._record_id: Optional[str] = None
    
    def _ensure_client(self) -> IKVClient:
        """Get or create the IKV client."""
        if self._client is None:
            self._client = IKVClient.from_env()
        return self._client
    
    def _ensure_loaded(self) -> None:
        """Load secrets if not already loaded."""
        if self._loaded:
            return
        
        # Check for record ID in environment
        record_id = os.environ.get("IKV_RECORD")
        if record_id:
            self.load(record_id)
    
    def load(self, record_id: str, inject: bool = False) -> None:
        """
        Load environment variables from a specific record.
        
        Args:
            record_id: The ID or name of the env record in IronKeyVault
            inject: If True, also inject into os.environ
        """
        client = self._ensure_client()
        self._cache = client.get_env(record_id)
        self._record_id = record_id
        self._loaded = True
        
        if inject:
            os.environ.update(self._cache)
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable with optional default."""
        self._ensure_loaded()
        return self._cache.get(key, default)
    
    def has(self, key: str) -> bool:
        """Check if an environment variable exists."""
        self._ensure_loaded()
        return key in self._cache
    
    def keys(self) -> list[str]:
        """Get all available environment variable names."""
        self._ensure_loaded()
        return list(self._cache.keys())
    
    def to_dict(self) -> dict[str, str]:
        """Export all variables as a dictionary."""
        self._ensure_loaded()
        return dict(self._cache)
    
    def to_dotenv(self) -> str:
        """Export as .env file format."""
        self._ensure_loaded()
        lines = [f'{k}="{v}"' for k, v in self._cache.items()]
        return "\n".join(lines)
    
    def to_shell(self) -> str:
        """Export as shell export commands."""
        self._ensure_loaded()
        lines = [f'export {k}="{v}"' for k, v in self._cache.items()]
        return "\n".join(lines)
    
    def clear(self) -> None:
        """Clear cached secrets from memory."""
        self._cache.clear()
        self._loaded = False
        self._record_id = None
    
    def __getattr__(self, name: str) -> str:
        """Allow attribute-style access: env.DATABASE_URL"""
        if name.startswith("_"):
            raise AttributeError(name)
        
        self._ensure_loaded()
        
        if name not in self._cache:
            raise AttributeError(
                f"Environment variable '{name}' not found. "
                f"Available: {', '.join(self._cache.keys()) or '(none loaded)'}"
            )
        
        return self._cache[name]
    
    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "not loaded"
        record = f", record={self._record_id}" if self._record_id else ""
        count = len(self._cache)
        return f"<EnvProxy({status}, {count} vars{record})>"


# Global instance for simple import
env = EnvProxy()
