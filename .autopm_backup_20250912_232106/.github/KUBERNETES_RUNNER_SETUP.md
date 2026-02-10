# Kubernetes Runner Configuration

This document explains the GitHub Actions workflow configuration for self-hosted Kubernetes runners.

## Overview

The workflows have been updated to work with self-hosted Kubernetes runners instead of requiring Docker daemon or AWS CLI dependencies.

## Runner Configuration

### Runner Labels

All workflows now use the standardized runner configuration:

```yaml
runs-on: [self-hosted, linux, x64, kubernetes]
```

**Exception**: Playwright E2E tests still use `[self-hosted, playwright, e2e]` as they require specialized setup.

### Updated Workflows

The following workflow files have been updated:

- `.github/workflows/ci.yml` - Main CI/CD pipeline
- `.github/workflows/ci-k3s.yml` - K3s specific workflow  
- `.github/workflows/pr-checks.yml` - Pull request validation
- `.github/workflows/test-*.yml` - Various test workflows
- `.github/workflows/frontend-v2-pr.yml` - Frontend PR checks

## Required Tools

### Essential (Must be installed)

- **kubectl** - Kubernetes command-line tool
- **python3** - Python runtime
- **node** - Node.js runtime  
- **npm** - Node package manager
- **nerdctl** OR **docker** - Container runtime CLI

### Optional (Gracefully handled if missing)

- **aws** - AWS CLI
- **az** - Azure CLI  
- **gcloud** - Google Cloud CLI
- **terraform** - Infrastructure as code
- **gh** - GitHub CLI

## Container Runtime

Workflows support both:

1. **nerdctl** (preferred for Kubernetes) - Uses containerd directly
2. **docker** (legacy) - Requires Docker daemon

The workflows automatically detect which is available and use the appropriate commands.

## Kubernetes Integration

### Service Deployment

Instead of Docker Compose services, workflows use Kubernetes pods:

```yaml
# Deploy MongoDB for tests
kubectl run mongodb-test --image=mongo:6.0 --port=27017 --env="MONGO_INITDB_ROOT_USERNAME=root"
kubectl wait --for=condition=ready pod/mongodb-test --timeout=60s
kubectl port-forward pod/mongodb-test 27017:27017 &
```

### Namespace Isolation

Each workflow run uses isolated namespaces:

```yaml
env:
  KUBE_NAMESPACE: 'ci-${{ github.run_id }}'
```

This prevents conflicts between parallel runs.

### Cleanup

Workflows automatically clean up resources:

```yaml
- name: Cleanup
  if: always()
  run: |
    kubectl delete namespace ${{ env.KUBE_NAMESPACE }} --ignore-not-found=true
```

## Validation

Use the validation script to check runner readiness:

```bash
./.github/scripts/validate-k8s-runner.sh
```

This script verifies:

- Required tools are installed
- Container runtime is working
- Kubernetes cluster is accessible
- Can create and manage K8s resources

## Migration Notes

### From Docker Compose

Services that were previously defined in workflow `services:` section are now deployed as Kubernetes pods in workflow steps.

### From containerd Labels

Changed from `[self-hosted, containerd]` to `[self-hosted, linux, x64, kubernetes]` for better specificity.

### Cloud CLI Dependencies

Cloud CLI tools (aws, az, gcloud) are now optional. Workflows will continue with warnings if these tools are missing, rather than failing.

## Troubleshooting

### Common Issues

1. **kubectl not found**
   ```bash
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   ```

2. **nerdctl permissions**
   ```bash
   # Add user to containerd group (if exists)
   sudo usermod -aG containerd $USER
   
   # Or configure sudoless access
   echo "$USER ALL=(ALL) NOPASSWD: /usr/local/bin/nerdctl" | sudo tee /etc/sudoers.d/nerdctl
   ```

3. **Cluster access**
   ```bash
   # Verify kubectl config
   kubectl config current-context
   kubectl cluster-info
   ```

### Validation Failure

If `validate-k8s-runner.sh` fails, address the specific issues reported:

- Install missing required tools
- Configure container runtime access
- Fix Kubernetes cluster connectivity
- Verify namespace creation permissions

## Best Practices

1. **Resource Limits**: Set appropriate resource limits in pod specs
2. **Cleanup**: Always clean up test resources in `if: always()` steps
3. **Namespaces**: Use unique namespaces per workflow run
4. **Error Handling**: Make optional tools truly optional with `|| true`
5. **Timeouts**: Set reasonable timeouts for Kubernetes operations

## Future Enhancements

- Helm chart deployments for complex applications
- ArgoCD integration for GitOps workflows  
- Multi-cluster support for staging/production separation
- Resource quotas and limits management
- Monitoring and alerting integration