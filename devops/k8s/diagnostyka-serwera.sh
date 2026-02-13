#!/bin/bash
#
# Skrypt diagnostyczny do uruchomienia na serwerze K8s
# Urucham przez: ssh root@10.204.201.1 'bash -s' 2>&1
#

echo "🔍 Diagnostyka WireGuard"
echo "================================"
echo ""

# Kolory
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Testy
echo "Test 1: Środowisko"
echo "------------------------------------"
uname -a
echo ""

echo "Test 2: WireGuard"
echo "------------------------------------"
if command -v wg >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Dostępne${NC}"
else
    echo -e "${RED}❌ Niedostępne${NC}"
fi
echo ""

echo "Test 3: Status usługi"
echo "------------------------------------"
systemctl is-active wg-quick@wg0 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Aktywny${NC}"
else
    echo -e "${YELLOW}⚠️  Nieaktywny (kod: $?)${NC}"
fi
echo ""

echo "Test 4: Interfejs"
echo "------------------------------------"
ip link show wg0 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ wg0 istnieje${NC}"
    ip link show wg0 2>/dev/null || true
else
    echo -e "${RED}❌ wg0 nie istnieje${NC}"
fi
echo ""

echo "Test 5: Adres IP"
echo "------------------------------------"
ip addr show wg0 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Adres przypisana${NC}"
else
    echo -e "${RED}❌ Brak adresu${NC}"
fi
echo ""

echo "Test 6: Routing"
echo "------------------------------------"
if ip route get | grep -q wg0 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Trasa wg0 istnieje${NC}"
    ip route get | grep wg0
else
    echo -e "${RED}❌ Brak trasy wg0${NC}"
fi
echo ""

echo "Test 7: Firewall"
echo "------------------------------------"
if iptables -L -n -v | grep -qE 'wg0|51820' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Reguły istnieją${NC}"
    iptables -L -n -v | grep -E 'wg0|51820'
else
    echo -e "${RED}❌ Brak reguł${NC}"
fi
echo ""

echo "Test 8: Ostatnie błędy"
echo "------------------------------------"
ERROR_COUNT=$(journalctl -u wg-quick@wg0 --since "10 minutes ago" -p err -n 0 2>/dev/null | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Znaleziono $ERROR_COUNT błędów${NC}"
else
    echo -e "${GREEN}✅ Brak błędów${NC}"
fi
echo ""
echo "================================"
