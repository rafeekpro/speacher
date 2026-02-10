#!/bin/bash

# Comprehensive Installation Script for K3s Containerd GitHub Actions Runners
# This script installs all dependencies needed for the Speecher project CI/CD workflows

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    log_error "This script should not be run as root. Please run as a regular user with sudo access."
    exit 1
fi

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
    log_info "Detected OS: $OS $VERSION"
}

# Update system packages
update_system() {
    log_info "Updating system packages..."
    case $OS in
        ubuntu|debian)
            sudo apt-get update -y
            sudo apt-get upgrade -y
            ;;
        centos|rhel|fedora)
            sudo yum update -y || sudo dnf update -y
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    log_success "System packages updated"
}

# Install basic system dependencies
install_system_dependencies() {
    log_info "Installing basic system dependencies..."
    case $OS in
        ubuntu|debian)
            sudo apt-get install -y \
                curl \
                wget \
                git \
                unzip \
                tar \
                gzip \
                build-essential \
                ca-certificates \
                gnupg \
                lsb-release \
                software-properties-common \
                apt-transport-https \
                jq \
                htop \
                vim \
                nano \
                tree
            ;;
        centos|rhel|fedora)
            sudo yum install -y \
                curl \
                wget \
                git \
                unzip \
                tar \
                gzip \
                gcc \
                gcc-c++ \
                make \
                ca-certificates \
                gnupg \
                jq \
                htop \
                vim \
                nano \
                tree \
            || sudo dnf install -y \
                curl \
                wget \
                git \
                unzip \
                tar \
                gzip \
                gcc \
                gcc-c++ \
                make \
                ca-certificates \
                gnupg \
                jq \
                htop \
                vim \
                nano \
                tree
            ;;
    esac
    log_success "Basic system dependencies installed"
}

# Install Python 3.11
install_python() {
    log_info "Installing Python 3.11..."
    
    if command -v python3.11 >/dev/null 2>&1; then
        log_success "Python 3.11 already installed: $(python3.11 --version)"
        return
    fi

    case $OS in
        ubuntu|debian)
            # Add deadsnakes PPA for Ubuntu/Debian
            sudo add-apt-repository ppa:deadsnakes/ppa -y
            sudo apt-get update -y
            sudo apt-get install -y \
                python3.11 \
                python3.11-venv \
                python3.11-dev \
                python3.11-distutils \
                python3-pip
            ;;
        centos|rhel)
            # Install Python 3.11 from source or EPEL
            sudo yum install -y python3 python3-pip python3-devel
            ;;
        fedora)
            sudo dnf install -y python3.11 python3.11-pip python3.11-devel
            ;;
    esac

    # Ensure pip is available
    python3.11 -m ensurepip --upgrade 2>/dev/null || true
    python3.11 -m pip install --upgrade pip

    # Create symlinks for easier access
    if ! command -v python3 >/dev/null 2>&1; then
        sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
    fi
    
    if ! command -v pip3 >/dev/null 2>&1; then
        sudo ln -sf /usr/bin/pip3.11 /usr/bin/pip3 2>/dev/null || true
    fi

    log_success "Python 3.11 installed: $(python3.11 --version)"
}

# Install Python development dependencies
install_python_dev_tools() {
    log_info "Installing Python development tools..."
    
    # Install common Python linting and testing tools globally
    python3.11 -m pip install --user --upgrade \
        pytest==7.4.3 \
        pytest-cov==4.1.0 \
        pytest-asyncio==0.21.1 \
        pytest-mock==3.12.0 \
        black==23.11.0 \
        isort==5.12.0 \
        flake8==6.1.0 \
        mypy==1.7.0 \
        safety==3.0.1 \
        bandit==1.7.5 \
        coverage==7.3.2

    log_success "Python development tools installed"
}

# Install Node.js (multiple versions via nvm)
install_nodejs() {
    log_info "Installing Node.js via nvm..."
    
    # Install nvm
    if [[ ! -d "$HOME/.nvm" ]]; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    else
        log_success "nvm already installed"
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi

    # Install Node.js versions needed by workflows
    log_info "Installing Node.js 18.x..."
    nvm install 18
    nvm use 18
    npm install -g npm@latest

    log_info "Installing Node.js 20.x..."
    nvm install 20
    nvm use 20
    npm install -g npm@latest

    # Set Node 20 as default
    nvm alias default 20
    nvm use default

    log_success "Node.js versions installed:"
    nvm list
}

# Install Playwright browsers and dependencies
install_playwright() {
    log_info "Installing Playwright browsers and system dependencies..."
    
    # Source nvm to ensure Node.js is available
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    nvm use 20

    # Install Playwright globally
    npm install -g @playwright/test@latest

    # Install system dependencies for Playwright browsers
    case $OS in
        ubuntu|debian)
            sudo apt-get install -y \
                libnss3-dev \
                libatk-bridge2.0-dev \
                libdrm2 \
                libgtk-3-dev \
                libgbm-dev \
                libasound2-dev
            ;;
        centos|rhel|fedora)
            sudo yum install -y \
                nss \
                atk \
                libdrm \
                gtk3 \
                mesa-libgbm \
                alsa-lib \
            || sudo dnf install -y \
                nss \
                atk \
                libdrm \
                gtk3 \
                mesa-libgbm \
                alsa-lib
            ;;
    esac

    # Install Playwright browsers
    npx playwright install --with-deps chromium firefox webkit

    log_success "Playwright installed with browser dependencies"
}

# Install MongoDB client tools
install_mongodb_tools() {
    log_info "Installing MongoDB client tools..."
    
    case $OS in
        ubuntu|debian)
            # Import MongoDB public GPG key
            wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
            
            # Create MongoDB source list file
            if [[ $OS == "ubuntu" ]]; then
                echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -sc)/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
            else
                echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/debian $(lsb_release -sc)/mongodb-org/6.0 main" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
            fi
            
            sudo apt-get update -y
            sudo apt-get install -y mongodb-mongosh mongodb-org-tools
            ;;
        centos|rhel)
            # Create MongoDB repo file
            sudo tee /etc/yum.repos.d/mongodb-org-6.0.repo > /dev/null <<EOF
[mongodb-org-6.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/6.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-6.0.asc
EOF
            sudo yum install -y mongodb-mongosh mongodb-org-tools
            ;;
        fedora)
            sudo tee /etc/yum.repos.d/mongodb-org-6.0.repo > /dev/null <<EOF
[mongodb-org-6.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/8/mongodb-org/6.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-6.0.asc
EOF
            sudo dnf install -y mongodb-mongosh mongodb-org-tools
            ;;
    esac

    log_success "MongoDB client tools installed"
}

# Install kubectl
install_kubectl() {
    log_info "Installing kubectl..."
    
    if command -v kubectl >/dev/null 2>&1; then
        log_success "kubectl already installed: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
        return
    fi

    case $OS in
        ubuntu|debian)
            sudo curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
            echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
            sudo apt-get update -y
            sudo apt-get install -y kubectl
            ;;
        centos|rhel|fedora)
            sudo tee /etc/yum.repos.d/kubernetes.repo > /dev/null <<EOF
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF
            if command -v yum >/dev/null 2>&1; then
                sudo yum install -y kubectl
            else
                sudo dnf install -y kubectl
            fi
            ;;
    esac

    log_success "kubectl installed: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
}

# Install nerdctl for container management
install_nerdctl() {
    log_info "Installing nerdctl..."
    
    if command -v nerdctl >/dev/null 2>&1; then
        log_success "nerdctl already installed: $(nerdctl version)"
        return
    fi

    # Download and install nerdctl
    NERDCTL_VERSION="1.7.1"
    wget -O nerdctl.tar.gz "https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-full-${NERDCTL_VERSION}-linux-amd64.tar.gz"
    sudo tar -xzf nerdctl.tar.gz -C /usr/local/
    sudo chmod +x /usr/local/bin/nerdctl
    rm nerdctl.tar.gz

    # Create systemd service for buildkitd if not exists
    if [[ ! -f /etc/systemd/system/buildkit.service ]]; then
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
        sudo systemctl daemon-reload
        sudo systemctl enable buildkit
        sudo systemctl start buildkit
    fi

    log_success "nerdctl installed: $(nerdctl version)"
}

# Install Trivy for security scanning
install_trivy() {
    log_info "Installing Trivy security scanner..."
    
    if command -v trivy >/dev/null 2>&1; then
        log_success "Trivy already installed: $(trivy version)"
        return
    fi

    case $OS in
        ubuntu|debian)
            wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
            echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
            sudo apt-get update -y
            sudo apt-get install -y trivy
            ;;
        centos|rhel)
            sudo tee /etc/yum.repos.d/trivy.repo > /dev/null <<EOF
[trivy]
name=Trivy repository
baseurl=https://aquasecurity.github.io/trivy-repo/rpm/releases/\$releasever/\$basearch/
gpgcheck=0
enabled=1
EOF
            sudo yum install -y trivy
            ;;
        fedora)
            sudo tee /etc/yum.repos.d/trivy.repo > /dev/null <<EOF
[trivy]
name=Trivy repository
baseurl=https://aquasecurity.github.io/trivy-repo/rpm/releases/\$releasever/\$basearch/
gpgcheck=0
enabled=1
EOF
            sudo dnf install -y trivy
            ;;
    esac

    log_success "Trivy installed: $(trivy version)"
}

# Install GitHub CLI
install_github_cli() {
    log_info "Installing GitHub CLI..."
    
    if command -v gh >/dev/null 2>&1; then
        log_success "GitHub CLI already installed: $(gh --version | head -n1)"
        return
    fi

    case $OS in
        ubuntu|debian)
            type -p curl >/dev/null || sudo apt install curl -y
            curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
            sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
            sudo apt update -y
            sudo apt install gh -y
            ;;
        centos|rhel)
            sudo dnf install 'dnf-command(config-manager)' -y
            sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
            sudo dnf install gh -y
            ;;
        fedora)
            sudo dnf install gh -y
            ;;
    esac

    log_success "GitHub CLI installed: $(gh --version | head -n1)"
}

# Configure environment
configure_environment() {
    log_info "Configuring environment..."
    
    # Add common environment variables to bashrc
    if ! grep -q "# GitHub Actions Runner Environment" ~/.bashrc; then
        cat >> ~/.bashrc << 'EOF'

# GitHub Actions Runner Environment
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Containerd namespace for K3s
export CONTAINERD_NAMESPACE=k8s.io

# Python path
export PATH="$HOME/.local/bin:$PATH"

# Node.js path
export PATH="$HOME/.nvm/versions/node/$(nvm version default 2>/dev/null | sed 's/v//')/bin:$PATH"

EOF
        log_success "Environment variables added to ~/.bashrc"
    fi

    # Source the updated bashrc
    source ~/.bashrc 2>/dev/null || true
}

# Verify installations
verify_installations() {
    log_info "Verifying installations..."
    
    # Check Python
    if command -v python3.11 >/dev/null 2>&1; then
        log_success "✓ Python: $(python3.11 --version)"
    else
        log_error "✗ Python 3.11 not found"
    fi

    # Check pip
    if command -v pip3 >/dev/null 2>&1; then
        log_success "✓ pip: $(pip3 --version)"
    else
        log_warning "⚠ pip3 not found in PATH"
    fi

    # Check Node.js
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    if command -v node >/dev/null 2>&1; then
        log_success "✓ Node.js: $(node --version)"
        log_success "✓ npm: $(npm --version)"
    else
        log_error "✗ Node.js not found"
    fi

    # Check kubectl
    if command -v kubectl >/dev/null 2>&1; then
        log_success "✓ kubectl: $(kubectl version --client --short 2>/dev/null || echo 'installed')"
    else
        log_error "✗ kubectl not found"
    fi

    # Check nerdctl
    if command -v nerdctl >/dev/null 2>&1; then
        log_success "✓ nerdctl: $(nerdctl version | head -n1)"
    else
        log_error "✗ nerdctl not found"
    fi

    # Check Playwright
    if command -v playwright >/dev/null 2>&1; then
        log_success "✓ Playwright: installed"
    else
        log_warning "⚠ Playwright command not found (may be installed locally in projects)"
    fi

    # Check MongoDB tools
    if command -v mongosh >/dev/null 2>&1; then
        log_success "✓ MongoDB Shell: $(mongosh --version)"
    else
        log_warning "⚠ mongosh not found"
    fi

    # Check Trivy
    if command -v trivy >/dev/null 2>&1; then
        log_success "✓ Trivy: $(trivy version | head -n1)"
    else
        log_warning "⚠ Trivy not found"
    fi

    # Check GitHub CLI
    if command -v gh >/dev/null 2>&1; then
        log_success "✓ GitHub CLI: $(gh --version | head -n1)"
    else
        log_warning "⚠ GitHub CLI not found"
    fi
}

# Main installation function
main() {
    log_info "Starting Containerd Runner Setup..."
    log_info "This script will install all dependencies needed for the Speecher project CI/CD workflows"
    
    detect_os
    update_system
    install_system_dependencies
    install_python
    install_python_dev_tools
    install_nodejs
    install_playwright
    install_mongodb_tools
    install_kubectl
    install_nerdctl
    install_trivy
    install_github_cli
    configure_environment
    verify_installations
    
    log_success "🎉 Containerd Runner Setup Complete!"
    log_info "Please restart your shell session or run 'source ~/.bashrc' to load environment variables"
    log_info "You may need to configure kubectl to connect to your K3s cluster"
    log_info "For GitHub Actions runner, configure the runner with the appropriate labels: [self-hosted, containerd]"
}

# Run main function
main "$@"