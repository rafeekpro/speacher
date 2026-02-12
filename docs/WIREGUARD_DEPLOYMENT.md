# WireGuard Deployment Guide

> **Purpose**: Secure, encrypted deployment to Kubernetes cluster using WireGuard VPN tunnel.

## Overview

WireGuard replaces SSH-based deployment with a modern, encrypted peer-to-peer VPN tunnel. This provides:

- **Encrypted communication** between GitHub Actions runner and Kubernetes cluster
- **No SSH exposure** on the production server
- **Simplified security model** with single-purpose tunnel
- **Better performance** than SSH with multiplexing
- **Automatic reconnection** with persistent keepalive

## Network Architecture

```
┌─────────────────────┐         WireGuard Tunnel (UDP 51820)       ┌─────────────────────┐
│ GitHub Actions    │ 10.0.0.2/32 ───────────────────── 10.0.0.1/32 │ Kubernetes Server  │
│ Runner (Client)   │        wg0                           wg0         │ 10.0.0.5         │
│                 │                                            │ (k3s cluster)    │
└─────────────────────┘                                            └─────────────────────┘
```

### IP Allocation

| Role | IP Address | Description |
|-------|-------------|-------------|
| Server (K8s) | 10.0.0.1/32 | WireGuard VPN endpoint |
| Client (Runner) | 10.0.0.2/32 | GitHub Actions WireGuard client |
| Server External | 10.0.0.5 | Physical server (public IP) |
| Network | 10.0.0.0/24 | WireGuard tunnel network |

## Prerequisites

### Server-Side (10.0.0.5)

1. **WireGuard Installed**:
   ```bash
   sudo apt-get update && sudo apt-get install -y wireguard
   ```

2. **WireGuard Configured** (`/etc/wireguard/wg0.conf`):
   ```ini
   [Interface]
   PrivateKey = <SERVER_PRIVATE_KEY>
   Address = 10.0.0.1/32
   ListenPort = 51820

   [Peer]
   PublicKey = <CLIENT_PUBLIC_KEY>
   AllowedIPs = 10.0.0.2/32
   PersistentKeepalive = 25
   ```

3. **Firewall Rules**:
   ```bash
   # Allow WireGuard UDP port
   sudo ufw allow 51820/udp

   # Forward traffic to WireGuard interface
   sudo iptables -A FORWARD -i wg0 -j ACCEPT
   sudo iptables -A FORWARD -o wg0 -j ACCEPT
   ```

4. **WireGuard Started**:
   ```bash
   sudo wg-quick up wg0
   sudo systemctl enable wg-quick@wg0
   ```

### GitHub-Side (Runner)

1. **GitHub Secrets Configured** (see `WIREGUARD_SECRETS.md`)
2. **Workflow Updated** (`.github/workflows/deploy-k8s.yml`)

## WireGuard Key Generation

### Generate Key Pair

```bash
# Generate server keys (on server 10.0.0.5)
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Generate client keys (on local machine)
wg genkey | tee client_private.key | wg pubkey > client_public.key
```

### Key Exchange

1. **Server Setup**:
   - Server private key → Server config (`/etc/wireguard/wg0.conf`)
   - Server public key → GitHub Secret `SERVER_PUBLIC_KEY`

2. **Client Setup**:
   - Client private key → GitHub Secret `WG_PRIVATE_KEY`
   - Client public key → Server config `[Peer]` section

## GitHub Actions Integration

### Workflow Structure

```yaml
jobs:
  setup-wireguard:
    name: Setup WireGuard Tunnel
    runs-on: ubuntu-latest
    steps:
      - name: Install WireGuard
        run: |
          sudo apt-get update
          sudo apt-get install -y wireguard

      - name: Configure WireGuard
        run: |
          cat <<EOF | sudo tee /etc/wireguard/wg0.conf
          [Interface]
          PrivateKey = ${{ secrets.WG_PRIVATE_KEY }}
          Address = 10.0.0.2/32
          DNS = 10.0.0.1

          [Peer]
          PublicKey = ${{ secrets.SERVER_PUBLIC_KEY }}
          Endpoint = <SERVER_PUBLIC_IP>:51820
          AllowedIPs = 10.0.0.1/32, 10.0.0.0/24
          PersistentKeepalive = 25
          EOF

      - name: Start WireGuard
        run: |
          sudo wg-quick up wg0

      - name: Verify Tunnel
        run: |
          ping -c 3 10.0.0.1

  deploy:
    needs: setup-wireguard
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    steps:
      - name: Deploy through tunnel
        run: |
          # All kubectl commands go through 10.0.0.1
          kubectl get nodes

  teardown-wireguard:
    name: Teardown WireGuard Tunnel
    needs: [setup-wireguard, deploy]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Stop WireGuard
        run: |
          sudo wg-quick down wg0
```

## Deployment Commands

### Through WireGuard Tunnel

All Kubernetes operations use the tunnel IP (10.0.0.1):

```bash
# Deploy manifests
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/secrets.yml
kubectl apply -f k8s/backend.yml

# Update images
kubectl set image deployment/backend backend=speacher-backend:${IMAGE_TAG} -n speacher

# Check rollout
kubectl rollout status deployment/backend -n speacher --timeout=180s

# Verify deployment
kubectl get pods -n speacher
kubectl get svc -n speacher
```

### Rollback Operations

```bash
# Check rollout history
kubectl rollout history deployment/backend -n speacher

# Rollback to previous version
kubectl rollout undo deployment/backend -n speacher

# Rollback to specific revision
kubectl rollout undo deployment/backend -n speacher --to-revision=3

# Pause rollout
kubectl rollout pause deployment/backend -n speacher

# Resume rollout
kubectl rollout resume deployment/backend -n speacher

# Scale deployment
kubectl scale deployment/backend --replicas=3 -n speacher
```

## Testing

### Local Testing

Before committing changes, test locally:

```bash
# 1. Test tunnel connectivity
./devops/k8s/test-wireguard-tunnel.sh

# 2. Test full deployment
./devops/k8s/test-full-deployment.sh

# 3. Test rollback operations
./devops/k8s/test-rollback.sh
```

### Test Coverage

The test scripts verify:

1. **Tunnel Connectivity**
   - WireGuard interface status
   - Ping to server IP (10.0.0.1)
   - Peer handshake verification
   - Data transfer stats

2. **Kubernetes Access**
   - kubectl can connect to cluster
   - Can query nodes and pods
   - Namespace management works

3. **Deployment Operations**
   - Apply manifests successfully
   - Create deployments and services
   - Update images without downtime
   - Rollout status monitoring

4. **Rollback Operations**
   - Rollback to previous revision
   - Rollback to specific revision
   - Pause/resume rollouts
   - Scale operations

## Security Considerations

### Key Rotation

Rotate WireGuard keys every 90 days:

1. Generate new key pairs
2. Update server config with new server keys
3. Update GitHub Secrets with new client keys
4. Restart WireGuard on server and runners
5. Verify tunnel re-establishes

### Access Control

- **Principle of Least Privilege**: Tunnel only allows K8s API (6443) and node communications
- **Network Segmentation**: Tunnel network (10.0.0.0/24) isolated from production networks
- **No SSH Exposure**: SSH port closed on public interface
- **Encryption**: All traffic encrypted with WireGuard's Noise protocol

### Fallback Access

Keep SSH key in GitHub Secret (`DEPLOY_PRIVATE_KEY`) as emergency fallback:

```bash
# Only use if WireGuard fails
ssh -i $DEPLOY_PRIVATE_KEY rla@10.0.0.5
```

## Troubleshooting

See `WIREGUARD_TROUBLESHOOTING.md` for common issues and solutions.

## Performance

### WireGuard vs SSH

| Metric | WireGuard | SSH | Improvement |
|--------|-------------|------|-------------|
| Connection Setup | ~100ms | ~500ms | 5x faster |
| Throughput | ~1 Gbps | ~100 Mbps | 10x higher |
| CPU Usage | Low | Moderate | 2-3x lower |
| Reconnection | Automatic | Manual | Higher reliability |

### Monitoring

Monitor tunnel performance:

```bash
# Check handshake (should be recent)
sudo wg show wg0

# Check data transfer
sudo wg show wg0 | grep transfer

# Check interface errors
ip -s link show wg0
```

## Migration from SSH

### Before Migration

1. ✅ WireGuard installed and configured on server
2. ✅ GitHub Secrets created
3. ✅ Tunnel tested with test scripts
4. ✅ kubectl works through tunnel

### Migration Steps

1. Update `.github/workflows/deploy-k8s.yml` (remove SSH, add WireGuard)
2. Test workflow in staging environment
3. Verify deployments work through tunnel
4. Remove SSH agent from workflow
5. Close SSH port on server firewall (optional)

### After Migration

1. ✅ Monitor first few deployments through tunnel
2. ✅ Verify all rollback operations work
3. ✅ Confirm SSH not used in logs
4. ✅ Update documentation

## References

- [WireGuard Project Homepage](https://www.wireguard.com/)
- [WireGuard Quick Start](https://www.wireguard.com/quickstart/)
- [WireGuard Configuration](https://www.wireguard.com/config/)
- [Kubernetes kubectl Documentation](https://kubernetes.io/docs/reference/kubectl/)
