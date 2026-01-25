#!/bin/bash
# Script de instalación del monitor de NPM

set -e

echo "🚀 Instalando NPM Monitor Service..."

# Copiar el archivo de servicio
echo "📋 Copiando archivo de servicio..."
sudo cp /admin/matrixbot/npm_monitor.service /etc/systemd/system/

# Hacer ejecutable el script de Python
echo "🔧 Configurando permisos..."
chmod +x /admin/matrixbot/npm_monitor.py

# Recargar systemd
echo "🔄 Recargando systemd..."
sudo systemctl daemon-reload

# Habilitar el servicio
echo "✅ Habilitando servicio..."
sudo systemctl enable npm_monitor.service

# Iniciar el servicio
echo "▶️ Iniciando servicio..."
sudo systemctl start npm_monitor.service

# Mostrar estado
echo ""
echo "📊 Estado del servicio:"
sudo systemctl status npm_monitor.service --no-pager

echo ""
echo "✅ Instalación completada!"
echo ""
echo "Comandos útiles:"
echo "  Ver logs:     sudo journalctl -u npm_monitor -f"
echo "  Ver estado:   sudo systemctl status npm_monitor"
echo "  Reiniciar:    sudo systemctl restart npm_monitor"
echo "  Detener:      sudo systemctl stop npm_monitor"
echo "  Deshabilitar: sudo systemctl disable npm_monitor"
