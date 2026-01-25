#!/bin/bash

# Script de inicio rápido para el bot de Matrix

echo "🤖 Iniciando Bot de Matrix..."

# Verificar que estamos en el directorio correcto
if [ ! -f "src/matrixbot/main.py" ]; then
    echo "❌ Error: Ejecuta este script desde /admin/matrixbot"
    exit 1
fi

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "📦 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "⚠️  No se encontró entorno virtual. Ejecutando con Python del sistema..."
fi

# Iniciar bot
python -m src.matrixbot.main

# Verificar configuración
if [ -f "check_config.py" ]; then
    echo "🔍 Verificando configuración..."
    python check_config.py
    
    read -p "¿Continuar con la ejecución? (s/n): " continuar
    if [ "$continuar" != "s" ] && [ "$continuar" != "S" ]; then
        echo "Ejecución cancelada"
        exit 0
    fi
fi

echo ""
echo "▶️  Ejecutando bot..."
echo "   Presiona Ctrl+C para detener"
echo ""

# Ejecutar el bot
python bot.py
