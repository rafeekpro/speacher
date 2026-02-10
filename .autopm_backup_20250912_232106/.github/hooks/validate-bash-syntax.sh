#!/bin/bash

# Validate Bash syntax in GitHub Actions workflows
# This script checks for common bash syntax errors in workflow files

set -e

echo "🔍 Validating Bash syntax in workflows..."

ERRORS=0

# Find all workflow files
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        echo "Checking: $(basename $workflow)"
        
        # Extract bash scripts from workflow and validate
        # Look for run: blocks that contain shell scripts
        grep -n "run: |" "$workflow" | while read -r line_info; do
            line_num=$(echo "$line_info" | cut -d: -f1)
            
            # Extract the script block (simplified check)
            # Check for common heredoc issues
            if grep -A 20 "run: |" "$workflow" | grep -q "cat <<EOF"; then
                # Check for proper EOF termination
                if ! grep -A 50 "run: |" "$workflow" | grep -q "^[[:space:]]*EOF$"; then
                    echo "  ⚠️  Line $line_num: Potential unterminated heredoc"
                    ERRORS=$((ERRORS + 1))
                fi
                
                # Check for embedded shell commands in heredoc
                if grep -A 50 "run: |" "$workflow" | grep "cat <<EOF" -A 30 | grep -q '\$('; then
                    echo "  ⚠️  Line $line_num: Shell command inside heredoc - may cause issues"
                    ERRORS=$((ERRORS + 1))
                fi
            fi
        done
        
        # Check for unbalanced quotes
        if grep "run: " "$workflow" | grep -E "['\"].*[^'\"]$" | grep -v "#"; then
            echo "  ⚠️  Potential unbalanced quotes detected"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ Found $ERRORS potential bash syntax issues"
    echo "Please review and fix before committing"
    exit 1
else
    echo "✅ Bash syntax validation passed"
fi