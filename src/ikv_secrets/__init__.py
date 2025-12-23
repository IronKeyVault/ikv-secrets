"""
ikv-secrets: Secure environment variable access for IronKeyVault.

Usage:
    from ikv_secrets import env
    
    DATABASE_URL = env.DATABASE_URL
    API_KEY = env.API_KEY
"""

from ikv_secrets.env import env, EnvProxy
from ikv_secrets.client import IKVClient
from ikv_secrets.auth import login, logout

__version__ = "0.1.0"
__all__ = ["env", "EnvProxy", "IKVClient", "login", "logout"]
