# Security Quick Start Guide

Quick reference for developers to run security scans locally and understand results.

## Prerequisites

### Install Security Tools

```bash
# macOS
brew install gitleaks trivy tfsec
npm install -g snyk semgrep

# Linux
curl -s https://raw.githubusercontent.com/gitleaks/gitleaks/master/scripts/install.sh | bash
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
npm install -g snyk semgrep

# Verify installation
gitleaks --version
trivy --version
snyk --version
semgrep --version
```

### Configure Environment

```bash
# Set Snyk token (get from https://snyk.io/account)
export SNYK_TOKEN="your-token-here"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export SNYK_TOKEN="your-token-here"' >> ~/.bashrc
```

## Local Scanning Commands

### 1. Secret Detection

```bash
# Scan entire repo
gitleaks detect --source . --verbose

# Scan specific directory
gitleaks detect --source ./src

# Scan with custom config
gitleaks detect --source . --config .gitleaks.toml
```

### 2. Dependency Scanning

#### Python
```bash
# Scan Python dependencies
snyk test --severity-threshold=high

# Interactive fix
snyk wizard

# Monitor for new vulnerabilities
snyk monitor
```

#### JavaScript
```bash
# Audit npm dependencies
npm audit

# Fix automatically
npm audit fix

# Fix with force (use carefully)
npm audit fix --force
```

### 3. Container Scanning

```bash
# Scan Docker image
trivy image your-image:tag

# Scan filesystem
trivy fs .

# Scan with severity filter
trivy image --severity CRITICAL,HIGH your-image:tag

# Generate report
trivy image --format json --output report.json your-image:tag
```

### 4. Static Code Analysis

```bash
# Run with default rules
semgrep --config auto .

# Run with specific ruleset
semgrep --config security .

# Check only errors
semgrep --config auto --severity ERROR .

# Auto-fix some issues
semgrep --config auto --autofix .
```

### 5. Infrastructure Scanning

```bash
# Terraform
tfsec .

# Kubernetes manifests
docker run --rm -v $(pwd):/workdir zegl/kube-score:latest /workdir/k8s/*.yaml
```

## Pre-Commit Hook Installation

```bash
# Install automated security checks on commits
.github/scripts/install-security-hooks.sh

# To bypass (not recommended)
git commit --no-verify
```

## Understanding Results

### Severity Levels

- **CRITICAL**: Immediate action required, blocks deployment
- **HIGH**: Fix within 1 week, blocks deployment
- **MEDIUM**: Fix within 1 month, warning only
- **LOW**: Technical debt, fix when convenient

### Common Issues and Fixes

#### Secret Detected
```
❌ FOUND: api-key in src/config.py:42
```
**Fix**:
1. Rotate the exposed credential
2. Remove from code
3. Use environment variable
4. Remove from git history

#### SQL Injection
```
❌ FOUND: SQL injection in api/users.py:123
```
**Fix**:
```python
# BAD
query = f"SELECT * FROM users WHERE id = {user_id}"

# GOOD
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

#### XSS Vulnerability
```
❌ FOUND: Cross-site scripting in web/views.py:45
```
**Fix**:
```python
# BAD
return f"<div>{user_input}</div>"

# GOOD
from markupsafe import escape
return f"<div>{escape(user_input)}</div>"
```

#### Dependency Vulnerability
```
❌ FOUND: CVE-2023-1234 in flask@2.0.0
```
**Fix**:
```bash
# Upgrade to safe version
pip install flask==2.0.3

# Or use Snyk wizard
snyk wizard
```

## CI/CD Pipeline

### Workflow Triggers

- **Push to main/master/develop**: Full security scan
- **Pull Request**: Full security scan + PR comment
- **Manual**: Trigger via GitHub Actions tab

### Pipeline Stages

1. **SAST** (Semgrep) - ~2 minutes
2. **Dependency Scan** (Snyk, npm audit) - ~3 minutes
3. **Container Scan** (Trivy) - ~4 minutes
4. **Secret Scan** (Gitleaks) - ~1 minute
5. **IaC Scan** (tfsec, kube-score) - ~2 minutes

**Total**: ~12 minutes for full scan

### Viewing Results

1. **GitHub Security Tab**: Code scanning alerts
2. **Workflow Run Page**: Artifacts and logs
3. **PR Comments**: Summary of findings

## Best Practices

### Before Committing

```bash
# Run full security scan locally
make security-scan

# Or individual scans
gitleaks detect --source .
snyk test --severity-threshold=high
npm audit --audit-level=high
semgrep --config auto --severity ERROR .
```

### Before Pushing

1. Ensure all security checks pass locally
2. Review pre-commit hook output
3. Check CI/CD results after push
4. Address any findings promptly

### Handling Vulnerabilities

1. **Assess impact**: Does it affect our usage?
2. **Check mitigation**: Are we already protected?
3. **Plan fix**: Create ticket, set priority
4. **Document**: Note why acceptable (if temporary)
5. **Follow up**: Don't ignore indefinitely

## Resources

- **Full Documentation**: `.github/SECURITY-SCAN.md`
- **Security Checklist**: `.claude/rules/security-checklist.md`
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE**: https://cwe.mitre.org/

## Support

Questions? Create GitHub issue with `security` label.
