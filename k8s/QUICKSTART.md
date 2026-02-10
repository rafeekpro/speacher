# Quick Start Guide - Speecher Kubernetes Deployment

## Prerequisites Checklist

- [ ] kubectl installed and configured for cluster at 10.0.0.5
- [ ] Docker images built and pushed:
  - [ ] `rla/speecher-backend:latest`
  - [ ] `rla/speecher-frontend:latest`
- [ ] PostgreSQL database running at 10.0.0.5:30432
- [ ] Ingress controller installed (Traefik, NGINX, or other)

## 5-Minute Deployment

### Step 1: Update Secrets

Generate a secure JWT secret:
```bash
openssl rand -base64 32
```

Edit `k8s/backend-deployment.yaml` and update:
- `JWT_SECRET_KEY` (use generated key)
- `ENCRYPTION_KEY` (change from default)

### Step 2: Update Domain

Edit `k8s/ingress.yaml`:
- Replace `speecher.local` with your actual domain

### Step 3: Deploy

```bash
cd /Users/rla/Projects/Speecher

# Option A: Use deployment script (recommended)
./k8s/deploy.sh

# Option B: Manual deployment
kubectl apply -f k8s/
```

### Step 4: Verify

```bash
# Check all pods are running
kubectl get pods -n speecher

# Should see:
# NAME                       READY   STATUS    RESTARTS   AGE
# backend-xxxxxxxxxx-xxxxx   1/1     Running   0          1m
# frontend-xxxxxxxxxx-xxxxx  1/1     Running   0          1m
```

## Access the Application

### Option 1: Via Domain (after DNS configured)
```
http://your-domain.com
```

### Option 2: Via Port Forward (immediate access)
```bash
# Terminal 1: Forward frontend
kubectl port-forward -n speecher svc/frontend 8080:8080

# Terminal 2: Forward backend (for API testing)
kubectl port-forward -n speecher svc/backend 8000:8000

# Access at: http://localhost:8080
```

### Option 3: Via Ingress IP
```bash
# Get ingress address
kubectl get ingress -n speecher

# Access via IP (add to /etc/hosts if needed)
http://ingress-ip/
```

## Troubleshooting

### Pods not starting?
```bash
# Check pod status
kubectl get pods -n speecher

# Describe pod for details
kubectl describe pod -n speecher <pod-name>

# View logs
kubectl logs -n speecher <pod-name>
```

### Can't access database?
```bash
# Test database connection from pod
kubectl run -n speecher --rm -it --restart=Never test-pg --image=postgres:15 -- \
  psql postgresql://speacher_user:SpeacherPro4_2024!@10.0.0.5:30432/speacher
```

### Images not pulling?
```bash
# Check if images exist
docker images | grep speecher

# Pull images on cluster nodes if needed
docker pull rla/speecher-backend:latest
docker pull rla/speecher-frontend:latest
```

## Common Commands

```bash
# View logs
kubectl logs -n speecher deployment/backend -f
kubectl logs -n speecher deployment/frontend -f

# Scale manually
kubectl scale -n speecher deployment/backend --replicas=5

# Restart deployment
kubectl rollout restart -n speecher deployment/backend

# Check resource usage
kubectl top pods -n speecher
kubectl top nodes

# Delete everything
./k8s/undeploy.sh
```

## Next Steps

1. **Configure monitoring** (Prometheus, Grafana)
2. **Set up log aggregation** (ELK, Loki)
3. **Enable TLS** on ingress
4. **Configure backups** for PostgreSQL
5. **Set up CI/CD** pipeline

## Production Checklist

- [ ] Change `JWT_SECRET_KEY` to strong random value
- [ ] Change `ENCRYPTION_KEY` from default
- [ ] Configure TLS certificates
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up database backups
- [ ] Configure resource quotas
- [ ] Set up network policies
- [ ] Enable RBAC
- [ ] Configure external DNS

## Support

For detailed documentation, see: [k8s/README.md](README.md)
