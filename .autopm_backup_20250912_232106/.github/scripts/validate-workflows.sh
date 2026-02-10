#!/usr/bin/env bash

# Workflow Validation Script
# Validates GitHub Actions workflows before push to prevent CI/CD failures
# Usage: ./validate-workflows.sh [workflow-file]

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
CONFIG_FILE="${SCRIPT_DIR}/validation-config.json"

# Counters
TOTAL_WORKFLOWS=0
PASSED_WORKFLOWS=0
FAILED_WORKFLOWS=0
WARNINGS_COUNT=0

# Arrays to track issues
declare -a ERRORS
declare -a WARNINGS

# Load configuration if exists
if [[ -f "${CONFIG_FILE}" ]]; then
    # Parse JSON config (basic parsing for shell)
    SKIP_CLOUD_TOOLS=$(grep -o '"skip_cloud_tools"[[:space:]]*:[[:space:]]*[^,}]*' "${CONFIG_FILE}" 2>/dev/null | grep -o 'true\|false' || echo "false")
    STRICT_MODE=$(grep -o '"strict_mode"[[:space:]]*:[[:space:]]*[^,}]*' "${CONFIG_FILE}" 2>/dev/null | grep -o 'true\|false' || echo "false")
else
    SKIP_CLOUD_TOOLS="false"
    STRICT_MODE="false"
fi

# Functions
log_error() {
    echo -e "${RED}✗ ERROR:${NC} $1" >&2
    ERRORS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
    WARNINGS+=("$1")
    ((WARNINGS_COUNT++))
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Validate YAML syntax
validate_yaml_syntax() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    
    log_info "Validating YAML syntax for ${workflow_name}..."
    
    # Check for YAML parser
    if command_exists yq; then
        if ! yq eval '.' "$workflow_file" > /dev/null 2>&1; then
            log_error "${workflow_name}: Invalid YAML syntax"
            return 1
        fi
    elif command_exists python3; then
        # Try with PyYAML if available
        if python3 -c "import yaml" 2>/dev/null; then
            if ! python3 -c "import yaml; yaml.safe_load(open('$workflow_file'))" 2>/dev/null; then
                log_error "${workflow_name}: Invalid YAML syntax"
                return 1
            fi
        else
            # Basic YAML check - look for obvious syntax errors
            if grep -E '^\t' "$workflow_file" > /dev/null; then
                log_error "${workflow_name}: YAML files must use spaces, not tabs"
                return 1
            fi
            log_info "${workflow_name}: Basic YAML structure check passed (install python3-yaml for full validation)"
        fi
    else
        log_warning "No YAML parser found (install yq or python3-yaml for syntax validation)"
    fi
    
    return 0
}

# Check for common workflow issues
check_workflow_structure() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    local has_errors=0
    
    log_info "Checking workflow structure for ${workflow_name}..."
    
    # Check for required fields
    if ! grep -q "^name:" "$workflow_file"; then
        log_warning "${workflow_name}: Missing 'name' field"
    fi
    
    if ! grep -q "^on:" "$workflow_file"; then
        log_error "${workflow_name}: Missing 'on' trigger definition"
        has_errors=1
    fi
    
    if ! grep -q "^jobs:" "$workflow_file"; then
        log_error "${workflow_name}: Missing 'jobs' definition"
        has_errors=1
    fi
    
    # Check for deprecated actions
    if grep -q "actions/checkout@v[12]" "$workflow_file"; then
        log_warning "${workflow_name}: Using deprecated checkout version (upgrade to v4)"
    fi
    
    if grep -q "actions/setup-node@v[12]" "$workflow_file"; then
        log_warning "${workflow_name}: Using deprecated setup-node version (upgrade to v4)"
    fi
    
    # Check for hardcoded secrets
    if grep -E '\$\{\{[^}]*secrets\.[^}]*\}\}' "$workflow_file" | grep -v "secrets\.GITHUB_TOKEN" > /dev/null; then
        local secrets=$(grep -oE 'secrets\.[A-Z_]+' "$workflow_file" | sort -u)
        log_info "${workflow_name}: Uses secrets: $(echo $secrets | tr '\n' ' ')"
    fi
    
    return $has_errors
}

# Validate commands in workflow
validate_commands() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    local has_errors=0
    
    log_info "Validating commands in ${workflow_name}..."
    
    # Extract run commands (basic extraction)
    local commands=$(grep -A 10 "run:" "$workflow_file" | grep -v "^--$" | sed 's/^[[:space:]]*run:[[:space:]]*//')
    
    # Check for potentially missing commands
    while IFS= read -r cmd; do
        [[ -z "$cmd" || "$cmd" =~ ^# ]] && continue
        
        # Extract the first command from the line
        local base_cmd=$(echo "$cmd" | awk '{print $1}' | sed 's/|.*//' | sed 's/;.*//')
        
        # Skip shell built-ins and common commands
        case "$base_cmd" in
            echo|cd|export|source|if|then|else|fi|for|while|do|done|true|false|test|\[|\[\[)
                continue
                ;;
        esac
        
        # Cloud CLI tools (often not available locally)
        case "$base_cmd" in
            aws|az|gcloud)
                if [[ "$SKIP_CLOUD_TOOLS" == "false" ]]; then
                    if ! command_exists "$base_cmd"; then
                        log_warning "${workflow_name}: Cloud CLI '$base_cmd' might not be available on runners"
                    fi
                fi
                continue
                ;;
        esac
        
        # Check if command might not exist
        case "$base_cmd" in
            # Common tools that might be missing
            jq|yq|xmllint|shellcheck)
                if ! command_exists "$base_cmd"; then
                    log_warning "${workflow_name}: Tool '$base_cmd' might not be installed on runners"
                fi
                ;;
            # Package managers
            apt|apt-get|yum|brew)
                log_warning "${workflow_name}: Package manager '$base_cmd' might not work on all runners"
                ;;
        esac
    done <<< "$commands"
    
    return $has_errors
}

# Check for environment variables
check_environment_variables() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    
    log_info "Checking environment variables in ${workflow_name}..."
    
    # Find environment variable usage
    local env_vars=$(grep -oE '\$\{[A-Z_][A-Z0-9_]*\}' "$workflow_file" 2>/dev/null | sort -u)
    local github_vars=$(grep -oE '\$\{\{[^}]+\}\}' "$workflow_file" 2>/dev/null | grep -v "secrets\." | grep -v "github\." | grep -v "matrix\." | grep -v "needs\." | grep -v "steps\." | grep -v "runner\." | sort -u)
    
    if [[ -n "$env_vars" ]]; then
        log_info "${workflow_name}: Uses environment variables: $(echo $env_vars | tr '\n' ' ')"
    fi
    
    # Check for undefined variables in env context
    if grep -qE '\$\{\{[[:space:]]*env\.[A-Z_][A-Z0-9_]*[[:space:]]*\}\}' "$workflow_file" 2>/dev/null; then
        local env_refs=$(grep -oE 'env\.[A-Z_][A-Z0-9_]*' "$workflow_file" 2>/dev/null | sed 's/env\.//' | sort -u)
        local env_defs=$(grep -E '^[[:space:]]*(env:|[A-Z_][A-Z0-9_]*:)' "$workflow_file" 2>/dev/null | grep -oE '[A-Z_][A-Z0-9_]*' | sort -u)
        
        for ref in $env_refs; do
            if ! echo "$env_defs" | grep -q "^$ref$"; then
                log_warning "${workflow_name}: Environment variable '$ref' used but might not be defined"
            fi
        done
    fi
}

# Check job dependencies
check_job_dependencies() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    
    log_info "Checking job dependencies in ${workflow_name}..."
    
    # Extract job names (jobs are indented with 2 spaces under "jobs:")
    local jobs=$(grep -E '^  [a-zA-Z0-9_-]+:' "$workflow_file" 2>/dev/null | sed 's/://g' | sed 's/^[[:space:]]*//')
    
    # Check needs references
    local needs=$(grep -oE 'needs:[[:space:]]*\[?[a-z0-9_, -]+\]?' "$workflow_file" | sed 's/needs:[[:space:]]*//' | tr -d '[]' | tr ',' '\n' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
    
    for need in $needs; do
        if [[ -n "$need" ]] && ! echo "$jobs" | grep -q "^$need$"; then
            log_error "${workflow_name}: Job dependency '$need' not found"
        fi
    done
}

# Validate action references
validate_actions() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    
    log_info "Validating action references in ${workflow_name}..."
    
    # Find uses statements
    local actions=$(grep -E 'uses:[[:space:]]*' "$workflow_file" | sed 's/.*uses:[[:space:]]*//' | sed 's/[[:space:]]*$//')
    
    for action in $actions; do
        # Check for typos in common actions
        case "$action" in
            actions/checkut@* | action/checkout@* | actions/chekout@*)
                log_error "${workflow_name}: Typo in action name '$action' (should be 'actions/checkout@...')"
                ;;
            actions/setup-nod@* | action/setup-node@*)
                log_error "${workflow_name}: Typo in action name '$action' (should be 'actions/setup-node@...')"
                ;;
            actions/upload-artificat@* | action/upload-artifact@*)
                log_error "${workflow_name}: Typo in action name '$action' (should be 'actions/upload-artifact@...')"
                ;;
        esac
        
        # Check for missing version tags
        if [[ "$action" =~ ^[^@]+$ ]] && [[ ! "$action" =~ ^\. ]]; then
            log_warning "${workflow_name}: Action '$action' missing version tag"
        fi
    done
}

# Simulate workflow locally (basic simulation)
simulate_workflow() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    
    if [[ "$STRICT_MODE" == "true" ]]; then
        log_info "Simulating workflow steps for ${workflow_name}..."
        
        # Extract and test simple echo/test commands
        local test_commands=$(grep -A 1 "run:" "$workflow_file" | grep -E "echo|test|\[" | head -5)
        
        if [[ -n "$test_commands" ]]; then
            log_info "Testing simple commands from workflow..."
            # Don't actually run commands, just validate syntax
            while IFS= read -r cmd; do
                if [[ -n "$cmd" ]] && [[ ! "$cmd" =~ ^[[:space:]]*# ]]; then
                    # Basic bash syntax check
                    if ! bash -n <(echo "$cmd") 2>/dev/null; then
                        log_warning "${workflow_name}: Potential syntax error in command: $cmd"
                    fi
                fi
            done <<< "$test_commands"
        fi
    fi
}

# Main validation function
validate_workflow() {
    local workflow_file=$1
    local workflow_name=$(basename "$workflow_file")
    local validation_failed=0
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Validating:${NC} ${workflow_name}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Reset error and warning arrays for this workflow
    ERRORS=()
    WARNINGS=()
    
    # Run all validation checks
    validate_yaml_syntax "$workflow_file" || validation_failed=1
    check_workflow_structure "$workflow_file" || validation_failed=1
    validate_commands "$workflow_file" || validation_failed=1
    check_environment_variables "$workflow_file"
    check_job_dependencies "$workflow_file" || validation_failed=1
    validate_actions "$workflow_file" || validation_failed=1
    simulate_workflow "$workflow_file"
    
    # Report results for this workflow
    if [[ $validation_failed -eq 0 ]] && [[ ${#ERRORS[@]} -eq 0 ]]; then
        if [[ ${#WARNINGS[@]} -gt 0 ]]; then
            log_success "${workflow_name} validated with ${#WARNINGS[@]} warning(s)"
        else
            log_success "${workflow_name} validated successfully!"
        fi
        ((PASSED_WORKFLOWS++))
    else
        log_error "${workflow_name} validation failed with ${#ERRORS[@]} error(s)"
        ((FAILED_WORKFLOWS++))
        
        # Show errors summary
        if [[ ${#ERRORS[@]} -gt 0 ]]; then
            echo -e "\n${RED}Errors found:${NC}"
            for error in "${ERRORS[@]}"; do
                echo "  • $error"
            done
        fi
    fi
    
    # Show warnings summary if any
    if [[ ${#WARNINGS[@]} -gt 0 ]] && [[ "$STRICT_MODE" == "true" ]]; then
        echo -e "\n${YELLOW}Warnings:${NC}"
        for warning in "${WARNINGS[@]}"; do
            echo "  • $warning"
        done
    fi
    
    ((TOTAL_WORKFLOWS++))
    
    return $validation_failed
}

# Provide fix suggestions
provide_suggestions() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Suggestions for Common Issues:${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "\n${GREEN}For missing cloud CLI tools:${NC}"
    echo "  • Add '|| true' to make commands optional"
    echo "  • Use 'if command -v aws &> /dev/null; then ... fi' to check availability"
    echo "  • Consider using Docker images with tools pre-installed"
    
    echo -e "\n${GREEN}For YAML syntax errors:${NC}"
    echo "  • Check indentation (use spaces, not tabs)"
    echo "  • Ensure proper quoting of strings with special characters"
    echo "  • Validate with: yamllint or online YAML validators"
    
    echo -e "\n${GREEN}For action version issues:${NC}"
    echo "  • Always specify action versions (e.g., @v4)"
    echo "  • Keep actions updated to latest stable versions"
    echo "  • Check action changelogs for breaking changes"
    
    echo -e "\n${GREEN}For environment variables:${NC}"
    echo "  • Define all env vars at workflow or job level"
    echo "  • Use secrets for sensitive data"
    echo "  • Document required environment variables"
}

# Main execution
main() {
    local exit_code=0
    
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   GitHub Workflow Validation System    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    
    # Check if specific workflow provided
    if [[ $# -gt 0 ]]; then
        for workflow in "$@"; do
            if [[ -f "$workflow" ]]; then
                validate_workflow "$workflow" || exit_code=1
            else
                log_error "Workflow file not found: $workflow"
                exit_code=1
            fi
        done
    else
        # Validate all workflows
        if [[ -d "$WORKFLOWS_DIR" ]]; then
            shopt -s nullglob
            for workflow in "$WORKFLOWS_DIR"/*.yml "$WORKFLOWS_DIR"/*.yaml; do
                [[ -f "$workflow" ]] || continue
                validate_workflow "$workflow" || exit_code=1
            done
            shopt -u nullglob
        else
            log_error "Workflows directory not found: $WORKFLOWS_DIR"
            exit 1
        fi
    fi
    
    # Final summary
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           Validation Summary            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Total workflows: $TOTAL_WORKFLOWS"
    echo -e "  ${GREEN}Passed: $PASSED_WORKFLOWS${NC}"
    echo -e "  ${RED}Failed: $FAILED_WORKFLOWS${NC}"
    echo -e "  ${YELLOW}Warnings: $WARNINGS_COUNT${NC}"
    
    if [[ $FAILED_WORKFLOWS -gt 0 ]]; then
        provide_suggestions
        echo ""
        echo -e "${RED}❌ Validation failed! Fix errors before pushing.${NC}"
    elif [[ $WARNINGS_COUNT -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}⚠️  Validation passed with warnings. Review them before pushing.${NC}"
    else
        echo ""
        echo -e "${GREEN}✅ All workflows validated successfully!${NC}"
    fi
    
    exit $exit_code
}

# Run main function
main "$@"