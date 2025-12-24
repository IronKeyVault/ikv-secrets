# CI/CD Integration

Using ikv-secrets in automated pipelines with service accounts.

## Overview

For CI/CD, you use **service account credentials** instead of browser login:

- `IKV_API_KEY` - Service account API key
- `IKV_MASTER_KEY` - Master password for decryption

These are set as secrets in your CI/CD platform.

## Setup

### 1. Create Service Account in IronKeyVault

1. Go to **Admin Panel** → **Service Accounts**
2. Click **Create Service Account**
3. Name it (e.g., `github-actions-prod`)
4. Set permissions (which records it can access)
5. Copy the **API Key** (shown once!)

### 2. Store Credentials in CI/CD

#### GitHub Actions

```yaml
# Settings → Secrets → Actions
IKV_TENANT: acme
IKV_VAULT_URL: https://vault.acme.com
IKV_API_KEY: <your-api-key>
IKV_MASTER_KEY: <your-master-password>
```

#### GitLab CI

```yaml
# Settings → CI/CD → Variables
IKV_TENANT: acme
IKV_VAULT_URL: https://vault.acme.com
IKV_API_KEY: <your-api-key>  # Masked
IKV_MASTER_KEY: <your-master-password>  # Masked
```

## GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install ikv-secrets
          pip install -r requirements.txt
      
      - name: Load secrets and deploy
        env:
          IKV_TENANT: ${{ secrets.IKV_TENANT }}
          IKV_VAULT_URL: ${{ secrets.IKV_VAULT_URL }}
          IKV_API_KEY: ${{ secrets.IKV_API_KEY }}
          IKV_MASTER_KEY: ${{ secrets.IKV_MASTER_KEY }}
        run: |
          # Login with service account
          ikv-secrets login --tenant $IKV_TENANT --url $IKV_VAULT_URL \
            --api-key $IKV_API_KEY --master-key $IKV_MASTER_KEY
          
          # Load secrets
          eval $(ikv-secrets load "prod-config")
          
          # Deploy (secrets now in env)
          ./deploy.sh
```

## GitLab CI Example

```yaml
stages:
  - deploy

deploy:
  stage: deploy
  image: python:3.11
  
  variables:
    IKV_TENANT: $IKV_TENANT
    IKV_VAULT_URL: $IKV_VAULT_URL
  
  script:
    - pip install ikv-secrets
    - |
      ikv-secrets login --tenant $IKV_TENANT --url $IKV_VAULT_URL \
        --api-key $IKV_API_KEY --master-key $IKV_MASTER_KEY
    - eval $(ikv-secrets load "prod-config")
    - ./deploy.sh
  
  only:
    - main
```

## Docker Build Example

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install ikv-secrets
RUN pip install ikv-secrets

# Copy app
COPY . /app
WORKDIR /app

# Secrets loaded at runtime, not build time!
CMD ["python", "app.py"]
```

```yaml
# docker-compose.yml
services:
  app:
    build: .
    environment:
      - IKV_TENANT=${IKV_TENANT}
      - IKV_VAULT_URL=${IKV_VAULT_URL}
      - IKV_API_KEY=${IKV_API_KEY}
      - IKV_MASTER_KEY=${IKV_MASTER_KEY}
```

## Python Script for CI/CD

```python
#!/usr/bin/env python3
"""CI/CD secret loader."""
import os
import sys
from ikv_secrets import login, IKVClient
from ikv_secrets.client import AuthenticationError

def main():
    tenant = os.environ.get("IKV_TENANT")
    vault_url = os.environ.get("IKV_VAULT_URL")
    api_key = os.environ.get("IKV_API_KEY")
    master_key = os.environ.get("IKV_MASTER_KEY")
    
    if not all([tenant, vault_url, api_key, master_key]):
        print("Missing required environment variables", file=sys.stderr)
        sys.exit(1)
    
    # Login
    login(
        tenant=tenant,
        vault_url=vault_url,
        api_key=api_key,
        master_key=master_key
    )
    
    # Fetch secrets
    client = IKVClient(tenant=tenant)
    record = client.get_record("prod-config")
    
    # Output as shell exports
    for key, value in record.fields.items():
        # Escape single quotes in value
        escaped = value.replace("'", "'\\''")
        print(f"export {key}='{escaped}'")

if __name__ == "__main__":
    main()
```

## Security Best Practices

### 1. Separate Service Accounts per Environment

```
github-actions-dev   → can access dev-* records only
github-actions-staging → can access staging-* records only  
github-actions-prod  → can access prod-* records only
```

### 2. Rotate Credentials Regularly

- Rotate API keys every 90 days
- Update master passwords quarterly
- Revoke immediately if compromised

### 3. Limit Permissions

Service accounts should only access:
- Records needed for that specific pipeline
- Read-only access (no create/update/delete)

### 4. Audit Logging

All service account access is logged in IronKeyVault:
- Which record was accessed
- Timestamp
- Source IP
- Success/failure

### 5. Never Commit Secrets

```bash
# .gitignore
.env
*.env
secrets.json
```

## Troubleshooting

### "Authentication failed"

Check that:
1. `IKV_API_KEY` is correct (copy again from admin panel)
2. `IKV_MASTER_KEY` is the correct master password
3. Service account is not disabled

### "Permission denied"

Check that:
1. Service account has access to the requested record
2. Record exists in the tenant
3. Tenant has Premium+ subscription

### "Token expired"

Service account tokens expire after 4 hours. For long-running jobs:
1. Login at the start of each job
2. Or refresh token mid-job if needed
