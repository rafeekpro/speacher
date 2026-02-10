#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="speecher"
CONTEXT="${KUBECONTEXT:-default}"
DOMAIN="${DOMAIN:-speecher.local}"

echo -e "${GREEN}=== Speecher Kubernetes Deployment Script ===${NC}"
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

# Check if we can connect to the cluster
print_status "Checking cluster connection..."
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

print_status "Connected to cluster successfully"
echo ""

# Check current context
CURRENT_CONTEXT=$(kubectl config current-context)
print_status "Current context: $CURRENT_CONTEXT"
print_status "Target namespace: $NAMESPACE"
print_status "Target domain: $DOMAIN"
echo ""

# Ask for confirmation
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Deployment cancelled"
    exit 0
fi

# Create namespace
print_status "Creating namespace..."
kubectl apply -f namespace.yaml

# Check if namespace exists
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    print_error "Failed to create namespace"
    exit 1
fi

# Deploy backend
print_status "Deploying backend..."
kubectl apply -f backend-deployment.yaml

# Deploy frontend
print_status "Deploying frontend..."
kubectl apply -f frontend-deployment.yaml

# Deploy ingress
print_status "Deploying ingress..."
kubectl apply -f ingress.yaml

echo ""
print_status "Waiting for deployments to be ready..."
kubectl rollout status -n $NAMESPACE deployment/backend --timeout=2m
kubectl rollout status -n $NAMESPACE deployment/frontend --timeout=2m

echo ""
print_status "Deployment completed successfully!"
echo ""

# Show status
echo -e "${GREEN}=== Deployment Status ===${NC}"
echo ""
print_status "Pods:"
kubectl get pods -n $NAMESPACE
echo ""
print_status "Services:"
kubectl get svc -n $NAMESPACE
echo ""
print_status "Ingress:"
kubectl get ingress -n $NAMESPACE
echo ""
print_status "HPA:"
kubectl get hpa -n $NAMESPACE
echo ""

# Show access information
echo -e "${GREEN}=== Access Information ===${NC}"
echo ""
print_status "Frontend URL: http://$DOMAIN"
print_status "Backend API: http://$DOMAIN/api"
print_status "API Docs: http://$DOMAIN/docs"
echo ""

# Show port forward command
print_status "To access via port forward:"
echo "  kubectl port-forward -n $NAMESPACE svc/frontend 8080:8080"
echo "  Then open: http://localhost:8080"
echo ""

# Show logs command
print_status "To view logs:"
echo "  Backend: kubectl logs -n $NAMESPACE deployment/backend -f"
echo "  Frontend: kubectl logs -n $NAMESPACE deployment/frontend -f"
echo ""

print_warning "Remember to:"
echo "  1. Update JWT_SECRET_KEY in backend-deployment.yaml"
echo "  2. Update ENCRYPTION_KEY in backend-deployment.yaml"
echo "  3. Update DOMAIN to your actual domain name"
echo "  4. Configure cloud provider credentials if needed"
echo ""

print_status "Deployment complete!"
