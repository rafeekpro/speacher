#!/bin/bash
#
# WireGuard Server Diagnostic Script
# Run this on your K8s server to diagnose WireGuard issues
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 WireGuard Server Diagnostics"
echo "================================"
echo ""

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
echo "Test 1: Systemd Service Status"
echo "------------------------------------"

# Check if systemd service is running
if systemctl is-active --quiet wg-quick@wg0; then
    test_result "WireGuard service is running" "pass" "Service is active"
else
    test_result "WireGuard service is running" "fail" "Service is not active"
fi

# Check for recent failures
if systemctl is-failed --quiet wg-quick@wg0; then
    test_result "WireGuard service has no recent failures" "pass"
else
    test_result "WireGuard service has no recent failures" "fail" "Service has failed recently"
fi

echo ""
echo "Test 2: Kernel Modules"
echo "------------------------------------"

# Check required kernel modules
REQUIRED_MODULES="ip_tables iptable_nat iptable_filter wireguard"

for module in $REQUIRED_MODULES; do
    if lsmod | grep -q "$module"; then
        test_result "Kernel module $module is loaded" "pass"
    else
        test_result "Kernel module $module is loaded" "fail" "Module missing - run: sudo modprobe $module"
    fi
done

echo ""
echo "Test 3: iptables Rules"
echo "------------------------------------"

# Check iptables rules for WireGuard
if command -v iptables >/dev/null 2>&1; then
    echo "Current iptables rules:"
    sudo iptables -L -n -v | grep -E "wg0|51820" || true
    echo ""

    # Check for FORWARD chain rules
    if sudo iptables -L FORWARD -n -v | grep -q "wg0"; then
        test_result "iptables FORWARD chain has wg0 rules" "pass"
    else
        test_result "iptables FORWARD chain has wg0 rules" "fail" "Missing FORWARD rules for wg0"
    fi

    # Check for NAT rules
    if sudo iptables -t nat -L -n | grep -q "wg0"; then
        test_result "iptables NAT table has wg0 rules" "pass"
    else
        test_result "iptables NAT table has wg0 rules" "fail" "Missing NAT rules for wg0"
    fi
else
    echo -e "${YELLOW}⚠️ WARNING${NC}: iptables command not found"
fi

echo ""
echo "Test 4: WireGuard Interface"
echo "------------------------------------"

# Check if WireGuard interface exists
if ip link show wg0 >/dev/null 2>&1; then
    INTERFACE_STATE=$(ip link show wg0 | grep -oP '(?<=state )\w+')
    if [ "$INTERFACE_STATE" = "up" ]; then
        test_result "WireGuard interface is UP" "pass" "Interface wg0 is active"
    else
        test_result "WireGuard interface is UP" "fail" "Interface state: $INTERFACE_STATE"
    fi
else
    test_result "WireGuard interface exists" "fail" "Interface wg0 not found"
fi

echo ""
echo "Test 5: WireGuard Configuration"
echo "------------------------------------"

# Validate WireGuard config
if [ -f /etc/wireguard/wg0.conf ]; then
    if command -v wg-quick >/dev/null 2>&1; then
        echo "Validating WireGuard config syntax..."
        if sudo wg-quick strip wg0 >/dev/null 2>&1; then
            test_result "WireGuard config syntax is valid" "pass" "Config file is valid"
        else
            VALIDATION_OUTPUT=$(sudo wg-quick strip wg0 2>&1)
            test_result "WireGuard config syntax is valid" "fail" "Config validation failed: $VALIDATION_OUTPUT"
        fi
    else
        echo -e "${YELLOW}⚠️ WARNING${NC}: wg-quick command not found"
    fi
else
    test_result "WireGuard config file exists" "fail" "Config file not found: /etc/wireguard/wg0.conf"
fi

echo ""
echo "Test 6: Port Availability"
echo "------------------------------------"

# Check if WireGuard port is listening
if command -v netstat >/dev/null 2>&1; then
    if sudo netstat -ulnp | grep -q ":51820"; then
        test_result "WireGuard port 51820 is listening" "pass" "Port is open and listening"
    else
        test_result "WireGuard port 51820 is listening" "fail" "Port 51820 not listening - check firewall"
    fi
else
    echo -e "${YELLOW}⚠️ WARNING${NC}: netstat command not found"
fi

# Alternative port check using ss
if command -v ss >/dev/null 2>&1; then
    if sudo ss -ulnp | grep -q ":51820"; then
        echo "  (Confirmed with ss command)"
    fi
fi

echo ""
echo "Test 7: WireGuard Peer Status"
echo "------------------------------------"

# Check WireGuard peer status
if command -v wg >/dev/null 2>&1; then
    PEER_INFO=$(sudo wg show wg0 2>/dev/null || echo "")

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

        # Check for peer endpoints
        PEER_COUNT=$(echo "$PEER_INFO" | grep -c "peer:")
        if [ "$PEER_COUNT" -gt 0 ]; then
            test_result "WireGuard has peers configured" "pass" "Found $PEER_COUNT peer(s)"
        else
            test_result "WireGuard has peers configured" "fail" "No peers found in config"
        fi
    else
        test_result "WireGuard peer status available" "fail" "Could not retrieve peer info"
    fi
else
    echo -e "${YELLOW}⚠️ WARNING${NC}: wg command not available"
fi

echo ""
echo "Test 8: Network Routing"
echo "------------------------------------"

# Check routing table
if ip route get | grep -q "wg0"; then
    WG_ROUTE=$(ip route get | grep "wg0")
    test_result "WireGuard route exists" "pass" "$WG_ROUTE"
else
    test_result "WireGuard route exists" "fail" "Route for wg0 not found in routing table"
fi

echo ""
echo "Test 9: Firewall Status"
echo "------------------------------------"

# Check for UFW
if command -v ufw >/dev/null 2>&1; then
    UFW_STATUS=$(sudo ufw status | grep "Status:" | cut -d: -f2)
    if [ "$UFW_STATUS" = "active" ]; then
        echo -e "${YELLOW}⚠️ WARNING${NC}: UFW is active - may conflict with manual iptables rules"
        echo "  Current status: $UFW_STATUS"
        echo "  Consider disabling: sudo ufw disable"
        echo "  Or add WireGuard to UFW: sudo ufw allow 51820/udp"
    fi
else
    echo "UFW not installed"
fi

echo ""
echo "Test 10: Systemd Journal (Recent Errors)"
echo "------------------------------------"

# Check recent WireGuard errors in journal
if command -v journalctl >/dev/null 2>&1; then
    RECENT_ERRORS=$(sudo journalctl -u wg-quick@wg0 --since "10 minutes ago" -p err -n 10 --no-pager || true)

    if [ -n "$RECENT_ERRORS" ]; then
        echo -e "${RED}Recent errors found in WireGuard logs:${NC}"
        echo "$RECENT_ERRORS"
        test_result "No recent errors in WireGuard logs" "fail" "Found errors in last 10 minutes"
    else
        test_result "No recent errors in WireGuard logs" "pass" "Clean logs in last 10 minutes"
    fi
else
    echo -e "${YELLOW}⚠️ WARNING${NC}: journalctl command not found"
fi

echo ""
echo "================================"
echo "Diagnostic Summary"
echo "================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo ""

# Exit with error if any tests failed
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}❌ Some diagnostics failed${NC}"
    echo ""
    echo "Recommended next steps:"
    echo "1. Review failed tests above"
    echo "2. Check systemd journal: sudo journalctl -u wg-quick@wg0 -n 50"
    echo "3. Restart WireGuard: sudo systemctl restart wg-quick@wg0"
    echo "4. Check server logs: sudo journalctl -u wg-quick@wg0 -f"
    exit 1
else
    echo -e "${GREEN}✅ All diagnostics passed!${NC}"
    exit 0
fi
