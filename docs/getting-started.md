# Getting Started

This guide walks you through installing ikv-secrets and fetching your first secret.

## Prerequisites

1. **IronKeyVault account** with Premium+ subscription
2. **Python 3.9+** installed
3. Access to at least one vault record in IronKeyVault

## Installation

### From PyPI (recommended)

```bash
pip install ikv-secrets
```

### From source (development)

```bash
git clone https://github.com/IronKeyVault/ikv-secrets.git
cd ikv-secrets
pip install -e .
```

## First Login

Login authenticates you via your browser (using your normal IronKeyVault login + MFA):

```bash
ikv-secrets login --tenant <your-tenant> --url https://vault.yourcompany.com
```

**What happens:**
1. Browser opens to your IronKeyVault login page
2. You authenticate with your username/password + MFA
3. SDK receives a secure token (stored in OS keyring)
4. Token expires after 4 hours (configurable by admin)

### Verify login

```bash
ikv-secrets status
```

Output:
```
Configured tenants:
✓ acme: token valid (expires in 237 minutes) - https://vault.acme.com
```

## Fetch a Secret

### CLI method

```bash
# Load a record's fields as environment variables
eval $(ikv-secrets load "my-api-config")

# Check what was loaded
echo $API_KEY
```

### Python method

```python
from ikv_secrets import env

# Access secrets like attributes
DATABASE_URL = env.DATABASE_URL
API_KEY = env.API_KEY

# Or use dictionary access
secret = env["MY_SECRET"]
```

## How it Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Your App       │────▶│  ikv-secrets    │────▶│  IronKeyVault   │
│                 │     │  SDK            │     │  User Plane     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │ env.API_KEY           │ Bearer token          │ Encrypted
        │                       │ from keyring          │ in database
        ▼                       ▼                       ▼
   Plaintext             Token expires           Zero-knowledge
   in memory             after 4 hours           encryption
```

**Security model:**
- Secrets are **never** written to disk by the SDK
- Tokens are stored in OS keyring (or encrypted file fallback)
- All API calls use HTTPS with certificate validation
- Your master password never leaves your browser

## Next Steps

- [CLI Reference](cli-reference.md) - All available commands
- [Python API](python-api.md) - Using secrets in code
- [CI/CD Integration](cicd-integration.md) - Automation with service accounts
