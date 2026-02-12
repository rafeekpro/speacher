# WireGuard Troubleshooting Guide

> **Purpose**: Diagnose and resolve common WireGuard deployment issues.

## Quick Diagnostics

### First Steps

When WireGuard deployment fails, run diagnostics in this order:

1. **Check tunnel status**:
   ```bash
   sudo wg show wg0
   ```

2. **Verify connectivity**:
   ```bash
   ping -c 3 10.0.0.1
   ```

3. **Test kubectl**:
   ```bash
   kubectl get nodes
   ```

4. **Check logs**:
   ```bash
   sudo journalctl -u wg-quick@wg0 -n 50
   ```

## Common Issues

### 1. Tunnel Not Establishing

#### Symptoms

- `ping 10.0.0.1` fails
- `wg show` shows "No handshake"
- Timeout errors in deployment logs

#### Diagnosis

```bash
# Check if WireGuard interface is up
ip link show wg0

# Check configuration syntax
sudo wg-quick strip wg0

# Verify key pairs match
echo "$SERVER_PUBLIC_KEY" | wg pubkey
echo "$WG_PRIVATE_KEY" | wg pubkey
```

#### Solutions

**Problem: Mismatched Keys**
```bash
# Solution: Regenerate and redistribute keys
# 1. Generate new key pair
wg genkey | tee private.key | wg pubkey > public.key

# 2. Update server config with new public key
# 3. Update GitHub WG_PRIVATE_KEY with new private key

# 4. Restart WireGuard on both ends
sudo wg-quick down wg0
sudo wg-quick up wg0
```

**Problem: Endpoint Unreachable**
```bash
# Check if server is listening
sudo netstat -ulnp | grep 51820

# Check firewall
sudo ufw status
sudo iptables -L -n -v | grep 51820

# Solution: Open UDP port 51820
sudo ufw allow 51820/udp
# or
sudo iptables -A INPUT -p udp --dport 51820 -j ACCEPT
```

**Problem: NAT/Traversal Issues**
```bash
# Test if server is behind NAT
# Check public IP matches SERVER_PUBLIC_IP
curl ifconfig.me

# Solution: Use port forwarding on router
# Forward UDP 51820 to internal server IP
```

### 2. Intermittent Connection

#### Symptoms

- Tunnel connects then drops
- Frequent re-handshakes
- Deployment fails randomly

#### Diagnosis

```bash
# Check keepalive setting
sudo wg show wg0 | grep keepalive

# Check for packet loss
ping -c 100 10.0.0.1 | grep "packet loss"

# Check interface errors
ip -s link show wg0
```

#### Solutions

**Problem: No Persistent Keepalive**
```ini
# Add to WireGuard config on both ends:
[Peer]
PersistentKeepalive = 25
```

**Problem: MTU Issues**
```ini
# Add to Interface section:
[Interface]
# Reduce MTU if connection unstable
# Common values: 1280, 1420
MTU = 1280
```

**Problem: Firewall State Tracking**
```bash
# Solution: Allow established connections
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
```

### 3. Slow Transfer Speeds

#### Symptoms

- Large image transfers timeout
- Deployment takes >10 minutes
- Throughput < 100 Mbps

#### Diagnosis

```bash
# Test bandwidth
iperf3 -c 10.0.0.1 -t 30

# Check CPU usage
top -bn1 | grep -i wg

# Check interface statistics
ip -s link show wg0
```

#### Solutions

**Problem: MTU Fragmentation**
```bash
# Find optimal MTU
for mtu in 1500 1420 1280; do
  ping -c 1 -M do -s $((mtu-28)) 10.0.0.1 && echo "MTU: $mtu"
done

# Set optimal MTU in config
```

**Problem: CPU Bottleneck**
```bash
# Solution: Enable multithreading (WireGuard 1.0+)
# No config change needed, WireGuard auto-scales
# Verify: Check if using WireGuard Go implementation
```

**Problem: Network Congestion**
```bash
# Solution: Use congestion control
sysctl -w net.core.default_qdisc=fq_codel
sysctl -w net.ipv4.tcp_congestion_control=bbr
```

### 4. kubectl Commands Fail

#### Symptoms

- `kubectl get nodes` fails
- "Connection refused" errors
- "Unauthorized" errors

#### Diagnosis

```bash
# Check kubectl config
kubectl config view

# Test direct connection
curl -k https://10.0.0.1:6443/version

# Check k3s service
sudo systemctl status k3s
```

#### Solutions

**Problem: Wrong kubeconfig**
```bash
# Solution: Generate correct kubeconfig
sudo cat /etc/rancher/k3s/k3s.yaml

# Update GitHub Secret KUBECONFIG or inline in workflow
```

**Problem: Certificate Issues**
```bash
# Check certificate expiration
openssl x509 -in /var/lib/rancher/k3s/server/tls/server.crt -noout -dates

# Solution: Restart k3s to regenerate certs
sudo systemctl restart k3s
```

**Problem: RBAC Permissions**
```bash
# Check user permissions
kubectl auth can-i '*' '*' --all-namespaces

# Solution: Use admin context or create service account
```

### 5. Image Transfer Failures

#### Symptoms

- `scp` fails with "connection lost"
- Image tar.gz corrupted
- Out of disk space

#### Diagnosis

```bash
# Check disk space
df -h /tmp

# Check transfer retry count
# Look for "retrying" in logs
```

#### Solutions

**Problem: Disk Space**
```bash
# Clean up old images
sudo k3s ctr images ls | grep -v "REPO" | \
  awk '{print $1}' | xargs -I {} sudo k3s ctr images rm {}

# Clean /tmp
sudo rm -rf /tmp/speacher-*
```

**Problem: Connection Timeout**
```bash
# Solution: Increase timeout
scp -o ConnectTimeout=60 file.tar.gz user@host:/tmp/
```

**Problem: Transfer Size**
```bash
# Solution: Compress more aggressively
cat backend.tar frontend.tar | \
  pigz -9 > combined.tar.gz
```

### 6. Deployment Rollback Failures

#### Symptoms

- `kubectl rollout undo` fails
- Pods stuck in pending state
- Old version not restored

#### Diagnosis

```bash
# Check deployment status
kubectl describe deployment/backend -n speacher

# Check replica sets
kubectl get rs -n speacher

# Check events
kubectl get events -n speacher --sort-by='.lastTimestamp'
```

#### Solutions

**Problem: No Previous Revisions**
```bash
# Check revision history
kubectl rollout history deployment/backend -n speacher

# Solution: Can't rollback if only 1 revision
# Deploy new version first, then rollback
```

**Problem: Stuck Rollout**
```bash
# Solution: Cancel and retry
kubectl rollout undo deployment/backend -n speacher
kubectl rollout status deployment/backend -n speacher --timeout=180s

# If still stuck, scale to zero first
kubectl scale deployment/backend --replicas=0 -n speacher
kubectl scale deployment/backend --replicas=2 -n speacher
```

**Problem: Image Not Found**
```bash
# Verify image exists
sudo k3s ctr images ls | grep speacher

# Solution: Import image first
# Load from tar or pull from registry
```

## Debugging Tools

### Log Collection

```bash
# WireGuard logs
sudo journalctl -u wg-quick@wg0 -f > wireguard.log

# kubectl debugging
kubectl get events -n speacher --watch > events.log

# Network capture
sudo tcpdump -i wg0 -w capture.pcap
```

### Connection Testing

```bash
# Full connectivity test
./devops/k8s/test-wireguard-tunnel.sh

# Full deployment test
IMAGE_TAG=test-123 ./devops/k8s/test-full-deployment.sh

# Rollback test
./devops/k8s/test-rollback.sh
```

### Performance Monitoring

```bash
# Real-time stats
watch -n 1 'sudo wg show wg0'

# Bandwidth monitoring
iftop -i wg0

# Latency testing
mtr -r -c 100 10.0.0.1
```

## Error Messages Reference

### WireGuard Errors

| Error | Meaning | Solution |
|--------|-----------|----------|
| `Invalid handshake` | Key mismatch | Regenerate keys |
| `Peer not responding` | Endpoint unreachable | Check firewall/NAT |
| `Device not found` | Interface not created | Run `wg-quick up` |
| `Permission denied` | Config file permissions | `chmod 600 /etc/wireguard/wg0.conf` |

### kubectl Errors

| Error | Meaning | Solution |
|--------|-----------|----------|
| `connection refused` | API server down | Restart k3s |
| `unauthorized` | Invalid credentials | Update kubeconfig |
| `context deadline exceeded` | Network timeout | Check tunnel |
| `image pull errors` | Image not found | Load image manually |

### GitHub Actions Errors

| Error | Meaning | Solution |
|--------|-----------|----------|
| `secrets not found` | Missing secrets | Add required secrets |
| `workflow timeout` | Operation too long | Increase timeout |
| `runner offline` | Runner unavailable | Check GitHub status |

## Emergency Procedures

### Full Reset

If all else fails:

```bash
# 1. Stop everything
sudo wg-quick down wg0
sudo systemctl stop k3s

# 2. Flush network config
sudo iptables -F
sudo iptables -t nat -F

# 3. Restart services
sudo systemctl start k3s
sudo wg-quick up wg0

# 4. Verify
ping -c 3 10.0.0.1
kubectl get nodes
```

### Fallback to SSH

Use emergency SSH access if WireGuard completely fails:

```bash
# Add to workflow manually
- name: Emergency SSH Access
  if: failure()
  uses: webfactory/ssh-agent@v0.9.0
  with:
    ssh-private-key: ${{ secrets.DEPLOY_PRIVATE_KEY }}

- name: Diagnose via SSH
  run: |
    ssh ${{ env.DEPLOY_HOST }} << 'EOF'
      # Check WireGuard status
      sudo wg show wg0
      # Check logs
      sudo journalctl -u wg-quick@wg0 -n 50
      # Restart WireGuard
      sudo systemctl restart wg-quick@wg0
    EOF
```

### Rollback Entire Deployment

```bash
# Use SSH fallback to revert
git revert HEAD
git push origin main

# Or manually rollback specific deployment
ssh rla@10.0.0.5 << 'EOF'
  kubectl rollout undo deployment/backend -n speacher
  kubectl rollout undo deployment/frontend -n speacher
EOF
```

## Prevention

### Monitoring Setup

```yaml
# Add to workflow for better debugging:
- name: WireGuard diagnostics
  if: failure()
  run: |
    echo "=== WireGuard Status ==="
    sudo wg show wg0
    echo ""
    echo "=== Interface Status ==="
    ip link show wg0
    echo ""
    echo "=== Connectivity Test ==="
    ping -c 5 10.0.0.1 || true
    echo ""
    echo "=== kubectl Test ==="
    kubectl get nodes || true
```

### Health Checks

```bash
# Add to workflow after tunnel setup
- name: Verify tunnel health
  run: |
    # Check handshake completed
    HANDSHAKE=$(sudo wg show wg0 | grep "latest handshake" | \
      awk '{print $3}' | cut -d: -f1-2)

    # Calculate seconds since handshake
    if [ -n "$HANDSHAKE" ]; then
      echo "Last handshake: $HANDSHAKE"
      # Verify handshake is recent (< 3 minutes)
      # ... validation logic
    fi

    # Verify data transfer
    sudo wg show wg0 | grep "transfer"
```

### Automated Recovery

```yaml
# Auto-retry on transient failures
- name: Deploy with retry
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: |
      kubectl apply -f k8s/backend.yml
      kubectl rollout status deployment/backend -n speacher --timeout=180s
```

## Support Resources

- **WireGuard Documentation**: https://www.wireguard.com/
- **Kubernetes Troubleshooting**: https://kubernetes.io/docs/tasks/debug/
- **GitHub Actions Debugging**: https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows
- **Project Logs**: Check GitHub Actions run logs

## Escalation

If issues persist after following this guide:

1. Collect diagnostic output:
   ```bash
   ./devops/k8s/test-wireguard-tunnel.sh > diagnostics.txt 2>&1
   ```

2. Gather logs:
   ```bash
   sudo journalctl -u wg-quick@wg0 -n 100 > wireguard.log
   kubectl get events --all-namespaces > events.log
   ```

3. Document steps to reproduce

4. Create issue with full diagnostics attached
