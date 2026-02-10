# GitHub Actions Self-Hosted Runner Setup with Containerd/K3s

## Table of Contents
- [Overview](#overview)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Using the Setup Script](#using-the-setup-script)
- [Manual Configuration](#manual-configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Overview

This guide documents how to set up GitHub Actions self-hosted runners in a K3s/containerd environment, ensuring compatibility with workflows that expect Docker commands while leveraging the containerd runtime.

## The Problem

GitHub Actions workflows commonly use Docker commands for:
- Building container images
- Running containers for testing
- Using container-based actions
- Security scanning with tools like Trivy

However, K3s uses **containerd** as its container runtime, not Docker. This creates a compatibility issue:

```bash
# What workflows expect (Docker)
docker build -t myapp .
docker run --rm myapp

# What K3s provides (containerd via nerdctl)
nerdctl build -t myapp .
nerdctl run --rm myapp
```

Many GitHub Actions and workflows are hardcoded to use `docker` commands, making them incompatible with pure containerd environments.

## The Solution

We solve this by creating a **symbolic link** from `docker` to `nerdctl`, which provides Docker-compatible commands for containerd:

```bash
# Create symlink
sudo ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker

# Now docker commands work with containerd
docker build -t myapp .  # Actually runs nerdctl
docker run --rm myapp    # Actually runs nerdctl
```

This approach provides:
- ✅ **Full compatibility** with existing GitHub Actions workflows
- ✅ **No workflow modifications** required
- ✅ **Native containerd performance** without Docker overhead
- ✅ **Seamless integration** with K3s container runtime

## Prerequisites

Before setting up the runner, ensure you have:

1. **K3s Cluster**: A working K3s installation
2. **Runner Machine**: Ubuntu 20.04+ or similar Linux distribution
3. **Sudo Access**: Required for system-level installations
4. **Internet Access**: For downloading dependencies
5. **GitHub Token**: For registering the runner

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 20GB+ free space
- **Network**: Stable internet connection

## Installation Steps

### Step 1: Install K3s (if not already installed)

```bash
# Install K3s with default configuration
curl -sfL https://get.k3s.io | sh -

# Verify K3s installation
sudo k3s kubectl get nodes
```

### Step 2: Run the Comprehensive Setup Script

We provide a complete setup script that installs all dependencies:

```bash
# Download and run the setup script
curl -O https://raw.githubusercontent.com/your-repo/speecher/main/scripts/setup-containerd-runner.sh
chmod +x setup-containerd-runner.sh
./setup-containerd-runner.sh
```

### Step 3: Create Docker Symlink

After running the setup script, create the Docker symlink:

```bash
# Create the docker -> nerdctl symlink
sudo ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker

# Verify the symlink
ls -la /usr/local/bin/docker
# Should show: /usr/local/bin/docker -> /usr/local/bin/nerdctl

# Test docker commands
docker --version
docker run --rm hello-world
```

### Step 4: Install GitHub Actions Runner

```bash
# Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download latest runner
curl -O -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure runner (requires GitHub token)
./config.sh --url https://github.com/your-org/your-repo \
  --token YOUR_RUNNER_TOKEN \
  --labels "self-hosted,containerd,Linux,x64" \
  --name "k3s-runner-1"

# Install and start as service
sudo ./svc.sh install
sudo ./svc.sh start

# Check service status
sudo ./svc.sh status
```

## Using the Setup Script

The `setup-containerd-runner.sh` script automates the installation of all required dependencies:

### What the Script Installs

1. **System Dependencies**
   - Build tools (gcc, make, etc.)
   - Development libraries
   - Package management tools

2. **Python Environment**
   - Python 3.11
   - pip package manager
   - Testing tools (pytest, coverage)
   - Linters (black, flake8, mypy)

3. **Node.js Environment**
   - Node.js 18.x and 20.x via nvm
   - npm package manager
   - Global npm packages

4. **Container Tools**
   - nerdctl (Docker-compatible CLI for containerd)
   - buildkit for container builds
   - kubectl for Kubernetes management

5. **Testing Tools**
   - Playwright browsers
   - MongoDB client tools
   - Trivy security scanner

6. **Development Tools**
   - GitHub CLI
   - Code formatters
   - Debugging utilities

### Running the Script

```bash
# Make script executable
chmod +x scripts/setup-containerd-runner.sh

# Run the setup script (as non-root user with sudo access)
./scripts/setup-containerd-runner.sh

# The script will:
# 1. Detect your OS
# 2. Update system packages
# 3. Install all dependencies
# 4. Configure environment variables
# 5. Verify installations
```

### Script Output

The script provides colored output showing progress:
- 🔵 **[INFO]** - Information messages
- 🟢 **[SUCCESS]** - Successful operations
- 🟡 **[WARNING]** - Non-critical issues
- 🔴 **[ERROR]** - Critical failures

## Manual Configuration

If you prefer manual setup or need to customize the installation:

### 1. Install nerdctl

```bash
# Download nerdctl
NERDCTL_VERSION="1.7.1"
wget -O nerdctl.tar.gz \
  "https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-full-${NERDCTL_VERSION}-linux-amd64.tar.gz"

# Extract to /usr/local
sudo tar -xzf nerdctl.tar.gz -C /usr/local/

# Verify installation
nerdctl --version
```

### 2. Configure buildkit

```bash
# Create buildkit service
sudo tee /etc/systemd/system/buildkit.service > /dev/null <<EOF
[Unit]
Description=BuildKit
After=containerd.service
Requires=containerd.service

[Service]
ExecStart=/usr/local/bin/buildkitd --oci-worker=false --containerd-worker=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start buildkit
sudo systemctl daemon-reload
sudo systemctl enable buildkit
sudo systemctl start buildkit
```

### 3. Create Docker Symlink

```bash
# Create symlink
sudo ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker

# Add to PATH if needed
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Configure Containerd Namespace

```bash
# Set K3s containerd namespace
echo 'export CONTAINERD_NAMESPACE=k8s.io' >> ~/.bashrc
source ~/.bashrc
```

## Verification

### Using the Test Workflow

We provide a test workflow to verify the runner setup:

```bash
# Trigger the test workflow
gh workflow run test-docker-symlink.yml

# Or push changes to trigger automatically
git add .github/workflows/test-docker-symlink.yml
git commit -m "Test runner setup"
git push
```

The test workflow (`test-docker-symlink.yml`) verifies:
- ✅ Docker command availability
- ✅ Nerdctl command availability
- ✅ Symlink configuration
- ✅ Container runtime functionality
- ✅ Image pull and run operations
- ✅ Kubectl availability

### Manual Verification

Run these commands on the runner machine:

```bash
# 1. Check docker symlink
ls -la /usr/local/bin/docker
# Expected: /usr/local/bin/docker -> /usr/local/bin/nerdctl

# 2. Test docker commands
docker --version
docker run --rm hello-world
docker pull alpine:latest
docker images

# 3. Test build capabilities
echo "FROM alpine:latest" > Dockerfile.test
docker build -f Dockerfile.test -t test:latest .
docker run --rm test:latest echo "Build test successful"
rm Dockerfile.test

# 4. Check containerd
sudo crictl --runtime-endpoint unix:///run/k3s/containerd/containerd.sock ps

# 5. Verify runner service
sudo systemctl status actions.runner.*.service
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Docker Command Not Found

**Problem**: `docker: command not found`

**Solution**:
```bash
# Check if symlink exists
ls -la /usr/local/bin/docker

# Recreate if missing
sudo ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker

# Ensure /usr/local/bin is in PATH
echo $PATH
export PATH="/usr/local/bin:$PATH"
```

#### 2. Permission Denied Errors

**Problem**: `permission denied while trying to connect to the Docker daemon`

**Solution**:
```bash
# Add user to appropriate groups
sudo usermod -aG sudo $USER

# For K3s/containerd access
sudo chown $USER /run/k3s/containerd/containerd.sock

# Or run with sudo
sudo docker run --rm hello-world
```

#### 3. Containerd Namespace Issues

**Problem**: `namespace "moby" not found`

**Solution**:
```bash
# Set correct namespace for K3s
export CONTAINERD_NAMESPACE=k8s.io

# Make permanent
echo 'export CONTAINERD_NAMESPACE=k8s.io' >> ~/.bashrc
source ~/.bashrc
```

#### 4. Build Failures

**Problem**: `error during connect: Post "http://...": dial unix: connect: no such file or directory`

**Solution**:
```bash
# Check buildkit service
sudo systemctl status buildkit

# Restart if needed
sudo systemctl restart buildkit

# Check logs
sudo journalctl -u buildkit -n 50
```

#### 5. Runner Not Picking Up Jobs

**Problem**: Runner is online but not executing jobs

**Solution**:
```bash
# Check runner labels
cd ~/actions-runner
./config.sh remove
./config.sh --url https://github.com/your-org/your-repo \
  --token YOUR_TOKEN \
  --labels "self-hosted,containerd,Linux,x64"

# Restart runner service
sudo ./svc.sh stop
sudo ./svc.sh start
```

### Debugging Commands

```bash
# Check all container-related services
sudo systemctl status containerd
sudo systemctl status buildkit
sudo systemctl status k3s

# View runner logs
sudo journalctl -u actions.runner.*.service -f

# Test nerdctl directly
sudo nerdctl --namespace k8s.io ps
sudo nerdctl --namespace k8s.io images

# Check symlinks and binaries
which docker
which nerdctl
readlink -f $(which docker)
```

## Maintenance

### Regular Updates

Keep your runner environment updated:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update nerdctl
# Check latest version at https://github.com/containerd/nerdctl/releases
NERDCTL_VERSION="1.7.1"  # Update this
wget -O nerdctl.tar.gz \
  "https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-full-${NERDCTL_VERSION}-linux-amd64.tar.gz"
sudo tar -xzf nerdctl.tar.gz -C /usr/local/

# Update GitHub runner
cd ~/actions-runner
sudo ./svc.sh stop
# Download and extract new version
sudo ./svc.sh start
```

### Monitoring

Set up monitoring for your runners:

```bash
# Create monitoring script
cat > ~/monitor-runner.sh << 'EOF'
#!/bin/bash
echo "=== Runner Status ==="
sudo systemctl status actions.runner.*.service --no-pager

echo -e "\n=== Container Runtime ==="
docker version

echo -e "\n=== Recent Runner Logs ==="
sudo journalctl -u actions.runner.*.service -n 20 --no-pager

echo -e "\n=== Disk Usage ==="
df -h /

echo -e "\n=== Memory Usage ==="
free -h
EOF

chmod +x ~/monitor-runner.sh

# Run monitoring
./monitor-runner.sh
```

### Cleanup

Periodically clean up unused resources:

```bash
# Remove unused container images
docker image prune -a -f

# Clean build cache
docker builder prune -f

# Remove stopped containers
docker container prune -f

# Clean runner work directory
cd ~/actions-runner/_work
# Be careful - only remove completed job directories
```

## Security Considerations

1. **Runner Isolation**: Run each runner in a separate VM or container
2. **Network Security**: Restrict outbound connections to required services
3. **Secret Management**: Use GitHub Secrets, never hardcode credentials
4. **Regular Updates**: Keep all components updated for security patches
5. **Audit Logs**: Monitor runner activity and system logs

## Performance Optimization

1. **SSD Storage**: Use SSDs for runner work directories
2. **Image Caching**: Pre-pull frequently used images
3. **Resource Limits**: Set appropriate CPU/memory limits
4. **Parallel Jobs**: Configure multiple runners for parallel execution
5. **Local Registry**: Consider a local container registry for large images

## Additional Resources

- [GitHub Actions Self-Hosted Runners Documentation](https://docs.github.com/en/actions/hosting-your-own-runners)
- [nerdctl Documentation](https://github.com/containerd/nerdctl)
- [K3s Documentation](https://docs.k3s.io/)
- [containerd Documentation](https://containerd.io/docs/)
- [Our Hybrid Strategy Documentation](.github/HYBRID_STRATEGY.md)

## Support

For issues specific to this setup:
1. Check the troubleshooting section above
2. Review runner logs: `sudo journalctl -u actions.runner.*.service -f`
3. Test with the verification workflow: `test-docker-symlink.yml`
4. Open an issue with detailed error messages and environment information

---

**Last Updated**: 2025-09-11
**Maintained By**: DevOps Team