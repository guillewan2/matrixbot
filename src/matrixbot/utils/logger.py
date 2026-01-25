"""
Security logging module for the Matrix bot.
Logs login attempts and sends webhooks to security room.
"""

import logging
import datetime
from typing import Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)


class SecurityLogger:
    """Logs security events and sends them as webhooks."""
    
    DEFAULT_SECURITY_ROOM = "!pDyuEmkITrMcncMFMy:matrix.nasfurui.cat"
    
    def __init__(self, webhook_callback=None):
        """
        Initialize the security logger.
        
        Args:
            webhook_callback: Async function to call for webhook notifications
        """
        self.webhook_callback = webhook_callback
        self.login_history: Dict[str, list] = {}
    
    async def log_login(self, user_id: str, homeserver: str, ip_address: str = "unknown", status: str = "success"):
        """
        Log a login attempt and send webhook.
        
        Args:
            user_id: Matrix user ID
            homeserver: Matrix homeserver URL
            ip_address: IP address of login attempt
            status: "success" or "failed"
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Store in history
        if user_id not in self.login_history:
            self.login_history[user_id] = []
        
        login_record = {
            "timestamp": timestamp,
            "user_id": user_id,
            "homeserver": homeserver,
            "ip_address": ip_address,
            "status": status
        }
        
        self.login_history[user_id].append(login_record)
        
        # Log locally
        emoji = "✅" if status == "success" else "❌"
        logger.info(f"{emoji} Login {status}: {user_id} from {ip_address} at {timestamp}")
        
        # Send webhook notification
        if self.webhook_callback:
            message = (
                f"{emoji} **Login {status.upper()}**\n\n"
                f"• **Usuario:** `{user_id}`\n"
                f"• **Servidor:** {homeserver}\n"
                f"• **IP:** `{ip_address}`\n"
                f"• **Tiempo:** {timestamp}"
            )
            
            try:
                await self.webhook_callback(message, self.DEFAULT_SECURITY_ROOM)
            except Exception as e:
                logger.error(f"Error sending login webhook: {e}")
    
    async def log_sync_start(self, user_id: str):
        """Log when sync starts."""
        logger.debug(f"Sync started for {user_id}")
    
    async def log_command_execution(self, user_id: str, command: str, room_id: str):
        """
        Log command execution.
        
        Args:
            user_id: User who executed the command
            command: Command that was executed
            room_id: Room where command was executed
        """
        timestamp = datetime.datetime.now().isoformat()
        logger.info(f"Command: {user_id} executed '{command}' in {room_id}")
        
        # Send webhook for admin commands (those starting with !)
        if command.startswith("!") and self.webhook_callback:
            message = (
                f"📋 **Comando Ejecutado**\n\n"
                f"• **Usuario:** `{user_id}`\n"
                f"• **Comando:** `{command}`\n"
                f"• **Room:** {room_id}\n"
                f"• **Tiempo:** {timestamp}"
            )
            
            try:
                await self.webhook_callback(message, self.DEFAULT_SECURITY_ROOM)
            except Exception as e:
                logger.debug(f"Command webhook not sent: {e}")
    
    async def log_unauthorized_access(self, user_id: str, command: str, room_id: str):
        """
        Log unauthorized access attempts.
        
        Args:
            user_id: User who attempted access
            command: Command they tried to execute
            room_id: Room where attempt occurred
        """
        timestamp = datetime.datetime.now().isoformat()
        logger.warning(f"Unauthorized: {user_id} tried '{command}' in {room_id}")
        
        if self.webhook_callback:
            message = (
                f"🚨 **Intento de Acceso No Autorizado**\n\n"
                f"• **Usuario:** `{user_id}`\n"
                f"• **Comando:** `{command}`\n"
                f"• **Room:** {room_id}\n"
                f"• **Tiempo:** {timestamp}"
            )
            
            try:
                await self.webhook_callback(message, self.DEFAULT_SECURITY_ROOM)
            except Exception as e:
                logger.error(f"Error sending unauthorized access webhook: {e}")
    
    def get_login_history(self, user_id: str) -> list:
        """Get login history for a user."""
        return self.login_history.get(user_id, [])
    
    async def send_security_alert(self, title: str, message: str, severity: str = "info"):
        """
        Send a custom security alert.
        
        Args:
            title: Alert title
            message: Alert message
            severity: "info", "warning", or "critical"
        """
        emoji = "ℹ️" if severity == "info" else "⚠️" if severity == "warning" else "🚨"
        timestamp = datetime.datetime.now().isoformat()
        
        full_message = (
            f"{emoji} **{title}**\n\n"
            f"{message}\n\n"
            f"_Tiempo: {timestamp}_"
        )
        
        logger.log(
            logging.WARNING if severity == "warning" else logging.CRITICAL if severity == "critical" else logging.INFO,
            f"Security Alert: {title}"
        )
        
        if self.webhook_callback:
            try:
                await self.webhook_callback(full_message, self.DEFAULT_SECURITY_ROOM)
            except Exception as e:
                logger.error(f"Error sending security alert: {e}")
