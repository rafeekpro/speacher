#!/bin/bash

# setup-nerdctl.sh
# Sets up nerdctl for K3s containerd runners without requiring sudo
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔧 Setting up nerdctl for K3s containerd runners..."

# Check if nerdctl is already available
if command -v nerdctl >/dev/null 2>&1; then
    echo -e "${GREEN}✅ nerdctl already available: $(nerdctl version | head -n 1)${NC}"
else
    echo -e "${YELLOW}⚠️ nerdctl not found - installing to user directory...${NC}"
    
    # Create user bin directory
    mkdir -p "$HOME/bin"
    
    # Download and extract nerdctl to user directory
    NERDCTL_VERSION="1.7.1"
    NERDCTL_URL="https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-full-${NERDCTL_VERSION}-linux-amd64.tar.gz"
    
    echo "📥 Downloading nerdctl v${NERDCTL_VERSION}..."
    curl -fsSL -o nerdctl.tar.gz "${NERDCTL_URL}"
    
    echo "📦 Extracting nerdctl..."
    tar -xzf nerdctl.tar.gz -C "$HOME/bin" --strip-components=1 bin/nerdctl
    rm nerdctl.tar.gz
    
    # Make nerdctl executable
    chmod +x "$HOME/bin/nerdctl"
    
    # Add to PATH for current session
    export PATH="$HOME/bin:$PATH"
    
    # Persist PATH for GitHub Actions steps
    if [[ -n "${GITHUB_PATH:-}" ]]; then
        echo "$HOME/bin" >> "$GITHUB_PATH"
    fi
    
    echo -e "${GREEN}✅ nerdctl installed to $HOME/bin${NC}"
fi

# Set containerd namespace for K3s
echo "🔧 Configuring containerd namespace for K3s..."
export CONTAINERD_NAMESPACE=k8s.io

# Persist environment variable for GitHub Actions
if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "CONTAINERD_NAMESPACE=k8s.io" >> "$GITHUB_ENV"
fi

# Verify nerdctl installation and configuration
echo "🧪 Verifying nerdctl installation..."
if nerdctl version >/dev/null 2>&1; then
    echo -e "${GREEN}✅ nerdctl version: $(nerdctl version | head -n 1)${NC}"
else
    echo -e "${RED}❌ nerdctl verification failed${NC}"
    exit 1
fi

# Test basic containerd access (may fail without proper permissions)
echo "🔍 Testing containerd access..."
if nerdctl info >/dev/null 2>&1; then
    echo -e "${GREEN}✅ containerd access working${NC}"
else
    echo -e "${YELLOW}⚠️ containerd access limited (may need additional permissions)${NC}"
    echo "This is normal for some K3s setups - image building may still work"
fi

echo -e "${GREEN}🎉 nerdctl setup completed successfully!${NC}"
echo "You can now use nerdctl as a drop-in replacement for docker commands."