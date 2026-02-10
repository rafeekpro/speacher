#!/bin/bash

# Reusable Kaniko Build Script for GitHub Actions
# This script standardizes container builds using Kaniko in Kubernetes
#
# Usage: ./kaniko-build.sh [options]
# 
# Options:
#   -n, --namespace     Build namespace (required)
#   -j, --job-name      Job name (required)
#   -d, --dockerfile    Dockerfile path (default: /workspace/Dockerfile)
#   -i, --image         Destination image name and tag (required)
#   -c, --context       Build context ConfigMap name (required)
#   -t, --timeout       Build timeout in seconds (default: 600)
#   -m, --memory        Memory limit (default: 2Gi)
#   --cpu              CPU limit (default: 1000m)
#   --cache-repo       Cache repository for build cache
#   --cleanup          Cleanup namespace after build (default: true)
#   --verbose          Enable verbose logging
#   --help             Show this help message

set -euo pipefail

# Default values
DOCKERFILE_PATH="/workspace/Dockerfile"
TIMEOUT="600"
MEMORY_LIMIT="2Gi"
CPU_LIMIT="1000m"
MEMORY_REQUEST="1Gi"
CPU_REQUEST="500m"
CLEANUP="true"
VERBOSE="false"
CACHE_REPO=""

# Required parameters (will be validated)
NAMESPACE=""
JOB_NAME=""
IMAGE=""
BUILD_CONTEXT_CONFIGMAP=""

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

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}🔍 $1${NC}"
    fi
}

# Usage function
usage() {
    cat << EOF
🏗️  Kaniko Build Script for Kubernetes

Usage: $0 [options]

Required Options:
  -n, --namespace NAMESPACE          Build namespace
  -j, --job-name JOB_NAME           Unique job name
  -i, --image IMAGE                 Destination image name and tag
  -c, --context CONFIGMAP           Build context ConfigMap name

Optional Options:
  -d, --dockerfile PATH             Dockerfile path (default: /workspace/Dockerfile)
  -t, --timeout SECONDS            Build timeout (default: 600)
  -m, --memory MEMORY               Memory limit (default: 2Gi)
      --cpu CPU                     CPU limit (default: 1000m)
      --cache-repo REPO             Cache repository for build cache
      --no-cleanup                  Don't cleanup namespace after build
      --verbose                     Enable verbose logging
      --help                        Show this help message

Examples:
  # Basic backend build
  $0 -n build-123 -j backend-build -i myapp:latest -c build-context

  # Frontend build with custom Dockerfile
  $0 -n build-123 -j frontend-build -i myapp-ui:v1.0 -c build-context \\
     -d /workspace/docker/react.Dockerfile

  # Build with cache and higher resources
  $0 -n build-123 -j api-build -i api:prod -c build-context \\
     --cache-repo myapp-cache --memory 4Gi --cpu 2000m

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -j|--job-name)
            JOB_NAME="$2"
            shift 2
            ;;
        -d|--dockerfile)
            DOCKERFILE_PATH="$2"
            shift 2
            ;;
        -i|--image)
            IMAGE="$2"
            shift 2
            ;;
        -c|--context)
            BUILD_CONTEXT_CONFIGMAP="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -m|--memory)
            MEMORY_LIMIT="$2"
            shift 2
            ;;
        --cpu)
            CPU_LIMIT="$2"
            shift 2
            ;;
        --cache-repo)
            CACHE_REPO="$2"
            shift 2
            ;;
        --no-cleanup)
            CLEANUP="false"
            shift
            ;;
        --verbose)
            VERBOSE="true"
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$NAMESPACE" ]]; then
    log_error "Namespace is required (-n, --namespace)"
    exit 1
fi

if [[ -z "$JOB_NAME" ]]; then
    log_error "Job name is required (-j, --job-name)"
    exit 1
fi

if [[ -z "$IMAGE" ]]; then
    log_error "Image name is required (-i, --image)"
    exit 1
fi

if [[ -z "$BUILD_CONTEXT_CONFIGMAP" ]]; then
    log_error "Build context ConfigMap is required (-c, --context)"
    exit 1
fi

# Validate kubectl is available
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is required but not installed"
    exit 1
fi

# Validate Kubernetes cluster access
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot access Kubernetes cluster"
    exit 1
fi

log_info "Starting Kaniko build with the following parameters:"
log_info "  Namespace: $NAMESPACE"
log_info "  Job Name: $JOB_NAME"
log_info "  Image: $IMAGE"
log_info "  Dockerfile: $DOCKERFILE_PATH"
log_info "  Context ConfigMap: $BUILD_CONTEXT_CONFIGMAP"
log_info "  Timeout: ${TIMEOUT}s"
log_info "  Resources: ${MEMORY_LIMIT} memory, ${CPU_LIMIT} CPU"

# Create namespace if it doesn't exist
log_verbose "Creating namespace $NAMESPACE if it doesn't exist"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Verify build context ConfigMap exists
log_verbose "Verifying build context ConfigMap exists"
if ! kubectl get configmap "$BUILD_CONTEXT_CONFIGMAP" -n "$NAMESPACE" &> /dev/null; then
    log_error "Build context ConfigMap '$BUILD_CONTEXT_CONFIGMAP' not found in namespace '$NAMESPACE'"
    exit 1
fi

# Build Kaniko job YAML
log_verbose "Creating Kaniko job YAML"
KANIKO_ARGS="--dockerfile=$DOCKERFILE_PATH --context=/workspace --destination=$IMAGE --cache=true --cache-ttl=24h"

if [[ -n "$CACHE_REPO" ]]; then
    KANIKO_ARGS="$KANIKO_ARGS --cache-repo=$CACHE_REPO"
fi

cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $JOB_NAME
  namespace: $NAMESPACE
  labels:
    app: kaniko-build
    build-type: container
    created-by: kaniko-build-script
spec:
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: kaniko-build
    spec:
      restartPolicy: Never
      containers:
      - name: kaniko
        image: gcr.io/kaniko-project/executor:latest
        args: [$(echo "$KANIKO_ARGS" | tr ' ' '\n' | sed 's/^/"/' | sed 's/$/"/' | tr '\n' ',' | sed 's/,$/\n/')]
        volumeMounts:
        - name: build-context
          mountPath: /workspace
        resources:
          requests:
            memory: "$MEMORY_REQUEST"
            cpu: "$CPU_REQUEST"
          limits:
            memory: "$MEMORY_LIMIT"
            cpu: "$CPU_LIMIT"
        securityContext:
          runAsUser: 1000
          runAsNonRoot: true
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      volumes:
      - name: build-context
        configMap:
          name: $BUILD_CONTEXT_CONFIGMAP
EOF

log_success "Kaniko job created: $JOB_NAME"

# Wait for job completion
log_info "Waiting for build to complete (timeout: ${TIMEOUT}s)..."

if kubectl wait --for=condition=complete job/$JOB_NAME \
    --timeout="${TIMEOUT}s" \
    --namespace="$NAMESPACE"; then
    log_success "Build completed successfully!"
    
    # Show build logs if verbose
    if [[ "$VERBOSE" == "true" ]]; then
        log_verbose "Build logs:"
        kubectl logs job/$JOB_NAME --namespace="$NAMESPACE" --tail=20
    fi
else
    log_error "Build failed or timed out"
    
    # Show error logs
    log_error "Build logs (last 50 lines):"
    kubectl logs job/$JOB_NAME --namespace="$NAMESPACE" --tail=50 || true
    
    # Show pod status for debugging
    log_error "Pod status:"
    kubectl get pods -l job-name=$JOB_NAME --namespace="$NAMESPACE" || true
    
    # Cleanup and exit with error
    if [[ "$CLEANUP" == "true" ]]; then
        log_info "Cleaning up failed build resources..."
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true --grace-period=30 &
    fi
    
    exit 1
fi

# Optional cleanup
if [[ "$CLEANUP" == "true" ]]; then
    log_info "Cleaning up build resources..."
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true --grace-period=30 &
    log_success "Cleanup initiated (running in background)"
else
    log_info "Build resources preserved in namespace: $NAMESPACE"
fi

log_success "Kaniko build script completed successfully!"
log_info "Image built: $IMAGE"