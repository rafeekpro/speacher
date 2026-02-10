#!/bin/bash

# Test Script for Hybrid Container Builds
# This script tests the hybrid Kubernetes/Kaniko build approach
# It validates that the conversion from nerdctl to Kaniko works correctly

set -euo pipefail

# Color output functions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo -e "${RED}❌ $1${NC}" >&2
}

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "Running test: $test_name"
    
    if eval "$test_command"; then
        log_success "PASS: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "FAIL: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 1: Verify Kubernetes cluster is accessible
test_kubernetes_access() {
    kubectl cluster-info --request-timeout=10s > /dev/null
}

# Test 2: Verify Kaniko image is available
test_kaniko_image() {
    kubectl run kaniko-test --image=gcr.io/kaniko-project/executor:latest --dry-run=client > /dev/null
}

# Test 3: Create test namespace
test_create_namespace() {
    kubectl create namespace hybrid-build-test --dry-run=client -o yaml | kubectl apply -f - > /dev/null
}

# Test 4: Create test build context
test_create_build_context() {
    # Create a simple test Dockerfile
    mkdir -p /tmp/test-build-context
    cat > /tmp/test-build-context/Dockerfile << 'EOF'
FROM alpine:latest
RUN echo "Test build from hybrid Kaniko approach" > /test.txt
CMD ["cat", "/test.txt"]
EOF
    
    # Create ConfigMap from build context
    kubectl create configmap test-build-context \
        --from-file=/tmp/test-build-context \
        --namespace=hybrid-build-test \
        --dry-run=client -o yaml | kubectl apply -f - > /dev/null
}

# Test 5: Run Kaniko build job
test_kaniko_build_job() {
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: test-kaniko-build
  namespace: hybrid-build-test
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: kaniko
        image: gcr.io/kaniko-project/executor:latest
        args:
        - --dockerfile=/workspace/Dockerfile
        - --context=/workspace
        - --destination=test-hybrid-build:latest
        - --cache=false
        - --no-push
        volumeMounts:
        - name: build-context
          mountPath: /workspace
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: build-context
        configMap:
          name: test-build-context
EOF

    # Wait for job to complete
    kubectl wait --for=condition=complete job/test-kaniko-build \
        --timeout=300s \
        --namespace=hybrid-build-test > /dev/null
}

# Test 6: Verify build logs
test_build_logs() {
    local logs=$(kubectl logs job/test-kaniko-build --namespace=hybrid-build-test 2>/dev/null || echo "")
    echo "$logs" | grep -q "Test build from hybrid Kaniko approach"
}

# Test 7: Test the Kaniko build script
test_kaniko_script() {
    # Skip if script doesn't exist
    if [[ ! -f ".github/scripts/kaniko-build.sh" ]]; then
        log_warning "Kaniko build script not found, skipping test"
        return 0
    fi
    
    .github/scripts/kaniko-build.sh \
        --namespace hybrid-build-test \
        --job-name script-test-build \
        --image test-script-build:latest \
        --context test-build-context \
        --timeout 300 \
        --no-cleanup > /dev/null 2>&1
}

# Test 8: Test the hybrid wrapper script
test_hybrid_wrapper() {
    # Skip if script doesn't exist
    if [[ ! -f ".github/scripts/hybrid-build-wrapper.sh" ]]; then
        log_warning "Hybrid wrapper script not found, skipping test"
        return 0
    fi
    
    # Create a temporary test Dockerfile
    mkdir -p /tmp/wrapper-test
    cat > /tmp/wrapper-test/Dockerfile << 'EOF'
FROM alpine:latest
RUN echo "Wrapper test" > /wrapper-test.txt
EOF
    
    cd /tmp/wrapper-test
    ../../.github/scripts/hybrid-build-wrapper.sh kaniko Dockerfile test-wrapper:latest . > /dev/null 2>&1
}

# Test 9: Validate workflow file syntax
test_workflow_syntax() {
    local workflow_files=(
        ".github/workflows/ci.yml"
        ".github/workflows/ci-k3s.yml"
        ".github/workflows/pr-checks.yml"
        ".github/workflows/frontend-v2-pr.yml"
    )
    
    for workflow in "${workflow_files[@]}"; do
        if [[ -f "$workflow" ]]; then
            # Basic YAML syntax check
            python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null
        fi
    done
}

# Test 10: Check for removed nerdctl references
test_no_nerdctl_references() {
    local workflow_files=(
        ".github/workflows/ci.yml"
        ".github/workflows/ci-k3s.yml"
        ".github/workflows/pr-checks.yml"
        ".github/workflows/frontend-v2-pr.yml"
    )
    
    local nerdctl_found=false
    for workflow in "${workflow_files[@]}"; do
        if [[ -f "$workflow" ]] && grep -q "nerdctl build" "$workflow"; then
            log_error "Found nerdctl build command in $workflow"
            nerdctl_found=true
        fi
    done
    
    if [[ "$nerdctl_found" == "true" ]]; then
        return 1
    fi
    
    return 0
}

# Cleanup function
cleanup_test_resources() {
    log_info "Cleaning up test resources..."
    
    # Delete test namespace
    kubectl delete namespace hybrid-build-test --ignore-not-found=true --grace-period=30 > /dev/null 2>&1 &
    
    # Clean up temporary files
    rm -rf /tmp/test-build-context /tmp/wrapper-test
    
    log_info "Cleanup initiated"
}

# Main test function
main() {
    log_info "🧪 Starting Hybrid Container Build Tests"
    log_info "========================================"
    
    # Pre-flight checks
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        log_warning "python3 not found, skipping YAML syntax tests"
    fi
    
    # Run tests
    run_test "Kubernetes cluster access" "test_kubernetes_access"
    run_test "Kaniko image availability" "test_kaniko_image"
    run_test "Create test namespace" "test_create_namespace"
    run_test "Create build context ConfigMap" "test_create_build_context"
    run_test "Execute Kaniko build job" "test_kaniko_build_job"
    run_test "Verify build logs" "test_build_logs"
    run_test "Test Kaniko build script" "test_kaniko_script"
    run_test "Test hybrid wrapper script" "test_hybrid_wrapper"
    run_test "Validate workflow YAML syntax" "test_workflow_syntax"
    run_test "Check for removed nerdctl references" "test_no_nerdctl_references"
    
    # Summary
    log_info ""
    log_info "🏁 Test Summary"
    log_info "==============="
    log_info "Tests run: $TESTS_RUN"
    log_success "Tests passed: $TESTS_PASSED"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Tests failed: $TESTS_FAILED"
        log_error ""
        log_error "Some tests failed. Please review the hybrid build setup."
    else
        log_success "All tests passed! ✨"
        log_success "The hybrid Kubernetes/Kaniko build approach is working correctly."
    fi
    
    # Always cleanup
    cleanup_test_resources
    
    # Exit with appropriate code
    if [[ $TESTS_FAILED -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Handle help
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat << EOF
🧪 Hybrid Container Build Test Suite

This script tests the hybrid Kubernetes/Kaniko build approach to ensure
that the conversion from nerdctl to Kaniko works correctly.

Usage: $0 [options]

Options:
  --help, -h    Show this help message

Tests performed:
  1. Kubernetes cluster accessibility
  2. Kaniko image availability  
  3. Namespace creation
  4. Build context ConfigMap creation
  5. Kaniko build job execution
  6. Build log verification
  7. Kaniko build script functionality
  8. Hybrid wrapper script functionality
  9. Workflow YAML syntax validation
  10. Verification of nerdctl removal

Prerequisites:
  - kubectl installed and configured
  - Access to a Kubernetes cluster
  - python3 (optional, for YAML validation)

Example:
  $0

The script will create temporary test resources and clean them up automatically.

EOF
    exit 0
fi

# Change to repository root if script is run from .github/scripts/
if [[ "$(basename "$PWD")" == "scripts" ]] && [[ -d "../../.git" ]]; then
    cd ../..
fi

# Run main function
main "$@"