# Kubernetes Deployment Pipeline Guide

## Overview

The `deploy-k8s-enhanced.yml` workflow provides comprehensive, production-ready Kubernetes deployment capabilities with environment-specific strategies, automated testing, rollback procedures, and monitoring.

## Features

- ✅ **Multi-environment deployment** (dev, staging, production)
- ✅ **Unique namespaces** per deployment for isolation
- ✅ **Automated smoke tests** with rollback on failure
- ✅ **Health monitoring** and diagnostics
- ✅ **Slack/Email notifications** for production deployments
- ✅ **Debug steps** on all failures
- ✅ **Production approval** required via GitHub Environments
- ✅ **Resource cleanup** for dev environments

## Quick Start

### Required Secrets

Configure these in GitHub repository settings:

```bash
# Required for all environments
KUBE_CONFIG=<base64-encoded kubeconfig file>

# Required for production
KUBE_CONFIG_PROD=<base64-encoded production kubeconfig file>

# Optional (with defaults)
CLUSTER_NAME=speecher-cluster
CONTAINER_REGISTRY=ghcr.io
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
NOTIFICATION_EMAIL=team@example.com
```

### Encode kubeconfig:

```bash
base64 -i ~/.kube/config | pbcopy  # macOS
base64 -w 0 ~/.kube/config           # Linux
```

## Usage

### Automatic Deployment Triggers

#### 1. Development Environment

Trigger: Push to feature branches

```bash
git checkout -b feature/new-feature
git push origin feature/new-feature
```

Result:
- Namespace: `dev-{run_id}`
- Image tag: `dev-{commit_sha}`
- No approval required
- Auto-cleanup after 1 hour

#### 2. Staging Environment

Trigger: Push to main/master branch

```bash
git checkout main
git merge feature/new-feature
git push origin main
```

Result:
- Namespace: `staging`
- Image tag: `staging-{commit_sha}`
- No approval required
- Smoke tests run automatically

#### 3. Production Environment

Trigger: Create release tag

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Result:
- Namespace: `production`
- Image tag: `v1.0.0`
- **Manual approval required**
- Full monitoring and notifications

### Manual Deployment

Use workflow_dispatch for manual control:

1. Go to **Actions** tab in GitHub
2. Select **Deploy to Kubernetes (Enhanced)**
3. Click **Run workflow**
4. Choose target environment (dev/staging/production)
5. Click **Run workflow**

## Workflow Stages

### 1. Prepare
- Determines target environment
- Sets namespace and image tags
- Outputs configuration to subsequent jobs

### 2. Build
- Builds Docker images using `docker/build-push-action`
- Pushes to container registry (ghcr.io)
- Caches layers for faster builds
- Tags images appropriately

### 3. Deploy (Environment-Specific)
- Creates namespace (if needed)
- Applies Kubernetes secrets
- Deploys backend and frontend
- Waits for rollout completion
- Applies ingress rules

### 4. Smoke Tests
- Waits for pods to be ready
- Tests backend health endpoint
- Tests frontend accessibility
- Verifies database connectivity
- Runs API smoke tests

### 5. Rollback (Conditional)
- Automatic on smoke test failure
- Skips for dev environment
- Rolls back both backend and frontend
- Verifies rollback success

### 6. Monitor
- Checks pod health and resource usage
- Scans logs for errors
- Verifies service endpoints
- Tests liveness/readiness probes

### 7. Notify
- Sends Slack notifications
- Emails on failures
- Comments on PRs
- Schedules cleanup for dev

## Kubernetes Manifests

Expected structure:

```
k8s/
├── backend-deployment.yaml         # Dev/staging backend
├── backend-deployment-prod.yaml    # Production backend
├── frontend-deployment.yaml        # Dev/staging frontend
├── frontend-deployment-prod.yaml   # Production frontend
├── backend-secrets-template.yaml   # Secret templates (envsubst)
├── ingress-dev.yaml               # Dev ingress rules
├── ingress.yaml                   # Staging ingress rules
├── ingress-prod.yaml              # Production ingress rules
└── namespace.yaml                  # Namespace definitions
```

### Environment Variables in Manifests

Use `envsubst` for dynamic values:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  template:
    spec:
      containers:
        - name: backend
          image: ${BACKEND_IMAGE}  # Replaced by workflow
          env:
            - name: DATABASE_URL
              value: ${DATABASE_URL}  # From secrets
```

## Smoke Tests

Create tests in `tests/smoke/` directory:

```python
# tests/smoke/test_api.py
def test_backend_health(client):
    """Test backend health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_database_connection(client):
    """Test database connectivity"""
    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
```

## Troubleshooting

### View Deployment Logs

```bash
# View recent logs
kubectl logs -n <namespace> -l app=backend --tail=50

# Follow logs
kubectl logs -n <namespace> -f -l app=backend

# All containers in pod
kubectl logs -n <namespace> <pod-name> --all-containers=true
```

### Check Pod Status

```bash
# Get all pods
kubectl get pods -n <namespace> -o wide

# Describe pod (events, conditions)
kubectl describe pod <pod-name> -n <namespace>
```

### Manual Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/backend -n <namespace>

# Check rollback status
kubectl rollout status deployment/backend -n <namespace>

# View rollout history
kubectl rollout history deployment/backend -n <namespace>
```

### Access Pod Shell

```bash
# Get shell in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh

# Run single command
kubectl exec <pod-name> -n <namespace> -- python -c "print('hello')"
```

## Debugging Failed Deployments

The workflow automatically runs debug steps on failure, gathering:

1. Pod status and descriptions
2. Recent events
3. Full container logs
4. Resource usage metrics

Access these from the **Actions** tab:

1. Click on failed workflow run
2. Expand failed job
3. View **Debug on Failure** step output

## Production Deployment Checklist

Before deploying to production:

- [ ] All tests passing in staging
- [ ] Database migrations tested
- [ ] Rollback plan documented
- [ ] Monitoring configured
- [ ] Team notified
- [ ] Off-peak time scheduled (if needed)
- [ ] Approval obtained from lead

## Monitoring

After deployment:

1. **Check Actions tab** - Verify all jobs passed
2. **Monitor pod health** - `kubectl get pods -n production`
3. **Check application logs** - Look for errors/warnings
4. **Verify endpoints** - Test critical user flows
5. **Monitor metrics** - CPU, memory, response times

## Rollback Procedure

### Automatic Rollback

Happens automatically if smoke tests fail (staging/production only).

### Manual Rollback

```bash
# Quick rollback
kubectl rollout undo deployment/backend -n production
kubectl rollout undo deployment/frontend -n production

# Rollback to specific revision
kubectl rollout undo deployment/backend -n production --to-revision=3

# Verify rollback
kubectl rollout status deployment/backend -n production
```

## Cleanup

### Dev Namespaces

Dev namespaces use unique IDs: `dev-{run_id}`

Cleanup schedule:
- Automatic: 1 hour after deployment
- Manual: `kubectl delete namespace dev-{run_id}`

### Staging/Production

These persist and are not auto-cleaned.

## Security Best Practices

1. **Secrets Management**
   - Never commit secrets to repository
   - Use GitHub Secrets for sensitive data
   - Rotate credentials regularly
   - Use separate kubeconfig for production

2. **Namespace Isolation**
   - Each deployment uses unique namespace (dev)
   - Network policies restrict communication
   - Resource quotas prevent overconsumption

3. **RBAC**
   - Service accounts with minimal permissions
   - Role-based access control
   - Regular audit of permissions

## Performance Optimization

The workflow uses several optimization techniques:

1. **Docker Layer Caching**
   - Subsequent builds are faster
   - Uses GitHub Actions cache

2. **Parallel Jobs**
   - Backend and frontend deploy in parallel
   - Smoke tests run concurrently

3. **Resource Limits**
   - Set in deployment manifests
   - Prevent resource exhaustion

## Advanced Usage

### Blue-Green Deployment

Modify workflow to support blue-green:

```yaml
- name: Deploy Green
  run: |
    envsubst < k8s/backend-deployment.yaml | \
      sed 's/name: backend/name: backend-green/' | \
      kubectl apply -f -

- name: Switch Traffic
  run: |
    kubectl patch svc backend -p '{"spec":{"selector":{"app":"backend-green"}}}'
```

### Canary Deployment

Implement gradual rollout:

```yaml
- name: Deploy Canary
  run: |
    kubectl scale deployment/backend --replicas=1 -n production
    # Monitor canary before full rollout
```

## Support

For issues or questions:

1. Check workflow run logs in Actions tab
2. Review this guide
3. Check `.claude/rules/devops-troubleshooting-playbook.md`
4. Contact DevOps team

## Changelog

### v1.0.0 (2024-02-14)
- Initial enhanced deployment workflow
- Multi-environment support
- Automated smoke tests and rollback
- Health monitoring and notifications
- Debug steps on failure
