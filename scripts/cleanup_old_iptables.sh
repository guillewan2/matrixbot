#!/bin/bash
# Script para limpiar las reglas antiguas de iptables (por puerto específico)
# y preparar para las nuevas reglas (bloqueo completo)

echo "🧹 Limpiando reglas antiguas de iptables..."

# Obtener todas las IPs bloqueadas en reglas por puerto
IPS=$(sudo iptables -L INPUT -n -v --line-numbers | grep 'DROP.*tcp dpt:' | awk '{print $9}' | sort -u)

echo "IPs encontradas en reglas antiguas:"
echo "$IPS"

# Eliminar todas las reglas DROP con puertos específicos
echo ""
echo "Eliminando reglas antiguas..."

# Contar reglas a eliminar
COUNT=$(sudo iptables -L INPUT -n --line-numbers | grep 'DROP.*tcp dpt:' | wc -l)
echo "Total de reglas a eliminar: $COUNT"

# Eliminar reglas (de mayor a menor número para no desajustar los índices)
while sudo iptables -L INPUT -n --line-numbers | grep -q 'DROP.*tcp dpt:'; do
    LINE=$(sudo iptables -L INPUT -n --line-numbers | grep 'DROP.*tcp dpt:' | head -1 | awk '{print $1}')
    echo "Eliminando regla $LINE..."
    sudo iptables -D INPUT $LINE
done

echo ""
echo "✅ Limpieza completada"
echo ""
echo "IPs que estaban bloqueadas (ahora desbloqueadas):"
echo "$IPS"
echo ""
echo "Estas IPs se re-bloquearán automáticamente con las nuevas reglas"
echo "al reiniciar el servicio ip_sync_monitor"
