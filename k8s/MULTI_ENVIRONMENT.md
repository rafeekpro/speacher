# Multi-Environment Deployment Guide

This project supports deployment to two separate environments:

## Environments

### 1. Production (Main Branch)
- **Frontend URL**: https://speacher.boostpilot.io
- **Backend API URL**: https://speacher-api.boostpilot.io
- **Namespace**: `speecher-prod`
- **TLS/HTTPS**: Enabled with automatic certificates via cert-manager

### 2. Development (Develop Branch)
- **Frontend URL**: https://speacher.local.pro4.es
- **Backend API URL**: https://speacher-api.local.pro4.es
- **Namespace**: `speecher`
- **TLS/HTTPS**: Enabled

## Quick Start

### Deploy to Development
```bash
# Apply development Ingress configuration
kubectl apply -f k8s/ingress-dev.yaml

# Deploy frontend and backend services
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml

# Or use the deployment script
./k8s/deploy-env.sh dev
```

### Deploy to Production
```bash
# Create production namespace
kubectl apply -f k8s/namespace-prod.yaml

# Apply production Ingress (with TLS)
kubectl apply -f k8s/ingress-prod.yaml

# Deploy production services
kubectl apply -f k8s/frontend-deployment-prod.yaml
kubectl apply -f k8s/backend-deployment-prod.yaml

# Or use the deployment script
./k8s/deploy-env.sh prod
```

## Deployment Workflow

### Development Workflow (develop branch)
1. Make changes on `develop` branch
2. Build and push Docker images:
   ```bash
   docker build -t rafeekpro/speecher-backend:develop -f Dockerfile --platform linux/amd64 .
   docker build -t rafeekpro/speecher-frontend:develop -f src/react-frontend/Dockerfile.k8s --platform linux/amd64 src/react-frontend/
   docker push rafeekpro/speecher-backend:develop
   docker push rafeekpro/speecher-frontend:develop
   ```
3. Update image tags in deployment files (or use `:develop` tag)
4. Deploy to development namespace
5. Test at https://speacher.local.pro4.es

### Production Workflow (main branch)
1. Merge `develop` to `main` branch
2. Build and push production Docker images:
   ```bash
   docker build -t rafeekpro/speecher-backend:latest -f Dockerfile --platform linux/amd64 .
   docker build -t rafeekpro/speecher-frontend:latest -f src/react-frontend/Dockerfile.k8s --platform linux/amd64 src/react-frontend/
   docker push rafeekpro/speecher-backend:latest
   docker push rafeekpro/speecher-frontend:latest
   ```
3. Update image tags in production deployment files
4. Deploy to production namespace
5. Verify at https://speacher.boostpilot.io

## Environment Variables

### Production
```yaml
env:
  - name: REACT_APP_API_URL
    value: "https://speacher-api.boostpilot.io"
  - name: REACT_APP_ENVIRONMENT
    value: "production"
```

### Development
```yaml
env:
  - name: REACT_APP_API_URL
    value: "https://speacher-api.local.pro4.es"
  - name: REACT_APP_ENVIRONMENT
    value: "development"
```

## TLS/HTTPS Configuration

Production uses cert-manager for automatic Let's Encrypt certificate management. To enable:

1. Install cert-manager in your cluster:
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

2. Create a ClusterIssuer for Let's Encrypt:
   ```yaml
   apiVersion: cert-manager.io/v1
   kind: ClusterIssuer
   metadata:
     name: letsencrypt-prod
   spec:
     acme:
       server: https://acme-v02.api.letsencrypt.org/directory
       email: your-email@example.com
       privateKeySecretRef:
         name: letsencrypt-prod
       solvers:
       - http01:
           ingress:
             class: traefik
   ```

3. The Ingress configuration already includes the cert-manager annotation.

## Monitoring

Check deployment status:
```bash
# Development
kubectl get pods -n speecher
kubectl get ingress -n speecher

# Production
kubectl get pods -n speecher-prod
kubectl get ingress -n speecher-prod
```

View logs:
```bash
# Development backend
kubectl logs -f deployment/backend -n speecher

# Production backend
kubectl logs -f deployment/backend -n speecher-prod
```

## Rollback

If something goes wrong:

```bash
# Rollback deployment
kubectl rollout undo deployment/backend -n speecher-prod
kubectl rollout undo deployment/frontend -n speecher-prod

# Check rollback status
kubectl rollout status deployment/backend -n speecher-prod
```

## DNS Configuration

Make sure your DNS records point to the Traefik LoadBalancer IP:

### Production (boostpilot.io)
```
speacher.boostpilot.io → <LoadBalancer-IP>
speacher-api.boostpilot.io → <LoadBalancer-IP>
```

### Development (local.pro4.es)
```
speacher.local.pro4.es → <LoadBalancer-IP>
speacher-api.local.pro4.es → <LoadBalancer-IP>
```

Get the LoadBalancer IP:
```bash
kubectl get svc -n traefik traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```
