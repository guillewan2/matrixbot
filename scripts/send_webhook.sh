#!/bin/bash
# Script interactivo para enviar webhooks a un usuario de Matrix usando el endpoint compatible

MATRIX_USER="$1"
if [ -z "$MATRIX_USER" ]; then
    read -p "Introduce el usuario Matrix destino (@usuario:matrix.nasfurui.cat): " MATRIX_USER
fi

# URL encode the Matrix User to ensure special characters like @ and : are handled correctly
ENCODED_USER=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$MATRIX_USER'''))")

# Use local IP by default, but allow override or use logic to determine target
# Assuming localhost for script default, change to your VPS IP if running remotely
BASE_URL="http://localhost:23983"
# BASE_URL="http://100.124.77.20:23983" # Descomentar para usar IP de Tailscale

WEBHOOK_URL="$BASE_URL/api/webhooks/${ENCODED_USER}/token"

echo "Configurado para enviar a: $WEBHOOK_URL"

while true; do
    read -p "Mensaje a enviar (vacío para salir): " MSG
    if [ -z "$MSG" ]; then
        echo "Saliendo."
        break
    fi
    
    echo "Enviando a: $WEBHOOK_URL"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d '{"content": "'$MSG'"}')
    
    if [ "$HTTP_CODE" -eq 204 ] || [ "$HTTP_CODE" -eq 200 ]; then
        echo " [enviado - $HTTP_CODE]"
    else
        echo " [ERROR - $HTTP_CODE]"
    fi
done
