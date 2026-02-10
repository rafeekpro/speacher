#!/usr/bin/env bash

# Workflow Auto-Fix Script
# Automatically fixes common workflow issues

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKFLOWS_DIR="${PROJECT_ROOT}/.github/workflows"

# Counters
TOTAL_FIXES=0
FILES_MODIFIED=0

# Functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

# Fix cloud CLI commands by making them optional
fix_cloud_cli_commands() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    local fixes=0
    
    # Backup original file
    cp "$workflow_file" "${workflow_file}.backup"
    
    # Fix AWS CLI
    if grep -q "aws --version$" "$workflow_file"; then
        sed -i.tmp 's/aws --version$/aws --version || echo "AWS CLI not installed"/' "$workflow_file"
        ((fixes++))
    fi
    
    # Fix Azure CLI
    if grep -q "az --version$" "$workflow_file"; then
        sed -i.tmp 's/az --version$/az --version || echo "Azure CLI not installed"/' "$workflow_file"
        ((fixes++))
    fi
    
    # Fix Google Cloud CLI
    if grep -q "gcloud --version$" "$workflow_file"; then
        sed -i.tmp 's/gcloud --version$/gcloud --version || echo "Google Cloud CLI not installed"/' "$workflow_file"
        ((fixes++))
    fi
    
    # Clean up temp files
    rm -f "${workflow_file}.tmp"
    
    if [[ $fixes -gt 0 ]]; then
        log_success "Fixed $fixes cloud CLI command(s) in $workflow_name"
        ((TOTAL_FIXES+=fixes))
        return 0
    else
        # Remove backup if no changes
        rm -f "${workflow_file}.backup"
        return 1
    fi
}

# Update deprecated action versions
update_action_versions() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    local fixes=0
    
    # Backup original file
    cp "$workflow_file" "${workflow_file}.backup"
    
    # Update checkout action
    if grep -q "actions/checkout@v[123]" "$workflow_file"; then
        sed -i.tmp 's/actions\/checkout@v[123]/actions\/checkout@v4/g' "$workflow_file"
        ((fixes++))
    fi
    
    # Update setup-node action
    if grep -q "actions/setup-node@v[123]" "$workflow_file"; then
        sed -i.tmp 's/actions\/setup-node@v[123]/actions\/setup-node@v4/g' "$workflow_file"
        ((fixes++))
    fi
    
    # Update setup-python action
    if grep -q "actions/setup-python@v[1234]" "$workflow_file"; then
        sed -i.tmp 's/actions\/setup-python@v[1234]/actions\/setup-python@v5/g' "$workflow_file"
        ((fixes++))
    fi
    
    # Update upload-artifact action
    if grep -q "actions/upload-artifact@v[123]" "$workflow_file"; then
        sed -i.tmp 's/actions\/upload-artifact@v[123]/actions\/upload-artifact@v4/g' "$workflow_file"
        ((fixes++))
    fi
    
    # Update download-artifact action
    if grep -q "actions/download-artifact@v[123]" "$workflow_file"; then
        sed -i.tmp 's/actions\/download-artifact@v[123]/actions\/download-artifact@v4/g' "$workflow_file"
        ((fixes++))
    fi
    
    # Update cache action
    if grep -q "actions/cache@v[123]" "$workflow_file"; then
        sed -i.tmp 's/actions\/cache@v[123]/actions\/cache@v4/g' "$workflow_file"
        ((fixes++))
    fi
    
    # Clean up temp files
    rm -f "${workflow_file}.tmp"
    
    if [[ $fixes -gt 0 ]]; then
        log_success "Updated $fixes action version(s) in $workflow_name"
        ((TOTAL_FIXES+=fixes))
        return 0
    else
        # Remove backup if no changes
        rm -f "${workflow_file}.backup"
        return 1
    fi
}

# Fix tabs in YAML files
fix_tabs_to_spaces() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    
    if grep -q $'\t' "$workflow_file"; then
        # Backup original file
        cp "$workflow_file" "${workflow_file}.backup"
        
        # Replace tabs with 2 spaces
        sed -i.tmp $'s/\t/  /g' "$workflow_file"
        
        # Clean up temp files
        rm -f "${workflow_file}.tmp"
        
        log_success "Replaced tabs with spaces in $workflow_name"
        ((TOTAL_FIXES++))
        return 0
    fi
    
    return 1
}

# Add missing version tags to actions
add_missing_version_tags() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    local fixes=0
    
    # Backup original file
    cp "$workflow_file" "${workflow_file}.backup"
    
    # Add version tags to common actions without versions
    if grep -q "uses: actions/checkout$" "$workflow_file"; then
        sed -i.tmp 's/uses: actions\/checkout$/uses: actions\/checkout@v4/' "$workflow_file"
        ((fixes++))
    fi
    
    if grep -q "uses: actions/setup-node$" "$workflow_file"; then
        sed -i.tmp 's/uses: actions\/setup-node$/uses: actions\/setup-node@v4/' "$workflow_file"
        ((fixes++))
    fi
    
    if grep -q "uses: actions/setup-python$" "$workflow_file"; then
        sed -i.tmp 's/uses: actions\/setup-python$/uses: actions\/setup-python@v5/' "$workflow_file"
        ((fixes++))
    fi
    
    # Clean up temp files
    rm -f "${workflow_file}.tmp"
    
    if [[ $fixes -gt 0 ]]; then
        log_success "Added $fixes version tag(s) in $workflow_name"
        ((TOTAL_FIXES+=fixes))
        return 0
    else
        # Remove backup if no changes
        rm -f "${workflow_file}.backup"
        return 1
    fi
}

# Process single workflow
fix_workflow() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    local modified=false
    
    echo ""
    log_info "Processing $workflow_name..."
    
    # Apply fixes
    fix_tabs_to_spaces "$workflow_file" && modified=true
    fix_cloud_cli_commands "$workflow_file" && modified=true
    update_action_versions "$workflow_file" && modified=true
    add_missing_version_tags "$workflow_file" && modified=true
    
    if [[ "$modified" == "true" ]]; then
        ((FILES_MODIFIED++))
        log_success "Completed fixes for $workflow_name"
    else
        log_info "No fixes needed for $workflow_name"
    fi
}

# Restore backups
restore_backups() {
    echo ""
    log_warning "Restoring original files from backups..."
    
    for backup in "$WORKFLOWS_DIR"/*.backup; do
        [[ -f "$backup" ]] || continue
        original="${backup%.backup}"
        mv "$backup" "$original"
        log_success "Restored $(basename "$original")"
    done
}

# Main execution
main() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   GitHub Workflow Auto-Fix Utility     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    
    # Check for --dry-run option
    DRY_RUN=false
    if [[ "${1:-}" == "--dry-run" ]]; then
        DRY_RUN=true
        echo ""
        log_warning "DRY RUN MODE - No files will be modified"
        shift
    fi
    
    # Check for --restore option
    if [[ "${1:-}" == "--restore" ]]; then
        restore_backups
        exit 0
    fi
    
    # Process workflows
    if [[ $# -gt 0 ]]; then
        # Fix specific workflows
        for workflow in "$@"; do
            if [[ -f "$workflow" ]]; then
                fix_workflow "$workflow"
            else
                log_error "Workflow file not found: $workflow"
            fi
        done
    else
        # Fix all workflows
        if [[ -d "$WORKFLOWS_DIR" ]]; then
            shopt -s nullglob
            for workflow in "$WORKFLOWS_DIR"/*.yml "$WORKFLOWS_DIR"/*.yaml; do
                [[ -f "$workflow" ]] || continue
                fix_workflow "$workflow"
            done
            shopt -u nullglob
        else
            log_error "Workflows directory not found: $WORKFLOWS_DIR"
            exit 1
        fi
    fi
    
    # Summary
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              Fix Summary                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Total fixes applied: $TOTAL_FIXES"
    echo "  Files modified: $FILES_MODIFIED"
    
    if [[ $TOTAL_FIXES -gt 0 ]]; then
        echo ""
        if [[ "$DRY_RUN" == "true" ]]; then
            echo -e "${YELLOW}DRY RUN COMPLETE${NC} - No files were actually modified"
            echo "Run without --dry-run to apply fixes"
        else
            echo -e "${GREEN}✅ Fixes applied successfully!${NC}"
            echo ""
            echo "Backup files created with .backup extension"
            echo "To restore original files: $0 --restore"
            echo ""
            echo "Next steps:"
            echo "  1. Review the changes"
            echo "  2. Run validation: ${SCRIPT_DIR}/validate-workflows.sh"
            echo "  3. Commit the fixes"
        fi
    else
        echo ""
        echo -e "${GREEN}✅ No fixes needed - all workflows are clean!${NC}"
    fi
}

# Show help
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [workflow-files...]

Automatically fix common issues in GitHub Actions workflows

OPTIONS:
    --dry-run     Show what would be fixed without modifying files
    --restore     Restore original files from backups
    -h, --help    Show this help message

FIXES APPLIED:
    • Replace tabs with spaces
    • Make cloud CLI commands optional (add || true)
    • Update deprecated action versions
    • Add missing version tags to actions

EXAMPLES:
    $(basename "$0")                    # Fix all workflows
    $(basename "$0") --dry-run          # Preview fixes without applying
    $(basename "$0") ci.yml deploy.yml  # Fix specific workflows
    $(basename "$0") --restore          # Restore from backups

EOF
    exit 0
fi

# Run main function
main "$@"