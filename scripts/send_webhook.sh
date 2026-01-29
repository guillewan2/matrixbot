#!/bin/bash
# Script interactivo para enviar webhooks a un usuario de Matrix usando el endpoint compatible

MATRIX_USER="$1"
if [ -z "$MATRIX_USER" ]; then
    read -p "Introduce el usuario Matrix destino (@usuario:matrix.nasfurui.cat): " MATRIX_USER
fi

WEBHOOK_URL="http://100.124.77.20:23983/api/webhooks/${MATRIX_USER}/token"

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
