#!/bin/bash
# Script de verificación y testing para los 3 cambios de seguridad

echo "🧪 Testing de Seguridad E2EE y Webhooks"
echo "======================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir resultado
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $1"
    else
        echo -e "${RED}❌ FAIL${NC}: $1"
    fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 TEST 1: Verificar que MATRIX_RECOVERY_KEY existe"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if grep -q "MATRIX_RECOVERY_KEY" /admin/matrixbot/.env; then
    echo -e "${GREEN}✅ MATRIX_RECOVERY_KEY${NC} encontrado en .env"
    echo "   Valor: $(grep 'MATRIX_RECOVERY_KEY' /admin/matrixbot/.env | cut -d'=' -f2)"
else
    echo -e "${RED}❌ MATRIX_RECOVERY_KEY${NC} NO encontrado en .env"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 TEST 2: Verificar sintaxis Python"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 -m py_compile /admin/matrixbot/bot.py 2>/dev/null
check_result "bot.py"

python3 -m py_compile /admin/matrixbot/security_logger.py 2>/dev/null
check_result "security_logger.py"

python3 -m py_compile /admin/matrixbot/webhook_server.py 2>/dev/null
check_result "webhook_server.py"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 TEST 3: Verificar archivos existen"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for file in bot.py security_logger.py webhook_server.py realdebrid_handler.py download_monitor.py command_handler.py users.json .env; do
    if [ -f "/admin/matrixbot/$file" ]; then
        echo -e "${GREEN}✅${NC} $file existe"
    else
        echo -e "${RED}❌${NC} $file NO existe"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✔️ TEST 4: Verificar JSON válido"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 -m json.tool /admin/matrixbot/users.json > /dev/null 2>&1
check_result "users.json es JSON válido"

python3 -m json.tool /admin/matrixbot/commands.json > /dev/null 2>&1
check_result "commands.json es JSON válido"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 TEST 5: Verificar imports en bot.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if grep -q "from security_logger import SecurityLogger" /admin/matrixbot/bot.py; then
    echo -e "${GREEN}✅${NC} SecurityLogger importado"
else
    echo -e "${RED}❌${NC} SecurityLogger NO importado"
fi

if grep -q "from webhook_server import WebhookServer" /admin/matrixbot/bot.py; then
    echo -e "${GREEN}✅${NC} WebhookServer importado"
else
    echo -e "${RED}❌${NC} WebhookServer NO importado"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 TEST 6: Estado del servicio"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if systemctl is-active --quiet matrixbot; then
    echo -e "${GREEN}✅${NC} matrixbot service está ACTIVO"
    
    # Mostrar últimos logs
    echo ""
    echo "Últimos 5 logs del servicio:"
    journalctl -u matrixbot -n 5 --no-pager | tail -5 | sed 's/^/  /'
else
    echo -e "${YELLOW}⚠️${NC} matrixbot service está INACTIVO"
    echo "   Para iniciar: sudo systemctl start matrixbot"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESUMEN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Todos los tests completados"
echo ""
echo "Próximos pasos:"
echo "1. Reiniciar el bot:"
echo "   $ sudo systemctl restart matrixbot"
echo ""
echo "2. Ver logs:"
echo "   $ journalctl -u matrixbot -f"
echo ""
echo "3. Testear webhooks:"
echo "   $ bash /admin/matrixbot/test_webhook.sh"
echo ""

