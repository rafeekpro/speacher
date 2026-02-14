# Docker Build Pipeline - Quick Reference

## Setup Commands

```bash
# Initial setup
./.github/scripts/setup-docker-build.sh

# Manual secret creation
kubectl create secret docker-registry docker-reg-secret \
  --namespace=github-runner \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  --docker-email=<email>

# Encode kubeconfig for GitHub secret
base64 -i ~/.kube/config
```

## Workflow Triggers

| Event | Branches | Paths |
|-------|----------|-------|
| Push | main, master | Dockerfile*, docker-compose*.yml |
| Pull Request | Any | Dockerfile*, docker-compose*.yml |
| Release | Any | v* tags |
| Manual | - | workflow_dispatch |

## Image Tags

```bash
# Production
ghcr.io/repo/image:abc123def        # SHA
ghcr.io/repo/image:main            # Branch
ghcr.io/repo/image:latest           # Latest (main only)
ghcr.io/repo/image:v1.2.3          # Semver (release)

# Development (if Dockerfile.dev exists)
ghcr.io/repo/image:dev-abc123def    # Dev SHA
ghcr.io/repo/image:dev-main         # Dev branch
```

## Build Platforms

| Event | Platforms |
|-------|-----------|
| Push/PR | linux/amd64 |
| Release | linux/amd64, linux/arm64 |

## Troubleshooting

| Issue | Command |
|-------|----------|
| Stuck job | `kubectl delete job kaniko-build-prod -n github-runner` |
| Secret error | `./.github/scripts/setup-docker-build.sh` |
| Build logs | `kubectl logs job/kaniko-build-prod -n github-runner -c kaniko` |
| Image list | `gh api /repos/owner/repo/packages?package_type=container` |

## GitHub Secrets Required

- `KUBECONFIG` - Base64 encoded kubeconfig

## GitHub Secrets Optional

- `REGISTRY` - Container registry (default: ghcr.io)
- `NAMESPACE` - K8s namespace (default: github-runner)

## Quick Links

- [Full Documentation](./DOCKER-BUILD-PIPELINE.md)
- [Workflow File](../.github/workflows/docker-build.yml)
- [Setup Script](../.github/scripts/setup-docker-build.sh)
