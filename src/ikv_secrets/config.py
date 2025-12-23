"""
Configuration management for ikv-secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml


def get_config_dir() -> Path:
    """Get the configuration directory (~/.ikv)."""
    config_dir = Path.home() / ".ikv"
    config_dir.mkdir(mode=0o700, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the config file path."""
    return get_config_dir() / "config.yaml"


def get_config() -> dict[str, Any]:
    """
    Load configuration from ~/.ikv/config.yaml.
    
    Returns:
        Configuration dictionary
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return {"tenants": {}}
    
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    return config


def save_config(config: dict[str, Any]) -> None:
    """
    Save configuration to ~/.ikv/config.yaml.
    
    Args:
        config: Configuration dictionary
    """
    config_path = get_config_path()
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    # Secure permissions
    os.chmod(config_path, 0o600)


def save_tenant_config(tenant: str, vault_url: str, default_record: Optional[str] = None) -> None:
    """
    Save tenant-specific configuration.
    
    Args:
        tenant: Tenant name
        vault_url: Vault URL
        default_record: Default env record (optional)
    """
    config = get_config()
    
    if "tenants" not in config:
        config["tenants"] = {}
    
    config["tenants"][tenant] = {
        "url": vault_url,
    }
    
    if default_record:
        config["tenants"][tenant]["default_record"] = default_record
    
    save_config(config)


def get_tenant_url(tenant: str) -> Optional[str]:
    """
    Get vault URL for a tenant.
    
    Args:
        tenant: Tenant name
        
    Returns:
        Vault URL or None
    """
    config = get_config()
    return config.get("tenants", {}).get(tenant, {}).get("url")
