#!/bin/bash

# Deploy to specific environment (dev or prod)
set -e

ENVIRONMENT=${1:-dev}
NAMESPACE=${2:-speecher}

if [ "$ENVIRONMENT" = "prod" ]; then
  NAMESPACE="speecher-prod"
  echo "🚀 Deploying to PRODUCTION (boostpilot.io)..."
elif [ "$ENVIRONMENT" = "dev" ]; then
  NAMESPACE="speecher"
  echo "🔧 Deploying to DEVELOPMENT (local.pro4.es)..."
else
  echo "❌ Usage: $0 [dev|prod]"
  exit 1
fi

# Create namespace if it doesn't exist
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Apply Ingress configuration
if [ "$ENVIRONMENT" = "prod" ]; then
  kubectl apply -f k8s/ingress-prod.yaml
else
  kubectl apply -f k8s/ingress-dev.yaml
fi

echo "✅ Deployment to $ENVIRONMENT complete!"
echo ""
echo "📝 Next steps:"
echo "1. Deploy backend and frontend services to namespace: $NAMESPACE"
echo "2. Configure environment variables:"
if [ "$ENVIRONMENT" = "prod" ]; then
  echo "   - REACT_APP_API_URL=https://speacher-api.boostpilot.io"
  echo "   - Frontend will be available at: https://speacher.boostpilot.io"
  echo "   - Backend API will be available at: https://speacher-api.boostpilot.io"
else
  echo "   - REACT_APP_API_URL=https://speacher-api.local.pro4.es"
  echo "   - Frontend will be available at: https://speacher.local.pro4.es"
  echo "   - Backend API will be available at: https://speacher-api.local.pro4.es"
fi
