# Security Scanning Pipeline

This document describes the automated security scanning pipeline implemented for this project.

## Overview

The security pipeline runs on every push to main/master/develop branches and on all pull requests. It performs comprehensive security checks across multiple dimensions:

- **SAST** (Static Application Security Testing)
- **Dependency Scanning** (Snyk, npm audit)
- **Container Scanning** (Trivy)
- **Secret Detection** (Gitleaks)
- **IaC Scanning** (tfsec, kube-score)

## Required Secrets

Configure these secrets in your GitHub repository settings:

### Snyk Token (Required for dependency scanning)
1. Sign up at https://snyk.io
2. Get your API token from https://snyk.io/account
3. Add as repository secret: `SNYK_TOKEN`

### Gitleaks License (Optional - for advanced features)
1. Get license at https://github.com/gitleaks/gitleaks
2. Add as repository secret: `GITLEAKS_LICENSE`

## Workflow Jobs

### 1. SAST - Semgrep
**Purpose**: Detect code-level security vulnerabilities

**Checks for**:
- SQL injection
- Cross-site scripting (XSS)
- Command injection
- Path traversal
- Insecure deserialization
- Cryptographic issues

**Severity**: Fails on ERROR and WARNING

**Output**:
- SARIF report for GitHub Security tab
- JSON artifacts for detailed review

**Remediation**:
```bash
# Run locally
semgrep --config auto --severity ERROR
```

### 2. Dependency Scanning

#### Snyk (Python dependencies)
**Purpose**: Check for known vulnerabilities in Python packages

**Scans**:
- `requirements.txt`
- `pyproject.toml`
- `setup.py`
- `Pipfile`

**Severity**: Fails on HIGH and CRITICAL

**Remediation**:
```bash
# Install Snyk
npm install -g snyk

# Scan locally
snyk test --severity-threshold=high

# Fix vulnerabilities
snyk wizard
```

#### npm audit (JavaScript dependencies)
**Purpose**: Check for known vulnerabilities in npm packages

**Scans**:
- `package.json` and `package-lock.json`
- Transitive dependencies

**Severity**: Fails on HIGH and CRITICAL

**Remediation**:
```bash
# Run locally
npm audit

# Fix automatically
npm audit fix

# Fix manually
npm audit fix --force  # Use with caution
```

### 3. Container Scanning - Trivy
**Purpose**: Scan container images and filesystem for vulnerabilities

**Scans**:
- Container image vulnerabilities
- Filesystem security issues
- License compliance
- Secret leakage in images

**Severity**: Fails on CRITICAL and HIGH

**Remediation**:
```bash
# Install Trivy
brew install trivy  # macOS
# or
docker pull aquasec/trivy:latest

# Scan image locally
trivy image --severity CRITICAL,HIGH your-image:tag

# Scan filesystem
trivy fs --severity CRITICAL,HIGH .
```

### 4. Secret Detection - Gitleaks
**Purpose**: Detect secrets, credentials, and sensitive data in code

**Detects**:
- API keys (AWS, Google Cloud, Azure, Stripe, etc.)
- Database credentials
- Certificates and keys
- Tokens and passwords
- PII (Personally Identifiable Information)

**Severity**: Fails on ANY finding (zero tolerance)

**Exclusions**:
- `node_modules/`
- `.venv/`, `venv/`, `__pycache__/`
- `.git/`
- Test fixtures (if marked appropriately)

**Remediation**:
```bash
# Install Gitleaks
brew install gitleaks  # macOS
# or
docker pull gitleaks/gitleaks:latest

# Scan locally
gitleaks detect --source . --verbose

# Scan specific file
gitleaks detect --source ./path/to/file
```

**If secrets found**:
1. **IMMEDIATELY** rotate all exposed credentials
2. Remove from git history: `git filter-branch` or BFG Repo-Cleaner
3. Add to `.gitleaks/config.toml` if false positive
4. Update secret detection patterns

### 5. IaC Scanning

#### tfsec (Terraform)
**Purpose**: Scan Terraform infrastructure for security misconfigurations

**Checks**:
- S3 bucket permissions
- Security group rules
- IAM policies
- Encryption settings
- Logging configuration

**Severity**: Fails on CRITICAL

**Remediation**:
```bash
# Install tfsec
brew install tfsec  # macOS
# or
docker pull tfsec/tfsec:latest

# Scan locally
tfsec .
```

#### kube-score (Kubernetes)
**Purpose**: Analyze Kubernetes manifests for best practices

**Checks**:
- Container security context
- Resource limits
- Health checks
- Pod anti-affinity
- Network policies

**Severity**: Warnings only (doesn't fail CI)

**Remediation**:
```bash
# Run locally
docker run --rm -v $(pwd):/workdir zegl/kube-score:latest /workdir/k8s/*.yaml
```

## Reports and Artifacts

### SARIF Reports
Uploaded to GitHub Security tab for:
- Semgrep (SAST)
- Snyk (dependencies)
- Trivy (containers)

View in: **Security → Code scanning alerts**

### Artifacts
Downloadable from workflow run page:
- `sast-results/` - Semgrep reports
- `dependency-scan-*` - Snyk and npm audit results
- `container-scan-results/` - Trivy reports
- `secret-scan-results/` - Gitleaks findings
- `iac-scan-results/` - tfsec and kube-score results

### PR Comments
Automated comment on PRs includes:
- Overall security status
- Summary of findings by category
- Actionable remediation steps
- Links to detailed reports

## Failure Conditions

The workflow will **FAIL** if:

1. **SAST**: Any ERROR or WARNING severity findings
2. **Secret Detection**: ANY potential secrets found (zero tolerance)
3. **Container Scan**: Any CRITICAL vulnerabilities
4. **Dependency Scan**: Any CRITICAL or HIGH severity vulnerabilities
5. **IaC Scan**: Any CRITICAL misconfigurations

## Best Practices

### Prevention

1. **Run scans locally** before pushing
2. **Enable pre-commit hooks** for secret detection
3. **Review dependencies** before adding them
4. **Use base images** from trusted sources
5. **Keep dependencies updated**

### Pre-commit Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "🔒 Running security checks..."

# Secret scan
if command -v gitleaks &> /dev/null; then
    gitleaks detect --source . --no-banner || exit 1
fi

# Dependency check (Python)
if [ -f "requirements.txt" ] && command -v snyk &> /dev/null; then
    snyk test --severity-threshold=high || exit 1
fi

# Dependency check (JavaScript)
if [ -f "package.json" ] && command -v npm &> /dev/null; then
    npm audit --audit-level=high || exit 1
fi

echo "✅ Security checks passed"
```

Install:
```bash
chmod +x .git/hooks/pre-commit
```

### Handling False Positives

#### Semgrep
Create `.semgrep/ignore.yml`:
```yaml
rules:
  - id: python.lang.correctness.useless-comparison
    ignore: |
      **/test_*.py
      tests/**/*.py
```

#### Snyk
Mark as ignored in Snyk dashboard with justification

#### Trivy
Add to `.trivyignore`:
```
# Acceptable risk for now
CVE-2023-1234
```

#### Gitleaks
Add to `.gitleaks/config.toml`:
```toml
[allowlist]
  description = "Test fixtures"
  files = [
    '''fixtures/.*''',
    '''tests/.*\.json''',
  ]
```

**IMPORTANT**: Always document justification for false positives

## Continuous Improvement

### Monthly Review
- Review scan results and trends
- Update false positive rules
- Identify recurring issues
- Add custom rules for project-specific patterns

### Quarterly Tasks
- Update security tool versions
- Review and adjust severity thresholds
- Update .gitignore patterns
- Audit and remove unnecessary ignore rules

### Training
- Security awareness for developers
- OWASP Top 10 review
- Secure coding practices
- Incident response procedures

## Emergency Procedures

### If secrets are detected

1. **IMMEDIATE ACTIONS** (< 1 hour)
   - Rotate all exposed credentials
   - Revoke compromised tokens
   - Notify security team

2. **WITHIN 24 HOURS**
   - Remove from git history
   - Investigate scope of exposure
   - Document incident

3. **PREVENTION**
   - Add to pre-commit hooks
   - Update detection patterns
   - Review developer access

### If critical vulnerabilities found

1. **STOP DEPLOYMENT**
   - Block merge to main
   - Notify team immediately

2. **ASSESS IMPACT**
   - Check if exploited in production
   - Review affected versions

3. **REMEDIATE**
   - Patch or upgrade dependencies
   - Implement mitigations
   - Test fixes thoroughly

## Resources

- **Security Checklist**: `.claude/rules/security-checklist.md`
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/
- **GitHub Security**: https://docs.github.com/en/code-security

## Support

For questions or issues with the security pipeline:
1. Check this documentation first
2. Review tool-specific documentation (links above)
3. Contact security team: security@yourcompany.com
4. Create GitHub issue with `security` label
