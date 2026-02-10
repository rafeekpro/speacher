#!/bin/bash

# Build and deploy production version
set -e

echo "🔨 Building production frontend..."

# Build production frontend with correct nginx config
cd src/react-frontend
npm run build
cd ..

# Create production nginx config
cat > docker/nginx.prod.conf <<'EOF'
server {
    listen 8080;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy - use backend service in same namespace
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# Build production image
echo "📦 Building production Docker image..."
docker build -t rafeekpro/speecher-frontend:prod -f src/react-frontend/Dockerfile.k8s --platform linux/amd64 src/react-frontend/

echo "🚀 Pushing to registry..."
docker push rafeekpro/speecher-frontend:prod

echo "✅ Production image built and pushed!"
echo ""
echo "📝 To deploy, run:"
echo "   kubectl set image deployment/frontend -n speecher-prod frontend=rafeekpro/speecher-frontend:prod"
