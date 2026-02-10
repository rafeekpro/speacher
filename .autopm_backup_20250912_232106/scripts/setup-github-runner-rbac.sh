#!/bin/bash

# GitHub Runner RBAC Setup Script
# This script deploys and verifies RBAC permissions for GitHub Actions runners
# in the github-runner namespace using the hybrid Kubernetes approach.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="github-runner"
SERVICE_ACCOUNT="github-runner"
RBAC_FILE="k8s/github-runner-rbac.yml"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
        exit 1
    fi
    
    # Check if RBAC file exists
    if [[ ! -f "$RBAC_FILE" ]]; then
        log_error "RBAC file not found: $RBAC_FILE"
        exit 1
    fi
    
    # Check if user has cluster-admin permissions for RBAC setup
    if ! kubectl auth can-i create roles --all-namespaces &> /dev/null; then
        log_warning "Current user may not have sufficient permissions to create RBAC resources"
        log_warning "Proceeding anyway - deployment may fail if permissions are insufficient"
    fi
    
    log_success "Prerequisites check completed"
}

deploy_rbac() {
    log_info "Deploying GitHub Runner RBAC configuration..."
    
    # Apply the RBAC configuration
    if kubectl apply -f "$RBAC_FILE"; then
        log_success "RBAC configuration deployed successfully"
    else
        log_error "Failed to deploy RBAC configuration"
        exit 1
    fi
    
    # Wait for namespace to be ready
    log_info "Waiting for namespace to be ready..."
    kubectl wait --for=condition=Active namespace/$NAMESPACE --timeout=30s
    
    log_success "Namespace $NAMESPACE is ready"
}

verify_deployment() {
    log_info "Verifying RBAC deployment..."
    
    # Check namespace
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_success "Namespace '$NAMESPACE' exists"
    else
        log_error "Namespace '$NAMESPACE' not found"
        return 1
    fi
    
    # Check ServiceAccount
    if kubectl get serviceaccount "$SERVICE_ACCOUNT" -n "$NAMESPACE" &> /dev/null; then
        log_success "ServiceAccount '$SERVICE_ACCOUNT' exists"
    else
        log_error "ServiceAccount '$SERVICE_ACCOUNT' not found"
        return 1
    fi
    
    # Check Role
    if kubectl get role "$SERVICE_ACCOUNT" -n "$NAMESPACE" &> /dev/null; then
        log_success "Role '$SERVICE_ACCOUNT' exists"
    else
        log_error "Role '$SERVICE_ACCOUNT' not found"
        return 1
    fi
    
    # Check RoleBinding
    if kubectl get rolebinding "$SERVICE_ACCOUNT" -n "$NAMESPACE" &> /dev/null; then
        log_success "RoleBinding '$SERVICE_ACCOUNT' exists"
    else
        log_error "RoleBinding '$SERVICE_ACCOUNT' not found"
        return 1
    fi
    
    log_success "All RBAC resources deployed correctly"
}

test_permissions() {
    log_info "Testing RBAC permissions..."
    
    local service_account_full="system:serviceaccount:$NAMESPACE:$SERVICE_ACCOUNT"
    local failed=false
    
    # Define test cases: resource verb expected_result
    local tests=(
        "jobs create true"
        "pods create true"
        "pods get true"
        "pods/log get true"
        "pods/portforward create true"
        "configmaps create true"
        "configmaps get true"
        "secrets get true"
        "services create true"
        "persistentvolumeclaims create true"
        "events get true"
        # Negative tests - should fail
        "deployments create false"
        "nodes get false"
        "namespaces create false"
        "clusterroles create false"
    )
    
    for test in "${tests[@]}"; do
        read -r resource verb expected <<< "$test"
        
        if kubectl auth can-i "$verb" "$resource" --as="$service_account_full" -n "$NAMESPACE" &> /dev/null; then
            result="true"
        else
            result="false"
        fi
        
        if [[ "$result" == "$expected" ]]; then
            if [[ "$expected" == "true" ]]; then
                log_success "✓ Can $verb $resource"
            else
                log_success "✓ Cannot $verb $resource (expected)"
            fi
        else
            if [[ "$expected" == "true" ]]; then
                log_error "✗ Cannot $verb $resource (unexpected)"
            else
                log_error "✗ Can $verb $resource (should be denied)"
            fi
            failed=true
        fi
    done
    
    if [[ "$failed" == "false" ]]; then
        log_success "All permission tests passed"
        return 0
    else
        log_error "Some permission tests failed"
        return 1
    fi
}

show_usage_examples() {
    log_info "GitHub Actions Usage Examples:"
    
    cat << 'EOF'

## 1. Kaniko Build Job Example
```yaml
- name: Build with Kaniko
  run: |
    kubectl create job kaniko-build-${{ github.run_id }} \
      --image=gcr.io/kaniko-project/executor:latest \
      --serviceaccount=github-runner \
      -n github-runner \
      -- --context=git://github.com/${{ github.repository }}.git#${{ github.sha }} \
      --dockerfile=Dockerfile \
      --destination=myregistry/myapp:${{ github.sha }}
    
    kubectl wait --for=condition=complete job/kaniko-build-${{ github.run_id }} \
      -n github-runner --timeout=600s
```

## 2. Test Execution with Port Forwarding
```yaml
- name: Run Integration Tests
  run: |
    kubectl create job test-${{ github.run_id }} \
      --image=myapp:test \
      --serviceaccount=github-runner \
      -n github-runner \
      -- npm test
    
    # Debug with port forwarding if needed
    kubectl port-forward job/test-${{ github.run_id }} 3000:3000 \
      -n github-runner &
    
    kubectl wait --for=condition=complete job/test-${{ github.run_id }} \
      -n github-runner --timeout=300s
```

## 3. Multi-step Build Pipeline
```yaml
- name: Multi-step Build
  run: |
    # Create build context ConfigMap
    kubectl create configmap build-context-${{ github.run_id }} \
      --from-file=. \
      -n github-runner
    
    # Frontend build
    kubectl create job frontend-build-${{ github.run_id }} \
      --image=node:18 \
      --serviceaccount=github-runner \
      -n github-runner \
      -- npm run build
    
    # Backend build with Kaniko
    kubectl create job backend-build-${{ github.run_id }} \
      --image=gcr.io/kaniko-project/executor:latest \
      --serviceaccount=github-runner \
      -n github-runner \
      -- --context=git://github.com/${{ github.repository }}.git#${{ github.sha }} \
      --dockerfile=backend/Dockerfile \
      --destination=myregistry/backend:${{ github.sha }}
    
    # Wait for both jobs
    kubectl wait --for=condition=complete \
      job/frontend-build-${{ github.run_id }} \
      job/backend-build-${{ github.run_id }} \
      -n github-runner --timeout=600s
```

EOF
}

cleanup() {
    log_info "Cleaning up test resources (if any)..."
    # Add cleanup commands here if needed
    log_success "Cleanup completed"
}

main() {
    echo "=== GitHub Runner RBAC Setup ==="
    echo "Namespace: $NAMESPACE"
    echo "ServiceAccount: $SERVICE_ACCOUNT"
    echo "RBAC File: $RBAC_FILE"
    echo "================================"
    echo
    
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            deploy_rbac
            verify_deployment
            test_permissions
            show_usage_examples
            ;;
        "verify")
            check_prerequisites
            verify_deployment
            test_permissions
            ;;
        "test")
            check_prerequisites
            test_permissions
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [command]

Commands:
  deploy   (default) Deploy RBAC configuration and verify
  verify   Verify existing deployment and test permissions
  test     Test RBAC permissions only
  cleanup  Clean up test resources
  help     Show this help message

Examples:
  $0                 # Deploy and verify
  $0 deploy          # Same as above
  $0 verify          # Verify existing deployment
  $0 test            # Test permissions only
  $0 cleanup         # Clean up
EOF
            ;;
        *)
            log_error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Trap to ensure cleanup on script exit
trap cleanup EXIT

# Run main function with all arguments
main "$@"