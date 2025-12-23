# ikv-secrets

Secure environment variable access for [IronKeyVault](https://ironkeyvault.com).

**Stop storing secrets in `.env` files.** Fetch them securely from your vault with your normal login + MFA.

## Installation

```bash
pip install ikv-secrets
```

## Quick Start

```python
from ikv_secrets import env

# Secrets are loaded automatically after login
DATABASE_URL = env.DATABASE_URL
API_KEY = env.API_KEY
```

## CLI Usage

```bash
# Login (opens browser for your normal auth + MFA)
ikv-secrets login --tenant acme

# Load secrets into your shell
eval $(ikv-secrets load prod-api)

# Export to .env file
ikv-secrets export prod-api > .env

# Check status
ikv-secrets status
```

## Features

- 🔐 **Zero plaintext storage** - Secrets never saved to disk
- 🔑 **Your auth, your MFA** - Uses your tenant's configured authentication
- 🔄 **Centralized rotation** - Update once, all devs get new values
- 📋 **Audit trail** - Know who accessed what and when
- 🐍 **Pythonic API** - Simple `env.SECRET` access pattern

## Requirements

- IronKeyVault **Premium+** subscription
- Python 3.9+

## Documentation

- [Full Documentation](https://ironkeyvault.com/docs/sdk)
- [API Reference](https://ironkeyvault.com/docs/sdk/api)
- [CI/CD Integration](https://ironkeyvault.com/docs/sdk/cicd)

## License

MIT License - see [LICENSE](LICENSE) for details.
