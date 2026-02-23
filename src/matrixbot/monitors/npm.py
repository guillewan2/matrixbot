#!/usr/bin/env python3
"""
Monitor de Nginx Proxy Manager
Verifica si nasfurui.es está disponible y reinicia el contenedor si es necesario
"""

import asyncio
import aiohttp
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging
log_dir = Path('/admin/matrixbot/logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'npm_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración
CHECK_URL = "https://nasfurui.es"
CONTAINER_NAME = "nginx_proxy_manager-app-1"
CHECK_INTERVAL = 300  # 5 minutos
RESTART_COOLDOWN = 3600  # 1 hora - tiempo mínimo entre reinicios
MAX_RETRIES = 3
TIMEOUT = 10  # segundos

# Estado
last_restart_time = 0
restart_count = 0

async def check_url(url: str) -> bool:
    """Verificar si la URL está disponible"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT), ssl=False) as response:
                if response.status < 500:  # Aceptar cualquier cosa menos error de servidor
                    logger.debug(f"✅ {url} respondió con código {response.status}")
                    return True
                else:
                    logger.warning(f"⚠️ {url} respondió con código {response.status}")
                    return False
    except asyncio.TimeoutError:
        logger.error(f"❌ Timeout al conectar con {url}")
        return False
    except aiohttp.ClientError as e:
        logger.error(f"❌ Error de conexión con {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado al verificar {url}: {e}")
        return False

def is_container_running(container_name: str) -> bool:
    """Verificar si el contenedor está corriendo"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return container_name in result.stdout
    except Exception as e:
        logger.error(f"Error verificando estado del contenedor: {e}")
        return False

def restart_container(container_name: str) -> bool:
    """Reiniciar el contenedor de Docker"""
    global last_restart_time, restart_count
    
    # Verificar cooldown
    current_time = datetime.now().timestamp()
    if current_time - last_restart_time < RESTART_COOLDOWN:
        time_remaining = int(RESTART_COOLDOWN - (current_time - last_restart_time))
        logger.warning(f"⏳ Cooldown activo. Esperando {time_remaining}s antes de poder reiniciar")
        return False
    
    try:
        logger.info(f"🔄 Reiniciando contenedor {container_name}...")
        result = subprocess.run(
            ['docker', 'restart', container_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            last_restart_time = current_time
            restart_count += 1
            logger.info(f"✅ Contenedor reiniciado exitosamente (reinicio #{restart_count})")
            return True
        else:
            logger.error(f"❌ Error al reiniciar contenedor: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout al reiniciar contenedor")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado al reiniciar contenedor: {e}")
        return False

async def monitor_loop():
    """Loop principal de monitoreo"""
    logger.info("🚀 Iniciando monitor de Nginx Proxy Manager")
    logger.info(f"📡 URL a monitorear: {CHECK_URL}")
    logger.info(f"🐳 Contenedor: {CONTAINER_NAME}")
    logger.info(f"⏱️ Intervalo de verificación: {CHECK_INTERVAL}s")
    logger.info(f"❄️ Cooldown entre reinicios: {RESTART_COOLDOWN}s")
    
    consecutive_failures = 0
    
    while True:
        try:
            # Verificar si la URL está disponible
            is_available = await check_url(CHECK_URL)
            
            if is_available:
                consecutive_failures = 0
                logger.debug(f"✅ Servicio disponible")
            else:
                consecutive_failures += 1
                logger.warning(f"⚠️ Servicio no disponible (fallo {consecutive_failures}/{MAX_RETRIES})")
                
                # Si hay múltiples fallos consecutivos, intentar reiniciar
                if consecutive_failures >= MAX_RETRIES:
                    logger.error(f"🚨 Servicio caído después de {MAX_RETRIES} intentos")
                    
                    # Verificar si el contenedor está corriendo
                    if not is_container_running(CONTAINER_NAME):
                        logger.error(f"❌ Contenedor {CONTAINER_NAME} no está corriendo")
                    
                    # Intentar reiniciar
                    if restart_container(CONTAINER_NAME):
                        logger.info("⏳ Esperando 60 segundos para que el servicio se inicie...")
                        await asyncio.sleep(60)
                        
                        # Verificar si se recuperó
                        is_recovered = await check_url(CHECK_URL)
                        if is_recovered:
                            logger.info("✅ Servicio recuperado después del reinicio")
                            consecutive_failures = 0
                        else:
                            logger.error("❌ Servicio sigue caído después del reinicio")
                    else:
                        logger.error("❌ No se pudo reiniciar el contenedor")
                    
            # Esperar antes del próximo check
            await asyncio.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("⚠️ Monitor detenido por el usuario")
            break
        except Exception as e:
            logger.error(f"❌ Error en el loop de monitoreo: {e}", exc_info=True)
            await asyncio.sleep(CHECK_INTERVAL)

async def main():
    """Punto de entrada principal"""
    try:
        await monitor_loop()
    except KeyboardInterrupt:
        logger.info("👋 Monitor finalizado")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
