# 📚 Documentación General - MatrixBot

> Bot de Matrix con soporte E2EE, comandos personalizables, integración con IA (Gemini).

---

## 📑 Índice

1. [Introducción](#introducción)
2. [Instalación](#instalación)
3. [Configuración](#configuración)
4. [Uso del Bot](#uso-del-bot)
5. [Sistema de Comandos](#sistema-de-comandos)
6. [Integración con IA (Gemini)](#integración-con-ia-gemini)
7. [RealDebrid y Descargas](#realdebrid-y-descargas)
8. [Servidor Webhook](#servidor-webhook)
9. [Seguridad y E2EE](#seguridad-y-e2ee)
10. [Ejecución como Servicio](#ejecución-como-servicio)
11. [Dockerización](#dockerización)
12. [Troubleshooting](#troubleshooting)
13. [FAQ](#faq)

---

## Introducción

MatrixBot es un bot completo para Matrix que incluye:

- ✅ **Cifrado E2EE**: Comunicaciones seguras end-to-end
- 🤖 **IA con Gemini**: Cada usuario puede tener su propia configuración
- ⚙️ **Comandos personalizables**: Sistema basado en JSON
-  **Auto-recarga**: Los archivos JSON se recargan sin reiniciar
- 🚪 **Auto-join**: Acepta invitaciones automáticamente
- 📥 **RealDebrid**: Integración para descargas de torrents
- 📡 **Webhooks**: Servidor para recibir notificaciones externas

---

## Instalación

### Requisitos

- Python 3.8+
- libolm-dev (para E2EE)
- Cuenta de Matrix
- API key de Gemini (opcional)

### Pasos

```bash
# 1. Clonar/acceder al proyecto
cd /admin/matrixbot

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
nano .env

# 5. Configurar usuarios
cp config/users.json.example config/users.json
nano config/users.json

# 6. Configurar comandos
cp config/commands.json.example config/commands.json
nano config/commands.json

# 7. Ejecutar
python -m src.matrixbot.main
```

---

## Configuración

### Archivo `.env`

```env
# Credenciales de Matrix
MATRIX_HOMESERVER=https://matrix.example.com
MATRIX_USER_ID=@bot:matrix.example.com
MATRIX_PASSWORD=tu_contraseña

# Directorio de claves E2EE
STORE_PATH=./store

# Recovery Key para verificación E2EE
MATRIX_RECOVERY_KEY=XXXX XXXX XXXX XXXX...
```

### Archivo `config/users.json`

```json
{
    "users": {
        "@usuario:matrix.example.com": {
            "ai_enabled": true,
            "realdebrid_api_key": "tu_api_key",
            "triggers": {
                "subaru": {
                    "api_key": "AIzaSy...",
                    "model": "gemini-2.5-flash",
                    "system_prompt": "Eres un asistente útil.",
                    "max_history": 10
                }
            }
        }
    }
}
```

### Archivo `config/commands.json`

```json
{
    "commands": {
        "!help": {
            "description": "Mostrar comandos disponibles",
            "allowed_users": [],
            "script": null,
            "type": "builtin"
        },
        "!uptime": {
            "description": "Ver uptime del sistema",
            "allowed_users": ["@admin:matrix.example.com"],
            "script": "uptime",
            "type": "shell"
        }
    }
}
```

---

## Uso del Bot

### Invitaciones

El bot acepta automáticamente todas las invitaciones a salas y envía un mensaje de bienvenida.

### Comandos Integrados

| Comando | Descripción |
|---------|-------------|
| `!help` | Muestra comandos disponibles |
| `!ping` | Verifica que el bot responde |
| `!espacio` | Muestra espacio en disco |
| `!reload` | Recarga configuración |

### Interacción con IA

La IA responde cuando mencionas el trigger configurado (por defecto "subaru"):

```
Usuario: Hola subaru, ¿cómo estás?
Bot: [Respuesta de IA]

Usuario: ¿Cuál es la capital de España?
Bot: [No responde - no se mencionó "subaru"]
```

---

## Sistema de Comandos

### Tipos de Comandos

1. **builtin**: Comandos integrados en el bot
2. **shell**: Ejecutan scripts del sistema

### Permisos

- `"allowed_users": []` → Todos pueden usar el comando
- `"allowed_users": ["@admin:matrix.org"]` → Solo usuarios listados

### Ejemplos

```json
{
    "!docker-ps": {
        "description": "Listar contenedores",
        "allowed_users": ["@admin:matrix.org"],
        "script": "docker ps",
        "type": "shell"
    },
    "!weather": {
        "description": "Ver el clima",
        "allowed_users": [],
        "script": "curl -s wttr.in/Madrid?format=3",
        "type": "shell"
    }
}
```

---

## Integración con IA (Gemini)

### Obtener API Key

1. Ve a [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Crea una API key
3. Añádela a `users.json`

### Modelos Disponibles

- `gemini-2.5-flash` - Rápido y eficiente
- `gemini-2.5-pro` - Más potente
- `gemini-2.0-flash-exp` - Experimental

### Configuración por Usuario

Cada usuario puede tener:
- Su propia API key
- Modelo preferido
- System prompt personalizado
- Historial de conversación

---

## RealDebrid y Descargas

### Comandos

| Comando | Descripción |
|---------|-------------|
| `magnet-config API_KEY` | Configura tu API key |
| `magnet magnet:?xt=...` | Agrega un magnet link |
| `magnet-list` | Lista tus torrents |
| `magnet-info ID` | Info de un torrent |

### Flujo

1. Configuras tu API key una vez
2. Envías un magnet link
3. El bot lo agrega a RealDebrid
4. Monitorea el progreso automáticamente
5. Te notifica con los links de descarga

---

## Servidor Webhook

El bot expone un servidor en el puerto **23983** para recibir notificaciones externas y webhooks.

### Endpoints clásicos

```bash
# Health check
GET /webhook/health

# Enviar mensaje
POST /webhook/message
{"message": "Texto", "room_id": "!xxx:matrix.org"}

# Enviar log
POST /webhook/log
{"level": "INFO", "message": "Log", "source": "app"}

# Enviar notificación
POST /webhook/notify
{"title": "Título", "message": "Texto", "priority": "high"}
```

### Endpoint compatible con Discord y envío directo a usuarios

Puedes usar el endpoint:

```
POST /api/webhooks/{id}/{token}
```

- Si `{id}` o `{token}` es un usuario Matrix (ej: `@usuario:nasfurui.es`), el mensaje se enviará como DM a ese usuario.
- Si no, se enviará al room por defecto.
- El formato del body es igual al de Discord:

```json
{
  "content": "Mensaje a enviar",
  "username": "Opcional",
  "embeds": [ ... ]
}
```

**Ejemplo de uso para enviar a un usuario:**

```bash
curl -X POST \
  "http://localhost:23983/api/webhooks/@guille:nasfurui.es/token" \
  -H "Content-Type: application/json" \
  -d '{"content": "¡Hola desde webhook!"}'
```

Puedes usar también el usuario URL-encoded:

```bash
curl -X POST \
  "http://localhost:23983/api/webhooks/%40guille%3Anasfurui.es/token" \
  -H "Content-Type: application/json" \
  -d '{"content": "Mensaje privado"}'
```

### Script interactivo para enviar webhooks

Se incluye el script `scripts/send_webhook.sh` para enviar mensajes fácilmente a cualquier usuario Matrix:

```bash
./scripts/send_webhook.sh
```

- Te pedirá el usuario destino (ej: `@usuario:nasfurui.es`)
- Podrás escribir mensajes y se enviarán como DM vía webhook
- Deja el mensaje vacío para salir

---

## Seguridad y E2EE

### Cifrado End-to-End

- El bot usa E2EE automáticamente en salas cifradas
- La recovery key permite verificar mensajes
- Las claves se almacenan en `store/`

### Webhooks de Seguridad

El bot registra automáticamente:
- ✅ Logins exitosos
- ❌ Logins fallidos
- 📋 Comandos ejecutados
- 🚨 Intentos de acceso no autorizado

### Recomendaciones

- Permisos restrictivos: `chmod 600 .env`
- No compartir `users.json` ni `.env`
- Configurar firewall para puerto 23983:
  ```bash
  sudo ufw allow from 100.0.0.0/8 to any port 23983
  ```

---

## Ejecución como Servicio

### Instalación

```bash
./scripts/install_service.sh
```

### Comandos

```bash
# Estado
sudo systemctl status matrixbot

# Logs
sudo journalctl -u matrixbot -f

# Reiniciar
sudo systemctl restart matrixbot

# Detener
sudo systemctl stop matrixbot
```

### Características

- Inicio automático al arrancar
- Reinicio automático si falla
- Logs integrados con journalctl

---

## Dockerización

### Archivos

- `Dockerfile` - Imagen del bot
- `docker-compose.yml` - Orquestación
- `.dockerignore` - Exclusiones

### Ejecutar

```bash
# Construir e iniciar
docker compose up -d

# Ver logs
docker compose logs -f

# Reconstruir después de cambios
docker compose up -d --build
```

### Configuración

El `docker-compose.yml` usa `network_mode: "host"` para acceder a la red del host (necesario para Tailscale y webhooks).

Volúmenes montados:
- `./config` → Configuración
- `./store` → Claves E2EE
- `./logs` → Logs
- `./.env` → Variables de entorno

---

## Troubleshooting

### El bot no conecta

```bash
# Verificar credenciales en .env
cat .env

# Verificar conectividad
ping matrix.example.com

# Ver logs
sudo journalctl -u matrixbot -n 50
```

### La IA no responde

1. Verifica que el usuario tenga `ai_enabled: true`
2. Verifica que la API key sea válida
3. Asegúrate de mencionar el trigger (ej: "subaru")

### Comandos no funcionan

1. Verifica que el comando esté en `commands.json`
2. Verifica permisos del usuario
3. Para comandos shell, verifica que el script exista y sea ejecutable

### Error de cifrado

```bash
# Eliminar store y reiniciar (perderás historial cifrado)
rm -rf store/
sudo systemctl restart matrixbot
```

### Webhook no llega

```bash
# Verificar que el servidor está corriendo
curl http://localhost:23983/webhook/health

# Verificar firewall
sudo ufw status
```

---

## FAQ

### ¿Cómo obtengo una API key de Gemini?

Ve a [Google AI Studio](https://aistudio.google.com/app/apikey), inicia sesión y crea una API key.

### ¿Necesito servidor Matrix propio?

No, puedes usar matrix.org u otro servidor público.

### ¿Cómo invito al bot a una sala?

Simplemente invítalo usando su user ID. El bot acepta automáticamente.

### ¿Cada usuario necesita su propia API key de Gemini?

No es obligatorio, pero recomendado para control de uso y costos.

### ¿El bot recuerda conversaciones?

Sí, si configuras `max_history` en `users.json`.

### ¿Es seguro dar acceso a comandos shell?

⚠️ Solo da acceso a usuarios de total confianza. Un usuario malintencionado podría ejecutar comandos peligrosos.

### ¿Cómo actualizo el bot?

```bash
# Si usas systemd
sudo systemctl stop matrixbot
git pull  # o actualiza los archivos
sudo systemctl start matrixbot

# Si usas Docker
docker compose down
git pull
docker compose up -d --build
```

### ¿Dónde se almacenan las claves de cifrado?

En el directorio `store/`. **No lo borres** o perderás acceso a mensajes cifrados anteriores.

---

## Estructura del Proyecto

```
/admin/matrixbot/
├── src/matrixbot/          # Código fuente principal
│   ├── main.py             # Punto de entrada
│   ├── handlers/           # Manejadores (comandos, IA)
│   ├── services/           # Servicios (webhook, RealDebrid)
│   ├── monitors/           # Monitores (descargas, login)
│   └── audit/              # Sistema de auditoría
├── config/                 # Archivos de configuración
│   ├── users.json          # Configuración de usuarios
│   └── commands.json       # Comandos personalizados
├── store/                  # Claves de cifrado E2EE
├── logs/                   # Logs y reportes de auditoría
├── scripts/                # Scripts de utilidad
├── Dockerfile              # Imagen Docker
├── docker-compose.yml      # Orquestación Docker
├── requirements.txt        # Dependencias Python
└── .env                    # Variables de entorno
```

---

## Enlaces Útiles

- [Matrix Protocol](https://matrix.org/)
- [matrix-nio Documentation](https://matrix-nio.readthedocs.io/)
- [Google Gemini API](https://ai.google.dev/)
- [RealDebrid API](https://api.real-debrid.com/)

---

*Última actualización: Enero 2026*
