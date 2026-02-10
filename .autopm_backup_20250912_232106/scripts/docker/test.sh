#!/bin/bash
# Run integration tests in Docker

set -e

echo "Running Speecher integration tests in Docker..."

# Check if services are running
if ! docker compose ps | grep -q "speecher-backend.*Up.*healthy"; then
    echo "Backend service is not running. Starting services first..."
    ./docker-start.sh
fi

# Create test results directory
mkdir -p test_results

# Run tests
echo "Running integration tests..."
docker compose --profile test up --abort-on-container-exit test-runner

# Check test results
if [ -f test_results/results.xml ]; then
    echo ""
    echo "Test results saved to test_results/results.xml"
    
    # Parse results (basic check)
    if grep -q 'errors="0" failures="0"' test_results/results.xml; then
        echo "All tests passed!"
        exit 0
    else
        echo "Some tests failed. Check test_results/results.xml for details."
        exit 1
    fi
else
    echo "Test results not found. Tests may have failed to run."
    exit 1
fi