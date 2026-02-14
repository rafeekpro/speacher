#!/bin/bash
# Create Release Helper Script
# Automates the release creation process with proper validation

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_git_status() {
    log_info "Checking git status..."

    if [ -n "$(git status --porcelain)" ]; then
        log_error "Working directory is not clean"
        echo ""
        git status --short
        echo ""
        log_error "Please commit or stash changes before creating a release"
        exit 1
    fi

    log_success "Working directory is clean"
}

check_current_branch() {
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    log_info "Current branch: $current_branch"

    if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
        log_warning "Not on main/master branch"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Release cancelled"
            exit 0
        fi
    fi
}

validate_version_format() {
    local version=$1

    if [[ ! $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
        log_error "Invalid semantic version: $version"
        echo ""
        echo "Valid formats:"
        echo "  v1.2.3          - Stable release"
        echo "  v1.2.3-alpha.1  - Pre-release"
        echo "  v1.2.3-beta.2   - Pre-release"
        echo "  v1.2.3-rc.3     - Release candidate"
        exit 1
    fi

    log_success "Version format is valid: $version"
}

check_tag_exists() {
    local tag=$1

    if git rev-parse "$tag" >/dev/null 2>&1; then
        log_warning "Tag $tag already exists locally"
        read -p "Delete existing tag? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git tag -d "$tag"
            log_success "Deleted local tag: $tag"
        else
            log_info "Release cancelled"
            exit 0
        fi
    fi

    if git ls-remote --tags origin | grep -q "refs/tags/$tag"; then
        log_warning "Tag $tag already exists on remote"
        log_error "Please delete remote tag first:"
        echo "  git push origin :refs/tags/$tag"
        exit 1
    fi
}

get_version_from_commits() {
    log_info "Analyzing recent commits..."

    local last_tag=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
    local commit_count=$(git rev-list --count ${last_tag}..HEAD 2>/dev/null || git rev-list --count HEAD)

    if [ -z "$last_tag" ]; then
        log_info "No previous tags found - this will be the first release"
    else
        log_info "Last tag: $last_tag"
        log_info "Commits since last tag: $commit_count"
    fi

    # Suggest version bump
    if [ -n "$last_tag" ]; then
        local major=$(echo $last_tag | sed 's/v//' | cut -d. -f1)
        local minor=$(echo $last_tag | sed 's/v//' | cut -d. -f2)
        local patch=$(echo $last_tag | sed 's/v//' | cut -d. -f3 | cut -d- -f1)

        echo ""
        log_info "Suggested versions:"
        echo "  v$((major+1)).0.0         - Major release (breaking changes)"
        echo "  v$major.$((minor+1)).0     - Minor release (new features)"
        echo "  v$major.$minor.$((patch+1)) - Patch release (bug fixes)"
    fi
}

show_commit_summary() {
    local version=$1

    log_info "Commits to be included in release:"

    local last_tag=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
    if [ -z "$last_tag" ]; then
        git log --oneline --graph --all | head -20
    else
        git log ${last_tag}..HEAD --oneline
    fi

    echo ""
    log_info "Categorized changes:"
    echo ""

    echo "🎉 Added:"
    git log ${last_tag}..HEAD --grep='^feat' --oneline | sed 's/^/  /' || echo "  - No new features"

    echo ""
    echo "🐛 Fixed:"
    git log ${last_tag}..HEAD --grep='^fix' --oneline | sed 's/^/  /' || echo "  - No bug fixes"

    echo ""
    echo "🔧 Changed:"
    git log ${last_tag}..HEAD --grep='^chore\|^refactor' --oneline | sed 's/^/  /' || echo "  - No changes"
}

confirm_release() {
    local version=$1

    echo ""
    log_warning "About to create release: $version"
    echo ""
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Release cancelled"
        exit 0
    fi
}

create_tag() {
    local version=$1
    local message=$2

    log_info "Creating tag: $version"
    git tag -a "$version" -m "$message"
    log_success "Tag created locally"
}

push_tag() {
    local version=$1

    log_info "Pushing tag to remote..."
    git push origin "$version"
    log_success "Tag pushed to remote"
}

show_workflow_status() {
    local version=$1

    echo ""
    log_info "Release workflow started:"
    echo "  https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
    echo ""
    log_info "Monitor workflow progress:"
    echo "  gh run list --workflow=release.yml"
    echo ""
    log_info "View release when ready:"
    echo "  gh release view $version"
}

# Main execution
main() {
    echo ""
    echo "🚀 Release Creation Helper"
    echo "======================="
    echo ""

    # Pre-flight checks
    check_git_status
    check_current_branch

    # Get or suggest version
    get_version_from_commits

    echo ""
    read -p "Enter version tag (e.g., v1.2.3): " VERSION

    if [ -z "$VERSION" ]; then
        log_error "Version is required"
        exit 1
    fi

    # Validate version
    validate_version_format "$VERSION"
    check_tag_exists "$VERSION"

    # Show commit summary
    show_commit_summary "$VERSION"

    # Confirm release
    local message="Release $VERSION"
    confirm_release "$VERSION"

    # Create and push tag
    create_tag "$VERSION" "$message"
    push_tag "$VERSION"

    # Show workflow info
    show_workflow_status "$VERSION"

    log_success "Release trigger complete!"
    echo ""
    log_info "Next steps:"
    echo "  1. Monitor GitHub Actions workflow"
    echo "  2. Verify release when complete"
    echo "  3. Announce release to users"
}

# Run main function
main "$@"
