#!/usr/bin/env bash

# ============================================================================
# VISUAL TESTING VERIFICATION SCRIPT
# ============================================================================
# This script MUST pass before any frontend task can be marked as complete.
# It performs comprehensive visual testing checks to ensure UI integrity.
# ============================================================================

set -e  # Exit on any error
set -o pipefail  # Pipe failures cause script to fail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/src/react-frontend"
VISUAL_TEST_DIR="$FRONTEND_DIR/tests/visual"
SCREENSHOTS_DIR="$VISUAL_TEST_DIR/__screenshots__"
REPORT_FILE="$PROJECT_ROOT/visual-verification-report.json"
LOG_FILE="$PROJECT_ROOT/.visual-test-verification.log"

# Exit codes
EXIT_SUCCESS=0
EXIT_MISSING_DEPS=1
EXIT_NO_BASELINES=2
EXIT_TESTS_FAILED=3
EXIT_COVERAGE_LOW=4
EXIT_OUTDATED_SNAPSHOTS=5
EXIT_BYPASSED=6

# Tracking variables
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
    ((PASSED_CHECKS++))
}

log_error() {
    log "${RED}❌ $1${NC}"
    ((FAILED_CHECKS++))
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

log_section() {
    log ""
    log "${BOLD}${CYAN}$1${NC}"
    log "${CYAN}$(printf '=%.0s' {1..60})${NC}"
}

show_progress() {
    echo -ne "${BLUE}⏳ $1...${NC}\r"
}

clear_progress() {
    echo -ne "\033[2K\r"
}

# ============================================================================
# Check if running in CI environment
# ============================================================================

check_environment() {
    if [ -n "$CI" ]; then
        log_info "Running in CI environment"
        export PLAYWRIGHT_BROWSERS_PATH=0
    else
        log_info "Running in local environment"
    fi
    
    # Check if being bypassed
    if [ -n "$SKIP_VISUAL_VERIFICATION" ]; then
        log_warning "Visual verification bypass detected!"
        echo "$(date): Visual verification bypassed by $USER" >> "$LOG_FILE"
        if [ "$FORCE_VISUAL_VERIFICATION" = "true" ]; then
            log_error "FORCE_VISUAL_VERIFICATION is enabled. Bypass not allowed!"
            return 1
        fi
        return 0
    fi
}

# ============================================================================
# Main Verification Functions
# ============================================================================

verify_dependencies() {
    log_section "Verifying Dependencies"
    ((TOTAL_CHECKS++))
    
    cd "$FRONTEND_DIR" || {
        log_error "Frontend directory not found: $FRONTEND_DIR"
        return $EXIT_MISSING_DEPS
    }
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        return $EXIT_MISSING_DEPS
    fi
    log_success "Node.js $(node --version) installed"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed"
        return $EXIT_MISSING_DEPS
    fi
    log_success "npm $(npm --version) installed"
    
    # Check Playwright
    if ! npx playwright --version &> /dev/null; then
        log_warning "Playwright not installed. Installing..."
        npm install -D @playwright/test
        npx playwright install --with-deps chromium firefox webkit
    fi
    log_success "Playwright $(npx playwright --version) installed"
    
    # Check if visual test file exists
    if [ ! -f "$VISUAL_TEST_DIR/visual.spec.ts" ]; then
        log_error "Visual test file not found: $VISUAL_TEST_DIR/visual.spec.ts"
        return $EXIT_MISSING_DEPS
    fi
    log_success "Visual test file exists"
    
    return 0
}

verify_baseline_snapshots() {
    log_section "Verifying Baseline Snapshots"
    ((TOTAL_CHECKS++))
    
    if [ ! -d "$SCREENSHOTS_DIR" ]; then
        log_warning "No baseline screenshots directory found"
        log_info "Creating baseline snapshots..."
        
        cd "$FRONTEND_DIR"
        npx playwright test tests/visual/visual.spec.ts --update-snapshots || {
            log_error "Failed to create baseline snapshots"
            return $EXIT_NO_BASELINES
        }
    fi
    
    # Count baseline snapshots
    SNAPSHOT_COUNT=$(find "$SCREENSHOTS_DIR" -name "*.png" 2>/dev/null | wc -l)
    
    if [ "$SNAPSHOT_COUNT" -eq 0 ]; then
        log_error "No baseline snapshots found"
        return $EXIT_NO_BASELINES
    fi
    
    log_success "Found $SNAPSHOT_COUNT baseline snapshots"
    
    # Check snapshot age
    OLD_SNAPSHOTS=$(find "$SCREENSHOTS_DIR" -name "*.png" -mtime +7 2>/dev/null | wc -l)
    if [ "$OLD_SNAPSHOTS" -gt 0 ]; then
        log_warning "$OLD_SNAPSHOTS snapshots are older than 7 days"
        ((WARNINGS++))
    fi
    
    return 0
}

run_visual_tests() {
    log_section "Running Visual Regression Tests"
    ((TOTAL_CHECKS++))
    
    cd "$FRONTEND_DIR"
    
    # Create test results directory
    mkdir -p test-results
    
    # Run tests for each browser
    local all_passed=true
    
    for browser in chromium firefox webkit; do
        show_progress "Testing in $browser"
        
        if npx playwright test tests/visual/visual.spec.ts --project="$browser" --reporter=json > test-results/${browser}-results.json 2>&1; then
            clear_progress
            log_success "$browser: All visual tests passed"
        else
            clear_progress
            log_error "$browser: Visual tests failed"
            all_passed=false
            
            # Parse failure details
            if [ -f "test-results/${browser}-results.json" ]; then
                FAILED_TESTS=$(jq '.suites[].specs[] | select(.tests[].results[].status == "failed") | .title' test-results/${browser}-results.json 2>/dev/null || echo "Unknown")
                log_error "Failed tests: $FAILED_TESTS"
            fi
        fi
    done
    
    if [ "$all_passed" = false ]; then
        log_error "Visual regression detected!"
        log_info "To review changes: npx playwright show-report"
        log_info "To update baselines: npx playwright test tests/visual/visual.spec.ts --update-snapshots"
        return $EXIT_TESTS_FAILED
    fi
    
    return 0
}

verify_test_coverage() {
    log_section "Verifying Test Coverage"
    ((TOTAL_CHECKS++))
    
    # Count routes in application
    cd "$FRONTEND_DIR"
    ROUTE_COUNT=$(find . -name "*.tsx" -o -name "*.jsx" | xargs grep -l "Route\|route" | wc -l)
    
    # Count visual tests
    TEST_COUNT=$(grep -c "test\|it" "$VISUAL_TEST_DIR/visual.spec.ts" 2>/dev/null || echo "0")
    
    # Calculate coverage percentage
    if [ "$ROUTE_COUNT" -gt 0 ]; then
        COVERAGE=$((TEST_COUNT * 100 / ROUTE_COUNT))
    else
        COVERAGE=0
    fi
    
    log_info "Routes found: $ROUTE_COUNT"
    log_info "Visual tests: $TEST_COUNT"
    log_info "Coverage: ${COVERAGE}%"
    
    if [ "$COVERAGE" -lt 80 ]; then
        log_warning "Visual test coverage is below 80%"
        if [ "$STRICT_COVERAGE" = "true" ]; then
            log_error "Strict coverage mode enabled. Coverage must be at least 80%"
            return $EXIT_COVERAGE_LOW
        fi
    else
        log_success "Visual test coverage is adequate (${COVERAGE}%)"
    fi
    
    return 0
}

check_visual_integrity() {
    log_section "Checking Visual Integrity"
    ((TOTAL_CHECKS++))
    
    cd "$FRONTEND_DIR"
    
    # Run integrity checks using Playwright
    cat > /tmp/integrity-check.spec.ts << 'EOF'
import { test, expect } from '@playwright/test';

test.describe('Visual Integrity Checks', () => {
  test('No layout breaks', async ({ page }) => {
    await page.goto('/');
    
    const hasOverlaps = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (let i = 0; i < elements.length; i++) {
        for (let j = i + 1; j < elements.length; j++) {
          const rect1 = elements[i].getBoundingClientRect();
          const rect2 = elements[j].getBoundingClientRect();
          
          if (!elements[i].contains(elements[j]) && !elements[j].contains(elements[i])) {
            const overlap = !(rect1.right < rect2.left || 
                            rect2.right < rect1.left || 
                            rect1.bottom < rect2.top || 
                            rect2.bottom < rect1.top);
            if (overlap && rect1.width > 0 && rect1.height > 0 && rect2.width > 0 && rect2.height > 0) {
              return true;
            }
          }
        }
      }
      return false;
    });
    
    expect(hasOverlaps).toBe(false);
  });

  test('No broken images', async ({ page }) => {
    await page.goto('/');
    
    const brokenImages = await page.evaluate(() => {
      const images = Array.from(document.querySelectorAll('img'));
      return images.filter(img => !img.complete || img.naturalWidth === 0).length;
    });
    
    expect(brokenImages).toBe(0);
  });

  test('No text overflow', async ({ page }) => {
    await page.goto('/');
    
    const hasTextOverflow = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (const element of elements) {
        if (element.scrollWidth > element.clientWidth || 
            element.scrollHeight > element.clientHeight) {
          const styles = window.getComputedStyle(element);
          if (styles.overflow !== 'auto' && styles.overflow !== 'scroll') {
            return true;
          }
        }
      }
      return false;
    });
    
    expect(hasTextOverflow).toBe(false);
  });
});
EOF

    if npx playwright test /tmp/integrity-check.spec.ts --reporter=json > /tmp/integrity-results.json 2>&1; then
        log_success "Visual integrity checks passed"
    else
        log_error "Visual integrity issues detected"
        cat /tmp/integrity-results.json 2>/dev/null || true
        return $EXIT_TESTS_FAILED
    fi
    
    rm -f /tmp/integrity-check.spec.ts /tmp/integrity-results.json
    
    return 0
}

generate_report() {
    log_section "Generating Verification Report"
    
    cat > "$REPORT_FILE" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "environment": "$([ -n "$CI" ] && echo "ci" || echo "local")",
  "user": "$USER",
  "branch": "$(git branch --show-current 2>/dev/null || echo "unknown")",
  "checks": {
    "total": $TOTAL_CHECKS,
    "passed": $PASSED_CHECKS,
    "failed": $FAILED_CHECKS,
    "warnings": $WARNINGS
  },
  "status": $([ "$FAILED_CHECKS" -eq 0 ] && echo '"passed"' || echo '"failed"'),
  "bypass_attempted": $([ -n "$SKIP_VISUAL_VERIFICATION" ] && echo "true" || echo "false")
}
EOF

    log_success "Report generated: $REPORT_FILE"
}

# ============================================================================
# Enforcement Functions
# ============================================================================

enforce_visual_testing() {
    log_section "VISUAL TESTING ENFORCEMENT"
    
    # This function ensures visual testing cannot be skipped
    if [ "$FAILED_CHECKS" -gt 0 ]; then
        log ""
        log "${RED}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
        log "${RED}${BOLD}║          VISUAL TESTING VERIFICATION FAILED!              ║${NC}"
        log "${RED}${BOLD}╠══════════════════════════════════════════════════════════╣${NC}"
        log "${RED}${BOLD}║                                                          ║${NC}"
        log "${RED}${BOLD}║  Frontend tasks CANNOT be marked complete until:        ║${NC}"
        log "${RED}${BOLD}║                                                          ║${NC}"
        log "${RED}${BOLD}║  1. All visual tests pass                               ║${NC}"
        log "${RED}${BOLD}║  2. Baseline snapshots are up to date                   ║${NC}"
        log "${RED}${BOLD}║  3. No visual regressions are detected                  ║${NC}"
        log "${RED}${BOLD}║  4. Test coverage meets requirements                    ║${NC}"
        log "${RED}${BOLD}║                                                          ║${NC}"
        log "${RED}${BOLD}║  Run: ./scripts/verify-visual.sh                        ║${NC}"
        log "${RED}${BOLD}║                                                          ║${NC}"
        log "${RED}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
        log ""
        
        # Create a lock file to prevent task completion
        echo "LOCKED: Visual tests failed at $(date)" > "$PROJECT_ROOT/.visual-test-lock"
        
        return $EXIT_TESTS_FAILED
    else
        log ""
        log "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
        log "${GREEN}${BOLD}║         VISUAL TESTING VERIFICATION PASSED!               ║${NC}"
        log "${GREEN}${BOLD}╠══════════════════════════════════════════════════════════╣${NC}"
        log "${GREEN}${BOLD}║                                                          ║${NC}"
        log "${GREEN}${BOLD}║  ✅ All visual tests passed                             ║${NC}"
        log "${GREEN}${BOLD}║  ✅ Baseline snapshots verified                         ║${NC}"
        log "${GREEN}${BOLD}║  ✅ No visual regressions detected                      ║${NC}"
        log "${GREEN}${BOLD}║  ✅ Visual integrity confirmed                          ║${NC}"
        log "${GREEN}${BOLD}║                                                          ║${NC}"
        log "${GREEN}${BOLD}║  Frontend task can be marked as complete!               ║${NC}"
        log "${GREEN}${BOLD}║                                                          ║${NC}"
        log "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
        log ""
        
        # Remove lock file if it exists
        rm -f "$PROJECT_ROOT/.visual-test-lock"
        
        return $EXIT_SUCCESS
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "${BOLD}${MAGENTA}🎭 VISUAL TESTING VERIFICATION SYSTEM${NC}"
    log "${MAGENTA}$(date)${NC}"
    log ""
    
    # Initialize log file
    echo "=== Visual Testing Verification Started ===" > "$LOG_FILE"
    echo "Timestamp: $(date)" >> "$LOG_FILE"
    echo "User: $USER" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    # Check environment
    check_environment
    
    # Run all verification steps
    local exit_code=0
    
    verify_dependencies || exit_code=$?
    if [ $exit_code -eq 0 ]; then
        verify_baseline_snapshots || exit_code=$?
    fi
    if [ $exit_code -eq 0 ]; then
        run_visual_tests || exit_code=$?
    fi
    if [ $exit_code -eq 0 ]; then
        verify_test_coverage || exit_code=$?
    fi
    if [ $exit_code -eq 0 ]; then
        check_visual_integrity || exit_code=$?
    fi
    
    # Generate report
    generate_report
    
    # Show summary
    log ""
    log_section "Summary"
    log "Total checks: $TOTAL_CHECKS"
    log "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    log "Failed: ${RED}$FAILED_CHECKS${NC}"
    log "Warnings: ${YELLOW}$WARNINGS${NC}"
    
    # Enforce visual testing
    enforce_visual_testing
    exit_code=$?
    
    # Append to log file
    echo "" >> "$LOG_FILE"
    echo "=== Visual Testing Verification Completed ===" >> "$LOG_FILE"
    echo "Exit code: $exit_code" >> "$LOG_FILE"
    
    exit $exit_code
}

# ============================================================================
# Script Entry Point
# ============================================================================

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        cat << EOF
Visual Testing Verification Script

Usage: $0 [OPTIONS]

Options:
  --help, -h          Show this help message
  --update-snapshots  Update baseline snapshots
  --strict            Enable strict mode (fail on warnings)
  --bypass            Attempt to bypass verification (logged)
  --force             Force verification (cannot be bypassed)

Environment Variables:
  SKIP_VISUAL_VERIFICATION  Skip verification (will be logged)
  FORCE_VISUAL_VERIFICATION Prevent bypass attempts
  STRICT_COVERAGE          Enforce 80% coverage minimum

This script must pass before any frontend task can be marked complete.
EOF
        exit 0
        ;;
    --update-snapshots)
        cd "$FRONTEND_DIR"
        npx playwright test tests/visual/visual.spec.ts --update-snapshots
        echo "Baseline snapshots updated"
        exit 0
        ;;
    --strict)
        export STRICT_COVERAGE=true
        ;;
    --bypass)
        export SKIP_VISUAL_VERIFICATION=true
        ;;
    --force)
        export FORCE_VISUAL_VERIFICATION=true
        ;;
esac

# Run main function
main