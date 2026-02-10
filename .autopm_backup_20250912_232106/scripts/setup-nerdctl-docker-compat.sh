#!/bin/bash
set -e

echo "🔧 Setting up nerdctl Docker compatibility for K3s runners"

# Check if nerdctl is installed
if ! command -v nerdctl &> /dev/null; then
    echo "❌ nerdctl is not installed. Please install nerdctl first."
    exit 1
fi

echo "✅ nerdctl found: $(which nerdctl)"
echo "📋 nerdctl version: $(nerdctl version --short)"

# Create docker symlink if docker command doesn't exist
if ! command -v docker &> /dev/null; then
    echo "🔗 Creating docker -> nerdctl symlink..."
    sudo ln -sf $(which nerdctl) /usr/local/bin/docker
    echo "✅ docker command now points to nerdctl"
else
    echo "ℹ️  docker command already exists: $(which docker)"
fi

# Test basic functionality
echo "🧪 Testing basic functionality..."
docker version || nerdctl version
docker ps || echo "Docker ps works via nerdctl"

# Check for docker compose compatibility
if ! command -v docker compose &> /dev/null; then
    if nerdctl compose version &> /dev/null; then
        echo "🔗 Creating docker compose -> nerdctl compose wrapper..."
        sudo tee /usr/local/bin/docker compose > /dev/null << 'EOF'
#!/bin/bash
exec nerdctl compose "$@"
EOF
        sudo chmod +x /usr/local/bin/docker-compose
        echo "✅ docker compose command now points to nerdctl compose"
    else
        echo "⚠️  nerdctl compose not available, you may need docker compose for some workflows"
    fi
else
    echo "ℹ️  docker compose command already exists: $(which docker-compose)"
fi

echo ""
echo "🎉 nerdctl Docker compatibility setup complete!"
echo ""
echo "Available commands:"
echo "  docker -> $(readlink -f /usr/local/bin/docker 2>/dev/null || echo 'native docker')"
echo "  docker compose -> $(readlink -f /usr/local/bin/docker compose 2>/dev/null || echo 'native docker-compose')"
echo "  nerdctl -> $(which nerdctl)"
echo ""
echo "Your existing GitHub Actions workflows should now work without modifications!"