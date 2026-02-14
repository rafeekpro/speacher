#!/bin/bash
# Setup script for Docker Build Pipeline
# This script helps configure the required Kubernetes secrets and validates the setup

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${REGISTRY:-ghcr.io}"
NAMESPACE="${NAMESPACE:-github-runner}"
SECRET_NAME="${SECRET_NAME:-docker-reg-secret}"

echo "🔧 Docker Build Pipeline Setup"
echo "================================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl first.${NC}"
    echo "   https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi
echo -e "${GREEN}✅ kubectl found${NC}"

# Check if kubectl can connect to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster.${NC}"
    echo "   Please configure KUBECONFIG or ensure you have access to the cluster."
    exit 1
fi
echo -e "${GREEN}✅ Kubernetes cluster accessible${NC}"

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Namespace '$NAMESPACE' not found. Creating...${NC}"
    kubectl create namespace "$NAMESPACE"
    echo -e "${GREEN}✅ Namespace '$NAMESPACE' created${NC}"
else
    echo -e "${GREEN}✅ Namespace '$NAMESPACE' exists${NC}"
fi

echo ""
echo "🔐 Docker Registry Secret Configuration"
echo "===================================="
echo ""

# Get registry credentials
echo "Registry: $REGISTRY"
echo ""
read -rp "Enter registry username (e.g., GitHub username): " USERNAME
read -rsp "Enter registry password/token (will be hidden): " PASSWORD
echo ""
read -rp "Enter registry email: " EMAIL

# Validate input
if [[ -z "$USERNAME" ]] || [[ -z "$PASSWORD" ]] || [[ -z "$EMAIL" ]]; then
    echo -e "${RED}❌ Username, password, and email are required.${NC}"
    exit 1
fi

# Delete existing secret if it exists
if kubectl get secret "$SECRET_NAME" --namespace "$NAMESPACE" &> /dev/null; then
    echo ""
    read -rp "Secret '$SECRET_NAME' already exists. Overwrite? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete secret "$SECRET_NAME" --namespace "$NAMESPACE"
        echo -e "${GREEN}✅ Old secret deleted${NC}"
    else
        echo -e "${YELLOW}⚠️  Skipping secret creation${NC}"
        exit 0
    fi
fi

# Create the secret
echo ""
echo "Creating secret..."
kubectl create secret docker-registry "$SECRET_NAME" \
    --namespace="$NAMESPACE" \
    --docker-server="$REGISTRY" \
    --docker-username="$USERNAME" \
    --docker-password="$PASSWORD" \
    --docker-email="$EMAIL"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Secret '$SECRET_NAME' created successfully${NC}"
else
    echo -e "${RED}❌ Failed to create secret${NC}"
    exit 1
fi

echo ""
echo "🎯 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Add KUBECONFIG to GitHub repository secrets:"
echo "   - Name: KUBECONFIG"
echo "   - Value: Base64 encoded kubeconfig file"
echo ""
echo "   To encode your kubeconfig:"
echo "   base64 -i ~/.kube/config"
echo ""
echo "2. Update workflow configuration if needed:"
echo "   - Registry: $REGISTRY (currently set in workflow)"
echo "   - Namespace: $NAMESPACE (currently set in workflow)"
echo ""
echo "3. Test the workflow:"
echo "   - Go to Actions tab in GitHub"
echo "   - Select 'Docker Build Pipeline'"
echo "   - Click 'Run workflow'"
echo ""
echo -e "${GREEN}✅ Ready to build images!${NC}"
