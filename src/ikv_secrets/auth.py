"""
Authentication flows for IronKeyVault.

Implements ADR-063: SDK login follows normal user-app login flow via browser.
"""

from __future__ import annotations

import http.server
import platform
import socket
import threading
import time
import urllib.parse
import webbrowser
from typing import Optional

import httpx

from ikv_secrets.keyring_store import save_token, delete_token, TokenInfo
from ikv_secrets.config import get_config, save_tenant_config


# Default vault URL for local development
DEFAULT_VAULT_URL = "https://localhost:5001"


class AuthError(Exception):
    """Authentication error."""
    pass


def get_device_fingerprint() -> dict:
    """Collect device fingerprint for session binding."""
    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "sdk": "ikv-secrets",
    }


def login(
    tenant: str,
    vault_url: Optional[str] = None,
    api_key: Optional[str] = None,
    master_key: Optional[str] = None,
    force_login: bool = False,
) -> TokenInfo:
    """
    Authenticate to IronKeyVault.
    
    For interactive use (opens browser for normal login flow):
        login(tenant="acme")
    
    For CI/CD (service account):
        login(tenant="acme", api_key="...", master_key="...")
    
    Args:
        tenant: Tenant name
        vault_url: Vault URL (optional, defaults to https://localhost:5001)
        api_key: Service account API key (for CI/CD)
        master_key: Master password (for CI/CD)
        force_login: If True, always require fresh login even if browser has session
        
    Returns:
        TokenInfo with access token
    """
    # Resolve vault URL
    if not vault_url:
        config = get_config()
        tenant_config = config.get("tenants", {}).get(tenant, {})
        vault_url = tenant_config.get("url")
    
    if not vault_url:
        vault_url = DEFAULT_VAULT_URL
        print(f"ℹ️  Using default vault URL: {vault_url}")
    
    vault_url = vault_url.rstrip("/")
    
    # Service account flow (non-interactive CI/CD)
    if api_key and master_key:
        return _service_account_login(tenant, vault_url, api_key, master_key)
    
    # Browser login flow (normal user login)
    return _browser_login(tenant, vault_url, force_login=force_login)


def _browser_login(tenant: str, vault_url: str, force_login: bool = False) -> TokenInfo:
    """
    Authenticate using browser login flow.
    
    Opens browser to IronKeyVault login page. User logs in normally
    (with MFA, master password etc). SDK receives auth code via callback,
    then exchanges it for access token.
    
    Args:
        tenant: Tenant name
        vault_url: Vault URL
        force_login: If True, always require fresh login even if browser has session
    """
    # Start local callback server
    callback_received = threading.Event()
    auth_result: dict = {}
    
    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            if "code" in params:
                # Got authorization code - exchange for token
                auth_result["code"] = params["code"][0]
                auth_result["state"] = params.get("state", [""])[0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Login Successful</title>
                        <style>
                            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                   background: #0a0f1a; color: #fff; display: flex; justify-content: center;
                                   align-items: center; height: 100vh; margin: 0; }
                            .container { text-align: center; }
                            h1 { color: #10b981; margin-bottom: 1rem; }
                            p { color: #888; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>&#x2705; Login Successful!</h1>
                            <p>You can close this window and return to your terminal.</p>
                        </div>
                        <script>setTimeout(() => window.close(), 2000);</script>
                    </body>
                    </html>
                """)
            elif "error" in params:
                # Login failed
                auth_result["error"] = params.get("error_description", params["error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error_msg = auth_result.get('error', 'Unknown error')
                self.wfile.write(f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Login Failed</title>
                        <style>
                            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                   background: #0a0f1a; color: #fff; display: flex; justify-content: center;
                                   align-items: center; height: 100vh; margin: 0; }}
                            .container {{ text-align: center; }}
                            h1 {{ color: #ef4444; margin-bottom: 1rem; }}
                            p {{ color: #888; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>&#x274C; Login Failed</h1>
                            <p>{error_msg}</p>
                        </div>
                    </body>
                    </html>
                """.encode())
            else:
                self.send_response(400)
                self.end_headers()
            
            callback_received.set()
        
        def log_message(self, format: str, *args) -> None:
            pass  # Suppress logging
    
    # Find available port
    server = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
    port = server.server_address[1]
    callback_url = f"http://127.0.0.1:{port}/callback"
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()
    
    # Generate state for CSRF protection
    import secrets as sec
    state = sec.token_urlsafe(16)
    
    # Build auth URL - use OAuth start endpoint
    device_info = get_device_fingerprint()
    auth_params = urllib.parse.urlencode({
        "redirect_uri": callback_url,
        "state": state,
        "device_fingerprint": urllib.parse.quote(str(device_info)),
        "force_login": "1" if force_login else "0",
    })
    auth_url = f"{vault_url}/auth/oauth/start?{auth_params}"
    
    print(f"\n🔐 IronKeyVault Login")
    print(f"   Opening browser for authentication...")
    print(f"   Vault: {vault_url}")
    print()
    print(f"   If browser doesn't open, visit:")
    print(f"   {auth_url}")
    print()
    
    # Open browser
    webbrowser.open(auth_url)
    
    # Wait for callback (5 minute timeout)
    print("   ⏳ Waiting for login...")
    callback_received.wait(timeout=300)
    server.server_close()
    
    if "error" in auth_result:
        raise AuthError(f"Authentication failed: {auth_result['error']}")
    
    if "code" not in auth_result:
        raise AuthError("Authentication timed out - please try again")
    
    # Exchange authorization code for token
    print("   🔄 Exchanging code for token...")
    try:
        # Use a client with SSL verification disabled for localhost/dev
        with httpx.Client(verify=False, timeout=30.0) as client:
            response = client.post(
                f"{vault_url}/auth/oauth/token",
                json={
                    "code": auth_result["code"],
                    "redirect_uri": callback_url,
                },
            )
        
        if not response.is_success:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            raise AuthError(error_data.get("error_description", f"Token exchange failed: {response.status_code}"))
        
        token_data = response.json()
        
    except httpx.ConnectError:
        raise AuthError(f"Cannot connect to {vault_url}")
    
    # Create token info
    token = TokenInfo(
        access_token=token_data["access_token"],
        expires_at=token_data.get("expires_at", int(time.time()) + token_data.get("expires_in", 14400)),
        tenant=tenant,
    )
    
    save_token(tenant, token)
    save_tenant_config(tenant, vault_url)
    
    print(f"   ✅ Login successful!")
    
    return token


def _service_account_login(
    tenant: str,
    vault_url: str,
    api_key: str,
    master_key: str,
) -> TokenInfo:
    """Authenticate using service account credentials (CI/CD)."""
    try:
        with httpx.Client(verify=False, timeout=30.0) as client:
            response = client.post(
                f"{vault_url}/api/v1/auth/service-account",
                json={
                    "tenant": tenant,
                    "api_key": api_key,
                    "master_key": master_key,
                },
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
        
    except httpx.ConnectError:
        raise AuthError(f"Cannot connect to {vault_url}")


def logout(tenant: Optional[str] = None) -> None:
    """
    Clear stored credentials.
    
    Args:
        tenant: Specific tenant to logout from (None = all)
    """
    if tenant:
        delete_token(tenant)
    else:
        # Clear all tenants
        config = get_config()
        for t in config.get("tenants", {}).keys():
            try:
                delete_token(t)
            except Exception:
                pass
