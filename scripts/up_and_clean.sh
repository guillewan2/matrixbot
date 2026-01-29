#!/bin/bash
# Script para levantar el stack con docker-compose y limpiar imágenes no usadas

set -e

echo "[+] Levantando servicios con build..."
docker compose up --build -d

echo "[+] Eliminando imágenes no utilizadas..."
docker image prune -af

echo "[✓] Listo."
