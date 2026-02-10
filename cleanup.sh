#!/bin/bash

# Cleanup script for Speecher project
# This script removes unnecessary files identified in cleanup-analysis.md

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script configuration
DRY_RUN=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --dry-run    Show what would be deleted without actually deleting"
            echo "  --verbose    Show detailed output"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to log messages
log() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "$1"
    fi
}

# Function to remove files/directories
remove_item() {
    local item=$1
    local description=$2
    
    if [[ -e "$item" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            echo -e "${YELLOW}[DRY RUN]${NC} Would remove: $item ($description)"
        else
            if rm -rf "$item" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Removed: $item ($description)"
            else
                echo -e "${RED}✗${NC} Failed to remove: $item"
            fi
        fi
    else
        log "${YELLOW}⊘${NC} Not found: $item"
    fi
}

echo "==================================="
echo "Speecher Project Cleanup Script"
echo "==================================="

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Running in DRY RUN mode - no files will be deleted${NC}"
fi

echo ""
echo "Starting cleanup process..."
echo ""

# 1. Remove example files in React frontend
echo "1. Removing example files..."
remove_item "src/react-frontend/src/App.auth.example.tsx" "Authentication example file"
remove_item "src/react-frontend/src/App.layout.example.tsx" "Layout example file"

# 2. Remove coverage HTML files for examples
echo ""
echo "2. Removing coverage reports for example files..."
remove_item "src/react-frontend/coverage/lcov-report/src/App.auth.example.tsx.html" "Coverage report for auth example"
remove_item "src/react-frontend/coverage/lcov-report/src/App.layout.example.tsx.html" "Coverage report for layout example"

# 3. Remove empty/unused directories
echo ""
echo "3. Removing empty directories..."
remove_item "test_results" "Empty test results directory"

# 4. Remove Python cache files
echo ""
echo "4. Removing Python cache files..."

# Find and remove all __pycache__ directories
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}[DRY RUN]${NC} Would remove all __pycache__ directories"
    find . -type d -name "__pycache__" 2>/dev/null | head -10
else
    pycache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
    if [[ $pycache_count -gt 0 ]]; then
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Removed $pycache_count __pycache__ directories"
    else
        log "${YELLOW}⊘${NC} No __pycache__ directories found"
    fi
fi

remove_item ".pytest_cache" "Pytest cache directory"

# 5. Optional: Remove .coverage file (uncomment if needed)
# echo ""
# echo "5. Removing coverage data..."
# remove_item "src/react-frontend/.coverage" "Coverage data file"

echo ""
echo "==================================="
echo "Cleanup Summary"
echo "==================================="

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Dry run completed. No files were actually deleted.${NC}"
    echo "Run without --dry-run to perform actual cleanup."
else
    echo -e "${GREEN}Cleanup completed successfully!${NC}"
fi

echo ""
echo "Note: The following were intentionally preserved:"
echo "  • All docker compose files (they serve different purposes)"
echo "  • requirements/ directory (modular dependency management)"
echo "  • All test files"
echo "  • All source code"
echo "  • .dockerignore and other config files"

# Update .gitignore suggestions
echo ""
echo "==================================="
echo ".gitignore Recommendations"
echo "==================================="
echo "Ensure your .gitignore includes:"
echo "  __pycache__/"
echo "  *.pyc"
echo "  .pytest_cache/"
echo "  .coverage"
echo "  coverage/"
echo "  test_results/"
echo "  *.example.*"