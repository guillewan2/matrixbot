#!/bin/bash

# Script de ejemplo para comandos personalizados del bot
# Este script muestra información del sistema

echo "=== Información del Sistema ==="
echo ""
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p)"
echo "Usuarios conectados: $(who | wc -l)"
echo "Carga del sistema: $(uptime | awk -F'load average:' '{print $2}')"
echo ""
echo "=== Uso de Disco ==="
df -h / | tail -n 1 | awk '{print "Usado: " $3 " de " $2 " (" $5 ")"}'
echo ""
echo "=== Uso de Memoria ==="
free -h | grep Mem | awk '{print "Usado: " $3 " de " $2}'
