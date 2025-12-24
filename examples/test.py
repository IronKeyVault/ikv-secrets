#!/usr/bin/env python3
"""
Test script for ikv-secrets SDK.

Usage:
    python test.py <record_name>
    python test.py "kunde 1 env"
    
Before running:
    1. ikv-secrets login --tenant <your-tenant> --url https://vault.example.com
    2. Set IKV_TENANT environment variable
"""

import sys
import os

# Add src to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ikv_secrets.client import IKVClient, IKVClientError, TierError, AuthenticationError
from ikv_secrets.config import get_tenant_url, get_config
from ikv_secrets.keyring_store import get_token


def main():
    if len(sys.argv) < 2:
        print("Usage: python test.py <record_name>")
        print("Example: python test.py 'kunde 1 env'")
        sys.exit(1)
    
    record_name = sys.argv[1]
    tenant = os.environ.get("IKV_TENANT")
    
    print("=" * 60)
    print("IKV-Secrets Test")
    print("=" * 60)
    
    # Check config
    print("\n📋 Configuration:")
    config = get_config()
    print(f"   Config file: ~/.config/ikv-secrets/config.json")
    print(f"   Tenants configured: {list(config.get('tenants', {}).keys())}")
    
    if not tenant:
        print("\n❌ IKV_TENANT not set!")
        print("   Run: export IKV_TENANT=<your-tenant>")
        sys.exit(1)
    
    print(f"   Active tenant: {tenant}")
    
    # Check vault URL
    url = get_tenant_url(tenant)
    if not url:
        print(f"\n❌ No URL configured for tenant '{tenant}'")
        print(f"   Run: ikv-secrets login --tenant {tenant} --url https://vault.example.com")
        sys.exit(1)
    
    print(f"   Vault URL: {url}")
    
    # Check token
    print("\n🔐 Authentication:")
    token = get_token(tenant)
    if not token:
        print(f"   ❌ Not logged in to '{tenant}'")
        print(f"   Run: ikv-secrets login --tenant {tenant} --url {url}")
        sys.exit(1)
    
    if token.is_expired:
        print(f"   ❌ Token expired")
        print(f"   Run: ikv-secrets login --tenant {tenant} --url {url}")
        sys.exit(1)
    
    print(f"   ✅ Token valid (expires in {token.expires_in // 60} minutes)")
    
    # Create client
    print(f"\n🔗 Connecting to vault...")
    client = IKVClient(vault_url=url, tenant=tenant)
    
    # List records
    print("\n📂 Available env records:")
    try:
        records = client.list_env_records()
        if not records:
            print("   (none)")
        for r in records:
            marker = "→" if r.get('name') == record_name else " "
            print(f"   {marker} [{r['id']}] {r['name']}")
    except Exception as e:
        print(f"   ❌ Failed to list: {e}")
    
    # Fetch specific record
    print(f"\n🔑 Fetching record: '{record_name}'")
    try:
        env_vars = client.get_env(record_name)
        
        print(f"   ✅ Found {len(env_vars)} variables:")
        print()
        for key, value in env_vars.items():
            # Mask sensitive values
            if any(s in key.lower() for s in ['password', 'secret', 'key', 'token']):
                display_value = value[:4] + "****" if len(value) > 4 else "****"
            else:
                display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"   {key}={display_value}")
        
        print("\n" + "=" * 60)
        print("✅ Test passed!")
        print("=" * 60)
        
    except AuthenticationError as e:
        print(f"   ❌ Authentication failed: {e}")
        sys.exit(1)
    except TierError as e:
        print(f"   ❌ Tier error: {e}")
        print(f"      Required: {e.required_tier}, Current: {e.current_tier}")
        sys.exit(1)
    except IKVClientError as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
