#!/usr/bin/env python3
"""
Script de prueba para generar eventos de Matrix de ejemplo
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import random

# Crear archivo de eventos de ejemplo
events_file = Path('./store/matrix_security_events.json')
events_file.parent.mkdir(exist_ok=True)

# Generar eventos de ejemplo con datos REALES del servidor
now = datetime.now()

auth_events = []
room_events = []
federation_events = []
device_events = []

# Usuarios REALES del servidor (basados en tu users.json y lo que has mencionado)
real_users = [
    '@pruebas:matrix.nasfurui.cat',  # Usuario de pruebas real
    '@admin:matrix.nasfurui.cat',     # Probablemente admin
]

# IPs REALES del servidor y red local
real_ips = [
    '192.168.1.1',      # Gateway local
    '192.168.1.100',    # IP local del servidor/cliente
    '10.0.0.50',        # Otra IP de red local
]

# IPs externas sospechosas REALES (ejemplos de IPs conocidas de ataques)
suspicious_ips = [
    '185.220.101.45',   # IP real de Tor exit node
    '89.248.165.189',   # IP real conocida por escaneos
]

# Dispositivos REALES (formato Matrix)
real_devices = [
    'ADKAKTBFXU',  # De tus archivos store
    'ASCQXGFDSK',
    'AUJZDPWWIF',
    'BQIZDOMWVC',
]

# Eventos de autenticación (últimas 24 horas)
# Logins exitosos de usuarios reales
for i in range(12):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    auth_events.append({
        'timestamp': timestamp,
        'type': 'login',
        'user_id': random.choice(real_users),
        'device_id': random.choice(real_devices),
        'success': True,
        'ip_address': random.choice(real_ips),
        'reason': None
    })

# Logins fallidos de IPs sospechosas (intentos de ataque reales)
suspicious_users_attempts = [
    '@admin:matrix.nasfurui.cat',  # Intentan adivinar credenciales de admin
    '@root:matrix.nasfurui.cat',   # Usuario común en ataques
    '@test:matrix.nasfurui.cat',   # Otro usuario común
]

for i in range(12):
    timestamp = (now - timedelta(hours=random.randint(0, 24), minutes=random.randint(0, 60))).isoformat()
    auth_events.append({
        'timestamp': timestamp,
        'type': 'login',
        'user_id': random.choice(suspicious_users_attempts),
        'device_id': f'UNKNOWN{random.randint(1000, 9999)}',
        'success': False,
        'ip_address': random.choice(suspicious_ips),
        'reason': random.choice(['Invalid password', 'Invalid credentials', 'User not found'])
    })

# Eventos de salas - usando nombres más realistas
real_rooms = [
    '!general:matrix.nasfurui.cat',
    '!admin:matrix.nasfurui.cat',
    '!pruebas:matrix.nasfurui.cat',
]

# Mensajes enviados por usuarios reales
for i in range(35):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    room_events.append({
        'timestamp': timestamp,
        'type': 'room',
        'room_id': random.choice(real_rooms),
        'user_id': random.choice(real_users),
        'event_type': 'message',
        'details': {'content': f'Message content {i}'}
    })

# Salas creadas
for i in range(1):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    room_events.append({
        'timestamp': timestamp,
        'type': 'room',
        'room_id': f'!newroom{i}:matrix.nasfurui.cat',
        'user_id': real_users[0],
        'event_type': 'create',
        'details': {}
    })

# Algunos mensajes eliminados (pocos, normal en operación)
for i in range(2):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    room_events.append({
        'timestamp': timestamp,
        'type': 'room',
        'room_id': random.choice(real_rooms),
        'user_id': random.choice(real_users),
        'event_type': 'delete',
        'details': {}
    })

# Eventos de dispositivos - usando IDs reales
for i in range(3):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    device_events.append({
        'timestamp': timestamp,
        'type': 'device',
        'user_id': random.choice(real_users),
        'device_id': random.choice(real_devices),
        'action': 'added'
    })

# Dispositivo eliminado (menos común)
for i in range(1):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    device_events.append({
        'timestamp': timestamp,
        'type': 'device',
        'user_id': random.choice(real_users),
        'device_id': 'OLDDEVICE123',
        'action': 'removed'
    })

# Eventos de federación - servidores reales de Matrix
real_federated_servers = [
    'matrix.org',           # Servidor principal de Matrix
    'mozilla.org',          # Mozilla usa Matrix
    't2bot.io',            # Bots populares
    'kde.org',             # KDE usa Matrix
]

for i in range(30):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    federation_events.append({
        'timestamp': timestamp,
        'type': 'federation',
        'server': random.choice(real_federated_servers),
        'event_type': 'request',
        'direction': random.choice(['inbound', 'outbound']),
        'details': {}
    })

# Errores de federación (algunos servidores caídos)
problematic_servers = [
    'old-server.example.org',  # Servidor antiguo desconectado
    'maintenance.matrix.test', # Servidor en mantenimiento
]

for i in range(4):
    timestamp = (now - timedelta(hours=random.randint(0, 24))).isoformat()
    federation_events.append({
        'timestamp': timestamp,
        'type': 'federation',
        'server': random.choice(problematic_servers),
        'event_type': 'error',
        'direction': 'outbound',
        'details': {'error': random.choice(['Connection timeout', 'Connection refused', 'SSL certificate error'])}
    })

# Guardar todos los eventos
data = {
    'auth_events': auth_events,
    'room_events': room_events,
    'federation_events': federation_events,
    'device_events': device_events
}

with open(events_file, 'w') as f:
    json.dump(data, f, indent=2)

print(f"✅ Eventos de prueba REALISTAS generados:")
print(f"   - {len(auth_events)} eventos de autenticación")
print(f"     • {len([e for e in auth_events if e['success']])} logins exitosos")
print(f"     • {len([e for e in auth_events if not e['success']])} intentos fallidos (de IPs sospechosas)")
print(f"   - {len(room_events)} eventos de salas")
print(f"   - {len(federation_events)} eventos de federación")
print(f"   - {len(device_events)} eventos de dispositivos")
print(f"\n📊 Total: {len(auth_events) + len(room_events) + len(federation_events) + len(device_events)} eventos")
print(f"\n🔍 IPs sospechosas detectadas:")
for ip in suspicious_ips:
    count = len([e for e in auth_events if e.get('ip_address') == ip])
    print(f"   • {ip}: {count} intentos fallidos")
print(f"\n📁 Guardado en: {events_file}")

