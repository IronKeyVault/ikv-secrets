# Troubleshooting

Common issues and solutions when using ikv-secrets.

## Authentication Issues

### "Run 'ikv-secrets login' first"

**Problem:** No valid token found.

**Solution:**
```bash
ikv-secrets login --tenant <your-tenant> --url https://vault.example.com
```

---

### "Token expired"

**Problem:** Your session has expired (tokens last 4 hours by default).

**Solution:**
```bash
ikv-secrets login --tenant <your-tenant> --force
```

---

### Browser doesn't open

**Problem:** Running in headless environment (SSH, container).

**Solutions:**

1. **Copy the URL manually:**
   ```
   Please open this URL in your browser:
   https://vault.example.com/auth/device?code=ABCD-1234
   ```
   
2. **Use service account credentials:**
   ```bash
   ikv-secrets login --tenant acme \
     --api-key $IKV_API_KEY \
     --master-key $IKV_MASTER_KEY
   ```

---

### "SSL certificate verify failed"

**Problem:** Self-signed certificate (common in development).

**Solution for development only:**
```bash
export IKV_VERIFY_SSL=false
ikv-secrets login --tenant dev --url https://localhost:5001
```

⚠️ Never disable SSL verification in production!

---

## Permission Issues

### "Tier restriction: Premium+ required"

**Problem:** Your IronKeyVault subscription doesn't include SDK access.

**Solution:** Contact your admin to upgrade to Premium+ plan.

---

### "Record not found"

**Problem:** The requested record doesn't exist or you don't have access.

**Check:**
1. Record name is spelled correctly (case-sensitive)
2. You have permission to access this record
3. Record exists in the correct tenant

```bash
# Verify you're using the right tenant
ikv-secrets status
```

---

## Configuration Issues

### Config file location

```bash
# View config
cat ~/.config/ikv-secrets/config.json

# Reset config
rm -rf ~/.config/ikv-secrets/
```

---

### Token storage issues

**Keyring not available:**

If OS keyring is not available (common in containers/CI), tokens are stored in:
```
~/.config/ikv-secrets/tokens.json
```

This file is encrypted and has restricted permissions (600).

**Fix permission issues:**
```bash
chmod 600 ~/.config/ikv-secrets/tokens.json
chmod 700 ~/.config/ikv-secrets/
```

---

## Network Issues

### "Connection refused"

**Problem:** Can't reach the vault server.

**Check:**
1. Vault URL is correct
2. Server is running
3. Firewall allows connection
4. VPN is connected (if required)

```bash
# Test connectivity
curl -I https://vault.example.com/health
```

---

### "Timeout"

**Problem:** Server is slow or unreachable.

**Solutions:**
1. Check network connectivity
2. Try again later
3. Contact your admin if persistent

---

## Python Issues

### "ModuleNotFoundError: No module named 'ikv_secrets'"

**Problem:** Package not installed in current environment.

**Solution:**
```bash
pip install ikv-secrets

# Or in virtual environment
source venv/bin/activate
pip install ikv-secrets
```

---

### "AttributeError: 'EnvProxy' object has no attribute 'MY_SECRET'"

**Problem:** Secret doesn't exist.

**Solution:**
```python
# Use .get() with default
value = env.get("MY_SECRET", "default")

# Or check first
if "MY_SECRET" in env:
    value = env.MY_SECRET
```

---

### Secrets not updating after change in vault

**Problem:** Secrets are cached in memory.

**Solution:**
```python
from ikv_secrets import env

# Clear cache
env.clear()

# Re-fetch
value = env.MY_SECRET
```

---

## Debug Mode

Enable verbose logging:

```bash
# CLI
IKV_DEBUG=1 ikv-secrets login --tenant acme

# Python
import logging
logging.basicConfig(level=logging.DEBUG)

from ikv_secrets import env
```

---

## Getting Help

1. **Check status:**
   ```bash
   ikv-secrets status
   ```

2. **View version:**
   ```bash
   ikv-secrets --version
   ```

3. **GitHub Issues:**
   [github.com/IronKeyVault/ikv-secrets/issues](https://github.com/IronKeyVault/ikv-secrets/issues)

4. **IronKeyVault Support:**
   [ironkeyvault.com/support](https://ironkeyvault.com/support)
