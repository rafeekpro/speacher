# GitHub Actions Containerd Runner Setup

## Co trzeba zainstalować na K3s containerd runners

### 🐍 Python Backend Dependencies
```bash
# Python 3.11 + development tools
sudo apt-get install python3.11 python3.11-dev python3.11-venv python3-pip
python3.11 -m pip install --upgrade pip

# Python testing and quality tools  
pip3.11 install pytest pytest-asyncio pytest-cov pytest-xdist
pip3.11 install black flake8 mypy bandit safety
pip3.11 install mongomock httpx fastapi uvicorn
```

### 🟢 Node.js Frontend Dependencies
```bash
# Multiple Node.js versions (workflows use 18.x, 20.x)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm install 20
nvm use 20  # default

# Playwright browsers + dependencies
npm install -g playwright
playwright install --with-deps chromium firefox webkit
```

### 🐳 Container Runtime (nerdctl)
```bash
# nerdctl for Docker compatibility
VERSION="1.7.0"
wget https://github.com/containerd/nerdctl/releases/download/v${VERSION}/nerdctl-${VERSION}-linux-amd64.tar.gz
sudo tar -xzf nerdctl-${VERSION}-linux-amd64.tar.gz -C /usr/local/bin/
sudo ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker

# BuildKit daemon for advanced builds
sudo systemctl enable --now buildkit
```

### ☸️ Kubernetes Tools
```bash
# kubectl (should already be available in K3s)
# If missing:
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

### 🗄️ Database Tools
```bash
# MongoDB shell for testing
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install mongodb-mongosh
```

### 🔒 Security Tools
```bash
# Trivy for container scanning
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

### 🛠️ System Dependencies
```bash
# Basic build tools
sudo apt-get install build-essential git curl wget unzip
sudo apt-get install ca-certificates gnupg lsb-release

# Additional libraries for Playwright
sudo apt-get install libnss3 libxss1 libasound2 libxtst6 libxrandr2 
sudo apt-get install libgtk-3-0 libgbm-dev libxshmfence1
```

## 🚀 Quick Install Script

Skopiuj i uruchom na każdym runner:

```bash
# Pobierz i uruchom installation script
wget https://raw.githubusercontent.com/[username]/speecher/feature/integrate-sidebar-layout/scripts/setup-containerd-runner.sh
chmod +x setup-containerd-runner.sh
./setup-containerd-runner.sh
```

## ✅ Verification Commands

Po instalacji sprawdź czy wszystko działa:

```bash
# Python
python3.11 --version
pip3.11 --version
pytest --version

# Node.js  
node --version
npm --version
npx playwright --version

# Container tools
nerdctl version
kubectl version --client

# Database
mongosh --version

# Security
trivy --version
```

## 🎯 Na którym runnerze co jest potrzebne

**Wszystkie 3 runnery potrzebują:**
- ✅ Python 3.11 + pip + pytest
- ✅ Node.js 18.x & 20.x + npm  
- ✅ nerdctl + Docker compatibility
- ✅ kubectl
- ✅ Basic system tools

**Dodatkowo dla visual tests:**
- ✅ Playwright browsers (chromium, firefox, webkit)
- ✅ System libraries for browser rendering

**Dodatkowo dla security scans:**
- ✅ Trivy vulnerability scanner
- ✅ Bandit, Safety for Python security

## 🔧 Troubleshooting

**Jeśli workflows nadal failują:**

1. **Check Python version:**
   ```bash
   python3.11 --version  # Should be 3.11.x
   which python3.11
   ```

2. **Check nerdctl Docker compatibility:**
   ```bash
   docker --version  # Should show nerdctl
   docker ps  # Should work
   ```

3. **Check Playwright browsers:**
   ```bash
   npx playwright install --dry-run
   ```

4. **Check kubectl access:**
   ```bash
   kubectl get nodes  # Should show K3s nodes
   kubectl get pods --all-namespaces
   ```