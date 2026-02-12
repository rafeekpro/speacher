# WireGuard Secrets Management

> **CRITICAL**: Never commit secrets to git repository. All secrets must be in GitHub Secrets.

## Required GitHub Secrets

### WireGuard Secrets

| Secret Name | Type | Description | Example |
|-------------|-------|-------------|----------|
| `WG_PRIVATE_KEY` | Required | Full WireGuard client private key | `yAnz... (base64 encoded)` |
| `SERVER_PUBLIC_KEY` | Required | WireGuard server public key | `goK1... (base64 encoded)` |
| `SERVER_WG_IP` | Required | WireGuard tunnel IP | `10.0.0.1` |
| `SERVER_PUBLIC_IP` | Optional | Server public IP for Endpoint | `203.0.113.5` |

### Fallback SSH Secret

| Secret Name | Type | Description | When to Use |
|-------------|-------|-------------|---------------|
| `DEPLOY_PRIVATE_KEY` | Optional | Emergency SSH fallback | Only when WireGuard fails |

## Secret Generation

### 1. Generate WireGuard Keys

#### Server Keys (on 10.0.0.5)

```bash
# Generate server key pair
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Output files:
# server_private.key - KEEP SECRET, add to server config
# server_public.key - Public key, add to GitHub as SERVER_PUBLIC_KEY
```

#### Client Keys (local machine)

```bash
# Generate client key pair
wg genkey | tee client_private.key | wg pubkey > client_public.key

# Output files:
# client_private.key - KEEP SECRET, add to GitHub as WG_PRIVATE_KEY
# client_public.key - Public key, add to server config
```

### 2. Configure Server

Edit `/etc/wireguard/wg0.conf` on server:

```ini
[Interface]
# Private key from server_private.key
PrivateKey = <SERVER_PRIVATE_KEY_CONTENT>
Address = 10.0.0.1/32
ListenPort = 51820

[Peer]
# Public key from client_public.key
PublicKey = <CLIENT_PUBLIC_KEY_CONTENT>
AllowedIPs = 10.0.0.2/32
PersistentKeepalive = 25
```

### 3. Add GitHub Secrets

Go to: **Repository Settings → Secrets and variables → Actions → New repository secret**

#### WG_PRIVATE_KEY

```bash
# Copy content of client_private.key (no extra whitespace)
cat client_private.key

# Add to GitHub:
# Name: WG_PRIVATE_KEY
# Value: <exact content of client_private.key>
```

#### SERVER_PUBLIC_KEY

```bash
# Copy content of server_public.key
cat server_public.key

# Add to GitHub:
# Name: SERVER_PUBLIC_KEY
# Value: <exact content of server_public.key>
```

#### SERVER_WG_IP

```bash
# Add WireGuard tunnel IP
# Name: SERVER_WG_IP
# Value: 10.0.0.1
```

#### SERVER_PUBLIC_IP (Optional)

Only needed if server has dynamic DNS or multiple IPs:

```bash
# Add server's public IP
# Name: SERVER_PUBLIC_IP
# Value: 203.0.113.5
```

## Secret Validation

### Test Secrets Setup

```bash
# 1. Verify WireGuard config syntax
sudo wg-quick strip wg0

# 2. Test connection (on runner)
echo "$WG_PRIVATE_KEY" | wg pubkey
# Should output public key matching SERVER_PUBLIC_KEY peer

# 3. Verify key format
# Keys should be base64 encoded, 44 characters (no padding)
```

### Common Secret Errors

| Error | Cause | Fix |
|--------|--------|-----|
| `Invalid handshake` | Mismatched keys | Verify SERVER_PUBLIC_KEY matches server |
| `Peer not responding` | Wrong Endpoint IP | Check SERVER_PUBLIC_IP or DNS |
| `Permission denied` | Key file permissions | Ensure `chmod 600` on private keys |
| `Interface creation failed` | Invalid IP config | Verify Address in [Interface] section |

## Key Rotation Procedure

### Schedule

Rotate WireGuard keys **every 90 days** for security compliance.

### Rotation Steps

#### 1. Generate New Keys

```bash
# On server: Generate new server keys
wg genkey | tee server_private_new.key | wg pubkey > server_public_new.key

# On local: Generate new client keys
wg genkey | tee client_private_new.key | wg pubkey > client_public_new.key
```

#### 2. Update Server Config

```bash
# Backup current config
sudo cp /etc/wireguard/wg0.conf /etc/wireguard/wg0.conf.bak

# Update with new keys
sudo nano /etc/wireguard/wg0.conf

# Restart WireGuard
sudo wg-quick down wg0
sudo wg-quick up wg0
```

#### 3. Update GitHub Secrets

Update secrets in GitHub:
- `WG_PRIVATE_KEY` → content of `client_private_new.key`
- `SERVER_PUBLIC_KEY` → content of `server_public_new.key`

#### 4. Verify Rotation

```bash
# Test new tunnel from GitHub Actions workflow
ping -c 3 10.0.0.1

# Verify handshake
sudo wg show wg0
```

#### 5. Cleanup

```bash
# On server: securely delete old keys
shred -u server_private_old.key

# On local: securely delete old keys
shred -u client_private_old.key

# Remove backups after 7 days
sudo rm /etc/wireguard/wg0.conf.bak
```

## Secret Security Best Practices

### Storage

- ✅ **GitHub Secrets**: For production deployments
- ✅ **Local Files**: Encrypted with `gpg` or `age`
- ❌ **Never**: Commit to git repository
- ❌ **Never**: Store in environment variables files
- ❌ **Never**: Share in messages/chats

### Access Control

1. **Principle of Least Privilege**
   - Only admins can update WireGuard secrets
   - Workflow runners only use secrets, never display
   - Audit log of secret access

2. **Separation of Duties**
   - Server admin controls server keys
   - DevOps admin controls GitHub secrets
   - Different people rotate different keys

3. **Emergency Access**
   - Keep SSH key (`DEPLOY_PRIVATE_KEY`) as fallback
   - Store in secure offline location
   - Require 2-person approval for emergency use

### Transmission

- ✅ **GitHub**: HTTPS encrypted in transit
- ✅ **CLI**: Use `gh secret set` (authenticated)
- ❌ **Never**: Email/Slack plain text
- ❌ **Never**: Clipboard in unencrypted sessions

### Generation

- ✅ **WireGuard**: Use `wg genkey` (official tool)
- ✅ **Entropy**: Ensure sufficient randomness before generation
- ✅ **Strength**: 256-bit Curve25519 keys
- ❌ **Never**: Online key generators
- ❌ **Never**: Short keys or predictable patterns

## Secret Rotation Automation

### GitHub Actions for Rotation

Create `.github/workflows/rotate-wireguard-keys.yml`:

```yaml
name: Rotate WireGuard Keys

on:
  schedule:
    - cron: '0 0 1 * *'  # First day of every month
  workflow_dispatch:

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Send notification
        run: |
          echo "🔐 WireGuard key rotation due!"
          echo "Follow procedure in docs/WIREGUARD_SECRETS.md"
```

### Rotation Reminders

- **Calendar Alert**: 90 days from last rotation
- **Secret Age Label**: Track in GitHub issue
- **Audit Log**: Document all rotations

## Secret Compliance

### Checklist

Before production deployment:

- [ ] All secrets added to GitHub (not workflow files)
- [ ] Secrets tested with test scripts
- [ ] No secrets in git history
- [ ] Rotation procedure documented
- [ ] Emergency access plan in place
- [ ] Audit trail configured

During operation:

- [ ] Monthly secret access reviews
- [ ] Quarterly key rotations
- [ ] Annual security audits
- [ ] Compliance verification

## Emergency Secret Recovery

### Compromised Keys

If WireGuard keys are compromised:

1. **Immediate Action**
   ```bash
   # On server: Shut down WireGuard
   sudo wg-quick down wg0

   # In GitHub: Rotate all secrets immediately
   # Update WG_PRIVATE_KEY and SERVER_PUBLIC_KEY
   ```

2. **Investigate**
   - Check server logs for unauthorized access
   - Review GitHub Actions audit log
   - Identify scope of compromise

3. **Recover**
   - Generate new key pairs
   - Update all configurations
   - Test tunnel thoroughly
   - Document incident

4. **Prevent Recurrence**
   - Implement access controls
   - Add rotation automation
   - Improve monitoring
   - Security training

### Lost Secrets

If you lose access to secrets:

1. **Server Keys**: Regenerate on server (requires physical/console access)
2. **Client Keys**: Regenerate locally and update GitHub
3. **Access Recovery**: Use emergency SSH key to restore WireGuard

## Secret API Reference

### GitHub CLI

```bash
# Set secret
gh secret set WG_PRIVATE_KEY -b"$(cat client_private.key)"

# List secrets (names only)
gh secret list

# Delete secret
gh secret delete WG_PRIVATE_KEY
```

### Validation

```bash
# Validate secret format
# Base64, 44 characters (no padding)
if [[ ! "$WG_PRIVATE_KEY" =~ ^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=+$ ]]; then
    echo "Invalid WireGuard key format"
    exit 1
fi
```

## References

- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [WireGuard Key Management](https://www.wireguard.com/#key-management)
- [NIST Key Management Guidelines](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5)
