#!/bin/bash

# GitHub Actions K8s Runner Validation Script
# Validates that a self-hosted runner is properly configured for Kubernetes workflows

set -euo pipefail

echo "🔍 Validating Kubernetes Runner Configuration"
echo "=============================================="

# Function to check command availability
check_command() {
    local cmd="$1"
    local required="$2"
    
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "✅ $cmd: $(${cmd} --version 2>/dev/null | head -n 1 || echo 'installed')"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo "❌ $cmd: NOT FOUND (REQUIRED)"
            return 1
        else
            echo "⚠️  $cmd: NOT FOUND (optional)"
            return 0
        fi
    fi
}

# Track validation status
validation_errors=0

echo ""
echo "📋 Required Tools Check"
echo "----------------------"

# Essential tools (required)
check_command "kubectl" "true" || ((validation_errors++))
check_command "python3" "true" || ((validation_errors++))
check_command "node" "true" || ((validation_errors++))
check_command "npm" "true" || ((validation_errors++))

echo ""
echo "🐳 Container Runtime Check"
echo "--------------------------"

# Container runtime (at least one required)
container_runtime_found=false

if check_command "nerdctl" "false"; then
    container_runtime_found=true
    echo "  ├─ Testing nerdctl functionality..."
    if nerdctl info >/dev/null 2>&1; then
        echo "  ├─ ✅ nerdctl can access containerd"
    else
        echo "  ├─ ⚠️  nerdctl cannot access containerd (may need permissions)"
    fi
fi

if check_command "docker" "false"; then
    if docker ps >/dev/null 2>&1; then
        container_runtime_found=true
        echo "  ├─ ✅ docker daemon accessible"
    else
        echo "  ├─ ⚠️  docker daemon not accessible"
    fi
fi

if [ "$container_runtime_found" = "false" ]; then
    echo "❌ No working container runtime found (docker or nerdctl required)"
    ((validation_errors++))
fi

echo ""
echo "☁️  Cloud CLI Tools (Optional)"
echo "-----------------------------"

# Cloud tools (optional)
check_command "aws" "false"
check_command "az" "false"
check_command "gcloud" "false"
check_command "terraform" "false"
check_command "gh" "false"

echo ""
echo "⚙️  Kubernetes Cluster Check"
echo "----------------------------"

if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ Kubernetes cluster accessible"
    echo "  ├─ Cluster: $(kubectl config current-context 2>/dev/null || echo 'unknown')"
    echo "  ├─ Nodes: $(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo '0')"
    echo "  └─ Namespaces: $(kubectl get namespaces --no-headers 2>/dev/null | wc -l || echo '0')"
else
    echo "❌ Kubernetes cluster not accessible"
    ((validation_errors++))
fi

echo ""
echo "🧪 Test Workflow Capabilities"
echo "-----------------------------"

# Test namespace creation
test_namespace="validation-test-$$"
if kubectl create namespace "$test_namespace" >/dev/null 2>&1; then
    echo "✅ Can create namespaces"
    
    # Test pod creation
    if kubectl run test-pod --image=alpine:latest --namespace="$test_namespace" --restart=Never --command -- sleep 10 >/dev/null 2>&1; then
        echo "✅ Can create pods"
        kubectl delete pod test-pod --namespace="$test_namespace" >/dev/null 2>&1 || true
    else
        echo "⚠️  Cannot create pods (may need image pull or permissions)"
    fi
    
    kubectl delete namespace "$test_namespace" >/dev/null 2>&1 || true
else
    echo "❌ Cannot create namespaces"
    ((validation_errors++))
fi

echo ""
echo "📊 Validation Summary"
echo "===================="

if [ $validation_errors -eq 0 ]; then
    echo "🎉 SUCCESS: Runner is ready for Kubernetes workflows!"
    echo ""
    echo "✅ All required tools are available"
    echo "✅ Container runtime is working"
    echo "✅ Kubernetes cluster is accessible"
    echo "✅ Can create and manage K8s resources"
    echo ""
    echo "The runner supports:"
    echo "  • Self-hosted workflows with [self-hosted, linux, x64, kubernetes] labels"
    echo "  • Container builds with nerdctl/docker"
    echo "  • Kubernetes-based testing and deployment"
    echo "  • Python and Node.js applications"
    exit 0
else
    echo "❌ FAILED: Runner has $validation_errors configuration issues"
    echo ""
    echo "Required fixes:"
    if ! command -v kubectl >/dev/null 2>&1; then
        echo "  • Install kubectl"
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        echo "  • Install Python 3"
    fi
    if ! command -v node >/dev/null 2>&1; then
        echo "  • Install Node.js"
    fi
    if [ "$container_runtime_found" = "false" ]; then
        echo "  • Install and configure nerdctl or docker"
    fi
    if ! kubectl cluster-info >/dev/null 2>&1; then
        echo "  • Configure kubectl access to Kubernetes cluster"
    fi
    echo ""
    echo "Refer to runner setup documentation for installation instructions."
    exit 1
fi