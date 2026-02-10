#!/bin/bash

# Setup script for K3s self-hosted GitHub runner
# This script installs necessary tools for K3s-compatible CI/CD

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root for security reasons"
   exit 1
fi

info "Setting up K3s GitHub runner environment..."

# 1. Install nerdctl if not present
install_nerdctl() {
    if command -v nerdctl >/dev/null 2>&1; then
        success "nerdctl already installed: $(nerdctl version --short)"
        return 0
    fi
    
    info "Installing nerdctl..."
    
    # Determine architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
        *) error "Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    
    # Download latest nerdctl
    NERDCTL_VERSION="1.7.1"
    NERDCTL_URL="https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-full-${NERDCTL_VERSION}-linux-${ARCH}.tar.gz"
    
    info "Downloading nerdctl from $NERDCTL_URL"
    curl -Lo nerdctl.tar.gz "$NERDCTL_URL"
    
    # Install to /usr/local (requires sudo)
    sudo tar -xzf nerdctl.tar.gz -C /usr/local/
    rm nerdctl.tar.gz
    
    # Verify installation
    if command -v nerdctl >/dev/null 2>&1; then
        success "nerdctl installed successfully: $(nerdctl version --short)"
    else
        error "nerdctl installation failed"
        exit 1
    fi
}

# 2. Install additional container tools
install_container_tools() {
    info "Installing container security and management tools..."
    
    # Install Trivy for security scanning
    if ! command -v trivy >/dev/null 2>&1; then
        info "Installing Trivy..."
        sudo sh -c 'echo "deb http://aquasec.github.io/trivy-repo/deb $(lsb_release -sc) main" > /etc/apt/sources.list.d/trivy.list'
        wget -qO - https://aquasec.github.io/trivy-repo/deb/public.key | sudo apt-key add -
        sudo apt-get update
        sudo apt-get install -y trivy
        success "Trivy installed"
    else
        success "Trivy already installed: $(trivy version --short)"
    fi
    
    # Install buildctl for advanced builds
    if ! command -v buildctl >/dev/null 2>&1; then
        info "Installing buildctl..."
        # buildctl is typically included with containerd, check containerd package
        if command -v containerd >/dev/null 2>&1; then
            success "buildctl should be available with containerd"
        else
            warn "containerd not found, buildctl may not be available"
        fi
    fi
}

# 3. Configure containerd namespace for K3s
configure_containerd() {
    info "Configuring containerd for K3s..."
    
    # Create containerd config directory if it doesn't exist
    CONFIG_DIR="$HOME/.config/nerdctl"
    mkdir -p "$CONFIG_DIR"
    
    # Set default namespace to K3s
    cat > "$CONFIG_DIR/nerdctl.toml" << EOF
# nerdctl configuration for K3s compatibility
namespace = "k8s.io"
debug = false
debug_full = false
insecure_registry = false
EOF
    
    success "containerd configuration created at $CONFIG_DIR/nerdctl.toml"
    
    # Add to shell profile for persistent environment
    SHELL_PROFILE=""
    if [[ -f "$HOME/.bashrc" ]]; then
        SHELL_PROFILE="$HOME/.bashrc"
    elif [[ -f "$HOME/.zshrc" ]]; then
        SHELL_PROFILE="$HOME/.zshrc"
    elif [[ -f "$HOME/.profile" ]]; then
        SHELL_PROFILE="$HOME/.profile"
    fi
    
    if [[ -n "$SHELL_PROFILE" ]]; then
        if ! grep -q "CONTAINERD_NAMESPACE" "$SHELL_PROFILE"; then
            echo "# K3s containerd namespace" >> "$SHELL_PROFILE"
            echo "export CONTAINERD_NAMESPACE=k8s.io" >> "$SHELL_PROFILE"
            success "Added CONTAINERD_NAMESPACE to $SHELL_PROFILE"
        fi
    fi
    
    # Set for current session
    export CONTAINERD_NAMESPACE=k8s.io
}

# 4. Verify K3s cluster access
verify_k3s() {
    info "Verifying K3s cluster access..."
    
    if command -v kubectl >/dev/null 2>&1; then
        if kubectl cluster-info >/dev/null 2>&1; then
            success "K3s cluster is accessible"
            kubectl get nodes --no-headers | while read -r line; do
                success "Node: $line"
            done
        else
            warn "kubectl found but cluster not accessible"
            warn "Make sure K3s is running and kubeconfig is properly set"
        fi
    else
        warn "kubectl not found - install K3s or add kubectl to PATH"
    fi
}

# 5. Create helper scripts
create_helper_scripts() {
    info "Creating helper scripts..."
    
    SCRIPTS_DIR="$HOME/.local/bin"
    mkdir -p "$SCRIPTS_DIR"
    
    # Docker-to-nerdctl wrapper
    cat > "$SCRIPTS_DIR/docker-compat" << 'EOF'
#!/bin/bash
# Docker compatibility wrapper for nerdctl

# Set K3s namespace
export CONTAINERD_NAMESPACE=k8s.io

# Map docker commands to nerdctl
case "$1" in
    "compose")
        # docker compose -> nerdctl compose or docker compose fallback
        if command -v nerdctl >/dev/null 2>&1; then
            nerdctl "$@"
        elif command -v docker compose >/dev/null 2>&1; then
            shift
            docker compose "$@"
        else
            echo "Neither nerdctl compose nor docker compose available"
            exit 1
        fi
        ;;
    *)
        # All other commands -> nerdctl
        nerdctl "$@"
        ;;
esac
EOF
    
    chmod +x "$SCRIPTS_DIR/docker-compat"
    success "Docker compatibility wrapper created at $SCRIPTS_DIR/docker-compat"
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$SCRIPTS_DIR:"* ]]; then
        if [[ -n "$SHELL_PROFILE" ]]; then
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_PROFILE"
            success "Added $SCRIPTS_DIR to PATH in $SHELL_PROFILE"
        fi
    fi
}

# 6. Test installation
test_installation() {
    info "Testing installation..."
    
    # Test nerdctl
    if command -v nerdctl >/dev/null 2>&1; then
        export CONTAINERD_NAMESPACE=k8s.io
        nerdctl version >/dev/null 2>&1 && success "nerdctl working" || warn "nerdctl test failed"
        nerdctl images >/dev/null 2>&1 && success "nerdctl images accessible" || warn "nerdctl images failed (may need containerd access)"
    fi
    
    # Test kubectl
    if command -v kubectl >/dev/null 2>&1; then
        kubectl version --client --short >/dev/null 2>&1 && success "kubectl working" || warn "kubectl test failed"
    fi
    
    # Test trivy
    if command -v trivy >/dev/null 2>&1; then
        trivy version >/dev/null 2>&1 && success "trivy working" || warn "trivy test failed"
    fi
}

# Main execution
main() {
    info "Starting K3s runner setup..."
    
    # Check prerequisites
    if ! command -v curl >/dev/null 2>&1; then
        error "curl is required but not installed"
        exit 1
    fi
    
    # Run installation steps
    install_nerdctl
    install_container_tools
    configure_containerd
    verify_k3s
    create_helper_scripts
    test_installation
    
    success "K3s runner setup complete!"
    echo ""
    info "Next steps:"
    echo "1. Restart your shell or run: source $SHELL_PROFILE"
    echo "2. Test with: nerdctl version"
    echo "3. Use updated workflows: ci-k3s.yml, test-runner-k3s.yml"
    echo ""
    warn "Note: You may need to restart the GitHub runner service for changes to take effect"
}

# Run main function
main "$@"