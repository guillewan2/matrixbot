"""
Webhook server for receiving notifications and logs from other devices.
Listens on port 23983 (Tailscale network only) and sends messages to Matrix.
"""

import asyncio
import logging
import json
from typing import Optional, Callable
from aiohttp import web

logger = logging.getLogger(__name__)


class WebhookServer:
    """HTTP webhook server for receiving notifications from other devices."""
    
    DEFAULT_ROOM_ID = "!pDyuEmkITrMcncMFMy:matrix.nasfurui.cat"
    DEFAULT_PORT = 23983
    
    def __init__(self, port: int = DEFAULT_PORT):
        """
        Initialize the webhook server.
        
        Args:
            port: Port to listen on (default 23983)
        """
        self.port = port
        self.app = web.Application()
        self.message_callback: Optional[Callable] = None
        self.setup_routes()
    
    def setup_routes(self):
        """Setup webhook routes."""
        # Support both GET and POST for compatibility with different webhook senders
        self.app.router.add_post("/webhook/message", self.handle_message)
        self.app.router.add_get("/webhook/message", self.handle_message)
        self.app.router.add_post("/webhook/log", self.handle_log)
        self.app.router.add_get("/webhook/log", self.handle_log)
        self.app.router.add_post("/webhook/notify", self.handle_notify)
        self.app.router.add_get("/webhook/notify", self.handle_notify)
        self.app.router.add_get("/webhook/health", self.handle_health)
    
    def set_message_callback(self, callback: Callable):
        """
        Set callback for handling incoming messages.
        
        The callback should be an async function that accepts:
        - message_text: str (the message to send)
        - room_id: str (Matrix room ID, defaults to DEFAULT_ROOM_ID)
        """
        self.message_callback = callback
    
    async def handle_message(self, request: web.Request) -> web.Response:
        """Handle incoming message webhook (supports GET and POST)."""
        try:
            if request.method == "POST":
                data = await request.json()
            else:  # GET
                data = dict(request.query)
        except Exception as e:
            logger.error(f"Invalid data in message webhook: {e}")
            return web.json_response({"error": "Invalid data"}, status=400)
        
        message = data.get("message", "")
        room_id = data.get("room_id", self.DEFAULT_ROOM_ID)
        
        if not message:
            return web.json_response({"error": "Missing message field"}, status=400)
        
        logger.info(f"Webhook message from {request.remote}: {message[:100]}")
        
        if self.message_callback:
            try:
                await self.message_callback(message, room_id)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")
                return web.json_response({"error": str(e)}, status=500)
        
        return web.json_response({"status": "ok"})
    
    async def handle_log(self, request: web.Request) -> web.Response:
        """Handle incoming log webhook (supports GET and POST)."""
        try:
            if request.method == "POST":
                data = await request.json()
            else:  # GET
                data = dict(request.query)
        except Exception as e:
            logger.error(f"Invalid data in log webhook: {e}")
            return web.json_response({"error": "Invalid data"}, status=400)
        
        log_level = data.get("level", "INFO").upper()
        log_message = data.get("message", "")
        source = data.get("source", "webhook")
        room_id = data.get("room_id", self.DEFAULT_ROOM_ID)
        
        if not log_message:
            return web.json_response({"error": "Missing message field"}, status=400)
        
        # Format log message
        formatted_message = f"📋 **[{log_level}]** {source}\n{log_message}"
        
        logger.info(f"Webhook log from {request.remote} ({log_level}): {log_message[:100]}")
        
        if self.message_callback:
            try:
                await self.message_callback(formatted_message, room_id)
            except Exception as e:
                logger.error(f"Error in log callback: {e}")
                return web.json_response({"error": str(e)}, status=500)
        
        return web.json_response({"status": "ok"})
    
    async def handle_notify(self, request: web.Request) -> web.Response:
        """Handle incoming notification webhook (supports GET and POST)."""
        try:
            if request.method == "POST":
                data = await request.json()
            else:  # GET
                data = dict(request.query)
        except Exception as e:
            logger.error(f"Invalid data in notify webhook: {e}")
            return web.json_response({"error": "Invalid data"}, status=400)
        
        title = data.get("title", "Notification")
        message = data.get("message", "")
        priority = data.get("priority", "normal")
        room_id = data.get("room_id", self.DEFAULT_ROOM_ID)
        
        if not message:
            return web.json_response({"error": "Missing message field"}, status=400)
        
        # Format notification
        emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
        formatted_message = f"{emoji} **{title}**\n{message}"
        
        logger.info(f"Webhook notification from {request.remote}: {title}")
        
        if self.message_callback:
            try:
                await self.message_callback(formatted_message, room_id)
            except Exception as e:
                logger.error(f"Error in notify callback: {e}")
                return web.json_response({"error": str(e)}, status=500)
        
        return web.json_response({"status": "ok"})
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "port": self.port})
    
    async def start(self):
        """Start the webhook server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        logger.info(f"Webhook server started on port {self.port}")
        return runner
    
    async def stop(self, runner):
        """Stop the webhook server."""
        await runner.cleanup()
        logger.info("Webhook server stopped")


async def create_webhook_server(port: int = 23983) -> WebhookServer:
    """Create and start the webhook server."""
    server = WebhookServer(port=port)
    return server
