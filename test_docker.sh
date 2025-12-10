#!/bin/bash

# Local Docker Testing Script for Lingolino API
# This script helps test the Docker container locally before deploying to AWS

set -e

echo "🐳 Lingolino Docker Testing Script"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Create a .env file with your environment variables (see .env.example)"
    exit 1
fi

# Function to check if port is in use
check_port() {
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}⚠️  Warning: Port 8000 is already in use${NC}"
        echo "Kill the process and try again, or use a different port"
        exit 1
    fi
}

# Function to build image
build_image() {
    echo "🔨 Building Docker image..."
    docker build -t lingolino-api:local .

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Image built successfully${NC}"
    else
        echo -e "${RED}❌ Failed to build image${NC}"
        exit 1
    fi
}

# Function to run container
run_container() {
    echo ""
    echo "🚀 Starting container..."
    docker run -d \
        --name lingolino-api-test \
        -p 8000:8000 \
        --env-file .env \
        lingolino-api:local

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Container started successfully${NC}"
        echo ""
        echo "📡 API is running at: http://localhost:8000"
        echo "📖 API Docs: http://localhost:8000/docs"
        echo "🏥 Health Check: http://localhost:8000/health"
    else
        echo -e "${RED}❌ Failed to start container${NC}"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    echo ""
    echo "📋 Container logs (Ctrl+C to exit):"
    echo "-----------------------------------"
    docker logs -f lingolino-api-test
}

# Function to stop container
stop_container() {
    echo ""
    echo "🛑 Stopping container..."
    docker stop lingolino-api-test 2>/dev/null || true
    docker rm lingolino-api-test 2>/dev/null || true
    echo -e "${GREEN}✅ Container stopped and removed${NC}"
}

# Function to test health endpoint
test_health() {
    echo ""
    echo "🏥 Testing health endpoint..."
    sleep 3  # Give container time to start

    for i in {1..10}; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Health check passed!${NC}"
            curl http://localhost:8000/health | jq .
            return 0
        fi
        echo "Waiting for container to be ready... ($i/10)"
        sleep 2
    done

    echo -e "${RED}❌ Health check failed${NC}"
    echo "Check container logs:"
    docker logs lingolino-api-test
    return 1
}

# Function to run tests
run_tests() {
    echo ""
    echo "🧪 Running API tests..."

    # Test root endpoint
    echo -n "Testing root endpoint... "
    if curl -f http://localhost:8000/ >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
    fi

    # Test docs
    echo -n "Testing /docs endpoint... "
    if curl -f http://localhost:8000/docs >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
    fi

    # Test health
    echo -n "Testing /health endpoint... "
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
    fi
}

# Main menu
case "${1:-}" in
    build)
        build_image
        ;;
    start)
        check_port
        stop_container  # Clean up any existing container
        build_image
        run_container
        test_health
        run_tests
        echo ""
        echo "💡 Tip: Run './test_docker.sh logs' to view container logs"
        echo "💡 Tip: Run './test_docker.sh stop' to stop the container"
        ;;
    stop)
        stop_container
        ;;
    logs)
        show_logs
        ;;
    test)
        test_health
        run_tests
        ;;
    restart)
        stop_container
        "$0" start
        ;;
    shell)
        echo "🐚 Opening shell in container..."
        docker exec -it lingolino-api-test /bin/bash
        ;;
    *)
        echo "Usage: $0 {build|start|stop|logs|test|restart|shell}"
        echo ""
        echo "Commands:"
        echo "  build   - Build Docker image only"
        echo "  start   - Build and start container"
        echo "  stop    - Stop and remove container"
        echo "  logs    - Show container logs (real-time)"
        echo "  test    - Run health checks"
        echo "  restart - Stop and start container"
        echo "  shell   - Open bash shell in running container"
        echo ""
        echo "Example: ./test_docker.sh start"
        exit 1
        ;;
esac

