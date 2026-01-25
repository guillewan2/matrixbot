#!/usr/bin/env python3
"""
Matrix Server Monitor - Monitorización avanzada de eventos de seguridad en Matrix
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class MatrixMonitor:
    """Monitoriza eventos de seguridad en Matrix para auditorías SIEM"""
    
    def __init__(self, client, store_path="./store"):
        self.client = client
        self.store_path = Path(store_path)
        self.events_log = self.store_path / "matrix_security_events.json"
        
        # Contadores de eventos por categoría
        self.auth_events = []
        self.room_events = []
        self.federation_events = []
        self.device_events = []
        
        # Umbrales de detección
        self.FAILED_LOGIN_THRESHOLD = 5  # Intentos fallidos antes de alertar
        self.SPAM_MESSAGE_THRESHOLD = 10  # Mensajes por minuto
        self.BULK_DELETE_THRESHOLD = 5    # Eliminaciones en 1 minuto
        
        # Cargar eventos históricos
        self._load_events()
    
    def _load_events(self):
        """Cargar eventos históricos desde disco"""
        if self.events_log.exists():
            try:
                with open(self.events_log, 'r') as f:
                    data = json.load(f)
                    self.auth_events = data.get('auth_events', [])
                    self.room_events = data.get('room_events', [])
                    self.federation_events = data.get('federation_events', [])
                    self.device_events = data.get('device_events', [])
                    logger.info(f"📊 Eventos cargados: {len(self.auth_events)} auth, {len(self.room_events)} room")
            except Exception as e:
                logger.error(f"Error cargando eventos: {e}")
    
    def _save_events(self):
        """Guardar eventos en disco"""
        try:
            # Mantener solo eventos de las últimas 24 horas
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            
            self.auth_events = [e for e in self.auth_events if e.get('timestamp', '') > cutoff]
            self.room_events = [e for e in self.room_events if e.get('timestamp', '') > cutoff]
            self.federation_events = [e for e in self.federation_events if e.get('timestamp', '') > cutoff]
            self.device_events = [e for e in self.device_events if e.get('timestamp', '') > cutoff]
            
            data = {
                'auth_events': self.auth_events,
                'room_events': self.room_events,
                'federation_events': self.federation_events,
                'device_events': self.device_events
            }
            
            with open(self.events_log, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando eventos: {e}")
    
    async def log_login_event(self, user_id: str, device_id: str, success: bool, 
                             ip_address: Optional[str] = None, reason: Optional[str] = None):
        """Registrar evento de login"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': 'login',
            'user_id': user_id,
            'device_id': device_id,
            'success': success,
            'ip_address': ip_address or 'unknown',
            'reason': reason
        }
        self.auth_events.append(event)
        self._save_events()
        
        # Detectar ataques de fuerza bruta
        if not success:
            recent_failures = [e for e in self.auth_events 
                             if e.get('user_id') == user_id 
                             and not e.get('success')
                             and e.get('timestamp', '') > (datetime.now() - timedelta(minutes=10)).isoformat()]
            
            if len(recent_failures) >= self.FAILED_LOGIN_THRESHOLD:
                logger.warning(f"🚨 Posible ataque de fuerza bruta en {user_id}: {len(recent_failures)} fallos")
                return {
                    'alert': True,
                    'type': 'brute_force',
                    'user_id': user_id,
                    'failed_attempts': len(recent_failures)
                }
        
        return None
    
    async def log_device_event(self, user_id: str, device_id: str, action: str):
        """Registrar evento de dispositivo (añadido/eliminado)"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': 'device',
            'user_id': user_id,
            'device_id': device_id,
            'action': action  # 'added', 'removed', 'verified'
        }
        self.device_events.append(event)
        self._save_events()
    
    async def log_room_event(self, room_id: str, user_id: str, event_type: str, 
                            details: Optional[Dict] = None):
        """Registrar evento de sala"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': 'room',
            'room_id': room_id,
            'user_id': user_id,
            'event_type': event_type,  # 'create', 'join', 'invite', 'message', 'delete', 'edit'
            'details': details or {}
        }
        self.room_events.append(event)
        self._save_events()
        
        # Detectar spam
        if event_type == 'message':
            recent_messages = [e for e in self.room_events 
                             if e.get('user_id') == user_id
                             and e.get('event_type') == 'message'
                             and e.get('timestamp', '') > (datetime.now() - timedelta(minutes=1)).isoformat()]
            
            if len(recent_messages) >= self.SPAM_MESSAGE_THRESHOLD:
                logger.warning(f"🚨 Posible spam de {user_id}: {len(recent_messages)} mensajes/min")
                return {
                    'alert': True,
                    'type': 'spam',
                    'user_id': user_id,
                    'message_count': len(recent_messages)
                }
        
        # Detectar eliminación masiva
        if event_type == 'delete':
            recent_deletes = [e for e in self.room_events 
                            if e.get('user_id') == user_id
                            and e.get('event_type') == 'delete'
                            and e.get('timestamp', '') > (datetime.now() - timedelta(minutes=1)).isoformat()]
            
            if len(recent_deletes) >= self.BULK_DELETE_THRESHOLD:
                logger.warning(f"🚨 Eliminación masiva por {user_id}: {len(recent_deletes)} mensajes")
                return {
                    'alert': True,
                    'type': 'bulk_delete',
                    'user_id': user_id,
                    'delete_count': len(recent_deletes)
                }
        
        return None
    
    async def log_federation_event(self, server: str, event_type: str, 
                                   direction: str, details: Optional[Dict] = None):
        """Registrar evento de federación"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': 'federation',
            'server': server,
            'event_type': event_type,  # 'request', 'response', 'error'
            'direction': direction,  # 'inbound', 'outbound'
            'details': details or {}
        }
        self.federation_events.append(event)
        self._save_events()
    
    async def get_user_activity(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Obtener actividad reciente de un usuario"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        user_logins = [e for e in self.auth_events 
                      if e.get('user_id') == user_id and e.get('timestamp', '') > cutoff]
        user_rooms = [e for e in self.room_events 
                     if e.get('user_id') == user_id and e.get('timestamp', '') > cutoff]
        user_devices = [e for e in self.device_events 
                       if e.get('user_id') == user_id and e.get('timestamp', '') > cutoff]
        
        return {
            'user_id': user_id,
            'login_count': len([e for e in user_logins if e.get('success')]),
            'failed_logins': len([e for e in user_logins if not e.get('success')]),
            'messages_sent': len([e for e in user_rooms if e.get('event_type') == 'message']),
            'rooms_joined': len([e for e in user_rooms if e.get('event_type') == 'join']),
            'devices_added': len([e for e in user_devices if e.get('action') == 'added']),
            'devices_removed': len([e for e in user_devices if e.get('action') == 'removed']),
            'total_events': len(user_logins) + len(user_rooms) + len(user_devices)
        }

    
    async def get_room_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener estadísticas detalladas de salas"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        recent_rooms = [e for e in self.room_events if e.get('timestamp', '') > cutoff]
        
        rooms_data = defaultdict(lambda: {
            'messages': 0,
            'joins': 0,
            'invites': 0,
            'deletes': 0,
            'users': set()
        })
        
        for event in recent_rooms:
            room_id = event.get('room_id')
            event_type = event.get('event_type')
            user_id = event.get('user_id')
            
            if event_type == 'message':
                rooms_data[room_id]['messages'] += 1
            elif event_type == 'join':
                rooms_data[room_id]['joins'] += 1
            elif event_type == 'invite':
                rooms_data[room_id]['invites'] += 1
            elif event_type == 'delete':
                rooms_data[room_id]['deletes'] += 1
            
            rooms_data[room_id]['users'].add(user_id)
        
        # Convertir sets a conteos
        result = []
        for room_id, data in rooms_data.items():
            result.append({
                'room_id': room_id,
                'messages': data['messages'],
                'joins': data['joins'],
                'invites': data['invites'],
                'deletes': data['deletes'],
                'unique_users': len(data['users'])
            })
        
        # Ordenar por actividad
        result.sort(key=lambda x: x['messages'], reverse=True)
        
        return {
            'total_rooms': len(result),
            'rooms': result[:20]  # Top 20 salas más activas
        }
