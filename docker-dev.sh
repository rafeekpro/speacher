#!/bin/bash
# Docker Development Quick Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker Desktop first."
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if docker compose is available
if ! command -v docker compose &> /dev/null; then
    print_warn "docker compose not found, trying docker compose..."
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available."
        exit 1
    fi
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start development environment"
    echo "  stop     - Stop development environment"
    echo "  restart  - Restart development environment"
    echo "  build    - Build Docker images"
    echo "  logs     - Show logs"
    echo "  clean    - Stop and remove volumes"
    echo "  test     - Run tests"
    echo "  shell    - Open backend shell"
    echo "  help     - Show this help message"
    echo ""
}

# Main script
case "$1" in
    start)
        print_info "Starting development environment..."
        
        # Check if .env file exists
        if [ ! -f .env ]; then
            if [ -f .env.docker.example ]; then
                print_warn ".env file not found. Creating from .env.docker.example..."
                cp .env.docker.example .env
                print_info "Please update .env with your configuration."
            else
                print_error ".env file not found and no example file available."
                exit 1
            fi
        fi
        
        # Build if needed
        print_info "Building Docker images..."
        $COMPOSE_CMD -f docker-compose.dev.yml build
        
        # Start services
        print_info "Starting services..."
        $COMPOSE_CMD -f docker-compose.dev.yml up -d
        
        # Wait for services to be ready
        print_info "Waiting for services to be ready..."
        sleep 5
        
        # Check health
        print_info "Checking service health..."
        $COMPOSE_CMD -f docker-compose.dev.yml ps
        
        print_info "Development environment is ready!"
        print_info "Frontend: http://localhost:3000"
        print_info "Backend API: http://localhost:8000"
        print_info "API Docs: http://localhost:8000/docs"
        ;;
        
    stop)
        print_info "Stopping development environment..."
        $COMPOSE_CMD -f docker-compose.dev.yml down
        print_info "Development environment stopped."
        ;;
        
    restart)
        print_info "Restarting development environment..."
        $COMPOSE_CMD -f docker-compose.dev.yml restart
        print_info "Development environment restarted."
        ;;
        
    build)
        print_info "Building Docker images..."
        $COMPOSE_CMD -f docker-compose.dev.yml build
        print_info "Build complete."
        ;;
        
    logs)
        print_info "Showing logs (press Ctrl+C to exit)..."
        $COMPOSE_CMD -f docker-compose.dev.yml logs -f
        ;;
        
    clean)
        print_warn "This will stop all containers and remove volumes!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cleaning up..."
            $COMPOSE_CMD -f docker-compose.dev.yml down -v
            print_info "Cleanup complete."
        else
            print_info "Cleanup cancelled."
        fi
        ;;
        
    test)
        print_info "Running tests..."
        $COMPOSE_CMD -f docker-compose.dev.yml --profile test up test-runner
        ;;
        
    shell)
        print_info "Opening backend shell..."
        $COMPOSE_CMD -f docker-compose.dev.yml exec backend bash
        ;;
        
    help|--help|-h)
        show_usage
        ;;
        
    "")
        show_usage
        ;;
        
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac