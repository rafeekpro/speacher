#!/usr/bin/env bash

# Install Git Hooks Script
# Sets up the pre-push workflow validation hook

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get repository root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOKS_DIR="${REPO_ROOT}/.githooks"
GIT_HOOKS_DIR="${REPO_ROOT}/.git/hooks"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Git Hooks Installation Script      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in a git repository
if [[ ! -d "${REPO_ROOT}/.git" ]]; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Check if hooks directory exists
if [[ ! -d "$HOOKS_DIR" ]]; then
    echo -e "${RED}Error: Hooks directory not found at $HOOKS_DIR${NC}"
    exit 1
fi

# Function to install a hook
install_hook() {
    local hook_name=$1
    local source_file="${HOOKS_DIR}/${hook_name}"
    local target_file="${GIT_HOOKS_DIR}/${hook_name}"
    
    if [[ ! -f "$source_file" ]]; then
        echo -e "${YELLOW}⚠ Warning: Hook ${hook_name} not found in ${HOOKS_DIR}${NC}"
        return 1
    fi
    
    # Backup existing hook if it exists
    if [[ -f "$target_file" ]] && [[ ! -L "$target_file" ]]; then
        echo -e "${YELLOW}Backing up existing ${hook_name} hook...${NC}"
        mv "$target_file" "${target_file}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create symlink
    ln -sf "$source_file" "$target_file"
    echo -e "${GREEN}✓${NC} Installed ${hook_name} hook"
    
    return 0
}

# Install pre-push hook
echo "Installing Git hooks..."
echo ""

install_hook "pre-push"

# Alternative: Configure Git to use the hooks directory
echo ""
echo "Configuring Git to use custom hooks directory..."
git config core.hooksPath "$HOOKS_DIR"
echo -e "${GREEN}✓${NC} Git configured to use ${HOOKS_DIR}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Git hooks installed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "The following hooks are now active:"
echo "  • pre-push: Validates GitHub workflows before pushing"
echo ""
echo "To skip hook validation (not recommended):"
echo "  git push --no-verify"
echo ""
echo "To test workflow validation manually:"
echo "  ${REPO_ROOT}/.github/scripts/validate-workflows.sh"
echo ""
echo "To uninstall hooks:"
echo "  git config --unset core.hooksPath"
echo ""