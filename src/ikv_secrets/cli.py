"""
CLI for ikv-secrets.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import click

from ikv_secrets import __version__
from ikv_secrets.auth import login as do_login, logout as do_logout, AuthError
from ikv_secrets.client import IKVClient, IKVClientError, TierError
from ikv_secrets.keyring_store import get_token
from ikv_secrets.config import get_config


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """ikv-secrets: Secure environment variables from IronKeyVault."""
    pass


@main.command()
@click.option("--tenant", "-t", required=True, help="Tenant name")
@click.option("--url", "-u", help="Vault URL")
@click.option("--api-key", envvar="IKV_API_KEY", help="Service account API key")
@click.option("--master-key", envvar="IKV_MASTER_KEY", help="Master password")
@click.option("--force", "-f", is_flag=True, help="Force re-login even if already logged in")
def login(
    tenant: str,
    url: Optional[str],
    api_key: Optional[str],
    master_key: Optional[str],
    force: bool,
) -> None:
    """Login to IronKeyVault."""
    # Check if already logged in
    existing_token = get_token(tenant)
    if existing_token and not existing_token.is_expired and not force:
        minutes_left = existing_token.expires_in // 60
        click.echo(f"✓ Already logged in to '{tenant}' (expires in {minutes_left} minutes)")
        click.echo(f"  Use --force to re-login")
        return
    
    try:
        token = do_login(
            tenant=tenant,
            vault_url=url,
            api_key=api_key,
            master_key=master_key,
        )
        click.echo(f"✓ Logged in to '{tenant}' (expires in {token.expires_in // 60} minutes)")
    except AuthError as e:
        click.echo(f"✗ Login failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--tenant", "-t", help="Tenant to logout from (all if not specified)")
def logout(tenant: Optional[str]) -> None:
    """Clear stored credentials."""
    do_logout(tenant)
    if tenant:
        click.echo(f"✓ Logged out from '{tenant}'")
    else:
        click.echo("✓ Logged out from all tenants")


@main.command()
def status() -> None:
    """Show authentication status."""
    config = get_config()
    tenants = config.get("tenants", {})
    
    if not tenants:
        click.echo("No tenants configured. Run 'ikv-secrets login --tenant <name>' first.")
        return
    
    for tenant_name, tenant_config in tenants.items():
        token = get_token(tenant_name)
        url = tenant_config.get("url", "unknown")
        
        if token and not token.is_expired:
            minutes = token.expires_in // 60
            click.echo(f"✓ {tenant_name}: logged in (expires in {minutes}m) - {url}")
        elif token:
            click.echo(f"✗ {tenant_name}: token expired - {url}")
        else:
            click.echo(f"○ {tenant_name}: not logged in - {url}")


@main.command("list")
@click.option("--tenant", "-t", envvar="IKV_TENANT", help="Tenant name")
def list_records(tenant: Optional[str]) -> None:
    """List available env records."""
    if not tenant:
        click.echo("Error: --tenant required or set IKV_TENANT", err=True)
        sys.exit(1)
    
    try:
        client = IKVClient.from_env() if os.environ.get("IKV_VAULT_URL") else None
        if not client:
            from ikv_secrets.config import get_tenant_url
            url = get_tenant_url(tenant)
            if not url:
                click.echo(f"Error: No URL for tenant '{tenant}'", err=True)
                sys.exit(1)
            client = IKVClient(vault_url=url, tenant=tenant)
        
        records = client.list_env_records()
        
        if not records:
            click.echo("No env records found.")
            return
        
        for record in records:
            click.echo(f"  {record['id']:>6}  {record['name']}")
    
    except TierError as e:
        click.echo(f"✗ {e} (requires {e.required_tier}, you have {e.current_tier})", err=True)
        sys.exit(1)
    except IKVClientError as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("record")
@click.option("--tenant", "-t", envvar="IKV_TENANT", help="Tenant name")
@click.option("--id", "by_id", is_flag=True, help="Record is an ID, not name")
def load(record: str, tenant: Optional[str], by_id: bool) -> None:
    """
    Load env variables (outputs shell export commands).
    
    Usage:
        eval $(ikv-secrets load prod-api)
    """
    if not tenant:
        click.echo("# Error: --tenant required or set IKV_TENANT", err=True)
        sys.exit(1)
    
    try:
        from ikv_secrets.config import get_tenant_url
        url = get_tenant_url(tenant)
        if not url:
            click.echo(f"# Error: No URL for tenant '{tenant}'", err=True)
            sys.exit(1)
        
        client = IKVClient(vault_url=url, tenant=tenant)
        env_vars = client.get_env(record)
        
        for key, value in env_vars.items():
            # Escape for shell
            escaped = value.replace("'", "'\"'\"'")
            click.echo(f"export {key}='{escaped}'")
    
    except TierError as e:
        click.echo(f"# Error: {e}", err=True)
        sys.exit(1)
    except IKVClientError as e:
        click.echo(f"# Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("record")
@click.option("--tenant", "-t", envvar="IKV_TENANT", help="Tenant name")
@click.option("--format", "-f", "fmt", default="dotenv", 
              type=click.Choice(["dotenv", "shell", "docker", "json"]),
              help="Output format")
def export(record: str, tenant: Optional[str], fmt: str) -> None:
    """
    Export env variables to file.
    
    Usage:
        ikv-secrets export prod-api > .env
        ikv-secrets export prod-api -f docker > docker.env
    """
    if not tenant:
        click.echo("# Error: --tenant required or set IKV_TENANT", err=True)
        sys.exit(1)
    
    try:
        from ikv_secrets.config import get_tenant_url
        import json
        
        url = get_tenant_url(tenant)
        if not url:
            click.echo(f"# Error: No URL for tenant '{tenant}'", err=True)
            sys.exit(1)
        
        client = IKVClient(vault_url=url, tenant=tenant)
        env_vars = client.get_env(record)
        
        if fmt == "json":
            click.echo(json.dumps(env_vars, indent=2))
        elif fmt == "shell":
            for key, value in env_vars.items():
                escaped = value.replace("'", "'\"'\"'")
                click.echo(f"export {key}='{escaped}'")
        elif fmt == "docker":
            for key, value in env_vars.items():
                click.echo(f"{key}={value}")
        else:  # dotenv
            for key, value in env_vars.items():
                escaped = value.replace('"', '\\"')
                click.echo(f'{key}="{escaped}"')
    
    except TierError as e:
        click.echo(f"# Error: {e}", err=True)
        sys.exit(1)
    except IKVClientError as e:
        click.echo(f"# Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
