#!/bin/bash

# Script de configuración inicial para el bot de Matrix

echo "🤖 Configuración inicial del Bot de Matrix"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "bot.py" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio /admin/matrixbot"
    exit 1
fi

# Crear archivos de configuración si no existen
echo "📝 Verificando archivos de configuración..."

if [ ! -f ".env" ]; then
    echo "Creando .env desde .env.example..."
    cp .env.example .env
    echo "✅ Archivo .env creado. ¡EDITA este archivo con tus credenciales!"
else
    echo "✅ .env ya existe"
fi

if [ ! -f "users.json" ]; then
    echo "Creando users.json desde users.json.example..."
    cp users.json.example users.json
    echo "✅ Archivo users.json creado. ¡EDITA este archivo para configurar usuarios!"
else
    echo "✅ users.json ya existe"
fi

if [ ! -f "commands.json" ]; then
    echo "Creando commands.json desde commands.json.example..."
    cp commands.json.example commands.json
    echo "✅ Archivo commands.json creado"
else
    echo "✅ commands.json ya existe"
fi

# Crear directorio store si no existe
if [ ! -d "store" ]; then
    mkdir -p store
    echo "✅ Directorio store creado para claves de cifrado"
fi

echo ""
echo "📦 Verificando entorno virtual..."

# Verificar si existe un entorno virtual
if [ ! -d "venv" ]; then
    echo "⚠️  No se encontró entorno virtual"
    read -p "¿Quieres crear un entorno virtual ahora? (s/n): " crear_venv
    
    if [ "$crear_venv" = "s" ] || [ "$crear_venv" = "S" ]; then
        echo "Creando entorno virtual..."
        python3 -m venv venv
        echo "✅ Entorno virtual creado"
        
        echo "Activando entorno virtual..."
        source venv/bin/activate
        
        echo "Instalando dependencias..."
        pip install -r requirements.txt
        echo "✅ Dependencias instaladas"
    else
        echo "⚠️  Recuerda crear un entorno virtual e instalar las dependencias:"
        echo "   python3 -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
    fi
else
    echo "✅ Entorno virtual encontrado"
fi

echo ""
echo "=========================================="
echo "✅ Configuración inicial completada!"
echo ""
echo "📋 Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales de Matrix"
echo "2. Edita users.json para configurar usuarios y API keys de Gemini"
echo "3. (Opcional) Edita commands.json para personalizar comandos"
echo "4. Activa el entorno virtual: source venv/bin/activate"
echo "5. Ejecuta el bot: python bot.py"
echo ""
echo "📖 Lee README.md para más información"
echo ""
