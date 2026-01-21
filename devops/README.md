# Speacher DevOps - Kubernetes Deployment

Pipeline do automatycznego deployu aplikacji Speacher na Kubernetes cluster.

## Struktura

```
devops/
├── k8s/                    # Kubernetes manifests
│   ├── namespace.yml       # Namespace definition
│   ├── mongodb.yml         # MongoDB deployment + PVC + Service
│   ├── backend.yml         # FastAPI backend deployment
│   ├── frontend.yml        # React frontend deployment
│   └── secrets.yml         # Secrets and ConfigMaps
├── scripts/
│   └── deploy.sh           # Manual deployment script
└── README.md
```

## Wymagania

### Na serwerze docelowym (10.0.0.5)

- K3s lub Kubernetes cluster
- `kubectl` skonfigurowany
- SSH dostęp dla użytkownika `rla`

### Dla GitHub Actions

- Secret `DEPLOY_SSH_KEY` - klucz prywatny SSH do serwera

## Użycie

### Ręczny deploy (lokalnie)

```bash
# Pełny deploy (build + transfer + deploy)
./devops/scripts/deploy.sh all

# Tylko build obrazów
./devops/scripts/deploy.sh build

# Tylko deploy (obrazy już na serwerze)
./devops/scripts/deploy.sh deploy

# Sprawdź status
./devops/scripts/deploy.sh status

# Rollback do poprzedniej wersji
./devops/scripts/deploy.sh rollback

# Usuń deployment
./devops/scripts/deploy.sh cleanup
```

### Automatyczny deploy (GitHub Actions)

Pipeline uruchamia się automatycznie przy push do `main`/`master`.

Można też uruchomić ręcznie: **Actions** → **Deploy to Kubernetes** → **Run workflow**

## Konfiguracja

### Secrets (GitHub)

Dodaj w **Settings** → **Secrets and variables** → **Actions**:

| Secret | Opis |
|--------|------|
| `DEPLOY_SSH_KEY` | Klucz prywatny SSH do serwera |

### Secrets (Kubernetes)

Edytuj `devops/k8s/secrets.yml` przed deployem:

```yaml
stringData:
  aws-access-key-id: "TWOJ_AWS_KEY"
  aws-secret-access-key: "TWOJ_AWS_SECRET"
```

Lub utwórz secret ręcznie:

```bash
kubectl create secret generic speacher-secrets \
  --from-literal=aws-access-key-id=XXXXX \
  --from-literal=aws-secret-access-key=XXXXX \
  -n speacher
```

## Dostęp do aplikacji

Po deployu:

| Serwis | URL |
|--------|-----|
| Frontend | http://10.0.0.5:80 (lub LoadBalancer IP) |
| Backend API | http://10.0.0.5:8000 (wewnętrzny) |
| API Docs | http://10.0.0.5:8000/docs |

## Troubleshooting

### Sprawdź logi

```bash
# Backend
ssh rla@10.0.0.5 "kubectl logs -f deployment/backend -n speacher"

# Frontend
ssh rla@10.0.0.5 "kubectl logs -f deployment/frontend -n speacher"

# MongoDB
ssh rla@10.0.0.5 "kubectl logs -f deployment/mongodb -n speacher"
```

### Restart deploymentu

```bash
ssh rla@10.0.0.5 "kubectl rollout restart deployment/backend -n speacher"
```

### Sprawdź eventy

```bash
ssh rla@10.0.0.5 "kubectl get events -n speacher --sort-by='.lastTimestamp'"
```
