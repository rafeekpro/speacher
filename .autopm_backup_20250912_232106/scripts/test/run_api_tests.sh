#!/bin/bash

# Speecher API Test Runner
# This script runs all API tests with coverage and generates reports

set -e

echo "🧪 Speecher API Test Suite"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install test dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q -r requirements-test.txt

# Create test results directory
mkdir -p test_results

# Run unit tests
echo ""
echo -e "${GREEN}Running Unit Tests...${NC}"
echo "---------------------"
pytest tests/test_api.py -v --cov=src/backend --cov-report=html:test_results/coverage_html --cov-report=term

# Run integration tests
echo ""
echo -e "${GREEN}Running Integration Tests...${NC}"
echo "-------------------------"
pytest tests/test_integration.py -v

# Run linting
echo ""
echo -e "${GREEN}Running Code Quality Checks...${NC}"
echo "-----------------------------"

echo "Black (formatting):"
black --check src/ tests/ || echo -e "${YELLOW}Some files need formatting${NC}"

echo ""
echo "isort (imports):"
isort --check-only src/ tests/ || echo -e "${YELLOW}Some imports need sorting${NC}"

echo ""
echo "Flake8 (linting):"
flake8 src/ tests/ --max-line-length=120 --ignore=E203,W503 || echo -e "${YELLOW}Some linting issues found${NC}"

# Generate test report
echo ""
echo -e "${GREEN}Generating Test Report...${NC}"
echo "------------------------"

# Create summary report
cat > test_results/summary.txt << EOF
Speecher API Test Results
Generated: $(date)

Test Statistics:
----------------
$(pytest tests/ --co -q | tail -1)

Coverage Report:
---------------
$(pytest tests/test_api.py --cov=src/backend --cov-report=term | grep TOTAL || echo "Coverage data not available")

To view detailed coverage report, open:
test_results/coverage_html/index.html
EOF

echo ""
echo -e "${GREEN}✅ Test suite completed!${NC}"
echo ""
echo "📊 Results saved to test_results/"
echo "📈 Coverage report: test_results/coverage_html/index.html"
echo ""

# Check if all tests passed
if pytest tests/ -q; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the output above.${NC}"
    exit 1
fi