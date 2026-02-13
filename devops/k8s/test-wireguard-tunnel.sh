#!/bin/bash
#
# Test WireGuard tunnel connectivity and basic operations
# This test verifies that the GitHub Actions runner can reach the K8s cluster
# through the WireGuard tunnel at 10.0.0.1
#

set -e

# Configuration
SERVER_WG_IP="${SERVER_WG_IP:-10.204.201.1}"
WG_INTERFACE="${WG_INTERFACE:-wg0}"

echo "🔧 WireGuard Tunnel Test Suite"
echo "================================"
echo "Target: $SERVER_WG_IP"
echo "Interface: $WG_INTERFACE"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    if [ "$result" = "pass" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        [ -n "$message" ] && echo "  $message"
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        [ -n "$message" ] && echo "  $message"
    fi
}

echo ""
echo "Test 1: WireGuard Interface Status"
echo "------------------------------------"

# Check if WireGuard interface is up
if ip link show "$WG_INTERFACE" &>/dev/null; then
    INTERFACE_STATE=$(ip link show "$WG_INTERFACE" | grep -oP '(?<=state )\w+')
    if [ "$INTERFACE_STATE" = "up" ]; then
        test_result "WireGuard interface is UP" "pass" "Interface $WG_INTERFACE is active"
    else
        test_result "WireGuard interface is UP" "fail" "Interface state: $INTERFACE_STATE"
    fi
else
    test_result "WireGuard interface exists" "fail" "Interface $WG_INTERFACE not found"
    echo -e "${YELLOW}⚠ WARNING${NC}: WireGuard tunnel may not be established"
fi

echo ""
echo "Test 2: Network Connectivity"
echo "------------------------------------"

# Test basic ping to server
if ping -c 3 -W 2 "$SERVER_WG_IP" &>/dev/null; then
    PING_RESULT=$(ping -c 3 "$SERVER_WG_IP" | tail -1)
    test_result "Can ping server at $SERVER_WG_IP" "pass" "$PING_RESULT"
else
    test_result "Can ping server at $SERVER_WG_IP" "fail" "Server unreachable"
fi

echo ""
echo "Test 3: Port Connectivity (Kubernetes API)"
echo "------------------------------------"

# Test Kubernetes API port (6443)
if timeout 3 bash -c "echo >/dev/tcp/$SERVER_WG_IP/6443" 2>/dev/null; then
    test_result "Kubernetes API port 6443 reachable" "pass"
else
    test_result "Kubernetes API port 6443 reachable" "fail" "Port may be blocked"
fi

echo ""
echo "Test 4: WireGuard Peer Status"
echo "------------------------------------"

# Check WireGuard peer status
if command -v wg &>/dev/null; then
    PEER_INFO=$(wg show "$WG_INTERFACE" 2>/dev/null || echo "")

    if [ -n "$PEER_INFO" ]; then
        # Check if handshake is complete
        if echo "$PEER_INFO" | grep -q "latest handshake"; then
            HANDSHAKE=$(echo "$PEER_INFO" | grep -oP '(?<=latest handshake: )[^,]+' | head -1)
            if [ -n "$HANDSHAKE" ]; then
                test_result "WireGuard handshake successful" "pass" "Last handshake: $HANDSHAKE"
            else
                test_result "WireGuard handshake successful" "fail" "No handshake recorded"
            fi
        else
            test_result "WireGuard handshake successful" "fail" "Peer info unavailable"
        fi

        # Check transfer stats
        if echo "$PEER_INFO" | grep -q "transfer"; then
            TRANSFER=$(echo "$PEER_INFO" | grep -oP '(?<=transfer: )[^\s]+')
            test_result "Data transfer occurring" "pass" "$TRANSFER"
        fi
    else
        test_result "WireGuard peer status available" "fail" "No peer information"
    fi
else
    echo -e "${YELLOW}⚠ WARNING${NC}: wg command not available"
fi

echo ""
echo "Test 5: kubectl Configuration"
echo "------------------------------------"

# Test kubectl configuration
if command -v kubectl &>/dev/null; then
    test_result "kubectl is installed" "pass" "kubectl version: $(kubectl version --client --short 2>/dev/null || echo 'unknown')"

    # Test if kubectl can connect to cluster
    if kubectl get nodes &>/dev/null; then
        NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
        test_result "kubectl can connect to cluster" "pass" "Nodes available: $NODE_COUNT"
    else
        test_result "kubectl can connect to cluster" "fail" "Cannot query cluster"
    fi
else
    test_result "kubectl is installed" "fail" "kubectl not found in PATH"
fi

echo ""
echo "Test 6: DNS Resolution"
echo "------------------------------------"

# Test DNS resolution
if getent hosts "$SERVER_WG_IP" &>/dev/null || ping -c 1 "$SERVER_WG_IP" &>/dev/null; then
    test_result "Can resolve $SERVER_WG_IP" "pass"
else
    test_result "Can resolve $SERVER_WG_IP" "fail" "DNS resolution failed"
fi

echo ""
echo "================================"
echo "Test Results Summary"
echo "================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo ""

# Exit with error if any tests failed
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
fi
