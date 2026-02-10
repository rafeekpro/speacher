#!/bin/bash

# Docker build script with fallback for registry availability issues
# Usage: ./scripts/docker/build-with-fallback.sh <service> [dockerfile] [tag]

set -e

SERVICE=${1:-frontend}
DOCKERFILE=${2:-docker/react.Dockerfile}
TAG=${3:-latest}
RETRY_COUNT=3
RETRY_DELAY=30

echo "🐳 Building Docker image for $SERVICE..."
echo "📄 Using Dockerfile: $DOCKERFILE"
echo "🏷️  Tag: $TAG"

# Function to try building with a specific dockerfile
try_build() {
    local dockerfile=$1
    local attempt=$2
    local max_attempts=$3
    
    echo "📦 Attempt $attempt/$max_attempts with $dockerfile"
    
    if docker build \
        --file "$dockerfile" \
        --tag "speecher-$SERVICE:$TAG" \
        --progress=plain \
        . ; then
        echo "✅ Build successful with $dockerfile"
        return 0
    else
        echo "❌ Build failed with $dockerfile (attempt $attempt/$max_attempts)"
        return 1
    fi
}

# Main build logic with retries and fallbacks
build_with_fallback() {
    local success=false
    
    # First, try with the specified Dockerfile with retries
    for attempt in $(seq 1 $RETRY_COUNT); do
        echo "🔄 Trying primary dockerfile: $DOCKERFILE"
        
        if try_build "$DOCKERFILE" "$attempt" "$RETRY_COUNT"; then
            success=true
            break
        fi
        
        if [ $attempt -lt $RETRY_COUNT ]; then
            echo "⏳ Waiting ${RETRY_DELAY}s before retry..."
            sleep $RETRY_DELAY
        fi
    done
    
    # If primary dockerfile failed, try fallback
    if [ "$success" = false ] && [ -f "docker/react.fallback.Dockerfile" ]; then
        echo "🔄 Trying fallback dockerfile: docker/react.fallback.Dockerfile"
        
        for attempt in $(seq 1 $RETRY_COUNT); do
            if try_build "docker/react.fallback.Dockerfile" "$attempt" "$RETRY_COUNT"; then
                success=true
                echo "⚠️  Build succeeded with fallback dockerfile due to registry issues"
                echo "💡 Consider using fallback dockerfile if Docker Hub issues persist"
                break
            fi
            
            if [ $attempt -lt $RETRY_COUNT ]; then
                echo "⏳ Waiting ${RETRY_DELAY}s before retry..."
                sleep $RETRY_DELAY
            fi
        done
    fi
    
    if [ "$success" = false ]; then
        echo "💥 All build attempts failed!"
        echo "🔍 Possible issues:"
        echo "   - Docker Hub registry unavailable (503 errors)"
        echo "   - Network connectivity issues"
        echo "   - Base image not found"
        echo ""
        echo "🛠️  Troubleshooting:"
        echo "   1. Check Docker Hub status: https://status.docker.com/"
        echo "   2. Try manual pull: docker pull node:lts-alpine"
        echo "   3. Use fallback: ./scripts/docker/build-with-fallback.sh $SERVICE docker/react.fallback.Dockerfile"
        echo "   4. Check network connectivity"
        exit 1
    fi
    
    echo "🎉 Docker build completed successfully!"
}

# Registry health check
check_registry_health() {
    echo "🔍 Checking Docker Hub connectivity..."
    
    if curl -s --connect-timeout 10 https://registry-1.docker.io/v2/ > /dev/null; then
        echo "✅ Docker Hub is reachable"
        return 0
    else
        echo "⚠️  Docker Hub may be experiencing issues"
        return 1
    fi
}

# Main execution
echo "🚀 Starting Docker build with fallback strategy"
echo "================================================"

# Check registry health (informational only)
check_registry_health || echo "⚠️  Proceeding with build despite connectivity issues"

# Execute build with fallback
build_with_fallback

echo "================================================"
echo "✅ Build process completed"
echo "🏷️  Image: speecher-$SERVICE:$TAG"
echo "🔍 Verify with: docker images | grep speecher-$SERVICE"