# GitHub Actions Release Pipeline

## Overview

This directory contains the automated release pipeline for the Speecher project. The pipeline supports Python (PyPI), Node.js (npm), and Docker multi-platform publishing with automatic changelog generation.

## Files

```
.github/workflows/
├── release.yml              # Main release workflow
├── RELEASE-PIPELINE.md      # Detailed documentation
├── RELEASE-QUICKSTART.md    # Quick reference guide
└── README.md               # This file

.github/scripts/
└── create-release.sh        # Interactive release helper
```

## Quick Start

### 1. Configure Secrets

Add these to your repository settings (Settings → Secrets and variables → Actions):

| Secret | Description | Source |
|--------|-------------|---------|
| `PYPI_API_TOKEN` | PyPI production token | https://pypi.org/manage/account/token/ |
| `TEST_PYPI_API_TOKEN` | PyPI test token | https://test.pypi.org/manage/account/token/ |
| `NPM_TOKEN` | npm authentication token | https://www.npmjs.com/settings/tokens |
| `DOCKER_USERNAME` | Docker Hub username | Your Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub password | https://hub.docker.com/settings/security |

### 2. Create Release

**Option A: Interactive Helper (Recommended)**

```bash
./.github/scripts/create-release.sh
```

**Option B: Manual Tag**

```bash
git tag v1.0.0
git push origin v1.0.0
```

**Option C: GitHub UI**

1. Go to Actions tab
2. Select "Create Release" workflow
3. Click "Run workflow"
4. Enter version (e.g., `v1.0.0`)
5. Click "Run workflow"

### 3. Monitor Progress

```bash
# Watch workflow run
gh run list --workflow=release.yml
gh run watch

# View release when complete
gh release view v1.0.0
```

## What Happens During Release

```
Tag Push → Version Validation → Changelog Generation
                                        ↓
                    ┌───────────────────┴───────────────────┐
                    │                                     │
                    ▼                                     ▼
            Build & Publish                       Build & Publish
              Python Packages                      Node Packages
                    │                                     │
                    ▼                                     ▼
            ┌───────────────────┬───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
          Build &            Create Release      Announce
          Push Images       & Attach Assets    to Users
            │
            ▼
          Multi-platform
          (amd64, arm64)
```

## Version Format

The pipeline validates semantic versioning:

```
vMAJOR.MINOR.PATCH[-PRERELEASE]

Examples:
  v1.0.0          - First stable release
  v1.2.3          - Bug fix release
  v2.0.0          - Major release (breaking changes)
  v1.2.3-alpha.1  - Pre-release
  v1.2.3-beta.2   - Beta release
  v1.2.3-rc.1     - Release candidate
```

## Changelog Generation

The pipeline automatically generates changelogs from commit messages:

**Commit Format:**
```
feat: add new feature
fix: correct bug
chore: update dependencies
docs: update readme
```

**Generated Changelog:**
```markdown
## What's Changed in v1.2.3

### 🎉 Added
  - feat: add new feature

### 🐛 Fixed
  - fix: correct bug

### 🔧 Changed
  - chore: update dependencies
```

## Published Artifacts

### PyPI (Python)
```
pip install speacher==1.2.3
```

### npm (Node.js)
```
npm install speacher@1.2.3
```

### Docker (Multi-platform)
```bash
# Specific version
docker pull ghcr.io/rlagowski/speecher:1.2.3

# Latest
docker pull ghcr.io/rlagowski/speecher:latest

# Docker Hub
docker pull rlagowski/speecher:1.2.3
```

## Documentation

- [Release Pipeline Documentation](RELEASE-PIPELINE.md) - Comprehensive guide
- [Quick Start Guide](RELEASE-QUICKSTART.md) - Fast reference
- [Semantic Versioning](https://semver.org/) - Version format specification
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit format

## Troubleshooting

### Release Already Exists

```bash
gh release delete v1.2.3 --yes
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3
```

### Workflow Failed

```bash
# Check logs
gh run view <run-id> --log-failed

# Re-run
gh run rerun <run-id>
```

### Authentication Errors

1. Check secrets are configured correctly
2. Verify tokens have not expired
3. Ensure tokens have write permissions

## Support

For issues or questions:
- Check [RELEASE-PIPELINE.md](RELEASE-PIPELINE.md)
- Review workflow logs in GitHub Actions
- Open an issue in the repository
