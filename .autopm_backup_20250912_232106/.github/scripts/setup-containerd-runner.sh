#!/usr/bin/env bash
#
# Script: setup-containerd-runner.sh
# Description: Configure GitHub Actions self-hosted runner for containerd/nerdctl
# Author: Speecher CI/CD
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Enable debug mode if DEBUG is set
[[ "${DEBUG:-0}" == "1" ]] && set -x

# Script configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly LOG_FILE="${LOG_FILE:-/tmp/setup-containerd-runner.log}"

# Configuration
readonly NERDCTL_VERSION="${NERDCTL_VERSION:-1.7.2}"
readonly CONTAINERD_NAMESPACE="${CONTAINERD_NAMESPACE:-k8s.io}"
readonly CNI_VERSION="${CNI_VERSION:-1.3.0}"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
    log "INFO: $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
    log "SUCCESS: $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
    log "WARNING: $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    log "ERROR: $*"
}

# Error handling
trap 'error_handler $? $LINENO' ERR

error_handler() {
    local exit_code=$1
    local line_number=$2
    log_error "Command failed with exit code ${exit_code} at line ${line_number}"
    exit "${exit_code}"
}

# Check if running as root or with sudo
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_info "Running as root"
        return 0
    fi
    
    if sudo -n true 2>/dev/null; then
        log_info "Passwordless sudo available"
        return 0
    fi
    
    log_error "This script requires root privileges or passwordless sudo"
    log_error "Configure passwordless sudo for the runner user with:"
    log_error "echo '$(whoami) ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/github-runner"
    exit 1
}

# Run command with appropriate privileges
run_privileged() {
    if [[ $EUID -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

# Check if containerd is running
check_containerd() {
    log_info "Checking containerd status..."
    
    if ! run_privileged systemctl is-active --quiet containerd; then
        log_warning "containerd is not running, attempting to start..."
        run_privileged systemctl start containerd
        sleep 2
    fi
    
    if run_privileged systemctl is-active --quiet containerd; then
        log_success "containerd is running"
        return 0
    else
        log_error "Failed to start containerd"
        return 1
    fi
}

# Check if K3s is installed and get its configuration
check_k3s() {
    log_info "Checking K3s installation..."
    
    if [[ -f /etc/rancher/k3s/k3s.yaml ]]; then
        log_success "K3s configuration found"
        
        # Check if K3s is using containerd
        if run_privileged k3s crictl info 2>/dev/null | grep -q containerd; then
            log_success "K3s is using containerd"
        else
            log_warning "K3s may not be using containerd"
        fi
    else
        log_warning "K3s configuration not found, continuing with standard containerd setup"
    fi
}

# Install nerdctl if not present
install_nerdctl() {
    log_info "Checking nerdctl installation..."
    
    if command -v nerdctl &> /dev/null; then
        local installed_version
        installed_version=$(nerdctl version 2>/dev/null | grep -oP 'Version:\s*\K[\d.]+' | head -1 || echo "unknown")
        log_info "nerdctl is already installed (version: ${installed_version})"
        return 0
    fi
    
    log_info "Installing nerdctl version ${NERDCTL_VERSION}..."
    
    local arch
    case "$(uname -m)" in
        x86_64)  arch="amd64" ;;
        aarch64) arch="arm64" ;;
        armv7l)  arch="arm" ;;
        *)       log_error "Unsupported architecture: $(uname -m)"; return 1 ;;
    esac
    
    local os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    local nerdctl_url="https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-${NERDCTL_VERSION}-${os}-${arch}.tar.gz"
    
    log_info "Downloading nerdctl from ${nerdctl_url}..."
    
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf ${temp_dir}" EXIT
    
    curl -sSL "${nerdctl_url}" | tar -xz -C "${temp_dir}"
    
    run_privileged mv "${temp_dir}/nerdctl" /usr/local/bin/
    run_privileged chmod +x /usr/local/bin/nerdctl
    
    log_success "nerdctl installed successfully"
}

# Install CNI plugins if not present
install_cni_plugins() {
    log_info "Checking CNI plugins..."
    
    if [[ -d /opt/cni/bin ]] && [[ -n "$(ls -A /opt/cni/bin 2>/dev/null)" ]]; then
        log_info "CNI plugins already installed"
        return 0
    fi
    
    log_info "Installing CNI plugins version ${CNI_VERSION}..."
    
    local arch
    case "$(uname -m)" in
        x86_64)  arch="amd64" ;;
        aarch64) arch="arm64" ;;
        armv7l)  arch="arm" ;;
        *)       log_error "Unsupported architecture: $(uname -m)"; return 1 ;;
    esac
    
    local cni_url="https://github.com/containernetworking/plugins/releases/download/v${CNI_VERSION}/cni-plugins-linux-${arch}-v${CNI_VERSION}.tgz"
    
    log_info "Downloading CNI plugins from ${cni_url}..."
    
    run_privileged mkdir -p /opt/cni/bin
    curl -sSL "${cni_url}" | run_privileged tar -xz -C /opt/cni/bin
    
    log_success "CNI plugins installed successfully"
}

# Create docker symlink to nerdctl
create_docker_symlink() {
    log_info "Setting up docker command symlink..."
    
    # Remove existing docker command if it's a broken symlink or points elsewhere
    if [[ -L /usr/local/bin/docker ]]; then
        local current_target
        current_target=$(readlink /usr/local/bin/docker)
        if [[ "${current_target}" != "/usr/local/bin/nerdctl" ]]; then
            log_warning "Removing existing docker symlink pointing to ${current_target}"
            run_privileged rm -f /usr/local/bin/docker
        else
            log_info "Docker symlink already points to nerdctl"
            return 0
        fi
    elif [[ -f /usr/local/bin/docker ]]; then
        log_warning "Found existing docker binary, backing up to docker.orig"
        run_privileged mv /usr/local/bin/docker /usr/local/bin/docker.orig
    fi
    
    # Create symlink
    run_privileged ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker
    log_success "Created docker -> nerdctl symlink"
    
    # Also create symlinks in /usr/bin if needed
    if [[ ! -e /usr/bin/docker ]]; then
        run_privileged ln -sf /usr/local/bin/nerdctl /usr/bin/docker
        log_success "Created /usr/bin/docker -> nerdctl symlink"
    fi
    
    if [[ ! -e /usr/bin/nerdctl ]]; then
        run_privileged ln -sf /usr/local/bin/nerdctl /usr/bin/nerdctl
        log_success "Created /usr/bin/nerdctl symlink"
    fi
}

# Configure nerdctl for the runner user
configure_nerdctl() {
    log_info "Configuring nerdctl..."
    
    local config_dir="${HOME}/.config/nerdctl"
    mkdir -p "${config_dir}"
    
    # Create nerdctl configuration
    cat > "${config_dir}/nerdctl.toml" << EOF
# nerdctl configuration for GitHub Actions runner
namespace = "${CONTAINERD_NAMESPACE}"
debug = false
debug_full = false
insecure_registry = false

[default_platform]
platform = "linux/amd64"
EOF
    
    log_success "Created nerdctl configuration"
    
    # Set up containerd address for K3s if available
    if [[ -S /run/k3s/containerd/containerd.sock ]]; then
        echo "address = \"/run/k3s/containerd/containerd.sock\"" >> "${config_dir}/nerdctl.toml"
        log_info "Configured nerdctl to use K3s containerd socket"
    elif [[ -S /run/containerd/containerd.sock ]]; then
        echo "address = \"/run/containerd/containerd.sock\"" >> "${config_dir}/nerdctl.toml"
        log_info "Configured nerdctl to use standard containerd socket"
    fi
}

# Set up environment variables
setup_environment() {
    log_info "Setting up environment variables..."
    
    local env_file="${HOME}/.bashrc"
    local marker="# GitHub Actions Runner Containerd Setup"
    
    # Remove old configuration if exists
    if grep -q "${marker}" "${env_file}" 2>/dev/null; then
        log_info "Removing old environment configuration..."
        sed -i "/${marker}/,/${marker} END/d" "${env_file}"
    fi
    
    # Add new configuration
    cat >> "${env_file}" << EOF

${marker}
# Use K3s containerd socket if available
if [[ -S /run/k3s/containerd/containerd.sock ]]; then
    export CONTAINERD_ADDRESS=/run/k3s/containerd/containerd.sock
elif [[ -S /run/containerd/containerd.sock ]]; then
    export CONTAINERD_ADDRESS=/run/containerd/containerd.sock
fi

# Set containerd namespace
export CONTAINERD_NAMESPACE=${CONTAINERD_NAMESPACE}

# Docker compatibility environment
export DOCKER_HOST=unix://\${CONTAINERD_ADDRESS}

# Add nerdctl to PATH if not already there
if [[ -d /usr/local/bin ]] && [[ ":\${PATH}:" != *":/usr/local/bin:"* ]]; then
    export PATH="/usr/local/bin:\${PATH}"
fi

# Alias for docker compose compatibility
alias docker-compose='nerdctl compose'
${marker} END
EOF
    
    log_success "Environment variables configured"
    
    # Also create a system-wide configuration for the runner service
    if [[ -d /etc/profile.d ]]; then
        run_privileged tee /etc/profile.d/containerd-runner.sh > /dev/null << EOF
#!/bin/bash
# GitHub Actions Runner Containerd Configuration

if [[ -S /run/k3s/containerd/containerd.sock ]]; then
    export CONTAINERD_ADDRESS=/run/k3s/containerd/containerd.sock
elif [[ -S /run/containerd/containerd.sock ]]; then
    export CONTAINERD_ADDRESS=/run/containerd/containerd.sock
fi

export CONTAINERD_NAMESPACE=${CONTAINERD_NAMESPACE}
export DOCKER_HOST=unix://\${CONTAINERD_ADDRESS}
EOF
        run_privileged chmod +x /etc/profile.d/containerd-runner.sh
        log_success "Created system-wide environment configuration"
    fi
}

# Configure permissions for the runner user
configure_permissions() {
    log_info "Configuring permissions..."
    
    local current_user=$(whoami)
    
    # Add user to docker group if it exists
    if getent group docker &>/dev/null; then
        if ! groups "${current_user}" | grep -q docker; then
            run_privileged usermod -aG docker "${current_user}"
            log_success "Added ${current_user} to docker group"
            log_warning "You may need to log out and back in for group changes to take effect"
        else
            log_info "User ${current_user} is already in docker group"
        fi
    fi
    
    # Set permissions on containerd socket
    if [[ -S /run/k3s/containerd/containerd.sock ]]; then
        run_privileged chmod 666 /run/k3s/containerd/containerd.sock
        log_success "Set permissions on K3s containerd socket"
    fi
    
    if [[ -S /run/containerd/containerd.sock ]]; then
        run_privileged chmod 666 /run/containerd/containerd.sock
        log_success "Set permissions on containerd socket"
    fi
}

# Test the setup
test_setup() {
    log_info "Testing setup..."
    
    # Source the environment
    if [[ -f "${HOME}/.bashrc" ]]; then
        # shellcheck source=/dev/null
        source "${HOME}/.bashrc"
    fi
    
    local test_passed=true
    
    # Test 1: Check docker command exists
    log_info "Test 1: Checking docker command..."
    if command -v docker &> /dev/null; then
        log_success "docker command is available"
    else
        log_error "docker command not found"
        test_passed=false
    fi
    
    # Test 2: Check nerdctl command exists
    log_info "Test 2: Checking nerdctl command..."
    if command -v nerdctl &> /dev/null; then
        log_success "nerdctl command is available"
    else
        log_error "nerdctl command not found"
        test_passed=false
    fi
    
    # Test 3: Test docker version
    log_info "Test 3: Testing docker version..."
    if docker version &>/dev/null; then
        log_success "docker version command works"
    else
        log_warning "docker version command failed (this may be normal if no runtime is available)"
    fi
    
    # Test 4: Test pulling a small image
    log_info "Test 4: Testing image pull..."
    if docker pull alpine:latest &>/dev/null; then
        log_success "Successfully pulled alpine:latest"
        
        # Test 5: Test running a container
        log_info "Test 5: Testing container run..."
        if docker run --rm alpine:latest echo "Hello from containerd" &>/dev/null; then
            log_success "Successfully ran test container"
        else
            log_warning "Failed to run test container"
        fi
        
        # Clean up test image
        docker rmi alpine:latest &>/dev/null || true
    else
        log_warning "Failed to pull test image (this may be normal in some environments)"
    fi
    
    # Test 6: Check namespace
    log_info "Test 6: Checking containerd namespace..."
    if nerdctl namespace ls 2>/dev/null | grep -q "${CONTAINERD_NAMESPACE}"; then
        log_success "Containerd namespace ${CONTAINERD_NAMESPACE} is available"
    else
        log_warning "Containerd namespace ${CONTAINERD_NAMESPACE} not found (will be created on first use)"
    fi
    
    if [[ "${test_passed}" == "true" ]]; then
        log_success "All critical tests passed!"
        return 0
    else
        log_error "Some tests failed. Please check the logs."
        return 1
    fi
}

# Display summary
display_summary() {
    echo
    echo "========================================="
    echo "  GitHub Actions Runner Setup Complete"
    echo "========================================="
    echo
    echo "Configuration Summary:"
    echo "  - nerdctl version: ${NERDCTL_VERSION}"
    echo "  - Containerd namespace: ${CONTAINERD_NAMESPACE}"
    echo "  - Docker command: symlinked to nerdctl"
    echo "  - Configuration file: ${HOME}/.config/nerdctl/nerdctl.toml"
    echo "  - Log file: ${LOG_FILE}"
    echo
    echo "Next Steps:"
    echo "  1. If you were added to the docker group, log out and back in"
    echo "  2. Start your GitHub Actions runner service"
    echo "  3. Monitor runner logs for any issues"
    echo
    echo "Useful Commands:"
    echo "  - docker ps                    # List containers"
    echo "  - docker images                # List images"
    echo "  - nerdctl namespace ls         # List namespaces"
    echo "  - sudo crictl ps               # K3s container list"
    echo
}

# Main function
main() {
    log_info "Starting ${SCRIPT_NAME}"
    log_info "System: $(uname -s) $(uname -m)"
    log_info "User: $(whoami)"
    
    # Perform setup steps
    check_permissions
    check_containerd
    check_k3s
    install_nerdctl
    install_cni_plugins
    create_docker_symlink
    configure_nerdctl
    setup_environment
    configure_permissions
    
    # Test the setup
    if test_setup; then
        display_summary
        log_success "Setup completed successfully!"
        exit 0
    else
        log_error "Setup completed with warnings. Please review the log at ${LOG_FILE}"
        exit 1
    fi
}

# Show usage
usage() {
    cat << EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Configure GitHub Actions self-hosted runner for containerd/nerdctl

OPTIONS:
    -h, --help              Show this help message
    -v, --version           Set nerdctl version (default: ${NERDCTL_VERSION})
    -n, --namespace         Set containerd namespace (default: ${CONTAINERD_NAMESPACE})
    -d, --debug             Enable debug output

ENVIRONMENT VARIABLES:
    NERDCTL_VERSION         Version of nerdctl to install
    CONTAINERD_NAMESPACE    Containerd namespace to use
    CNI_VERSION            Version of CNI plugins to install
    DEBUG                  Set to 1 to enable debug output
    LOG_FILE              Path to log file

EXAMPLES:
    # Basic setup
    ${SCRIPT_NAME}
    
    # Setup with custom nerdctl version
    ${SCRIPT_NAME} --version 1.7.2
    
    # Setup with debug output
    DEBUG=1 ${SCRIPT_NAME}
    
    # Setup with custom namespace
    ${SCRIPT_NAME} --namespace default

NOTES:
    - This script requires root or passwordless sudo access
    - It's safe to run multiple times (idempotent)
    - Adds the current user to the docker group if it exists
    - Creates docker as a symlink to nerdctl for compatibility

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--version)
            NERDCTL_VERSION="$2"
            shift 2
            ;;
        -n|--namespace)
            CONTAINERD_NAMESPACE="$2"
            shift 2
            ;;
        -d|--debug)
            set -x
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Execute main function
main "$@"