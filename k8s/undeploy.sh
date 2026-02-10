#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="speecher"

echo -e "${RED}=== Speecher Kubernetes Undeploy Script ===${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    print_warning "Namespace $NAMESPACE does not exist"
    exit 0
fi

# Show current resources
echo -e "${GREEN}=== Current Resources ===${NC}"
echo ""
print_status "Pods:"
kubectl get pods -n $NAMESPACE 2>/dev/null || echo "  No pods found"
echo ""
print_status "Services:"
kubectl get svc -n $NAMESPACE 2>/dev/null || echo "  No services found"
echo ""
print_status "Ingress:"
kubectl get ingress -n $NAMESPACE 2>/dev/null || echo "  No ingress found"
echo ""

# Ask for confirmation
read -p "Delete all Speecher resources in namespace '$NAMESPACE'? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Undeploy cancelled"
    exit 0
fi

# Delete all resources
print_status "Deleting ingress..."
kubectl delete -f ingress.yaml --ignore-not-found=true

print_status "Deleting frontend..."
kubectl delete -f frontend-deployment.yaml --ignore-not-found=true

print_status "Deleting backend..."
kubectl delete -f backend-deployment.yaml --ignore-not-found=true

print_status "Deleting namespace..."
kubectl delete namespace $NAMESPACE --ignore-not-found=true

echo ""
print_status "Waiting for resources to be deleted..."
kubectl wait --for=delete namespace/$NAMESPACE --timeout=60s 2>/dev/null || true

echo ""
print_status "Undeploy completed!"
print_warning "Note: Persistent data in PostgreSQL was not affected"
