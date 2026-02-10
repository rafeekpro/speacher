# GitHub Runner RBAC Setup Guide

## Overview

This guide sets up proper RBAC permissions for GitHub Actions runners in the `github-runner` namespace, enabling the hybrid Kubernetes approach where runners orchestrate container builds and tests without having container runtimes installed.

## Quick Start

```bash
# Deploy RBAC configuration
./scripts/setup-github-runner-rbac.sh

# Or verify existing deployment
./scripts/setup-github-runner-rbac.sh verify
```

## Architecture

### Hybrid Kubernetes Approach
- **GitHub Runners**: Orchestrate jobs via kubectl
- **Kubernetes Cluster**: Executes container builds and tests
- **No Container Runtime**: Runners don't need Docker/nerdctl
- **Security**: Minimal RBAC permissions following least-privilege

### Components Created
1. **Namespace**: `github-runner`
2. **ServiceAccount**: `github-runner`
3. **Role**: Minimal permissions for CI/CD operations
4. **RoleBinding**: Links ServiceAccount to Role
5. **NetworkPolicy**: Security isolation
6. **ResourceQuota**: Prevents resource exhaustion
7. **LimitRange**: Default resource limits

## Permissions Granted

### Core Permissions
- ✅ **Jobs**: Create, get, list, watch, delete (for Kaniko builds)
- ✅ **Pods**: Create, get, list, watch, delete (for test execution)
- ✅ **Pod Logs**: Get, list (for CI output)
- ✅ **Port Forward**: Create, get (for debugging)
- ✅ **ConfigMaps**: Full CRUD (for build context)
- ✅ **Secrets**: Get, list (for registry credentials)
- ✅ **Services**: Create, get, list, delete (for temporary services)
- ✅ **PVCs**: Create, get, list, delete (for build caches)
- ✅ **Events**: Get, list (for debugging)

### Denied Permissions
- ❌ **Deployments**: Not needed for CI/CD jobs
- ❌ **Nodes**: No cluster-level access
- ❌ **Namespaces**: No cross-namespace access
- ❌ **ClusterRoles**: No cluster-level RBAC changes

## Usage in GitHub Actions

### 1. Kaniko Container Build

```yaml
name: Build Container
on: [push, pull_request]

jobs:
  build:
    runs-on: self-hosted
    steps:
    - uses: actions/checkout@v4
    
    - name: Build with Kaniko
      run: |
        # Create unique job name with run ID
        JOB_NAME="kaniko-build-${{ github.run_id }}"
        
        # Create Kaniko job
        kubectl create job $JOB_NAME \
          --image=gcr.io/kaniko-project/executor:v1.9.0 \
          --serviceaccount=github-runner \
          -n github-runner \
          -- --context=git://github.com/${{ github.repository }}.git#${{ github.sha }} \
          --dockerfile=Dockerfile \
          --destination=myregistry/myapp:${{ github.sha }} \
          --cache=true
        
        # Wait for completion
        kubectl wait --for=condition=complete job/$JOB_NAME \
          -n github-runner --timeout=600s
        
        # Get logs
        kubectl logs job/$JOB_NAME -n github-runner
        
        # Cleanup
        kubectl delete job/$JOB_NAME -n github-runner
```

### 2. Test Execution

```yaml
- name: Run Tests
  run: |
    JOB_NAME="test-${{ github.run_id }}"
    
    kubectl create job $JOB_NAME \
      --image=node:18 \
      --serviceaccount=github-runner \
      -n github-runner \
      -- npm test
    
    kubectl wait --for=condition=complete job/$JOB_NAME \
      -n github-runner --timeout=300s
    
    kubectl logs job/$JOB_NAME -n github-runner
    kubectl delete job/$JOB_NAME -n github-runner
```

### 3. Multi-Stage Pipeline

```yaml
- name: Multi-Stage Build
  run: |
    RUN_ID="${{ github.run_id }}"
    
    # Frontend build
    kubectl create job frontend-$RUN_ID \
      --image=node:18 \
      --serviceaccount=github-runner \
      -n github-runner \
      -- sh -c "npm ci && npm run build"
    
    # Backend build with Kaniko
    kubectl create job backend-$RUN_ID \
      --image=gcr.io/kaniko-project/executor:v1.9.0 \
      --serviceaccount=github-runner \
      -n github-runner \
      -- --context=git://github.com/${{ github.repository }}.git#${{ github.sha }} \
      --dockerfile=backend/Dockerfile \
      --destination=myregistry/backend:${{ github.sha }}
    
    # Wait for both
    kubectl wait --for=condition=complete \
      job/frontend-$RUN_ID job/backend-$RUN_ID \
      -n github-runner --timeout=600s
    
    # Get logs from both
    kubectl logs job/frontend-$RUN_ID -n github-runner
    kubectl logs job/backend-$RUN_ID -n github-runner
    
    # Cleanup
    kubectl delete job frontend-$RUN_ID backend-$RUN_ID -n github-runner
```

## Security Features

### Least-Privilege Principle
- Only necessary permissions granted
- Namespace-scoped permissions only
- No cluster-level access

### Network Isolation
- NetworkPolicy restricts pod-to-pod communication
- Only allows egress to API server, registries, and DNS

### Resource Protection
- ResourceQuota prevents resource exhaustion
- LimitRange sets default resource limits
- TTL cleanup for completed jobs

## Verification Commands

```bash
# Check namespace
kubectl get namespace github-runner

# Verify ServiceAccount
kubectl get serviceaccount github-runner -n github-runner

# Test specific permissions
kubectl auth can-i create jobs \
  --as=system:serviceaccount:github-runner:github-runner \
  -n github-runner

kubectl auth can-i get pods/log \
  --as=system:serviceaccount:github-runner:github-runner \
  -n github-runner

kubectl auth can-i create pods/portforward \
  --as=system:serviceaccount:github-runner:github-runner \
  -n github-runner

# Should fail (negative test)
kubectl auth can-i get nodes \
  --as=system:serviceaccount:github-runner:github-runner \
  -n github-runner
```

## Troubleshooting

### Permission Denied Errors

```bash
# Check if ServiceAccount exists
kubectl get sa github-runner -n github-runner

# Verify RoleBinding
kubectl describe rolebinding github-runner -n github-runner

# Check Role permissions
kubectl describe role github-runner -n github-runner
```

### Job Creation Issues

```bash
# Check ResourceQuota usage
kubectl describe quota github-runner-quota -n github-runner

# Check LimitRange settings
kubectl describe limitrange github-runner-limits -n github-runner

# Check for failed jobs
kubectl get jobs -n github-runner --field-selector status.successful!=1
```

### Port Forward Issues

```bash
# Verify port-forward permissions
kubectl auth can-i create pods/portforward \
  --as=system:serviceaccount:github-runner:github-runner \
  -n github-runner

# Check if pod is running
kubectl get pods -n github-runner
```

## Maintenance

### Regular Security Review
- Review permissions quarterly
- Check for unused resources
- Update resource quotas based on usage

### Cleanup Old Resources
```bash
# Delete completed jobs older than 1 hour
kubectl delete jobs -n github-runner \
  --field-selector status.successful=1 \
  --field-selector metadata.creationTimestamp<$(date -d '1 hour ago' -Ins)
```

### Monitoring
- Monitor resource usage with ResourceQuota
- Track job success/failure rates
- Alert on permission denied errors

## Files Created

1. `k8s/github-runner-rbac.yml` - Complete RBAC configuration
2. `scripts/setup-github-runner-rbac.sh` - Deployment and verification script
3. `docs/github-runner-rbac-setup.md` - This documentation

## Migration from Old Setup

If migrating from the old `speecher-ci` namespace:

1. Deploy new RBAC configuration
2. Update GitHub Actions workflows to use `github-runner` namespace
3. Test thoroughly with new setup
4. Remove old `speecher-ci` resources when confident

## Support

For issues or questions:
1. Check verification commands above
2. Review GitHub Actions workflow logs
3. Check Kubernetes events: `kubectl get events -n github-runner`
4. Verify cluster connectivity and permissions