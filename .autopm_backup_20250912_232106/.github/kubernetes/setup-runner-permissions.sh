#!/bin/bash

# Setup script for GitHub Actions Runner permissions on Kubernetes
# This script should be run by a Kubernetes administrator

set -e

echo "🔧 GitHub Actions Runner Kubernetes Setup"
echo "========================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if user has cluster-admin permissions
if ! kubectl auth can-i '*' '*' --all-namespaces &> /dev/null; then
    echo "⚠️  Warning: You may not have sufficient permissions to apply all configurations."
    echo "   Some operations may fail. Consider running with cluster-admin privileges."
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create namespace if it doesn't exist
echo "📦 Creating github-runner namespace..."
kubectl create namespace github-runner --dry-run=client -o yaml | kubectl apply -f -

# Apply RBAC configuration
echo "🔒 Applying RBAC permissions..."
kubectl apply -f rbac-runner-permissions.yaml

# Verify the setup
echo ""
echo "✅ Verifying setup..."
echo ""

# Check ServiceAccount
if kubectl get serviceaccount -n github-runner default &> /dev/null; then
    echo "✓ ServiceAccount 'default' exists in github-runner namespace"
else
    echo "✗ ServiceAccount 'default' not found"
fi

# Check permissions
echo ""
echo "📋 Checking permissions for github-runner service account..."
echo ""

NAMESPACE="github-runner"
SA="system:serviceaccount:github-runner:default"

# Check pod permissions
if kubectl auth can-i create pods --namespace=$NAMESPACE --as=$SA &> /dev/null; then
    echo "✓ Can create pods"
else
    echo "✗ Cannot create pods"
fi

# Check ConfigMap permissions
if kubectl auth can-i create configmaps --namespace=$NAMESPACE --as=$SA &> /dev/null; then
    echo "✓ Can create ConfigMaps"
else
    echo "✗ Cannot create ConfigMaps"
fi

# Check Job permissions
if kubectl auth can-i create jobs --namespace=$NAMESPACE --as=$SA &> /dev/null; then
    echo "✓ Can create Jobs"
else
    echo "✗ Cannot create Jobs"
fi

# Check namespace permissions (optional)
if kubectl auth can-i create namespaces --as=$SA &> /dev/null; then
    echo "✓ Can create namespaces (cluster-wide)"
else
    echo "ℹ️  Cannot create namespaces (this is optional)"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Deploy your GitHub Actions runners to the 'github-runner' namespace"
echo "2. Ensure runners use the 'default' or 'github-runner' ServiceAccount"
echo "3. Update your workflow files to use the 'github-runner' namespace"
echo ""
echo "To test the setup, run:"
echo "  kubectl run test-pod --image=busybox --namespace=github-runner --command -- echo 'Hello, World!'"
echo ""
echo "For more restrictive permissions, edit rbac-runner-permissions.yaml"
echo "and remove the ClusterRole/ClusterRoleBinding sections."