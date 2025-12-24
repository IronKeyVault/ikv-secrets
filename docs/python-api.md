# Python API Reference

Using ikv-secrets in your Python applications.

## Quick Start

```python
from ikv_secrets import env

# Access secrets as attributes
DATABASE_URL = env.DATABASE_URL
API_KEY = env.API_KEY
```

## The `env` Object

The `env` object is a lazy-loading proxy that fetches secrets on first access.

### Attribute Access

```python
from ikv_secrets import env

# Raises AttributeError if secret doesn't exist
api_key = env.API_KEY
```

### Dictionary Access

```python
from ikv_secrets import env

# Raises KeyError if secret doesn't exist
api_key = env["API_KEY"]

# With default value (returns None if not found)
api_key = env.get("API_KEY", "default-value")
```

### Check if Secret Exists

```python
from ikv_secrets import env

if "API_KEY" in env:
    use_api(env.API_KEY)
```

### List All Secrets

```python
from ikv_secrets import env

# Get all secret names
secret_names = list(env)

# Get all as dict
all_secrets = dict(env)
```

## IKVClient Class

For more control, use the `IKVClient` directly:

```python
from ikv_secrets import IKVClient

# Create client (uses default tenant from config)
client = IKVClient()

# Or specify tenant explicitly
client = IKVClient(tenant="acme")

# Fetch a specific record
record = client.get_record("prod-api-config")
print(record.fields)  # {'API_KEY': 'sk-...', 'SECRET': '...'}

# List available records
records = client.list_records()
for r in records:
    print(f"{r.name}: {r.record_type}")
```

### Client Options

```python
client = IKVClient(
    tenant="acme",           # Tenant name
    vault_url="https://...", # Override vault URL
    api_key="...",           # Service account key
    master_key="..."         # Service account password
)
```

## Authentication

### Check Authentication Status

```python
from ikv_secrets import IKVClient
from ikv_secrets.keyring_store import get_token

# Check if token exists and is valid
token = get_token("acme")
if token and not token.is_expired:
    print(f"Token valid for {token.expires_in // 60} minutes")
else:
    print("Need to login")
```

### Programmatic Login

```python
from ikv_secrets import login, logout

# Interactive login (opens browser)
token = login(tenant="acme", vault_url="https://vault.acme.com")

# Service account login (no browser)
token = login(
    tenant="acme",
    vault_url="https://vault.acme.com",
    api_key="your-api-key",
    master_key="your-master-password"
)

# Logout
logout(tenant="acme")
logout(all_tenants=True)
```

## Error Handling

```python
from ikv_secrets import IKVClient
from ikv_secrets.client import (
    IKVClientError,      # Base exception
    AuthenticationError, # Token expired/invalid
    TierError           # Premium+ required
)

client = IKVClient()

try:
    record = client.get_record("my-config")
except AuthenticationError:
    print("Please run: ikv-secrets login --tenant <name>")
except TierError as e:
    print(f"Upgrade required: {e}")
except IKVClientError as e:
    print(f"Error: {e}")
```

## Configuration

### Config File Location

```
~/.config/ikv-secrets/config.json
```

### Read Config

```python
from ikv_secrets.config import get_config, get_tenant_url

# Get full config
config = get_config()
print(config["tenants"])

# Get URL for tenant
url = get_tenant_url("acme")
```

## Examples

### Django Settings

```python
# settings.py
from ikv_secrets import env

SECRET_KEY = env.DJANGO_SECRET_KEY
DEBUG = env.get("DEBUG", "false").lower() == "true"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.DB_NAME,
        'USER': env.DB_USER,
        'PASSWORD': env.DB_PASSWORD,
        'HOST': env.DB_HOST,
        'PORT': env.get("DB_PORT", "5432"),
    }
}
```

### FastAPI

```python
from fastapi import FastAPI
from ikv_secrets import env

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Pre-load secrets
    _ = env.API_KEY
    
@app.get("/")
async def root():
    # Secrets already cached
    return {"status": "ok"}
```

### Flask

```python
from flask import Flask
from ikv_secrets import env

app = Flask(__name__)
app.config["SECRET_KEY"] = env.FLASK_SECRET_KEY
```

## Security Best Practices

1. **Never log secrets** - Avoid printing env values
2. **Use narrow scopes** - Only fetch secrets you need
3. **Handle expiration** - Token expires after 4 hours
4. **CI/CD isolation** - Use separate service accounts per environment
