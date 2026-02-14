# Release Pipeline Quick Start

## Quick Reference

### Creating a Release

```bash
# Interactive helper (recommended)
./.github/scripts/create-release.sh

# Manual tag creation
git tag v1.2.3
git push origin v1.2.3

# With message
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

### Checking Releases

```bash
# List all releases
gh release list

# View specific release
gh release view v1.2.3

# Download release assets
gh release download v1.2.3
```

### Monitoring Workflow

```bash
# List workflow runs
gh run list --workflow=release.yml

# View latest run
gh run list --workflow=release.yml --limit 1 --json databaseId,conclusion,status | jq -r '.[] | "\(.databaseId): \(.status) - \(.conclusion)"'

# Watch logs in real-time
gh run watch
```

### Deleting Releases (Emergency)

```bash
# Delete release and tag
gh release delete v1.2.3 --yes
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3
```

## Version Format

```
vMAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

Examples:
  v1.0.0          - First stable release
  v1.2.3          - Bug fix release
  v2.0.0          - Major release (breaking changes)
  v1.2.3-alpha.1  - Pre-release version
  v1.2.3-beta.2   - Beta release
  v1.2.3-rc.1     - Release candidate
```

## Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

Types:
  feat:     New feature
  fix:      Bug fix
  chore:     Maintenance task
  refactor:  Code refactoring
  docs:      Documentation
  test:      Test additions/changes
  perf:      Performance improvements
  style:     Code style changes
  revert:    Revert previous commit
```

## Release Workflow Timeline

```
Tag Push → 1 min (validation)
           → 5-10 min (build & publish)
           → 2 min (create release)
           → 1 min (announcements)

Total: ~10-15 minutes
```

## Required Secrets

Set these in repository settings:

```bash
# PyPI
PYPI_API_TOKEN=<token from pypi.org>

# npm
NPM_TOKEN=<token from npmjs.com>

# Docker Hub
DOCKER_USERNAME=<username>
DOCKER_PASSWORD=<password>
```

## Troubleshooting

### Release already exists

```bash
gh release delete v1.2.3 --yes
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3
```

### Wrong version format

```bash
# Correct
git tag v1.2.3

# Wrong
git tag 1.2.3
git tag v1.2
git tag v1.2.3.4
```

### Workflow failed

```bash
# Check logs
gh run view <run-id> --log-failed

# Re-run workflow
gh run rerun <run-id>
```

## Best Practices

1. **Use Conventional Commits** - Better changelogs
2. **Test Before Release** - Ensure CI/CD passes
3. **Pre-release First** - Test with alpha/beta
4. **Review Changelog** - Check before publishing
5. **Monitor Deployments** - Verify all platforms succeed

## Release Checklist

```bash
# Before creating release
[ ] All tests passing
[ ] CI/CD green on main branch
[ ] Documentation updated
[ ] CHANGELOG.md current
[ ] Version number appropriate
[ ] Release notes prepared
[ ] Backward compatibility checked

# After release
[ ] Verify PyPI package
[ ] Verify npm package
[ ] Verify Docker images
[ ] Test installation from registry
[ ] Announce to users
[ ] Update version badges
```

## Next Steps

For detailed documentation, see:
- [Release Pipeline Documentation](.github/workflows/RELEASE-PIPELINE.md)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
