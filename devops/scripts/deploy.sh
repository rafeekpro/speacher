#!/bin/bash
set -euo pipefail

# Speacher Kubernetes Deployment Script
# Usage: ./deploy.sh [build|deploy|all|rollback]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
K8S_DIR="$SCRIPT_DIR/../k8s"

# Configuration
REMOTE_HOST="${DEPLOY_HOST:-rla@10.0.0.5}"
REMOTE_DIR="/tmp/speacher-deploy"
REGISTRY="${DOCKER_REGISTRY:-localhost:5000}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Build Docker images locally
build_images() {
    log_info "Building Docker images..."

    cd "$PROJECT_ROOT"

    # Build backend
    log_info "Building backend image..."
    docker build -f docker/backend.Dockerfile -t "$REGISTRY/speacher-backend:$IMAGE_TAG" --target production .

    # Build frontend
    log_info "Building frontend image..."
    docker build -f docker/react.Dockerfile -t "$REGISTRY/speacher-frontend:$IMAGE_TAG" .

    log_info "Images built successfully"
}

# Push images to registry (if using remote registry)
push_images() {
    log_info "Pushing images to registry..."

    docker push "$REGISTRY/speacher-backend:$IMAGE_TAG"
    docker push "$REGISTRY/speacher-frontend:$IMAGE_TAG"

    log_info "Images pushed successfully"
}

# Save and transfer images via SSH (for local registry)
transfer_images() {
    log_info "Transferring images to remote host..."

    # Save images to tar
    docker save "$REGISTRY/speacher-backend:$IMAGE_TAG" "$REGISTRY/speacher-frontend:$IMAGE_TAG" | gzip > /tmp/speacher-images.tar.gz

    # Transfer to remote
    scp /tmp/speacher-images.tar.gz "$REMOTE_HOST:/tmp/"

    # Load images on remote
    ssh "$REMOTE_HOST" "gunzip -c /tmp/speacher-images.tar.gz | sudo k3s ctr images import -"

    # Cleanup
    rm -f /tmp/speacher-images.tar.gz
    ssh "$REMOTE_HOST" "rm -f /tmp/speacher-images.tar.gz"

    log_info "Images transferred successfully"
}

# Deploy to Kubernetes cluster
deploy() {
    log_info "Deploying to Kubernetes cluster on $REMOTE_HOST..."

    # Create remote directory
    ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR"

    # Copy manifests
    scp -r "$K8S_DIR"/* "$REMOTE_HOST:$REMOTE_DIR/"

    # Apply manifests in order
    ssh "$REMOTE_HOST" << 'DEPLOY_SCRIPT'
        set -e
        cd /tmp/speacher-deploy

        echo "Applying namespace..."
        kubectl apply -f namespace.yml

        echo "Applying secrets and config..."
        kubectl apply -f secrets.yml

        echo "Deploying MongoDB..."
        kubectl apply -f mongodb.yml

        echo "Waiting for MongoDB to be ready..."
        kubectl wait --for=condition=available --timeout=120s deployment/mongodb -n speacher || true

        echo "Deploying backend..."
        kubectl apply -f backend.yml

        echo "Deploying frontend..."
        kubectl apply -f frontend.yml

        echo "Waiting for deployments to be ready..."
        kubectl wait --for=condition=available --timeout=180s deployment/backend -n speacher
        kubectl wait --for=condition=available --timeout=180s deployment/frontend -n speacher

        echo "Deployment complete!"
        kubectl get pods -n speacher
        kubectl get svc -n speacher
DEPLOY_SCRIPT

    log_info "Deployment completed successfully"
}

# Rollback to previous version
rollback() {
    log_info "Rolling back deployments..."

    ssh "$REMOTE_HOST" << 'ROLLBACK_SCRIPT'
        kubectl rollout undo deployment/backend -n speacher
        kubectl rollout undo deployment/frontend -n speacher

        echo "Waiting for rollback to complete..."
        kubectl rollout status deployment/backend -n speacher
        kubectl rollout status deployment/frontend -n speacher

        echo "Rollback complete!"
        kubectl get pods -n speacher
ROLLBACK_SCRIPT

    log_info "Rollback completed"
}

# Check deployment status
status() {
    log_info "Checking deployment status..."

    ssh "$REMOTE_HOST" << 'STATUS_SCRIPT'
        echo "=== Pods ==="
        kubectl get pods -n speacher -o wide

        echo ""
        echo "=== Services ==="
        kubectl get svc -n speacher

        echo ""
        echo "=== Deployments ==="
        kubectl get deployments -n speacher

        echo ""
        echo "=== Recent Events ==="
        kubectl get events -n speacher --sort-by='.lastTimestamp' | tail -10
STATUS_SCRIPT
}

# Cleanup deployment
cleanup() {
    log_warn "Removing all speacher resources..."

    ssh "$REMOTE_HOST" << 'CLEANUP_SCRIPT'
        kubectl delete namespace speacher --ignore-not-found=true
        echo "Cleanup complete"
CLEANUP_SCRIPT
}

# Show usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build      Build Docker images locally"
    echo "  push       Push images to registry"
    echo "  transfer   Transfer images via SSH (for local/air-gapped)"
    echo "  deploy     Deploy to Kubernetes cluster"
    echo "  all        Build, transfer, and deploy"
    echo "  rollback   Rollback to previous deployment"
    echo "  status     Check deployment status"
    echo "  cleanup    Remove all speacher resources"
    echo ""
    echo "Environment variables:"
    echo "  DEPLOY_HOST    Remote host (default: rla@10.0.0.5)"
    echo "  DOCKER_REGISTRY Registry URL (default: localhost:5000)"
    echo "  IMAGE_TAG      Image tag (default: latest)"
}

# Main
case "${1:-help}" in
    build)
        build_images
        ;;
    push)
        push_images
        ;;
    transfer)
        transfer_images
        ;;
    deploy)
        deploy
        ;;
    all)
        build_images
        transfer_images
        deploy
        ;;
    rollback)
        rollback
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    *)
        usage
        ;;
esac
