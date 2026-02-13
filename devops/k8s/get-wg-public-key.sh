#!/bin/bash
#
# Wydobranie kluczza publicznego z klucza prywatnego
# Usage: ./get-wg-public-key.sh
#

echo "📋 Wydobywam klucz publiczny WireGuard..."
echo ""

# Sprawdź czy zmienna środowiskowa jest ustawiona
if [ -z "$WG_PRIVATE_KEY" ]; then
    echo "❌ Błąd: Zmienna WG_PRIVATE_KEY nie jest ustawiona"
    echo "   Ustaw wartość:"
    echo "   export WG_PRIVATE_KEY='twój_klucz_prywatny'"
    echo ""
    echo "Lub użyj GitHub Secrets:"
    echo "   echo \"${{ secrets.WG_PRIVATE_KEY }}\" | wg pubkey"
    exit 1
fi

# Wydobierz klucz publiczny
if [ -n "$1" ]; then
    KEY_FROM="$1"
else
    # Jeśli argument podany, użyj go
    if [ -n "$2" ]; then
        KEY_FROM="$2"
    else
        echo "❌ Błąd: Podaj klucz prywatny jako argument lub ustaw WG_PRIVATE_KEY"
        echo "   Użycie: ./get-wg-public-key.sh <klucz_prywatny>"
        echo "   Lub: export WG_PRIVATE_KEY='twój_klucz_prywatny'"
        exit 1
    fi
fi

# Wydobierz klucz publiczny z klucza lub argumentu
if [ "$KEY_FROM" = "$1" ]; then
    echo "$WG_PRIVATE_KEY" | wg pubkey
elif [ "$KEY_FROM" = "$2" ]; then
    echo "$2" | wg pubkey
else
    # Zmienna środowiskowa
    if [ -z "$WG_PRIVATE_KEY" ]; then
        echo "$WG_PRIVATE_KEY" | wg pubkey
    else
        echo "${{ secrets.WG_PRIVATE_KEY }}" | wg pubkey
    fi
fi
