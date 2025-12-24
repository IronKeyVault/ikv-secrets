# CLI Reference

Complete reference for all ikv-secrets CLI commands.

## Global Options

These options work with all commands:

| Option | Description |
|--------|-------------|
| `--help` | Show help for command |
| `--version` | Show version |

## Commands

### `login`

Authenticate with an IronKeyVault tenant.

```bash
ikv-secrets login --tenant <name> [options]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--tenant`, `-t` | Tenant name (required) | - |
| `--url` | Vault URL | `https://vault.example.com` |
| `--force` | Force re-login even if token valid | `false` |
| `--api-key` | Service account API key (CI/CD) | - |
| `--master-key` | Master password (CI/CD) | - |

**Examples:**

```bash
# Interactive login (browser-based)
ikv-secrets login --tenant acme --url https://vault.acme.com

# Force re-login
ikv-secrets login --tenant acme --force

# Service account (CI/CD)
ikv-secrets login --tenant acme --api-key $IKV_API_KEY --master-key $IKV_MASTER_KEY
```

---

### `logout`

Remove stored credentials for a tenant.

```bash
ikv-secrets logout [--tenant <name>] [--all]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--tenant`, `-t` | Specific tenant to logout |
| `--all` | Logout from all tenants |

**Examples:**

```bash
# Logout from specific tenant
ikv-secrets logout --tenant acme

# Logout from all tenants
ikv-secrets logout --all
```

---

### `status`

Show authentication status for all configured tenants.

```bash
ikv-secrets status
```

**Output example:**

```
Configured tenants:
✓ acme: token valid (expires in 237 minutes) - https://vault.acme.com
✗ staging: token expired - https://staging.vault.com
```

---

### `load`

Output environment variables for shell eval.

```bash
ikv-secrets load <record-name> [--tenant <name>]
```

**Usage:**

```bash
# Load into current shell
eval $(ikv-secrets load "prod-api-config")

# Specify tenant explicitly
eval $(ikv-secrets load "prod-api" --tenant acme)
```

**Output format:**

```bash
export API_KEY="sk-abc123..."
export DATABASE_URL="postgres://..."
export SECRET_TOKEN="xyz789..."
```

---

### `export`

Export secrets to a file format.

```bash
ikv-secrets export <record-name> [options]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--tenant`, `-t` | Tenant name | default tenant |
| `--format`, `-f` | Output format | `dotenv` |

**Formats:**

| Format | Description |
|--------|-------------|
| `dotenv` | Standard `.env` file format |
| `docker` | Docker env-file format |
| `json` | JSON object |

**Examples:**

```bash
# Export to .env file
ikv-secrets export prod-api > .env

# Docker format
ikv-secrets export prod-api -f docker > docker.env

# JSON format
ikv-secrets export prod-api -f json > secrets.json
```

---

## Environment Variables

The CLI respects these environment variables:

| Variable | Description |
|----------|-------------|
| `IKV_TENANT` | Default tenant name |
| `IKV_VAULT_URL` | Default vault URL |
| `IKV_API_KEY` | Service account API key |
| `IKV_MASTER_KEY` | Service account master password |

**Example:**

```bash
export IKV_TENANT=acme
export IKV_VAULT_URL=https://vault.acme.com

# Now these work without --tenant
ikv-secrets status
ikv-secrets load "my-config"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Authentication required |
| 3 | Permission denied (tier restriction) |
| 4 | Record not found |
