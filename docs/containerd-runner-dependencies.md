# Containerd Runner Dependencies

This document outlines all dependencies required for GitHub Actions workflows running on K3s containerd self-hosted runners for the Speecher project.

## Overview

The Speecher project requires multiple runtime environments and tools to support:
- Python backend API testing and deployment
- React frontend building and testing
- Visual regression testing with Playwright
- Container image building and deployment
- Security scanning and code quality checks

## Dependency Categories

### 1. Python Backend Dependencies

**Required for:** API testing, linting, security scanning
**Workflows affected:** `ci-k3s.yml` (test, lint, security jobs)

#### Core Python
- **Python 3.11**: Required by `env.PYTHON_VERSION` in workflows
- **pip**: Package installation and dependency management
- **venv**: Virtual environment creation for isolated testing

#### Python Packages
- **pytest 7.4.3**: Test framework for unit and integration tests
- **pytest-cov 4.1.0**: Coverage reporting for tests
- **pytest-asyncio 0.21.1**: Async test support for FastAPI
- **pytest-mock 3.12.0**: Mocking framework for tests

#### Code Quality Tools
- **black 23.11.0**: Code formatter (required by CI)
- **isort 5.12.0**: Import sorting (required by CI)
- **flake8 6.1.0**: Linting and style checking
- **mypy 1.7.0**: Static type checking
- **bandit 1.7.5**: Security vulnerability scanner
- **safety 3.0.1**: Dependency security scanner

### 2. Node.js Frontend Dependencies

**Required for:** React frontend building, testing, visual regression
**Workflows affected:** `frontend-v2-pr.yml`, `visual-tests.yml`

#### Node.js Versions
- **Node.js 18.x**: LTS support for compatibility testing
- **Node.js 20.x**: Current LTS version for primary builds
- **npm**: Package manager (automatically installed with Node.js)

#### Build & Test Tools
- **React Scripts 5.0.1**: Create React App build system
- **Jest**: Testing framework (included in React Scripts)
- **ESLint**: JavaScript linting (configured in React Scripts)

### 3. Browser Testing Dependencies

**Required for:** Visual regression testing, E2E testing
**Workflows affected:** `visual-tests.yml`

#### Playwright
- **@playwright/test**: Latest version for browser automation
- **Chromium browser**: Primary browser for testing
- **Firefox browser**: Cross-browser compatibility testing  
- **WebKit browser**: Safari compatibility testing

#### System Dependencies for Browsers
- **libnss3-dev**: Network Security Services
- **libatk-bridge2.0-dev**: Accessibility toolkit bridge
- **libdrm2**: Direct Rendering Manager
- **libgtk-3-dev**: GTK+ 3 development files
- **libgbm-dev**: Generic Buffer Management
- **libasound2-dev**: Advanced Linux Sound Architecture

### 4. Container Runtime Dependencies

**Required for:** Container building and deployment
**Workflows affected:** `ci-k3s.yml` (container-build job)

#### Container Tools
- **nerdctl 1.7.1**: Docker-compatible CLI for containerd
- **containerd**: Container runtime (provided by K3s)
- **buildkitd**: BuildKit daemon for advanced image building

#### Configuration
- **CONTAINERD_NAMESPACE=k8s.io**: K3s-specific containerd namespace

### 5. Database Dependencies

**Required for:** Integration testing with MongoDB
**Workflows affected:** `ci-k3s.yml` (test job with MongoDB service)

#### MongoDB Tools
- **mongosh**: MongoDB shell for health checks and debugging
- **mongodb-org-tools**: Database utilities for backup/restore

### 6. Kubernetes Dependencies

**Required for:** K3s deployment and testing
**Workflows affected:** `ci-k3s.yml` (container-build job)

#### Kubernetes CLI
- **kubectl**: Kubernetes command-line tool
- **K3s cluster access**: Configured kubeconfig for cluster communication

### 7. Security & Quality Dependencies

**Required for:** Security scanning and vulnerability detection
**Workflows affected:** `ci-k3s.yml` (security job), `frontend-v2-pr.yml` (security-check job)

#### Security Tools
- **Trivy**: Container image vulnerability scanner
- **TruffleHog**: Secret detection in code repositories

### 8. CI/CD Integration Dependencies

**Required for:** GitHub Actions integration and automation
**Workflows affected:** All workflows

#### GitHub Integration
- **GitHub CLI (gh)**: GitHub API interactions and automation
- **actions/checkout@v4**: Code checkout action
- **actions/setup-node@v4**: Node.js setup action
- **actions/setup-python@v4**: Python setup action
- **actions/cache@v4**: Dependency caching
- **actions/upload-artifact@v4**: Artifact management

## System Requirements

### Operating System Support
- **Ubuntu 20.04/22.04**: Primary support
- **Debian 11/12**: Full support
- **CentOS/RHEL 8/9**: Basic support
- **Fedora 37+**: Basic support

### Hardware Requirements
- **CPU**: 4+ cores (for parallel browser testing)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB+ available space
- **Network**: High-speed internet for downloading dependencies

### User Permissions
- **sudo access**: Required for system package installation
- **docker group**: For containerd/nerdctl access (if applicable)
- **GitHub runner user**: Dedicated user account for runner service

## Installation Process

### Automated Installation
Use the provided installation script:
```bash
./scripts/setup-containerd-runner.sh
```

### Manual Installation Steps
1. **System Updates**: Update package repositories
2. **Base Dependencies**: Install build tools and utilities
3. **Python Environment**: Install Python 3.11 and tools
4. **Node.js Environment**: Install via nvm for version management
5. **Browser Dependencies**: Install Playwright and system libraries
6. **Database Tools**: Install MongoDB client tools
7. **Container Runtime**: Install nerdctl and buildkitd
8. **Kubernetes Tools**: Install kubectl
9. **Security Tools**: Install Trivy and other scanners
10. **GitHub Integration**: Install GitHub CLI
11. **Environment Setup**: Configure shell environment
12. **Verification**: Test all installed components

## Environment Configuration

### Shell Environment Variables
```bash
# Node.js version management
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Containerd namespace for K3s
export CONTAINERD_NAMESPACE=k8s.io

# Python user packages
export PATH="$HOME/.local/bin:$PATH"

# GitHub Actions specific
export CI=true
export PLAYWRIGHT_BROWSERS_PATH=0
```

### Service Configuration
- **buildkitd service**: Systemd service for container building
- **GitHub Actions runner**: Configured with `[self-hosted, containerd]` labels

## Workflow-Specific Requirements

### CI/CD Pipeline (ci-k3s.yml)
- Python 3.11 + development tools
- MongoDB client tools for health checks
- nerdctl for container building
- kubectl for K3s deployment testing
- Security scanning tools (Trivy, Bandit, Safety)

### Visual Regression Testing (visual-tests.yml)
- Node.js 20.x
- Playwright with all browsers
- System libraries for browser rendering
- Artifact management for screenshots

### Frontend PR Checks (frontend-v2-pr.yml)
- Node.js 18.x and 20.x for compatibility testing
- React Scripts build system
- Security audit tools (npm audit, TruffleHog)
- Coverage reporting tools

## Troubleshooting

### Common Issues

1. **Python Module Import Errors**
   - Ensure Python 3.11 is properly installed
   - Check virtual environment activation
   - Verify pip package installation paths

2. **Node.js Version Conflicts**
   - Use nvm to manage multiple Node.js versions
   - Ensure correct version is active for each workflow
   - Clear npm cache if dependencies fail

3. **Playwright Browser Issues**
   - Install system dependencies with `--with-deps` flag
   - Check browser binary paths and permissions
   - Verify display server availability for GUI testing

4. **Container Build Failures**
   - Ensure buildkitd service is running
   - Check containerd namespace configuration
   - Verify nerdctl permissions and socket access

5. **MongoDB Connection Issues**
   - Verify MongoDB service is running in containers
   - Check network connectivity between containers
   - Ensure proper health check configuration

### Verification Commands
```bash
# Check Python installation
python3.11 --version && pip3 --version

# Check Node.js versions
nvm list && node --version && npm --version

# Check container tools
nerdctl version && kubectl version --client

# Check browser tools
npx playwright --version

# Check database tools  
mongosh --version

# Check security tools
trivy version && gh --version
```

## Security Considerations

### Package Sources
- Use official package repositories when possible
- Verify GPG signatures for external repositories
- Pin specific versions to prevent supply chain attacks

### Runtime Security
- Run GitHub Actions runner as dedicated user
- Limit sudo access to necessary operations only
- Use least-privilege principles for service accounts
- Regular security updates and vulnerability scanning

### Container Security
- Scan all container images before deployment
- Use minimal base images
- Implement proper security contexts in Kubernetes
- Regular security audits of dependencies

## Maintenance

### Regular Updates
- Monthly security updates for system packages
- Quarterly updates for development tools
- As-needed updates for critical security fixes

### Monitoring
- Monitor disk space for build artifacts
- Track dependency installation times
- Monitor workflow success/failure rates
- Alert on security vulnerability detections

### Backup & Recovery
- Document installation configuration
- Backup runner configuration and secrets
- Test recovery procedures regularly
- Maintain spare runner capacity for high availability