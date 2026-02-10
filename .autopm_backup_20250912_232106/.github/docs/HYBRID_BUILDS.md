# Hybrid Kubernetes Container Builds

This document describes the hybrid approach for container builds in GitHub Actions workflows, replacing `nerdctl` commands with Kubernetes-native Kaniko builds.

## 🎯 Overview

**Problem**: GitHub Actions workflows were attempting to use `nerdctl build` commands on runners, but nerdctl was not installed and shouldn't be required on runners.

**Solution**: Hybrid Kubernetes approach where:
- **Runners**: Only orchestrate workflows (no container tools needed)
- **Kubernetes Jobs**: Handle all container builds using Kaniko
- **Image Storage**: Use Kubernetes-native image storage accessible to both build and deploy phases

## 🏗️ Architecture

```
GitHub Actions Runner
├── Orchestrate workflow
├── Create Kubernetes namespace
├── Create build context ConfigMap
├── Submit Kaniko build job
├── Wait for completion
└── Clean up resources

Kubernetes Cluster
├── Execute Kaniko build jobs
├── Store images in containerd
├── Provide image caching
└── Handle resource management
```

## 🔄 Changes Made

### 1. Workflow Updates

**Before (nerdctl approach):**
```yaml
- name: Build Backend Image with nerdctl
  run: |
    nerdctl build -t speecher-backend:ci-${{ github.run_id }} .
```

**After (Kaniko approach):**
```yaml
- name: Build Backend Image with Kaniko
  run: |
    # Create build namespace
    kubectl create namespace container-build-${{ github.run_id }} || true
    
    # Create build context
    kubectl create configmap backend-build-context \
      --from-file=. \
      --namespace=container-build-${{ github.run_id }}
    
    # Submit Kaniko build job
    kubectl apply -f - <<EOF
    apiVersion: batch/v1
    kind: Job
    metadata:
      name: backend-build
      namespace: container-build-${{ github.run_id }}
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
          - name: kaniko
            image: gcr.io/kaniko-project/executor:latest
            args:
            - --dockerfile=/workspace/Dockerfile
            - --context=/workspace
            - --destination=speecher-backend:ci-${{ github.run_id }}
            - --cache=true
    EOF
```

### 2. Files Updated

- **`.github/workflows/ci.yml`** - Main CI/CD pipeline
- **`.github/workflows/ci-k3s.yml`** - K3s-specific pipeline  
- **`.github/workflows/pr-checks.yml`** - Pull request checks
- **`.github/workflows/frontend-v2-pr.yml`** - Frontend PR checks

### 3. New Utilities Created

- **`.github/templates/kaniko-build-job.yml`** - Reusable Kaniko job template
- **`.github/scripts/kaniko-build.sh`** - Standardized Kaniko build script
- **`.github/scripts/hybrid-build-wrapper.sh`** - Fallback mechanism wrapper
- **`.github/scripts/test-hybrid-builds.sh`** - Test suite for validation

## 🚀 Usage

### Basic Kaniko Build

```bash
# Using the reusable script
.github/scripts/kaniko-build.sh \
  --namespace build-123 \
  --job-name backend-build \
  --image myapp:latest \
  --context build-context \
  --dockerfile /workspace/Dockerfile
```

### Hybrid Build with Fallbacks

```bash
# Auto-detect best build method
.github/scripts/hybrid-build-wrapper.sh auto Dockerfile myapp:latest .

# Force specific build method
.github/scripts/hybrid-build-wrapper.sh kaniko Dockerfile myapp:latest .
```

### Template-based Build

```yaml
# Use the template and replace placeholders
sed -e 's/{{JOB_NAME}}/my-build/' \
    -e 's/{{NAMESPACE}}/my-namespace/' \
    -e 's/{{DESTINATION_IMAGE}}/my-image:tag/' \
    .github/templates/kaniko-build-job.yml | kubectl apply -f -
```

## ✅ Benefits

### 1. **No Container Tools on Runners**
- Runners don't need Docker, nerdctl, or BuildKit installed
- Simpler runner setup and maintenance
- Better security isolation

### 2. **Kubernetes-Native Builds**
- Leverages cluster's container runtime
- Better resource management and scheduling
- Native image caching within cluster

### 3. **Improved Reliability**
- Proper error handling and logging
- Automatic cleanup of build resources
- Fallback mechanisms for different scenarios

### 4. **Better Security**
- Builds run in isolated Kubernetes namespaces
- No privileged access required on runners
- Secure image storage within cluster

### 5. **Scalability**
- Multiple builds can run in parallel
- Kubernetes handles resource allocation
- Better build performance with cluster resources

## 🛠️ Configuration

### Environment Variables

- `KUBE_NAMESPACE` - Base namespace for builds (auto-generated if not set)
- `BUILD_TIMEOUT` - Build timeout in seconds (default: 600)
- `KANIKO_IMAGE` - Kaniko executor image (default: gcr.io/kaniko-project/executor:latest)

### Resource Limits

Default resource allocation per build:
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### Caching

Kaniko builds use automatic caching:
- `--cache=true` enables layer caching
- `--cache-ttl=24h` sets cache expiration
- Optional `--cache-repo` for shared cache repository

## 🧪 Testing

Run the comprehensive test suite:

```bash
# From repository root
.github/scripts/test-hybrid-builds.sh

# With verbose output
HYBRID_BUILD_VERBOSE=true .github/scripts/test-hybrid-builds.sh
```

### Test Coverage

1. ✅ Kubernetes cluster accessibility
2. ✅ Kaniko image availability
3. ✅ Namespace creation and cleanup
4. ✅ Build context ConfigMap creation
5. ✅ Kaniko build job execution
6. ✅ Build log verification
7. ✅ Script functionality
8. ✅ Fallback mechanisms
9. ✅ Workflow YAML syntax
10. ✅ Complete nerdctl removal

## 🔧 Troubleshooting

### Common Issues

#### 1. Build Namespace Creation Failed
```bash
Error: failed to create namespace
```
**Solution**: Check Kubernetes cluster access and permissions

#### 2. Kaniko Job Timeout
```bash
Error: build failed or timed out
```
**Solutions**:
- Increase timeout: `--timeout 900`
- Check cluster resources: `kubectl top nodes`
- Review build logs: `kubectl logs job/build-name -n namespace`

#### 3. Build Context Too Large
```bash
Error: configmap too large
```
**Solutions**:
- Add `.dockerignore` file to reduce context size
- Use multi-stage builds to minimize context
- Consider using persistent volumes for large contexts

#### 4. Image Not Found After Build
```bash
Error: image not available for deployment
```
**Solutions**:
- Verify image was built: `kubectl get job -n build-namespace`
- Check build logs for errors
- Ensure image name matches exactly

### Debug Commands

```bash
# Check build job status
kubectl get jobs -n build-namespace

# View build logs
kubectl logs job/build-job-name -n build-namespace

# Inspect build pod
kubectl describe pod -l job-name=build-job-name -n build-namespace

# Check available images in cluster
kubectl get nodes -o jsonpath='{.items[0].status.images[*].names[*]}'
```

## 📈 Performance

### Build Times

Typical build times with Kaniko:
- **Simple Alpine-based**: 30-60 seconds
- **Node.js application**: 2-5 minutes  
- **Python application**: 3-7 minutes
- **Multi-stage builds**: 5-15 minutes

### Optimization Tips

1. **Use build cache**: Always enable `--cache=true`
2. **Optimize Dockerfile**: Use multi-stage builds, combine RUN commands
3. **Minimize context**: Use `.dockerignore` effectively
4. **Resource allocation**: Increase CPU/memory for faster builds
5. **Parallel builds**: Use different namespaces for concurrent builds

## 🔒 Security Considerations

### Best Practices

1. **Namespace Isolation**: Each build runs in its own namespace
2. **Resource Limits**: Prevent resource exhaustion attacks
3. **Security Context**: Kaniko runs as non-root user
4. **Image Scanning**: Integrate with security scanners
5. **Access Control**: Use RBAC for build permissions

### Security Features

```yaml
securityContext:
  runAsUser: 1000
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

## 🚦 Migration Guide

### For Existing Workflows

1. **Backup existing workflows**
2. **Update build steps** to use Kaniko approach
3. **Test thoroughly** in development environment
4. **Validate image availability** after builds
5. **Update deployment scripts** if necessary

### Breaking Changes

- **nerdctl commands removed** - Use Kaniko jobs instead
- **Different image storage** - Images stored in cluster containerd
- **Namespace cleanup** - Temporary build namespaces are auto-deleted
- **Resource requirements** - Builds now require Kubernetes cluster access

## 📋 Checklists

### Pre-Migration Checklist

- [ ] Kubernetes cluster is accessible from runners
- [ ] Kaniko executor image is available
- [ ] Sufficient cluster resources for builds
- [ ] Proper RBAC permissions configured
- [ ] Network policies allow build traffic
- [ ] Image registry configured (if using external registry)

### Post-Migration Checklist

- [ ] All workflows updated and tested
- [ ] nerdctl references completely removed
- [ ] Build times are acceptable
- [ ] Images are properly cached
- [ ] Cleanup processes work correctly
- [ ] Error handling functions properly
- [ ] Documentation updated

## 🔮 Future Enhancements

### Planned Improvements

1. **Registry Integration**: Push images to external registries
2. **Build Optimization**: Advanced caching strategies
3. **Monitoring**: Build metrics and alerting
4. **Multi-Architecture**: ARM and AMD64 builds
5. **GitOps Integration**: Automated deployment triggers

### Potential Features

- **Build notifications** via Slack/Teams
- **Artifact signing** with cosign
- **SBOM generation** for security compliance
- **Build analytics** and performance metrics
- **Custom builder images** for specialized builds

## 📞 Support

### Getting Help

1. **Check logs**: Review Kaniko job logs for errors
2. **Run tests**: Execute the test suite to validate setup
3. **Review documentation**: Check this guide and Kaniko docs
4. **Use fallbacks**: Try different build methods if needed

### Contributing

To improve the hybrid build system:

1. **Test thoroughly** with your use cases
2. **Report issues** with detailed logs
3. **Submit improvements** via pull requests
4. **Update documentation** for new features

---

*This hybrid approach ensures reliable, scalable, and secure container builds without requiring container tools on GitHub Actions runners.*