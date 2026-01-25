#!/bin/bash
# Script para instalar y configurar el servicio systemd del bot de Matrix

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Instalador de Servicio Systemd - Matrix Bot             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que el script se ejecuta como root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}⚠️  Este script debe ejecutarse SIN sudo${NC}"
    echo -e "${YELLOW}   El script pedirá permisos cuando sea necesario${NC}"
    exit 1
fi

# Verificar que existe el archivo de servicio
if [ ! -f "matrixbot.service" ]; then
    echo -e "${RED}❌ Error: No se encuentra matrixbot.service${NC}"
    exit 1
fi

# Verificar que existe el bot
if [ ! -f "bot.py" ]; then
    echo -e "${RED}❌ Error: No se encuentra bot.py${NC}"
    exit 1
fi

# Verificar que existe el venv
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Error: No se encuentra el entorno virtual (venv)${NC}"
    echo -e "${YELLOW}   Ejecuta: ./setup.sh${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Pasos a realizar:${NC}"
echo "  1. Copiar matrixbot.service a /etc/systemd/system/"
echo "  2. Recargar configuración de systemd"
echo "  3. Habilitar el servicio para inicio automático"
echo "  4. Iniciar el servicio"
echo ""

read -p "¿Continuar? (s/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo -e "${YELLOW}❌ Instalación cancelada${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}📦 Paso 1: Copiando archivo de servicio...${NC}"
sudo cp matrixbot.service /etc/systemd/system/
echo -e "${GREEN}✅ Archivo copiado${NC}"

echo ""
echo -e "${BLUE}🔄 Paso 2: Recargando systemd...${NC}"
sudo systemctl daemon-reload
echo -e "${GREEN}✅ Systemd recargado${NC}"

echo ""
echo -e "${BLUE}⚙️  Paso 3: Habilitando servicio...${NC}"
sudo systemctl enable matrixbot.service
echo -e "${GREEN}✅ Servicio habilitado (se iniciará automáticamente al arrancar)${NC}"

echo ""
echo -e "${BLUE}▶️  Paso 4: Iniciando servicio...${NC}"
sudo systemctl start matrixbot.service
echo -e "${GREEN}✅ Servicio iniciado${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ INSTALACIÓN COMPLETADA                          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Estado del servicio:${NC}"
sudo systemctl status matrixbot.service --no-pager -l
echo ""
echo -e "${BLUE}📝 Comandos útiles:${NC}"
echo ""
echo -e "  ${GREEN}Ver estado:${NC}"
echo "    sudo systemctl status matrixbot"
echo ""
echo -e "  ${GREEN}Ver logs en tiempo real:${NC}"
echo "    sudo journalctl -u matrixbot -f"
echo ""
echo -e "  ${GREEN}Ver logs completos:${NC}"
echo "    sudo journalctl -u matrixbot"
echo ""
echo -e "  ${GREEN}Reiniciar servicio:${NC}"
echo "    sudo systemctl restart matrixbot"
echo ""
echo -e "  ${GREEN}Detener servicio:${NC}"
echo "    sudo systemctl stop matrixbot"
echo ""
echo -e "  ${GREEN}Deshabilitar inicio automático:${NC}"
echo "    sudo systemctl disable matrixbot"
echo ""
echo -e "  ${GREEN}Ver logs de las últimas 50 líneas:${NC}"
echo "    sudo journalctl -u matrixbot -n 50"
echo ""
