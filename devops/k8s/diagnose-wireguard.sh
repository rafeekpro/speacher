#!/bin/bash
#
# WireGuard Diagnostic Script
# Checks all possible issues with WireGuard tunnel
#

set -e

echo "🔍 WireGuard Diagnostics"
echo "===================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Diagnostic results
ISSUES_FOUND=0

echo "📋 Environment Check"
echo "--------------------"

# Check 1: Environment Variables
if [ -z "$WG_PRIVATE_KEY" ]; then
    echo -e "${RED}❌ WG_PRIVATE_KEY not set${NC}"
    echo "   Required: Wyeksportuj WG_PRIVATE_KEY w GitHub Secrets"
    echo "   Lub ustaw lokalnie:"
    echo "   export WG_PRIVATE_KEY='twoja_klucz_prywatny'"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✅ WG_PRIVATE_KEY is set${NC}"
fi

# Check 2: wg command availability
echo ""
echo "📋 WireGuard Tool Check"
echo "--------------------"

if command -v wg >/dev/null 2>&1; then
    echo -e "${GREEN}✅ wg command available${NC}"
    WG_VERSION=$(wg --version 2>/dev/null || echo "unknown")
    echo "   Version: $WG_VERSION"
else
    echo -e "${RED}❌ wg command not available${NC}"
    echo "   Install: sudo apt-get install wireguard"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check 3: WireGuard kernel module
echo ""
echo "📋 Kernel Module Check"
echo "--------------------"

if lsmod | grep -q wireguard; then
    echo -e "${GREEN}✅ WireGuard kernel module loaded${NC}"
else
    echo -e "${YELLOW}⚠️  WireGuard kernel module not loaded${NC}"
    echo "   Load: sudo modprobe wireguard"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check 4: WireGuard interface
echo ""
echo "📋 Interface Check"
echo "--------------------"

if ip link show wg0 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Interface wg0 exists${NC}"
    ip link show wg0
else
    echo -e "${RED}❌ Interface wg0 not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check 5: WireGuard config file
echo ""
echo "📋 Configuration Check"
echo "--------------------"

if [ -f /etc/wireguard/wg0.conf ]; then
    echo -e "${GREEN}✅ Config file exists${NC}"
    echo "   Content:"
    cat /etc/wireguard/wg0.conf
else
    echo -e "${RED}❌ Config file not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check 6: WireGuard service status
echo ""
echo "📋 Service Status"
echo "--------------------"

if systemctl is-active wg-quick@wg0 >/dev/null 2>&1; then
    SERVICE_STATUS=$(systemctl is-active wg-quick@wg0)
    if [ "$SERVICE_STATUS" = "active" ]; then
        echo -e "${GREEN}✅ WireGuard service is active${NC}"
    else
        echo -e "${YELLOW}⚠️  WireGuard service: $SERVICE_STATUS${NC}"
    fi
else
    echo -e "${RED}❌ WireGuard service not running${NC}"
    echo "   Start: sudo systemctl start wg-quick@wg0"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check 7: Recent WireGuard errors
echo ""
echo "📋 Recent Errors (last 10 minutes)"
echo "--------------------"

ERROR_COUNT=$(sudo journalctl -u wg-quick@wg0 --since "10 minutes ago" -p err -n 0 | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $ERROR_COUNT errors${NC}"
    sudo journalctl -u wg-quick@wg0 --since "10 minutes ago" -p err -n 0
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✅ No recent errors${NC}"
fi

# Check 8: Network connectivity
echo ""
echo "📋 Network Check"
echo "--------------------"

if ping -c 1 -W 2 10.204.201.1 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Server 10.204.201.1 reachable${NC}"
else
    echo -e "${RED}❌ Server 10.204.201.1 unreachable${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Summary
echo ""
echo "===================="
echo "📊 Diagnostic Summary"
echo "===================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo "Następne kroki:"
    echo "1. Sprawdź uprawnienia: chmod +x skrypty"
    echo "2. Ustaw WG_PRIVATE_KEY w GitHub Secrets"
    echo "3. Uruchom: bash devops/k8s/diagnose-wireguard.sh"
else
    echo -e "${RED}❌ Znaleziono $ISSUES_FOUND problemów${NC}"
fi
echo ""
echo "===================="

# Exit with error if problems found
if [ $ISSUES_FOUND -gt 0 ]; then
    exit 1
else
    exit 0
fi
