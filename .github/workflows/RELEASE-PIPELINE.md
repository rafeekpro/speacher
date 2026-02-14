# Release Pipeline Documentation

This document describes the automated release pipeline for the Speecher project.

## Overview

The release pipeline is triggered by:
- Creating a git tag matching semantic versioning (`v*`)
- Manual trigger via `workflow_dispatch` with custom parameters
- Automatic trigger on main branch merge (optional, not enabled by default)

## Workflow Structure

```
┌─────────────────────┐
│  Trigger (v* tag)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Extract & Validate   │ ← Version validation
│     Version          │ ← Duplicate check
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Generate Changelog  │ ← Categorize commits
│                     │ ← List contributors
└──────────┬──────────┘
           │
    ┌──────┴──────┬───────────┬──────────┐
    │             │           │          │
    ▼             ▼           ▼          ▼
┌────────┐  ┌────────┐  ┌────────┐ ┌────────┐
│ Python │  │  Node  │  │ Docker │ │ Create │
│ Build  │  │  Build  │  │  Build │ │Release │
└────┬───┘  └────┬───┘  └────┬───┘ └────┬───┘
     │            │            │           │
     ▼            ▼            ▼           ▼
┌────────┐  ┌────────┐  ┌────────┐ ┌────────┐
│  PyPI  │  │   npm  │  │Registry│ │Announce│
│Publish │  │ Publish│  │  Push  │ │        │
└────────┘  └────────┘  └────────┘ └────────┘
```

## Version Management

### Semantic Versioning

The pipeline validates that tags follow semantic versioning:
- Format: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.3`)
- Optional pre-release: `v1.2.3-alpha.1`, `v1.2.3-beta.2`
- Invalid examples: `v1.2`, `1.2.3`, `v1.2.3.4`

### Version Extraction

```bash
# From git tag
VERSION="${GITHUB_REF#refs/tags/}"  # v1.2.3

# From manual input
VERSION="${{ github.event.inputs.version }}"
```

### Duplicate Prevention

Pipeline checks if release already exists:
```bash
if gh release view $VERSION 2>/dev/null; then
  echo "❌ Release $VERSION already exists"
  exit 1
fi
```

## Changelog Generation

### Commit Categorization

Commits are categorized using Conventional Commits format:

| Prefix | Category | Example |
|--------|----------|---------|
| `feat:` | 🎉 Added | New features |
| `chore:`, `refactor:` | 🔧 Changed | Code changes |
| `fix:` | 🐛 Fixed | Bug fixes |
| `remove:` | 🗑️ Removed | Deprecations |

### Changelog Structure

```markdown
## What's Changed in v1.2.3

**Full Changelog**: https://github.com/.../compare/v1.2.2...v1.2.3

### 🎉 Added
  - feat: add speaker diarization support
  - feat: integrate Azure Speech Services

### 🔧 Changed
  - chore: upgrade dependencies
  - refactor: improve API error handling

### 🐛 Fixed
  - fix: correct audio file upload validation
  - fix: handle WebSocket disconnections

### 🗑️ Removed
  - remove: deprecate old authentication method

### 👥 Contributors
  - @alice
  - @bob
  - @charlie

### 📝 Full Commit History
  abc1234 feat: add speaker diarization
  def5678 fix: correct audio validation
  ...
```

## Build & Publish

### Python Projects

**Detected by:** `pyproject.toml` exists

```yaml
build-python:
  - Build wheel and sdist
  - Run `twine check` for validation
  - Upload artifacts for release attachment

publish-python:
  - Test PyPI: For pre-releases/branches
  - Production PyPI: For main branch
  - Verify installation after publish
```

**Required Secrets:**
- `TEST_PYPI_API_TOKEN` - Test PyPI token
- `PYPI_API_TOKEN` - Production PyPI token

### Node.js Projects

**Detected by:** `package.json` exists

```yaml
build-node:
  - Install dependencies with `npm ci`
  - Update package version
  - Run `npm run build` if available

publish-node:
  - Publish to npm registry
  - Verify package info after publish
```

**Required Secrets:**
- `NPM_TOKEN` - npm authentication token

### Docker Projects

**Detected by:** `Dockerfile` exists

```yaml
build-docker:
  - Multi-platform builds (amd64, arm64)
  - Tag with semantic version
  - Push to Docker Hub and GHCR
  - Tag as `latest` for main branch
```

**Tags Generated:**
- `v1.2.3` - Exact version
- `v1.2` - Minor version
- `v1` - Major version
- `latest` - Latest stable

**Required Secrets:**
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password
- `GITHUB_TOKEN` - Automatic (GHCR)

## GitHub Release

### Release Creation

```yaml
create-release:
  - Create release with generated notes
  - Attach build artifacts
  - Support draft and pre-release flags
  - Update version badges in README
```

### Release Properties

| Property | Source | Notes |
|-----------|--------|-------|
| Title | Version tag | `Release v1.2.3` |
| Notes | Changelog.md | Auto-generated |
| Draft | Manual input | `--draft` flag |
| Pre-release | Manual input | `--prerelease` flag |
| Artifacts | Build outputs | Python, Node packages |

### Asset Attachments

- Python: `dist/*` (wheel, sdist)
- Node: `package.json`, `package-lock.json`, `build/`, `dist/`
- Docker: Links to registries in notes

## Announcements

### Slack Notification

**Variable:** `SLACK_WEBHOOK_URL`

```bash
curl -X POST $SLACK_WEBHOOK_URL \
  --data "{\"text\": \"🚀 New Release: $VERSION\n\n$(cat changelog.md)\"}"
```

### Release Announcement Template

```markdown
# 🚀 Speecher v1.2.3 Released

We're excited to announce the release of Speecher v1.2.3!

## What's Changed

[Full changelog]

## Installation

### Python
```bash
pip install speacher==1.2.3
```

### Docker
```bash
docker pull ghcr.io/rlagowki/speecher:1.2.3
```

## Documentation

Full documentation: https://github.com/rlagowki/Speecher

## Links

- GitHub: https://github.com/rlagowki/Speecher
- PyPI: https://pypi.org/p/speacher
- Docker Hub: https://hub.docker.com/r/rlagowki/speecher
```

## Usage

### Creating a Release

#### Method 1: Tag and Push

```bash
# Ensure main is up to date
git checkout main
git pull origin main

# Create semantic version tag
git tag v1.2.3

# Push tag to trigger release
git push origin v1.2.3
```

#### Method 2: Manual Trigger

1. Go to Actions tab in GitHub
2. Select "Create Release" workflow
3. Click "Run workflow"
4. Enter version: `v1.2.3`
5. Check "Draft" or "Pre-release" if needed
6. Click "Run workflow"

### Release Workflow

```
Tag Push (v1.2.3)
       │
       ▼
┌────────────────────┐
│ GitHub Actions     │
│ Validate Version   │
│ Generate Changelog │
└────────┬───────────┘
         │
         ▼ (5-10 minutes)
┌────────────────────┐
│ Build & Publish    │
│ - Python to PyPI   │
│ - Node to npm      │
│ - Docker to Hub    │
└────────┬───────────┘
         │
         ▼ (2-3 minutes)
┌────────────────────┐
│ Create Release      │
│ Attach Artifacts   │
└────────┬───────────┘
         │
         ▼ (1 minute)
┌────────────────────┐
│ Announcements      │
│ - Slack            │
│ - Update badges    │
└────────────────────┘
```

## Configuration

### Required Secrets

Configure these in GitHub repository settings:

| Secret | Description | Where to Get |
|--------|-------------|---------------|
| `PYPI_API_TOKEN` | Production PyPI token | https://pypi.org/manage/account/token/ |
| `TEST_PYPI_API_TOKEN` | Test PyPI token | https://test.pypi.org/manage/account/token/ |
| `NPM_TOKEN` | npm authentication token | https://www.npmjs.com/settings/tokens |
| `DOCKER_PASSWORD` | Docker Hub password | https://hub.docker.com/settings/security |
| `DOCKER_USERNAME` | Docker Hub username | Your Docker Hub username |

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | `https://hooks.slack.com/...` |

### Environment Protection

Configure environments in repository settings:

**PyPI Environment:**
- Name: `pypi`
- URL: `https://pypi.org/p/speacher`
- Required reviewers: Maintainers
- Deployment branches: `main`

**npm Environment:**
- Name: `npm`
- URL: `https://www.npmjs.com/package/speacher`
- Required reviewers: Maintainers
- Deployment branches: `main`

## Troubleshooting

### Release Already Exists

**Error:** `❌ Release v1.2.3 already exists`

**Solution:**
```bash
# Delete existing release (careful!)
gh release delete v1.2.3

# Delete tag
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3

# Re-tag and push
git tag v1.2.3
git push origin v1.2.3
```

### Invalid Semantic Version

**Error:** `❌ Invalid semantic version: 1.2.3`

**Solution:**
```bash
# Add 'v' prefix
git tag v1.2.3  # Correct
git tag 1.2.3    # Wrong
```

### PyPI Upload Fails

**Error:** `400 Invalid or missing authentication credentials`

**Solution:**
1. Check `PYPI_API_TOKEN` is set in repository secrets
2. Verify token has not expired
3. Ensure token has write permissions

### Docker Build Fails

**Error:** `unauthorized: authentication required`

**Solution:**
1. Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` are correct
2. Check Docker Hub account has access
3. Ensure GHCR token has `packages:write` permission

### Changelog is Empty

**Issue:** No commits shown between tags

**Solution:**
```bash
# Check if previous tag exists
git describe --tags --abbrev=0 HEAD^

# If no previous tag, this is expected for first release
# Subsequent releases will show commits
```

## Best Practices

### Commit Messages

Use Conventional Commits format for better changelogs:

```bash
git commit -m "feat: add speaker diarization support"
git commit -m "fix: correct audio file upload validation"
git commit -m "chore: upgrade dependencies to latest"
git commit -m "docs: update installation instructions"
```

### Pre-release Versions

```bash
# Alpha releases
git tag v1.2.3-alpha.1
git push origin v1.2.3-alpha.1

# Beta releases
git tag v1.2.3-beta.1
git push origin v1.2.3-beta.1

# RC releases
git tag v1.2.3-rc.1
git push origin v1.2.3-rc.1
```

### Production Releases

```bash
# Stable release
git tag v1.2.3
git push origin v1.2.3
```

### Draft Releases

Use manual trigger with draft flag:
1. Go to Actions → Create Release
2. Run workflow
3. Check "Create as draft"
4. Review and publish manually

## Security Considerations

### Secret Management

- Never commit tokens to repository
- Rotate tokens regularly
- Use separate tokens for test/production
- Limit token permissions to minimum required

### Environment Protection

- Enable required reviewers for production deployments
- Use protected branches for releases
- Require status checks before merging

### Package Verification

Pipeline verifies packages after publish:
```bash
# Python
pip install speacher==$VERSION
python -c "import speacher; print(speacher.__version__)"

# Node
npm info speacher@$VERSION

# Docker
docker pull ghcr.io/.../speacher:$VERSION
```

## Monitoring

### Release Status

Check release status:
```bash
# List releases
gh release list

# View release details
gh release view v1.2.3

# Download release assets
gh release download v1.2.3
```

### Workflow Runs

View workflow runs:
```bash
# List workflow runs
gh run list --workflow=release.yml

# View specific run
gh run view <run-id>

# Watch logs in real-time
gh run watch
```

## Integration with CI/CD

### Branch Protection

Configure branch protection for `main`:
- Require status checks to pass
- Require pull request reviews
- Limit who can push
- Require signed commits

### Required Checks

Before release can be created:
- ✅ Tests pass
- ✅ Linting passes
- ✅ Build succeeds
- ✅ Security scan clean

### Automated Release (Optional)

To enable automatic releases on merge to main:

```yaml
# Add to release.yml
on:
  push:
    branches:
      - main
```

**Warning:** Only enable if you have strict CI/CD controls!

## Rollback Procedure

If a release has critical issues:

### 1. Delete Release

```bash
gh release delete v1.2.3 --yes
```

### 2. Revert Tag

```bash
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3
```

### 3. Publish Hotfix

```bash
# Create hotfix version
git tag v1.2.4
git push origin v1.2.4
```

### 4. Yank Package (Last Resort)

**PyPI:**
```bash
# Requires PyPI admin privileges
# Use PyPI web interface to yank release
```

**npm:**
```bash
npm deprecate speacher@1.2.3 "Critical security issue, use 1.2.4"
```

## References

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [PyPI Publishing](https://packaging.python.org/tutorials/packaging-projects/)
- [npm Publishing](https://docs.npmjs.com/cli/v9/commands/npm-publish)
- [Docker Hub](https://docs.docker.com/docker-hub/)
