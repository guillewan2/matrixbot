#!/bin/bash
# Script para desinstalar el servicio systemd del bot de Matrix

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Desinstalador de Servicio Systemd - Matrix Bot           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que el script se ejecuta como usuario normal
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}⚠️  Este script debe ejecutarse SIN sudo${NC}"
    echo -e "${YELLOW}   El script pedirá permisos cuando sea necesario${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Pasos a realizar:${NC}"
echo "  1. Detener el servicio"
echo "  2. Deshabilitar el servicio"
echo "  3. Eliminar archivo de servicio"
echo "  4. Recargar systemd"
echo ""

read -p "¿Continuar? (s/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo -e "${YELLOW}❌ Desinstalación cancelada${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}⏹️  Paso 1: Deteniendo servicio...${NC}"
if sudo systemctl is-active --quiet matrixbot.service; then
    sudo systemctl stop matrixbot.service
    echo -e "${GREEN}✅ Servicio detenido${NC}"
else
    echo -e "${YELLOW}⚠️  El servicio no estaba corriendo${NC}"
fi

echo ""
echo -e "${BLUE}🚫 Paso 2: Deshabilitando servicio...${NC}"
if sudo systemctl is-enabled --quiet matrixbot.service 2>/dev/null; then
    sudo systemctl disable matrixbot.service
    echo -e "${GREEN}✅ Servicio deshabilitado${NC}"
else
    echo -e "${YELLOW}⚠️  El servicio no estaba habilitado${NC}"
fi

echo ""
echo -e "${BLUE}🗑️  Paso 3: Eliminando archivo de servicio...${NC}"
if [ -f "/etc/systemd/system/matrixbot.service" ]; then
    sudo rm /etc/systemd/system/matrixbot.service
    echo -e "${GREEN}✅ Archivo eliminado${NC}"
else
    echo -e "${YELLOW}⚠️  El archivo de servicio no existía${NC}"
fi

echo ""
echo -e "${BLUE}🔄 Paso 4: Recargando systemd...${NC}"
sudo systemctl daemon-reload
sudo systemctl reset-failed
echo -e "${GREEN}✅ Systemd recargado${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ DESINSTALACIÓN COMPLETADA                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}ℹ️  El bot ya no se ejecutará como servicio${NC}"
echo -e "${BLUE}   Puedes ejecutarlo manualmente con: ./start.sh${NC}"
echo ""
