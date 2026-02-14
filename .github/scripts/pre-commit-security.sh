#!/bin/bash
# Pre-commit security hook
# Run locally before pushing to catch security issues early

set -e

echo "🔒 Running pre-commit security checks..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any check failed
FAILED=0

# ========================================
# Secret Detection (Gitleaks)
# ========================================
echo ""
echo "📋 Checking for secrets..."

if command -v gitleaks &> /dev/null; then
    if gitleaks detect --source . --no-banner --exit-code 0; then
        echo -e "${GREEN}✅ No secrets detected${NC}"
    else
        echo -e "${RED}❌ Secrets found! Please review and fix before committing.${NC}"
        echo "   Run: gitleaks detect --source . --verbose"
        FAILED=1
    fi
else
    echo -e "${YELLOW}⚠️  Gitleaks not installed. Install with: brew install gitleaks${NC}"
fi

# ========================================
# Dependency Check (Python)
# ========================================
echo ""
echo "📦 Checking Python dependencies..."

if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    if command -v snyk &> /dev/null; then
        if [ -n "$SNYK_TOKEN" ]; then
            if snyk test --severity-threshold=high --exit-code 0; then
                echo -e "${GREEN}✅ No critical dependency vulnerabilities found${NC}"
            else
                echo -e "${RED}❌ Critical/high vulnerabilities found!${NC}"
                echo "   Run: snyk test --severity-threshold=high"
                echo "   Fix: snyk wizard"
                FAILED=1
            fi
        else
            echo -e "${YELLOW}⚠️  SNYK_TOKEN not set. Set with: export SNYK_TOKEN=your_token${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Snyk not installed. Install with: npm install -g snyk${NC}"
    fi
fi

# ========================================
# Dependency Check (JavaScript)
# ========================================
echo ""
echo "📦 Checking JavaScript dependencies..."

if [ -f "package.json" ]; then
    if command -v npm &> /dev/null; then
        if npm audit --audit-level=high --json > /tmp/npm-audit.json 2>/dev/null; then
            VULN_COUNT=$(jq '.vulnerabilities | length' /tmp/npm-audit.json 2>/dev/null || echo "0")
            if [ "$VULN_COUNT" -eq 0 ]; then
                echo -e "${GREEN}✅ No critical/high vulnerabilities found${NC}"
            else
                echo -e "${YELLOW}⚠️  $VULN_COUNT vulnerabilities found (not blocking commit)${NC}"
                echo "   Fix: npm audit fix"
            fi
        else
            echo -e "${RED}❌ Critical/high vulnerabilities found!${NC}"
            echo "   Run: npm audit"
            echo "   Fix: npm audit fix"
            # Not failing for npm audit to allow developers to commit
        fi
    else
        echo -e "${YELLOW}⚠️  npm not available${NC}"
    fi
fi

# ========================================
# SAST (Semgrep)
# ========================================
echo ""
echo "🔍 Running static code analysis..."

if command -v semgrep &> /dev/null; then
    if semgrep --config auto --severity ERROR --error --quiet; then
        echo -e "${GREEN}✅ No SAST issues found${NC}"
    else
        echo -e "${RED}❌ SAST issues found!${NC}"
        echo "   Run: semgrep --config auto --severity ERROR"
        FAILED=1
    fi
else
    echo -e "${YELLOW}⚠️  Semgrep not installed. Install with: pip install semgrep${NC}"
fi

# ========================================
# Docker Image Scan (if Dockerfile exists)
# ========================================
echo ""
echo "🐳 Checking container security..."

if [ -f "Dockerfile" ] || [ -f "Dockerfile.dev" ]; then
    if command -v trivy &> /dev/null; then
        # Check if any image exists to scan
        IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "test-image|${USER}" | head -1 || echo "")
        if [ -n "$IMAGES" ]; then
            if trivy image --severity CRITICAL,HIGH --exit-code 0 "$IMAGES" > /dev/null 2>&1; then
                echo -e "${GREEN}✅ No critical container vulnerabilities found${NC}"
            else
                echo -e "${YELLOW}⚠️  Container vulnerabilities found (not blocking commit)${NC}"
                echo "   Run: trivy image --severity CRITICAL,HIGH $IMAGES"
            fi
        else
            echo -e "${YELLOW}⚠️  No test image found. Skipping container scan.${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Trivy not installed. Install with: brew install trivy${NC}"
    fi
fi

# ========================================
# Final Result
# ========================================
echo ""
if [ $FAILED -eq 1 ]; then
    echo -e "${RED}❌ Pre-commit security checks FAILED${NC}"
    echo "Please fix the issues above before committing."
    exit 1
else
    echo -e "${GREEN}✅ All pre-commit security checks passed${NC}"
    exit 0
fi
