#!/usr/bin/env python3
"""
Matrix Bot with E2EE support, custom commands, and AI integration.
"""

import asyncio
import os
import json
import logging
import markdown
from pathlib import Path
from nio import (
    AsyncClient,
    AsyncClientConfig,
    MatrixRoom,
    RoomMessageText,
    LoginResponse,
    RoomCreateResponse,
    SyncResponse,
    InviteMemberEvent,
    RoomMemberEvent,
    KeyVerificationEvent,
    KeyVerificationStart,
    KeyVerificationCancel,
    KeyVerificationKey,
    KeyVerificationMac,
    ToDeviceError,
)
from dotenv import load_dotenv
from .handlers.command import CommandHandler
from .handlers.ai import AIHandler
from .services.webhook import WebhookServer
from .utils.logger import SecurityLogger
from .monitors.login import LoginMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MatrixBot:
    def __init__(self):
        """Initialize the Matrix bot."""
        load_dotenv()
        
        self.homeserver = os.getenv("MATRIX_HOMESERVER")
        self.user_id = os.getenv("MATRIX_USER_ID")
        self.password = os.getenv("MATRIX_PASSWORD")
        self.recovery_key = os.getenv("MATRIX_RECOVERY_KEY")
        self.store_path = os.getenv("STORE_PATH", "./store")
        
        # Validate environment variables
        if not all([self.homeserver, self.user_id, self.password]):
            raise ValueError("Missing required environment variables. Check your .env file.")
        
        # Create store directory if it doesn't exist
        os.makedirs(self.store_path, exist_ok=True)
        
        # Configure client with encryption support
        config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=3,
            store_sync_tokens=True,
            encryption_enabled=True,
        )
        
        self.client = AsyncClient(
            self.homeserver,
            self.user_id,
            store_path=self.store_path,
            config=config,
        )
        
        # Initialize handlers
        self.command_handler = CommandHandler()
        self.ai_handler = AIHandler()
        
        # Initialize security logger
        self.security_logger = SecurityLogger()
        
        # Initialize login monitor
        self.login_monitor = LoginMonitor()
        
        # Initialize webhook server
        self.webhook_server = WebhookServer(port=23983)
        self.webhook_runner = None
        
        # Track JSON file modification times for auto-reload
        self.json_files = {
            'users.json': Path('users.json'),
            'commands.json': Path('commands.json')
        }
        self.json_mtimes = {}
        self.update_json_mtimes()
        
        # Bot trigger name (case-insensitive)
        self.bot_name = "subaru"
        
        # Setup callbacks
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        self.client.add_event_callback(self.invite_callback, InviteMemberEvent)
        self.client.add_event_callback(self.member_callback, RoomMemberEvent)
        self.client.add_response_callback(self.sync_callback, SyncResponse)
        
        # Add key verification callbacks for auto-accept
        self.client.add_to_device_callback(self.key_verification_start_callback, KeyVerificationStart)
        self.client.add_to_device_callback(self.key_verification_key_callback, KeyVerificationKey)
        self.client.add_to_device_callback(self.key_verification_mac_callback, KeyVerificationMac)
    
    def update_json_mtimes(self):
        """Update the modification times of JSON files."""
        for name, path in self.json_files.items():
            if path.exists():
                self.json_mtimes[name] = path.stat().st_mtime
            else:
                self.json_mtimes[name] = 0
    
    def check_json_updates(self):
        """Check if any JSON files have been modified and reload them."""
        reloaded = []
        for name, path in self.json_files.items():
            if not path.exists():
                continue
            
            current_mtime = path.stat().st_mtime
            if current_mtime != self.json_mtimes.get(name, 0):
                # File has been modified
                if name == 'users.json':
                    self.ai_handler.load_users()
                    reloaded.append('users.json')
                elif name == 'commands.json':
                    self.command_handler.load_commands()
                    reloaded.append('commands.json')
                
                self.json_mtimes[name] = current_mtime
        
        if reloaded:
            logger.info(f"🔄 Auto-reloaded: {', '.join(reloaded)}")
        
        return reloaded
    
    async def login(self):
        """Login to the Matrix server."""
        logger.info(f"Logging in as {self.user_id}")
        
        response = await self.client.login(self.password)
        
        if isinstance(response, LoginResponse):
            logger.info("Login successful")
            
            # Trust this device automatically
            if self.client.should_upload_keys:
                logger.info("Uploading encryption keys...")
                await self.client.keys_upload()
            
            # Mark our own device as verified
            try:
                logger.info("Verifying this device...")
                # Get our device ID
                device_id = self.client.device_id
                
                # Trust our own device
                self.client.verify_device(self.client.olm.account.identity_keys["ed25519"])
                logger.info(f"✅ Device {device_id} verified")
            except Exception as e:
                logger.warning(f"Device verification failed: {e}")
            
            return True
        else:
            logger.error(f"Login failed: {response}")
            return False
    
    async def sync_callback(self, response: SyncResponse):
        """Handle sync responses."""
        logger.debug(f"Sync response received. Next batch: {response.next_batch}")
        
        # Check for JSON file updates on each sync
        self.check_json_updates()
    
    async def invite_callback(self, room: MatrixRoom, event: InviteMemberEvent):
        """Handle room invitations - auto-accept all invites."""
        if event.membership == "invite" and event.state_key == self.client.user_id:
            logger.info(f"Received invite to {room.room_id} from {event.sender}")
            
            try:
                result = await self.client.join(room.room_id)
                if hasattr(result, 'room_id'):
                    logger.info(f"Successfully joined room: {room.room_id}")
                    # Send a greeting message
                    await self.send_message(
                        room.room_id,
                        f"¡Hola! Soy Subaru 🤖\n\nPara hablar conmigo, menciona mi nombre 'subaru' en tu mensaje.\nPara comandos, usa !help"
                    )
                else:
                    logger.error(f"Failed to join room {room.room_id}: {result}")
            except Exception as e:
                logger.error(f"Error joining room {room.room_id}: {e}")
    
    async def key_verification_start_callback(self, event: KeyVerificationStart):
        """Auto-accept device verification requests."""
        try:
            logger.info(f"🔐 Verification request from {event.sender} (device {event.from_device})")
            
            # Accept the verification
            await self.client.accept_key_verification(event.transaction_id)
            logger.info(f"✅ Accepted verification from {event.sender}")
            
            # Send security alert
            if self.security_logger:
                await self.security_logger.send_security_alert(
                    f"🔐 Device verification accepted\nUser: {event.sender}\nDevice: {event.from_device}"
                )
        except Exception as e:
            logger.error(f"Error accepting verification: {e}", exc_info=True)
    
    async def key_verification_key_callback(self, event: KeyVerificationKey):
        """Auto-confirm key verification."""
        try:
            logger.info(f"🔑 Key exchange from {event.sender} (txn {event.transaction_id})")
            
            # Confirm the short authentication string (emoji comparison)
            await self.client.confirm_short_auth_string(event.transaction_id)
            logger.info(f"✅ Confirmed key exchange with {event.sender}")
        except Exception as e:
            logger.error(f"Error confirming key: {e}", exc_info=True)
    
    async def key_verification_mac_callback(self, event: KeyVerificationMac):
        """Handle MAC verification completion."""
        try:
            logger.info(f"✅ Verification complete with {event.sender} (device {event.keys})")
            
            # Send success notification
            if self.security_logger:
                await self.security_logger.send_security_alert(
                    f"✅ Device verification completed\nUser: {event.sender}\nStatus: Trusted"
                )
        except Exception as e:
            logger.error(f"Error handling MAC: {e}", exc_info=True)
    
    async def member_callback(self, room: MatrixRoom, event: RoomMemberEvent):
        """Handle room member events."""
        # Log when users join or leave
        if event.membership == "join":
            logger.debug(f"User {event.state_key} joined room {room.room_id}")
            
            # TODO: Commented out LOGIN SUCCESS notification for user room joins - for later fix
            # Send security alert for user logins (exclude bot itself)
            # if event.state_key != self.client.user_id and self.security_logger:
            #     # Extract homeserver from user_id (@user:homeserver)
            #     homeserver = event.state_key.split(':')[1] if ':' in event.state_key else 'unknown'
            #     await self.security_logger.log_login(
            #         user_id=event.state_key,
            #         homeserver=homeserver,
            #         ip_address='unknown',
            #         status='success'
            #     )
        elif event.membership == "leave":
            logger.debug(f"User {event.state_key} left room {room.room_id}")
        
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming messages."""
        # Ignore messages from the bot itself
        if event.sender == self.client.user_id:
            return
        
        # Ignore old messages (before bot started)
        if hasattr(self, 'start_time') and event.server_timestamp < self.start_time:
            return
        
        logger.info(f"Message from {event.sender} in {room.display_name}: {event.body}")
        
        # Process the message
        try:
            response_text = await self.process_message(event.sender, event.body, room)
            
            # Send response if there is one
            if response_text:
                await self.send_message(room.room_id, response_text)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Try to send error message to user
            try:
                await self.send_message(room.room_id, f"❌ Lo siento, ocurrió un error procesando tu mensaje: {str(e)[:200]}")
            except:
                logger.error("Failed to send error message to user")
    
    async def process_message(self, sender: str, message: str, room: MatrixRoom) -> str:
        """Process incoming message and generate response."""
        message = message.strip()
        
        # Easter egg: que -> so
        if message.lower() == "que" or message.lower() == "qué":
            return "so"
        
        # Get user configuration
        user_config = self.ai_handler.get_user_config(sender)
        
        # Check if message starts with !prompt (AI trigger with different personality)
        if message.lower().startswith("!prompt "):
            # Extract the actual message after !prompt
            clean_message = message[8:].strip()  # Remove "!prompt "
            return await self.ai_handler.handle_message(sender, clean_message, trigger="!prompt")
        
        # Check if it's a regular command (starts with !)
        if message.startswith("!") or message.startswith("magnet"):
            return await self.command_handler.handle_command(sender, message, user_config, room.room_id)
        
        # Check if the message mentions "subaru" (case-insensitive)
        if "subaru" in message.lower():
            # Use subaru trigger
            return await self.ai_handler.handle_message(sender, message, trigger="subaru")
        
        # Don't respond to messages that don't mention any trigger
        return None
    
    def split_into_messages(self, message: str) -> list:
        """
        Split a long response into separate messages by paragraph.
        Each paragraph becomes one message, EXCEPT code blocks which stay intact.
        
        Args:
            message: The message to split
            
        Returns:
            List of individual paragraph messages
        """
        import re
        
        # Find all code blocks (``` ... ```)
        code_block_pattern = r'```(?:\w+)?\n.*?\n```'
        code_blocks = []
        
        # Extract code blocks and replace with placeholders
        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f'___CODEBLOCK_{len(code_blocks)-1}___'
        
        text_without_code = re.sub(code_block_pattern, save_code_block, message, flags=re.DOTALL)
        
        # Split by single OR double line breaks (paragraphs)
        # First normalize: replace double+ newlines with double newline
        text_normalized = re.sub(r'\n{2,}', '\n\n', text_without_code)
        
        # Split by double newline to get paragraphs
        paragraphs = text_normalized.split('\n\n')
        
        # Each paragraph is a separate message
        messages = []
        for para in paragraphs:
            if para.strip():  # Only add non-empty paragraphs
                messages.append(para.strip())
        
        # Restore code blocks in their messages
        restored_messages = []
        for msg in messages:
            # Check if this message contains a code block placeholder
            has_code = False
            for i, code_block in enumerate(code_blocks):
                placeholder = f'___CODEBLOCK_{i}___'
                if placeholder in msg:
                    msg = msg.replace(placeholder, code_block)
                    has_code = True
            
            if msg.strip():
                restored_messages.append(msg)
        
        # If no messages were created (edge case), return original
        return restored_messages if restored_messages else [message]

    async def send_message(self, room_id: str, message: str):
        """Send a message to a room with markdown support, splitting into one message per paragraph."""
        try:
            # Split into one message per paragraph
            message_parts = self.split_into_messages(message)
            
            # Send each message separately
            for i, msg in enumerate(message_parts):
                # Convert markdown to HTML for Matrix
                try:
                    formatted_body = self.markdown_to_html(msg)
                except Exception as e:
                    logger.error(f"Markdown conversion failed: {e}. Sending plain text.")
                    formatted_body = msg
                
                # Send the message with both plain text and formatted HTML
                content = {
                    "msgtype": "m.text",
                    "body": msg,  # Plain text fallback
                }
                
                # Only add formatted_body if there's actual formatting
                if formatted_body != msg:
                    content["format"] = "org.matrix.custom.html"
                    content["formatted_body"] = formatted_body
                
                await self.client.room_send(
                    room_id=room_id,
                    message_type="m.room.message",
                    content=content,
                    ignore_unverified_devices=True
                )
                
                if len(message_parts) > 1:
                    logger.info(f"Sent paragraph {i+1}/{len(message_parts)} to {room_id}")
                else:
                    logger.info(f"Sent message to {room_id}")
                
                # Calculate delay based on message length (simulating typing time)
                if i < len(message_parts) - 1:
                    # Base calculation: ~50 characters per second (reading/typing speed)
                    # Minimum 2 seconds, maximum 15 seconds
                    char_count = len(msg)
                    delay = min(max(char_count / 50.0, 2.0), 15.0)
                    logger.info(f"Waiting {delay:.1f} seconds before next message ({char_count} chars)")
                    await asyncio.sleep(delay)
                    
        except Exception as e:
            logger.error(f"Failed to send message: {e}", exc_info=True)

    
    async def sync_forever(self):
        """Sync loop that runs forever."""
        # Set the start time to ignore old messages
        import time
        self.start_time = int(time.time() * 1000)
        
        logger.info("Starting sync loop")
        await self.client.sync_forever(timeout=30000, full_state=True)
    
    async def run(self):
        """Main run loop for the bot."""
        try:
            # Login
            if not await self.login():
                logger.error("Failed to login, exiting")
                # TODO: Commented out LOGIN SUCCESS notification for bot login failures - for later fix
                # await self.security_logger.log_login(
                #     self.user_id, 
                #     self.homeserver, 
                #     ip_address="local",
                #     status="failed"
                # )
                return
            
            # TODO: Commented out LOGIN SUCCESS notification for bot login - for later fix
            # Log successful login
            # await self.security_logger.log_login(
            #     self.user_id,
            #     self.homeserver,
            #     ip_address="local",
            #     status="success"
            # )
            
            logger.info("Bot is ready!")
            
            # Start webhook server
            logger.info("Starting webhook server on port 23983...")
            self.webhook_runner = await self.webhook_server.start()
            
            # Set webhook callback to send messages to the bot's default room
            self.webhook_server.set_message_callback(self.send_webhook_message)
            
            # Set security logger webhook callback
            self.security_logger.webhook_callback = self.send_webhook_message
            
            # Setup login monitor callback
            self.login_monitor.set_callback(self.on_system_login)
            
            # Start login monitor
            login_monitor_task = asyncio.create_task(
                self.login_monitor.start_monitoring()
            )
            
            # Start download monitor
            monitor_task = asyncio.create_task(
                self.command_handler.download_monitor.start_monitoring(self.on_download_complete)
            )
            
            # Start syncing
            await self.sync_forever()
            
        except Exception as e:
            logger.error(f"Error in run loop: {e}", exc_info=True)
        finally:
            if self.webhook_runner:
                await self.webhook_server.stop(self.webhook_runner)
            await self.client.close()
    
    async def send_webhook_message(self, message: str, room_id: str):
        """Send a message to a room from webhook."""
        try:
            target_room_id = room_id
            
            # Handle Direct Message to user (if room_id is a user ID like @user:server)
            if room_id.startswith('@'):
                user_id = room_id
                target_room_id = None
                
                # Check if we already have a DM with this user
                # We iterate through rooms to find a direct chat
                for room_id_iter, room in self.client.rooms.items():
                    # Check for direct chat with 2 members including the target
                    # Note: room.users might be incomplete if lazy loading members, 
                    # but for DMs usually we have the members locally if we talked recently.
                    if len(room.users) == 2 and user_id in room.users:
                        target_room_id = room_id_iter
                        logger.info(f"Found existing DM {target_room_id} for {user_id}")
                        break
                
                # If not found, create a new DM
                if not target_room_id:
                    logger.info(f"Creating DM with {user_id}")
                    # We don't catch exceptions here to let them propagate to the webhook handler (so it returns 500)
                    resp = await self.client.room_create(
                        invite=[user_id],
                        is_direct=True,
                        preset="private_chat"
                    )
                    if isinstance(resp, RoomCreateResponse):
                        target_room_id = resp.room_id
                        logger.info(f"Created/Found DM room {target_room_id} with {user_id}")
                    else:
                        # Si falla, puede que el usuario no exista o no permita invites
                        if hasattr(resp, 'message') and "M_UNKNOWN" in resp.message:
                             # Intentar enviar solo el invite primero si falla la creacion directa
                             logger.warning(f"Failed to create DM room, retrying differently. Error: {resp}")
                        
                        error_msg = f"Failed to create DM with {user_id}. Response: {resp}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

            if not target_room_id:
                raise Exception(f"Could not obtain a valid room ID for target {room_id}")

            # Convert markdown-style formatting to HTML for better display
            html_body = self.markdown_to_html(message)
            
            content = {
                "msgtype": "m.text",
                "body": message,
                "format": "org.matrix.custom.html",
                "formatted_body": html_body
            }
            
            logger.debug(f"Sending webhook message to {target_room_id}")
            
            # For security room, ignore unverified devices
            # (webhooks need to work even if devices aren't verified)
            response = await self.client.room_send(
                room_id=target_room_id,
                message_type="m.room.message",
                content=content,
                ignore_unverified_devices=True
            )
            
            # Check for error in response
            if hasattr(response, 'transport_response'): 
                 # Assuming it's a RoomSendResponse or Error. 
                 # Nio returns RoomSendError on failure logic usually but let's check basic success
                 pass
            
            # If response indicates error (nio usually returns Error classes)
            # We can check if it has 'event_id' which means success
            if not hasattr(response, 'event_id'):
                 # It might be an error response
                 logger.error(f"Failed to send webhook message: {response}")
                 raise Exception(f"Matrix send failed: {response}")

            logger.info(f"✅ Webhook message sent to {target_room_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending webhook message to {room_id}: {e}", exc_info=True)
            # Re-raise exception so the webhook server returns 500
            raise e
    
    def markdown_to_html(self, text: str) -> str:
        """Convert markdown to HTML using the markdown library."""
        try:
            # Convert using markdown library with useful extensions
            return markdown.markdown(
                text,
                extensions=['fenced_code', 'nl2br', 'sane_lists', 'tables']
            )
        except Exception as e:
            logger.error(f"Error converting markdown: {e}")
            return text
    
    async def on_system_login(self, event_type: str, user: str, details: dict):
        """Callback when a system login is detected."""
        try:
            # Format message based on event type
            if event_type == "ssh_login":
                title = "SSH Login Detected"
                message = (
                    f"• **User:** `{user}`\n"
                    f"• **IP:** `{details.get('ip')}`\n"
                    f"• **Port:** `{details.get('port')}`\n"
                    f"• **Status:** ✅ Success\n"
                    f"• **Time:** `{details.get('timestamp')}`"
                )
                severity = "warning"
            elif event_type == "ssh_failed":
                title = "SSH Login Failed"
                message = (
                    f"• **User:** `{user}`\n"
                    f"• **IP:** `{details.get('ip')}`\n"
                    f"• **Port:** `{details.get('port')}`\n"
                    f"• **Status:** ❌ Failed\n"
                    f"• **Time:** `{details.get('timestamp')}`"
                )
                severity = "error"
            elif event_type == "sudo_command":
                title = "Sudo Command Executed"
                message = (
                    f"• **User:** `{user}`\n"
                    f"• **Command:** `{details.get('command')}`\n"
                    f"• **Time:** `{details.get('timestamp')}`"
                )
                severity = "info"
            elif event_type == "console_login":
                title = "Console Login"
                message = (
                    f"• **User:** `{user}`\n"
                    f"• **Time:** `{details.get('timestamp')}`"
                )
                severity = "info"
            else:
                title = "System Event"
                message = f"Event: {event_type}\nUser: {user}"
                severity = "info"
            
            # Send to security logger which will forward to webhook
            if self.security_logger:
                await self.security_logger.send_security_alert(title, message, severity)
            
            logger.info(f"System login detected: {event_type} by {user}")
        
        except Exception as e:
            logger.error(f"Error handling system login: {e}", exc_info=True)
    
    async def on_download_complete(self, user_id: str, room_id: str, torrent_data: dict):
        """Callback when a download completes."""
        filename = torrent_data.get("filename", "Unknown")
        links = torrent_data.get("links", [])
        
        # Format message
        message = (
            f"✅ **Descarga Completada!**\n\n"
            f"• **Archivo:** {filename}\n"
            f"• **Torrent ID:** {torrent_data.get('torrent_id')}\n\n"
            f"**Enlaces disponibles:**\n"
        )
        
        if links:
            for i, link in enumerate(links[:5], 1):  # Show first 5 links
                message += f"{i}. `{link}`\n"
            if len(links) > 5:
                message += f"\n... y {len(links) - 5} enlaces más"
        else:
            message += "No links available yet"
        
        try:
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message}
            )
            logger.info(f"Sent download completion message to {room_id}")
        except Exception as e:
            logger.error(f"Error sending download complete message: {e}")
    
    async def close(self):
        """Close the client connection."""
        if self.webhook_runner:
            await self.webhook_server.stop(self.webhook_runner)
        await self.client.close()


async def main():
    """Main entry point."""
    bot = MatrixBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
