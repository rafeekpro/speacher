#!/bin/bash
set -e

echo "🚀 Pushing Speecher images to Docker Hub..."
echo ""

# Push backend image
echo "📦 Pushing backend image (rla/speecher-backend:latest)..."
docker push rla/speecher-backend:latest

echo "✅ Backend pushed!"
echo ""

# Push frontend image
echo "📦 Pushing frontend image (rla/speecher-frontend:latest)..."
docker push rla/speecher-frontend:latest

echo "✅ Frontend pushed!"
echo ""
echo "🎉 All images pushed successfully!"
echo ""
echo "Next steps:"
echo "1. Update secrets in k8s/backend-deployment.yaml"
echo "2. Run: ./k8s/deploy.sh"
