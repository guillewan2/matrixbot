#!/bin/bash
# Script para probar el webhook server
# Uso: ./test_webhook.sh <ip_o_host_bot>

BOT_HOST="${1:-localhost}"
BOT_PORT=23983

echo "🧪 Probando Webhook Server en http://${BOT_HOST}:${BOT_PORT}"
echo ""

# 1. Health check
echo "1️⃣  Health Check..."
curl -s -X GET "http://${BOT_HOST}:${BOT_PORT}/webhook/health" | jq '.' || echo "❌ Conexión fallida"
echo ""

# 2. Enviar mensaje
echo "2️⃣  Enviando mensaje..."
curl -s -X POST "http://${BOT_HOST}:${BOT_PORT}/webhook/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "🧪 Mensaje de prueba desde el script de test"
  }' | jq '.' || echo "❌ Falló"
echo ""

# 3. Enviar log
echo "3️⃣  Enviando log..."
curl -s -X POST "http://${BOT_HOST}:${BOT_PORT}/webhook/log" \
  -H "Content-Type: application/json" \
  -d '{
    "level": "INFO",
    "message": "Este es un log de prueba desde el script",
    "source": "test_webhook.sh"
  }' | jq '.' || echo "❌ Falló"
echo ""

# 4. Enviar notificación LOW
echo "4️⃣  Enviando notificación LOW..."
curl -s -X POST "http://${BOT_HOST}:${BOT_PORT}/webhook/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Prueba LOW",
    "message": "Notificación de baja prioridad",
    "priority": "low"
  }' | jq '.' || echo "❌ Falló"
echo ""

# 5. Enviar notificación MEDIUM
echo "5️⃣  Enviando notificación MEDIUM..."
curl -s -X POST "http://${BOT_HOST}:${BOT_PORT}/webhook/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Prueba MEDIUM",
    "message": "Notificación de media prioridad",
    "priority": "medium"
  }' | jq '.' || echo "❌ Falló"
echo ""

# 6. Enviar notificación HIGH
echo "6️⃣  Enviando notificación HIGH..."
curl -s -X POST "http://${BOT_HOST}:${BOT_PORT}/webhook/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Prueba HIGH",
    "message": "Notificación de alta prioridad",
    "priority": "high"
  }' | jq '.' || echo "❌ Falló"
echo ""

# 7. Enviar log ERROR
echo "7️⃣  Enviando log ERROR..."
curl -s -X POST "http://${BOT_HOST}:${BOT_PORT}/webhook/log" \
  -H "Content-Type: application/json" \
  -d '{
    "level": "ERROR",
    "message": "Este es un log de ERROR de prueba",
    "source": "test_webhook.sh"
  }' | jq '.' || echo "❌ Falló"
echo ""

echo "✅ Pruebas completadas. Revisa los mensajes en la room de Matrix:"
echo "   !pDyuEmkITrMcncMFMy:nasfurui.es"
