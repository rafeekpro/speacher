#!/bin/bash
#
# Dodaje GitHub Actions Runner jako peera WireGuard na serwerze
# Usage: ./add-github-actions-peer.sh <publiczny_klucz>
#

set -e

echo "🔧 Dodawaj GitHub Actions jako peera WireGuard..."
echo ""

# Sprawdź argumenty
if [ -z "$1" ]; then
    echo "❌ Błąd: Brak klucza publicznego"
    echo "   Użycie: $0 <klucz_publiczny>"
    echo ""
    echo "Przykład:"
    echo "   ./add-github-actions-peer.sh yNz/...lUx8z9pIw...=="
    exit 1
fi

PUBLIC_KEY="$1"

# Sprawdź czy zmienna środowiskowa jest ustawiona
if [ -z "$WG_PRIVATE_KEY" ]; then
    echo "⚠️  Ostrzeżenie: Zmienna WG_PRIVATE_KEY nie jest ustawiona"
    echo "   Ustaw wartość:"
    echo "   export WG_PRIVATE_KEY='twój_klucz_prywatny'"
    echo ""
    echo "Lub ustawj wartość przez GitHub Secrets:"
    echo "   Settings → Secrets → Actions → New repository secret"
    echo "   Nazwa: WG_PRIVATE_KEY"
    echo "   Wartość: <twój_klucz_prywatny>"
    exit 1
fi

# Wyświetl klucz publiczny do weryfikacji
echo "Klucz publiczny do weryfikacji:"
echo "$PUBLIC_KEY"
echo ""

# Zapytaj czy kontynuować
if [ -t 0 ]; then
    echo ""
    read -p "Kontynuować? (t/n): "
    case $REPLY in
        t|T)
            CONTINUE="yes"
            ;;
        n|N)
            CONTINUE=""
            ;;
        *)
            echo "❌ Błąd: Nieprawidłowa odpowiedź"
            exit 1
            ;;
    esac
fi

if [ "$CONTINUE" = "yes" ]; then
    echo "✅ Przerwano. Nie dodano peera."
    exit 0
fi

echo ""
echo "❌ Anulowano. Nie dodano peera."
exit 1
