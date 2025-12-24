#!/usr/bin/env python3
"""
Fetch environment variables from IronKeyVault.

Installation:
    pip install ikv-secrets

Usage:
    python get_env.py "kunde1 env"
    python get_env.py "Production API"
    
    # Or with explicit tenant
    python get_env.py "kunde1 env" --tenant acme
    
    # Export to shell
    eval $(python get_env.py "kunde1 env" --shell)

Before first use:
    1. Login: ikv-secrets login --tenant <your-tenant> --url https://vault.example.com
    2. Set tenant: export IKV_TENANT=<your-tenant>
"""

import argparse
import sys
import os

# Add src to path for local development (remove when using pip install)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ikv_secrets import env
from ikv_secrets.client import IKVClient, IKVClientError, TierError, AuthenticationError
from ikv_secrets.config import get_tenant_url, get_config
from ikv_secrets.keyring_store import get_token


def main():
    parser = argparse.ArgumentParser(
        description="Fetch environment variables from IronKeyVault",
        epilog="Example: python get_env.py 'kunde1 env'"
    )
    parser.add_argument(
        "record",
        help="Name or ID of the env record in IronKeyVault"
    )
    parser.add_argument(
        "-t", "--tenant",
        default=os.environ.get("IKV_TENANT"),
        help="Tenant name (default: IKV_TENANT env var)"
    )
    parser.add_argument(
        "-u", "--url",
        default=os.environ.get("IKV_VAULT_URL"),
        help="Vault URL (default: from config or IKV_VAULT_URL)"
    )
    parser.add_argument(
        "--shell",
        action="store_true",
        help="Output as shell export commands"
    )
    parser.add_argument(
        "--dotenv",
        action="store_true", 
        help="Output as .env file format"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only output errors"
    )
    
    args = parser.parse_args()
    
    # Validate tenant
    if not args.tenant:
        print("Error: --tenant required or set IKV_TENANT environment variable", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  export IKV_TENANT=acme", file=sys.stderr)
        print("  python get_env.py 'kunde1 env'", file=sys.stderr)
        sys.exit(1)
    
    # Get vault URL
    url = args.url or get_tenant_url(args.tenant)
    if not url:
        print(f"Error: No URL configured for tenant '{args.tenant}'", file=sys.stderr)
        print(f"\nRun: ikv-secrets login --tenant {args.tenant} --url https://your-vault.com", file=sys.stderr)
        sys.exit(1)
    
    # Check token
    token = get_token(args.tenant)
    if not token:
        print(f"Error: Not logged in to '{args.tenant}'", file=sys.stderr)
        print(f"\nRun: ikv-secrets login --tenant {args.tenant} --url {url}", file=sys.stderr)
        sys.exit(1)
    
    if token.is_expired:
        print(f"Error: Token expired for '{args.tenant}'", file=sys.stderr)
        print(f"\nRun: ikv-secrets login --tenant {args.tenant} --url {url}", file=sys.stderr)
        sys.exit(1)
    
    # Fetch secrets
    try:
        client = IKVClient(vault_url=url, tenant=args.tenant)
        env_vars = client.get_env(args.record)
        client.close()
        
        # Output format
        if args.shell:
            for key, value in env_vars.items():
                escaped = value.replace("'", "'\"'\"'")
                print(f"export {key}='{escaped}'")
        
        elif args.dotenv:
            for key, value in env_vars.items():
                escaped = value.replace('"', '\\"')
                print(f'{key}="{escaped}"')
        
        elif args.json:
            import json
            print(json.dumps(env_vars, indent=2))
        
        else:
            # Human readable
            if not args.quiet:
                print(f"✅ Loaded {len(env_vars)} variables from '{args.record}':")
                print()
            
            for key, value in env_vars.items():
                # Mask sensitive values
                if any(s in key.lower() for s in ['password', 'secret', 'key', 'token', 'api']):
                    display = value[:4] + "****" if len(value) > 4 else "****"
                else:
                    display = value[:60] + "..." if len(value) > 60 else value
                print(f"  {key}={display}")
    
    except AuthenticationError as e:
        print(f"Error: Authentication failed - {e}", file=sys.stderr)
        sys.exit(1)
    except TierError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"  Required tier: {e.required_tier}", file=sys.stderr)
        print(f"  Your tier: {e.current_tier}", file=sys.stderr)
        sys.exit(1)
    except IKVClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
