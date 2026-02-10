# Speecher Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Speecher application to a Kubernetes cluster at `rla@10.0.0.5`.

## Prerequisites

1. **kubectl** configured to access the cluster at `10.0.0.5`
2. **Docker images** built and pushed to registry:
   - `rla/speecher-backend:latest`
   - `rla/speecher-frontend:latest`
3. **PostgreSQL database** running at `10.0.0.5:30432`
4. **Traefik** (or other ingress controller) installed in the cluster

## Manifests Overview

### 1. namespace.yaml
- Creates the `speecher` namespace for the application

### 2. backend-deployment.yaml
- **Secret**: `backend-secrets` - Database credentials, API keys, JWT secret
- **Deployment**: `backend` - FastAPI backend with 2 replicas
- **Service**: `backend` - ClusterIP service on port 8000
- **HPA**: `backend-hpa` - Autoscales 2-10 replicas based on CPU/memory

### 3. frontend-deployment.yaml
- **ConfigMap**: `frontend-config` - Frontend environment variables
- **Deployment**: `frontend` - React frontend with nginx, 2 replicas
- **Service**: `frontend` - ClusterIP service on port 8080
- **HPA**: `frontend-hpa` - Autoscales 2-6 replicas based on CPU/memory

### 4. ingress.yaml
- **Ingress**: Routes traffic to frontend and backend services
- **Middleware**: HTTP to HTTPS redirect (Traefik)

## Quick Start

### 1. Set up kubectl context

```bash
# Verify you can access the cluster
kubectl cluster-info
kubectl get nodes
```

### 2. Update secrets

Edit `backend-deployment.yaml` and update:
- `JWT_SECRET_KEY` - Generate a strong random key
- `ENCRYPTION_KEY` - Change from default
- AWS/Azure/GCP credentials (if using cloud providers)

```bash
# Generate a secure JWT secret
openssl rand -base64 32
```

### 3. Update ingress domain

Edit `ingress.yaml` and replace `speecher.local` with your actual domain name.

### 4. Deploy the application

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Or apply everything at once
kubectl apply -f k8s/
```

### 5. Verify deployment

```bash
# Check pods are running
kubectl get pods -n speecher

# Check services
kubectl get svc -n speecher

# Check ingress
kubectl get ingress -n speecher

# View logs
kubectl logs -n speecher deployment/backend
kubectl logs -n speecher deployment/frontend

# Port forward to test locally
kubectl port-forward -n speecher svc/frontend 8080:8080
# Then open http://localhost:8080
```

## Configuration

### Environment Variables

**Backend (from Secret):**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - JWT signing key (CHANGE IN PRODUCTION!)
- `ENCRYPTION_KEY` - API key encryption key
- `AWS_*` - AWS S3 credentials (optional)
- `AZURE_*` - Azure Speech/Storage credentials (optional)
- `GCP_*` - Google Cloud credentials (optional)

**Frontend (from ConfigMap):**
- `REACT_APP_API_URL` - Backend API URL (uses Kubernetes service name)

### Resource Limits

**Backend:**
- Request: 256Mi RAM, 100m CPU
- Limit: 1Gi RAM, 1000m CPU

**Frontend:**
- Request: 64Mi RAM, 50m CPU
- Limit: 256Mi RAM, 200m CPU

### Autoscaling

**Backend:** 2-10 replicas
**Frontend:** 2-6 replicas

Scale based on CPU (70%) and memory (80%) utilization.

## Accessing the Application

### Via Ingress (Recommended)

After updating the ingress domain and DNS:

```bash
# Get ingress URL
kubectl get ingress -n speecher

# Access via your domain
http://speecher.local  # or your configured domain
```

### Via Port Forward (Development)

```bash
# Forward frontend
kubectl port-forward -n speecher svc/frontend 8080:8080

# Forward backend
kubectl port-forward -n speecher svc/backend 8000:8000
```

### Via NodePort (If needed)

Edit the service definitions to change type to `NodePort`:

```yaml
spec:
  type: NodePort
  ports:
  - port: 8080
    targetPort: http
    nodePort: 30080  # Frontend
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl get pods -n speecher

# Describe pod for detailed info
kubectl describe pod -n speecher <pod-name>

# View logs
kubectl logs -n speecher <pod-name> --previous  # If pod crashed

# Check events
kubectl get events -n speecher --sort-by='.lastTimestamp'
```

### Database connection issues

```bash
# Check if database is accessible from cluster
kubectl run -n speecher --rm -it --restart=Never test-pg --image=postgres:15 -- psql postgresql://speacher_user:SpeacherPro4_2024!@10.0.0.5:30432/speacher
```

### Image pull errors

```bash
# Check if images exist
docker images | grep speecher

# Pull images manually on nodes if needed
docker pull rla/speecher-backend:latest
docker pull rla/speecher-frontend:latest
```

### Ingress not working

```bash
# Check Traefik dashboard
kubectl port-forward -n traefik svc/traefik 9000:9000
# Open http://localhost:9000/dashboard/

# Check ingress controller logs
kubectl logs -n traefik deployment/traefik
```

## Maintenance

### Update deployment

```bash
# Build and push new images
docker build -f docker/backend.Dockerfile -t rla/speecher-backend:latest .
docker build -f docker/react.Dockerfile -t rla/speecher-frontend:latest .
docker push rla/speecher-backend:latest
docker push rla/speecher-frontend:latest

# Rollout restart
kubectl rollout restart -n speecher deployment/backend
kubectl rollout restart -n speecher deployment/frontend

# Watch rollout status
kubectl rollout status -n speecher deployment/backend
kubectl rollout status -n speecher deployment/frontend
```

### Scale manually

```bash
# Scale backend to 5 replicas
kubectl scale -n speecher deployment/backend --replicas=5

# Scale frontend to 3 replicas
kubectl scale -n speecher deployment/frontend --replicas=3
```

### View resource usage

```bash
# Check pod resource usage
kubectl top pods -n speecher

# Check node resource usage
kubectl top nodes
```

### Delete deployment

```bash
# Delete all resources
kubectl delete -f k8s/

# Or delete namespace (deletes everything)
kubectl delete namespace speecher
```

## Security Considerations

1. **Change default secrets** - Update `JWT_SECRET_KEY` and `ENCRYPTION_KEY` in production
2. **Use TLS** - Enable TLS on ingress for production
3. **Network policies** - Consider adding network policies to restrict pod-to-pod communication
4. **RBAC** - Implement RBAC if multiple teams share the cluster
5. **Secret management** - Use external secret management (e.g., Sealed Secrets, Vault) for production

## Production Checklist

- [ ] Change JWT_SECRET_KEY to strong random value
- [ ] Change ENCRYPTION_KEY from default
- [ ] Configure TLS certificates for ingress
- [ ] Set up monitoring and alerting (Prometheus, Grafana)
- [ ] Configure log aggregation (ELK, Loki)
- [ ] Set up backup strategy for PostgreSQL
- [ ] Configure resource quotas for namespace
- [ ] Set up pod disruption budgets
- [ ] Configure network policies
- [ ] Enable pod security policies/standards
- [ ] Set up CI/CD pipeline for automated deployments
- [ ] Configure external DNS for ingress

## Architecture

```
                          ┌─────────────┐
                          │   Ingress   │
                          │  (Traefik)  │
                          └──────┬──────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              ┌─────▼─────┐             ┌─────▼─────┐
              │ Frontend  │             │  Backend  │
              │  (nginx)  │◄────────────┤ (FastAPI) │
              │  Port 8080│             │  Port 8000│
              └───────────┘             └─────┬─────┘
                                             │
                                             │
                                      ┌──────▼──────┐
                                      │ PostgreSQL  │
                                      │10.0.0.5:30432│
                                      └─────────────┘
```

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Traefik Kubernetes Ingress](https://doc.traefik.io/traefik/providers/kubernetes-ingress/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [React Production Build](https://create-react-app.dev/docs/production-build/)
