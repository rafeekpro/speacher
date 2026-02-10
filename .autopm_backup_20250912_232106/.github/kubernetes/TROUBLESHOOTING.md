# GitHub Actions Kubernetes Runner Troubleshooting Guide

## Common Issues and Solutions

### 1. Permission Denied Errors

#### Error: "namespaces is forbidden"
```
Error from server (Forbidden): namespaces is forbidden: 
User "system:serviceaccount:github-runner:default" cannot create resource "namespaces"
```

**Solution:**
- This error occurs when trying to create namespaces without cluster-level permissions
- The updated CI workflow now uses the `github-runner` namespace instead of creating new ones
- If you need namespace creation, apply the ClusterRole in `rbac-runner-permissions.yaml`

#### Error: "pods is forbidden"
```
Error from server (Forbidden): pods "mongodb-xxx" is forbidden:
User "system:serviceaccount:github-runner:default" cannot create resource "pods"
```

**Solution:**
1. Apply the RBAC configuration:
   ```bash
   kubectl apply -f .github/kubernetes/rbac-runner-permissions.yaml
   ```

2. Verify permissions:
   ```bash
   kubectl auth can-i create pods --namespace=github-runner \
     --as=system:serviceaccount:github-runner:default
   ```

### 2. ConfigMap Size Limit Exceeded

#### Error: "ConfigMap too large"
```
error validating data: ConfigMap "build-context" is invalid: 
[]: Too long: must have at most 1048576 bytes
```

**Solution:**
- The updated workflow creates compressed archives instead of full directory ConfigMaps
- Source code is tar.gz compressed before creating ConfigMap
- Large files are excluded from the build context

### 3. Kaniko Build Failures

#### Error: "Kaniko build failed"
```
Error: kaniko build failed
kubectl logs job/kaniko-build-xxx --tail=50
```

**Common causes:
1. **Missing Dockerfile**: Ensure the Dockerfile path is correct
2. **Build context issues**: Check that source files are properly mounted
3. **Resource limits**: Increase memory/CPU limits if build is complex

**Solution:**
- The updated workflow includes fallback to Docker if Kaniko fails
- Provides better error messages and logs
- Uses init containers to properly extract source archives

### 4. MongoDB Connection Issues

#### Error: "MongoDB not accessible"
```
Failed to connect to MongoDB on attempt 1
MongoDB not accessible on localhost:27017
```

**Solutions:**
1. **Port forwarding issues**: The workflow now includes retry logic
2. **Pod not ready**: Increased wait timeout to 60 seconds
3. **Network policies**: Check if NetworkPolicies are blocking connections

### 5. Runner Configuration Issues

#### Error: "No runner matching labels"
```
Waiting for a runner to pick up this job...
Job was cancelled while waiting for a runner
```

**Solution:**
Ensure your runners have the correct labels:
```yaml
runs-on: [self-hosted, linux, x64, kubernetes]
```

### 6. Debugging Commands

#### Check runner pods:
```bash
kubectl get pods -n github-runner
kubectl logs <runner-pod-name> -n github-runner
```

#### Check service account permissions:
```bash
# List all permissions for the service account
kubectl auth can-i --list --namespace=github-runner \
  --as=system:serviceaccount:github-runner:default
```

#### Monitor job execution:
```bash
# Watch CI jobs
kubectl get jobs -n github-runner -w

# Get job logs
kubectl logs job/<job-name> -n github-runner
```

#### Clean up stuck resources:
```bash
# Delete all CI resources older than 1 hour
kubectl delete pods,jobs,configmaps -n github-runner \
  --field-selector metadata.creationTimestamp<$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)
```

## Workflow Features

### Automatic Fallbacks

The updated CI workflow includes multiple fallback mechanisms:

1. **Permission fallbacks**:
   - Falls back to `github-runner` namespace if cannot create namespaces
   - Falls back to Docker if Kaniko cannot be used
   - Skips MongoDB tests if pods cannot be created

2. **Build fallbacks**:
   - Tries Kaniko first
   - Falls back to Docker if available
   - Skips container build if neither is available

3. **Test fallbacks**:
   - Runs containerized tests if image available
   - Falls back to direct Python execution
   - Runs unit tests only if MongoDB unavailable

### Resource Cleanup

The workflow automatically cleans up:
- Kubernetes pods after test completion
- ConfigMaps after builds
- Port-forward processes
- Temporary files

### Monitoring

Check workflow execution in GitHub Actions:
1. Go to Actions tab in your repository
2. Click on the failing workflow run
3. Expand the failed job to see detailed logs
4. Look for "🔍 Checking Kubernetes permissions" to see what's available

## Quick Fixes

### Minimal permissions (no namespace creation):
```bash
# Remove ClusterRole sections from rbac-runner-permissions.yaml
# Only keep Role and RoleBinding for github-runner namespace
kubectl apply -f rbac-runner-permissions.yaml
```

### Full permissions (development only):
```bash
# Grant cluster-admin to runner (NOT for production!)
kubectl create clusterrolebinding github-runner-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=github-runner:default
```

### Reset and start fresh:
```bash
# Delete everything and start over
kubectl delete namespace github-runner
kubectl create namespace github-runner
kubectl apply -f .github/kubernetes/rbac-runner-permissions.yaml
```

## Support

For additional help:
1. Check the GitHub Actions logs for detailed error messages
2. Review the Kubernetes events: `kubectl get events -n github-runner`
3. Check runner pod logs: `kubectl logs -n github-runner <runner-pod>`
4. Open an issue with the error message and workflow configuration