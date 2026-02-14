#!/bin/bash
# Install security pre-commit hooks
# Usage: .github/scripts/install-security-hooks.sh

set -e

echo "🔒 Installing security pre-commit hooks..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Check if .git directory exists
if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "❌ Error: Not a git repository root"
    exit 1
fi

# Copy pre-commit hook
HOOK_SRC="$SCRIPT_DIR/pre-commit-security.sh"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"

if [ -f "$HOOK_DST" ]; then
    echo "⚠️  Pre-commit hook already exists"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

# Copy and make executable
cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"

echo "✅ Security pre-commit hook installed"
echo ""
echo "The hook will run before each commit to check:"
echo "  - Secrets (Gitleaks)"
echo "  - Python dependencies (Snyk)"
echo "  - JavaScript dependencies (npm audit)"
echo "  - Static analysis (Semgrep)"
echo "  - Container vulnerabilities (Trivy)"
echo ""
echo "Tools need to be installed locally:"
echo "  brew install gitleaks trivy"
echo "  npm install -g snyk semgrep"
echo ""
echo "Required environment variables:"
echo "  export SNYK_TOKEN=your_token"
echo ""
echo "To bypass the hook (not recommended):"
echo "  git commit --no-verify"
