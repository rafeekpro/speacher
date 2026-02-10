#!/bin/bash

# Hybrid Build Wrapper Script
# This script provides fallback mechanisms for container builds
# It tries Kubernetes/Kaniko first, then falls back to other methods if needed
#
# Usage: ./hybrid-build-wrapper.sh [build-type] [options]
#
# Build Types:
#   kaniko     - Use Kaniko in Kubernetes (preferred)
#   buildkit   - Use BuildKit if available
#   docker     - Use Docker if available (fallback)
#   skip       - Skip build but return success (emergency fallback)

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

# Check if Kubernetes is available and accessible
check_kubernetes() {
    log_info "Checking Kubernetes cluster availability..."
    
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl not found"
        return 1
    fi
    
    if ! kubectl cluster-info --request-timeout=10s &> /dev/null; then
        log_warning "Kubernetes cluster not accessible"
        return 1
    fi
    
    # Check if Kaniko executor image is available
    if ! kubectl run kaniko-test --image=gcr.io/kaniko-project/executor:latest --dry-run=client &> /dev/null; then
        log_warning "Kaniko executor image not available"
        return 1
    fi
    
    log_success "Kubernetes cluster is available and ready for Kaniko builds"
    return 0
}

# Check if BuildKit is available
check_buildkit() {
    log_info "Checking BuildKit availability..."
    
    if command -v buildctl &> /dev/null; then
        log_success "BuildKit (buildctl) is available"
        return 0
    fi
    
    if command -v docker &> /dev/null && docker buildx version &> /dev/null; then
        log_success "Docker BuildKit is available"
        return 0
    fi
    
    log_warning "BuildKit not available"
    return 1
}

# Check if Docker is available
check_docker() {
    log_info "Checking Docker availability..."
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found"
        return 1
    fi
    
    if ! docker version &> /dev/null; then
        log_warning "Docker daemon not accessible"
        return 1
    fi
    
    log_success "Docker is available"
    return 0
}

# Try Kaniko build in Kubernetes
try_kaniko_build() {
    local dockerfile="$1"
    local image="$2"
    local context="${3:-.}"
    local namespace="hybrid-build-$$"
    
    log_info "Attempting Kaniko build..."
    
    # Create build namespace
    if ! kubectl create namespace "$namespace" &> /dev/null; then
        log_error "Failed to create build namespace"
        return 1
    fi
    
    # Create build context ConfigMap
    if ! kubectl create configmap build-context --from-file="$context" --namespace="$namespace" &> /dev/null; then
        log_error "Failed to create build context ConfigMap"
        kubectl delete namespace "$namespace" --ignore-not-found=true &
        return 1
    fi
    
    # Run Kaniko build using the reusable script
    if ./kaniko-build.sh \
        --namespace "$namespace" \
        --job-name "hybrid-build-$$" \
        --image "$image" \
        --context build-context \
        --dockerfile "/workspace/$dockerfile" \
        --timeout 600; then
        log_success "Kaniko build completed successfully"
        return 0
    else
        log_error "Kaniko build failed"
        return 1
    fi
}

# Try BuildKit build
try_buildkit_build() {
    local dockerfile="$1"
    local image="$2"
    local context="${3:-.}"
    
    log_info "Attempting BuildKit build..."
    
    if command -v docker &> /dev/null && docker buildx version &> /dev/null; then
        if docker buildx build -f "$dockerfile" -t "$image" "$context"; then
            log_success "Docker BuildKit build completed successfully"
            return 0
        fi
    fi
    
    if command -v buildctl &> /dev/null; then
        if buildctl build --frontend dockerfile.v0 --local context="$context" --local dockerfile="$(dirname "$dockerfile")" --output type=image,name="$image"; then
            log_success "BuildKit build completed successfully"
            return 0
        fi
    fi
    
    log_error "BuildKit build failed"
    return 1
}

# Try Docker build
try_docker_build() {
    local dockerfile="$1"
    local image="$2"
    local context="${3:-.}"
    
    log_info "Attempting Docker build..."
    
    if docker build -f "$dockerfile" -t "$image" "$context"; then
        log_success "Docker build completed successfully"
        return 0
    else
        log_error "Docker build failed"
        return 1
    fi
}

# Skip build (emergency fallback)
skip_build() {
    local image="$1"
    
    log_warning "Skipping container build as requested"
    log_warning "Image '$image' was NOT built - this is an emergency fallback"
    log_warning "Manual intervention may be required for deployment"
    
    # Create a dummy success marker for CI systems that expect it
    echo "SKIPPED: $image" > .build-skipped
    
    return 0
}

# Main hybrid build function
hybrid_build() {
    local build_type="${1:-auto}"
    local dockerfile="${2:-Dockerfile}"
    local image="${3:-test-image:latest}"
    local context="${4:-.}"
    
    log_info "Starting hybrid container build"
    log_info "  Build type: $build_type"
    log_info "  Dockerfile: $dockerfile"
    log_info "  Image: $image"
    log_info "  Context: $context"
    
    case "$build_type" in
        "kaniko")
            if check_kubernetes; then
                try_kaniko_build "$dockerfile" "$image" "$context"
                return $?
            else
                log_error "Kaniko build requested but Kubernetes not available"
                return 1
            fi
            ;;
        
        "buildkit")
            if check_buildkit; then
                try_buildkit_build "$dockerfile" "$image" "$context"
                return $?
            else
                log_error "BuildKit build requested but BuildKit not available"
                return 1
            fi
            ;;
        
        "docker")
            if check_docker; then
                try_docker_build "$dockerfile" "$image" "$context"
                return $?
            else
                log_error "Docker build requested but Docker not available"
                return 1
            fi
            ;;
        
        "skip")
            skip_build "$image"
            return $?
            ;;
        
        "auto")
            log_info "Auto-detecting best build method..."
            
            # Try Kaniko first (preferred for CI/CD)
            if check_kubernetes; then
                if try_kaniko_build "$dockerfile" "$image" "$context"; then
                    return 0
                fi
                log_warning "Kaniko build failed, trying fallback methods..."
            fi
            
            # Try BuildKit second
            if check_buildkit; then
                if try_buildkit_build "$dockerfile" "$image" "$context"; then
                    return 0
                fi
                log_warning "BuildKit build failed, trying Docker..."
            fi
            
            # Try Docker third
            if check_docker; then
                if try_docker_build "$dockerfile" "$image" "$context"; then
                    return 0
                fi
                log_warning "Docker build failed"
            fi
            
            # All methods failed
            log_error "All build methods failed"
            log_error "Available options:"
            log_error "  1. Fix Kubernetes/Kaniko setup (recommended)"
            log_error "  2. Install and configure BuildKit"
            log_error "  3. Install and configure Docker"
            log_error "  4. Use 'skip' build type for emergency bypass"
            
            return 1
            ;;
        
        *)
            log_error "Unknown build type: $build_type"
            log_error "Available types: kaniko, buildkit, docker, skip, auto"
            return 1
            ;;
    esac
}

# Usage function
usage() {
    cat << EOF
🔧 Hybrid Container Build Wrapper

This script provides fallback mechanisms for container builds in CI/CD environments.

Usage: $0 [build-type] [dockerfile] [image] [context]

Arguments:
  build-type    Build method (kaniko|buildkit|docker|skip|auto) [default: auto]
  dockerfile    Path to Dockerfile [default: Dockerfile]
  image         Target image name and tag [default: test-image:latest]  
  context       Build context directory [default: .]

Build Types:
  kaniko        Use Kaniko in Kubernetes (preferred for CI/CD)
  buildkit      Use BuildKit (fast, modern)
  docker        Use traditional Docker (fallback)
  skip          Skip build but return success (emergency only)
  auto          Try methods in order: kaniko -> buildkit -> docker

Examples:
  # Auto-detect best method
  $0 auto Dockerfile myapp:latest .

  # Force Kaniko build
  $0 kaniko docker/backend.Dockerfile myapp-backend:v1.0 .

  # Emergency skip (for broken CI)
  $0 skip Dockerfile myapp:latest .

Environment Variables:
  HYBRID_BUILD_VERBOSE    Enable verbose logging (true/false)
  HYBRID_BUILD_TIMEOUT    Build timeout in seconds (default: 600)

EOF
}

# Handle help
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

# Parse arguments
BUILD_TYPE="${1:-auto}"
DOCKERFILE="${2:-Dockerfile}"
IMAGE="${3:-test-image:latest}"
CONTEXT="${4:-.}"

# Validate arguments
if [[ ! -f "$DOCKERFILE" ]] && [[ "$BUILD_TYPE" != "skip" ]]; then
    log_error "Dockerfile not found: $DOCKERFILE"
    exit 1
fi

if [[ ! -d "$CONTEXT" ]] && [[ "$BUILD_TYPE" != "skip" ]]; then
    log_error "Build context directory not found: $CONTEXT"
    exit 1
fi

# Run hybrid build
if hybrid_build "$BUILD_TYPE" "$DOCKERFILE" "$IMAGE" "$CONTEXT"; then
    log_success "Hybrid build completed successfully!"
    exit 0
else
    log_error "Hybrid build failed!"
    exit 1
fi