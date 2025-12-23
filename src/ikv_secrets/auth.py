"""
Authentication flows for IronKeyVault.
"""

from __future__ import annotations

import http.server
import threading
import urllib.parse
import webbrowser
from typing import Optional

import httpx

from ikv_secrets.keyring_store import save_token, delete_token, TokenInfo
from ikv_secrets.config import get_config, save_tenant_config


class AuthError(Exception):
    """Authentication error."""
    pass


def login(
    tenant: str,
    vault_url: Optional[str] = None,
    api_key: Optional[str] = None,
    master_key: Optional[str] = None,
) -> TokenInfo:
    """
    Authenticate to IronKeyVault.
    
    For interactive use (opens browser):
        login(tenant="acme")
    
    For CI/CD (service account):
        login(tenant="acme", api_key="...", master_key="...")
    
    Args:
        tenant: Tenant name
        vault_url: Vault URL (optional, uses config if not provided)
        api_key: Service account API key (for CI/CD)
        master_key: Master password (for CI/CD)
        
    Returns:
        TokenInfo with access token
    """
    # Resolve vault URL
    if not vault_url:
        config = get_config()
        tenant_config = config.get("tenants", {}).get(tenant, {})
        vault_url = tenant_config.get("url")
    
    if not vault_url:
        raise AuthError(
            f"No vault URL for tenant '{tenant}'. "
            f"Use --url or configure in ~/.ikv/config.yaml"
        )
    
    vault_url = vault_url.rstrip("/")
    
    # Service account flow (non-interactive)
    if api_key and master_key:
        return _service_account_login(tenant, vault_url, api_key, master_key)
    
    # Browser OAuth flow (interactive)
    return _browser_login(tenant, vault_url)


def _service_account_login(
    tenant: str,
    vault_url: str,
    api_key: str,
    master_key: str,
) -> TokenInfo:
    """Authenticate using service account credentials."""
    response = httpx.post(
        f"{vault_url}/api/v1/auth/service-account",
        json={
            "tenant": tenant,
            "api_key": api_key,
            "master_key": master_key,
        },
        timeout=30.0,
    )
    
    if response.status_code == 401:
        raise AuthError("Invalid service account credentials")
    if response.status_code == 403:
        raise AuthError("Service accounts require Enterprise tier")
    
    response.raise_for_status()
    
    data = response.json()
    token = TokenInfo(
        access_token=data["access_token"],
        expires_at=data["expires_at"],
        tenant=tenant,
    )
    
    save_token(tenant, token)
    save_tenant_config(tenant, vault_url)
    
    return token


def _browser_login(tenant: str, vault_url: str) -> TokenInfo:
    """Authenticate using browser OAuth flow."""
    
    # Start local callback server
    callback_received = threading.Event()
    auth_result: dict = {}
    
    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            if "code" in params:
                auth_result["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html><body>
                    <h1>Login successful!</h1>
                    <p>You can close this window.</p>
                    <script>window.close();</script>
                    </body></html>
                """)
            elif "error" in params:
                auth_result["error"] = params.get("error_description", params["error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                    <html><body>
                    <h1>Login failed</h1>
                    <p>{auth_result['error']}</p>
                    </body></html>
                """.encode())
            
            callback_received.set()
        
        def log_message(self, format: str, *args) -> None:
            pass  # Suppress logging
    
    # Find available port
    server = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
    port = server.server_address[1]
    callback_url = f"http://127.0.0.1:{port}/callback"
    
    # Start server in background
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()
    
    # Open browser for auth
    auth_url = f"{vault_url}/auth/oauth/start?tenant={tenant}&redirect_uri={callback_url}"
    print(f"Opening browser for authentication...")
    print(f"If browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)
    
    # Wait for callback
    callback_received.wait(timeout=300)  # 5 minute timeout
    server.server_close()
    
    if "error" in auth_result:
        raise AuthError(f"Authentication failed: {auth_result['error']}")
    
    if "code" not in auth_result:
        raise AuthError("Authentication timed out")
    
    # Exchange code for token
    response = httpx.post(
        f"{vault_url}/auth/oauth/token",
        json={
            "code": auth_result["code"],
            "redirect_uri": callback_url,
        },
        timeout=30.0,
    )
    
    response.raise_for_status()
    
    data = response.json()
    token = TokenInfo(
        access_token=data["access_token"],
        expires_at=data["expires_at"],
        tenant=tenant,
    )
    
    save_token(tenant, token)
    save_tenant_config(tenant, vault_url)
    
    return token


def logout(tenant: Optional[str] = None) -> None:
    """
    Clear stored credentials.
    
    Args:
        tenant: Specific tenant to logout from (None = all)
    """
    if tenant:
        delete_token(tenant)
    else:
        # TODO: Clear all tokens
        pass
