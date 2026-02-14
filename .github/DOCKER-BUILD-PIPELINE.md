# Docker Build Pipeline Documentation

## Overview

This repository implements a Kubernetes-native CI/CD pipeline for building Docker images using Kaniko. The GitHub Actions runner acts as an orchestrator, delegating all container operations to the Kubernetes cluster.

## Architecture

```
GitHub Actions (Orchestrator)
    ↓
Kubernetes Cluster (Builder)
    ↓
Kaniko Job (Image Builder)
    ↓
Container Registry (Storage)
```

## Quick Start

### 1. Prerequisites

- Kubernetes cluster with GitHub Actions runner
- `kubectl` configured with cluster access
- Container registry credentials (ghcr.io or custom)

### 2. Initial Setup

Run the setup script:

```bash
./.github/scripts/setup-docker-build.sh
```

This will:
- Check prerequisites (kubectl, cluster access)
- Create namespace (if needed)
- Configure Docker registry secret

### 3. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

**Required:**
- `KUBECONFIG` - Base64 encoded kubeconfig file
  ```bash
  base64 -i ~/.kube/config | pbcopy  # macOS
  base64 -i ~/.kube/config | xclip   # Linux
  ```

**Optional:**
- `REGISTRY` - Container registry URL (default: ghcr.io)
- `NAMESPACE` - Kubernetes namespace for builds (default: github-runner)

### 4. Trigger Build

The workflow runs automatically on:
- Push to main/master branch (Dockerfile changes)
- Pull requests (Dockerfile changes)
- Tag creation (v*)
- Manual trigger (workflow_dispatch)

## Workflow Stages

### 1. Prepare

Extracts build metadata:
- Checks for Dockerfile.dev
- Generates image tags (branch, SHA, semver)
- Determines target platforms (amd64, arm64)

### 2. Build Production

Creates Kaniko job in Kubernetes:
- Clones repository to init container
- Builds from Dockerfile
- Tags with SHA and branch name
- Uses layer caching for speed
- Pushes to registry

### 3. Build Development (optional)

If Dockerfile.dev exists:
- Builds development image
- Tags with `dev-` prefix
- Separate cache repository

### 4. Security Scan

Runs Trivy vulnerability scanner:
- Scans built image
- Generates SARIF report
- Posts results to GitHub Security
- Comments on PRs

### 5. Cleanup

Maintains registry hygiene:
- Lists all image tags
- Deletes old images (keeps last 10)
- Runs only on main branch

## Configuration

### Environment Variables

Edit `.github/workflows/docker-build.yml`:

```yaml
env:
  REGISTRY: ghcr.io                    # Container registry
  IMAGE_NAME: ${{ github.repository }} # Image name
  KUBECONFIG: /tmp/kubeconfig          # Kubeconfig path
  K8S_NAMESPACE: ci-${{ github.run_id }} # Unique namespace
  RETENTION_COUNT: 10                   # Images to keep
```

### Multi-Platform Builds

By default, builds are linux/amd64. For releases, builds both:

```yaml
- name: Determine build platforms
  run: |
    if [ "${{ github.event_name }}" == "release" ]; then
      echo "platforms=linux/amd64,linux/arm64"
    else
      echo "platforms=linux/amd64"
    fi
```

### Build Triggers

Customize in workflow YAML:

```yaml
on:
  push:
    branches: [main, master]
    paths:
      - 'Dockerfile*'
      - 'docker-compose*.yml'
  pull_request:
    paths:
      - 'Dockerfile*'
  workflow_dispatch:  # Manual trigger
  release:
    types: [created]
```

## Troubleshooting

### Job Fails with "field is immutable"

**Cause:** Old job resource exists in cluster

**Solution:** The workflow automatically deletes old jobs. If manual cleanup needed:

```bash
kubectl delete job kaniko-build-prod --namespace=github-runner
```

### Build fails with "ImagePullBackOff"

**Cause:** Kaniko executor image cannot be pulled

**Solution:** Check cluster has internet access or configure image pull secrets:

```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: docker-reg-secret
```

### Secret not found

**Cause:** Docker registry secret not configured

**Solution:** Run setup script:

```bash
./.github/scripts/setup-docker-build.sh
```

Or create manually:

```bash
kubectl create secret docker-registry docker-reg-secret \
  --namespace=github-runner \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  --docker-email=<email>
```

### Build is slow

**Cause:** Layer caching not configured or cache miss

**Solution:** Verify cache repository is accessible:

```bash
kubectl get pods --namespace=github-runner
kubectl logs <kaniko-pod> --container=kaniko | grep -i cache
```

## Best Practices

### 1. Layer Caching

The pipeline uses registry caching for speed. Ensure:
- Cache repository exists: `<image>-cache`
- Sufficient storage quota
- Proper permissions

### 2. Multi-Stage Builds

Optimize Dockerfile for Kaniko:

```dockerfile
# Bad: No cache mount points
FROM node:20-alpine
COPY . .
RUN npm install

# Good: Leverage layers
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build
```

### 3. Security Scanning

Configure Trivy severity levels:

```yaml
- uses: aquasecurity/trivy-action@master
  with:
    severity: 'CRITICAL,HIGH'
    exit-code: '1'  # Fail on findings
```

### 4. Image Retention

Adjust retention count based on:
- Registry storage limits
- Release frequency
- Rollback requirements

## Advanced Usage

### Custom Registry

For non-GitHub registries:

```yaml
env:
  REGISTRY: gcr.io/my-project
  IMAGE_NAME: my-app
```

Update secret creation:

```bash
kubectl create secret docker-registry docker-reg-secret \
  --docker-server=gcr.io \
  --docker-username=_json_key \
  --docker-password="$(cat key.json)" \
  --docker-email=dev@example.com
```

### Build Args

Pass build arguments to Kaniko:

```yaml
args:
  - --dockerfile=/workspace/Dockerfile
  - --context=dir:///workspace
  - --build-arg NODE_ENV=production
  - --build-arg VERSION=${{ github.sha }}
  - --destination=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

### Private Dependencies

If Dockerfile requires private packages:

```yaml
initContainers:
- name: prepare-context
  image: alpine/git:latest
  command:
    - sh
    - -c
  - |
    git clone --depth 1 https://github.com/${{ github.repository }}.git /workspace
    cd /workspace && git checkout ${{ github.sha }}
  volumeMounts:
    - name: workspace
      mountPath: /workspace
    - name: ssh-key
      mountPath: /root/.ssh
  volumes:
  - name: workspace
    emptyDir: {}
  - name: ssh-key
    secret:
      secretName: github-ssh-key
      defaultMode: 0400
```

## Monitoring

### View Build Logs

```bash
# Get Kaniko pod name
POD=$(kubectl get pods --namespace=github-runner --selector=job-name=kaniko-build-prod -o jsonpath='{.items[0].metadata.name}')

# Follow logs
kubectl logs -f $POD --namespace=github-runner --container=kaniko
```

### Check Job Status

```bash
kubectl get jobs --namespace=github-runner
kubectl describe job kaniko-build-prod --namespace=github-runner
```

### View Security Results

Results are posted to:
- GitHub Security tab (SARIF)
- PR comments (for pull requests)
- Workflow logs (Trivy output)

## References

- [Kaniko Documentation](https://github.com/GoogleContainerTools/kaniko)
- [Trivy Scanner](https://aquasecurity.github.io/trivy/)
- [GitHub Actions Security](https://docs.github.com/en/code-security/securing-your-software-supply-chain)
- [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
