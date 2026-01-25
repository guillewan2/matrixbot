"""
Command handler for the Matrix bot.
Reads commands from commands.json and executes system scripts.
"""

import json
import logging
import subprocess
import asyncio
from typing import Optional
from .realdebrid import RealDebridHandler
from ..monitors.download import DownloadMonitor

logger = logging.getLogger(__name__)


class CommandHandler:
    def __init__(self, config_file: str = "config/commands.json"):
        """Initialize the command handler."""
        self.config_file = config_file
        self.commands = {}
        self.realdebrid = RealDebridHandler()
        self.download_monitor = DownloadMonitor()
        self.load_commands()
    
    def load_commands(self):
        """Load commands from JSON configuration file."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.commands = data.get("commands", {})
                logger.info(f"Loaded {len(self.commands)} commands from {self.config_file}")
        except FileNotFoundError:
            logger.warning(f"Commands file {self.config_file} not found. Creating default...")
            self.create_default_config()
            self.load_commands()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing {self.config_file}: {e}")
            self.commands = {}
    
    def create_default_config(self):
        """Create a default commands configuration file."""
        default_config = {
            "commands": {
                "!help": {
                    "description": "Show available commands",
                    "allowed_users": [],  # Empty list = everyone can use
                    "script": None,  # Built-in command
                    "type": "builtin"
                },
                "!ping": {
                    "description": "Check if bot is responsive",
                    "allowed_users": [],
                    "script": None,
                    "type": "builtin"
                },
                "!uptime": {
                    "description": "Show system uptime",
                    "allowed_users": ["@admin:matrix.example.com"],
                    "script": "uptime",
                    "type": "shell"
                },
                "!date": {
                    "description": "Show current date and time",
                    "allowed_users": [],
                    "script": "date",
                    "type": "shell"
                },
                "!reload": {
                    "description": "Reload commands configuration",
                    "allowed_users": ["@admin:matrix.example.com"],
                    "script": None,
                    "type": "builtin"
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        logger.info(f"Created default commands config at {self.config_file}")
    
    async def handle_command(self, sender: str, message: str, user_config: Optional[dict] = None, room_id: Optional[str] = None) -> Optional[str]:
        """Handle a command from a user.
        
        Args:
            sender: User ID who sent the command
            message: The command message
            user_config: Optional user configuration dict from users.json
            room_id: Optional room ID where the command was sent
        """
        # Split command and arguments
        parts = message.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Handle magnet commands (special case, not in commands.json)
        if command == "magnet":
            return await self.handle_magnet(sender, args, user_config)
        elif command == "magnet-config":
            return await self.handle_magnet_config(sender, args)
        elif command == "magnet-list":
            return await self.handle_magnet_list(sender, user_config)
        elif command == "magnet-info":
            return await self.handle_magnet_info(sender, args, user_config)
        
        # Check if command exists
        if command not in self.commands:
            return f"Unknown command: {command}. Use !help to see available commands."
        
        cmd_config = self.commands[command]
        
        # Check permissions
        allowed_users = cmd_config.get("allowed_users", [])
        if allowed_users and sender not in allowed_users:
            return f"You don't have permission to use {command}"
        
        # Handle built-in commands
        if cmd_config.get("type") == "builtin":
            return await self.handle_builtin_command(command, args, sender)
        
        # Handle shell commands
        elif cmd_config.get("type") == "shell":
            script = cmd_config.get("script")
            if not script:
                return "Error: No script configured for this command"
            
            return await self.execute_script(script, args)
        
        else:
            return "Error: Unknown command type"
    
    async def handle_builtin_command(self, command: str, args: str, sender: str) -> str:
        """Handle built-in commands."""
        if command == "!help":
            return self.generate_help(sender)
        
        elif command == "!ping":
            return "Pong! 🏓"
        
        elif command == "!reload":
            self.load_commands()
            return "Commands reloaded successfully!"
        
        elif command == "!espacio":
            return await self.get_disk_space()
        
        else:
            return "Unknown built-in command"
    
    async def get_disk_space(self) -> str:
        """Get disk space information."""
        try:
            # Use df command to get disk space
            process = await asyncio.create_subprocess_exec(
                'df', '-h', '/',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
            
            if process.returncode != 0:
                return f"❌ Error getting disk space: {stderr.decode()}"
            
            # Parse df output
            lines = stdout.decode().strip().split('\n')
            if len(lines) < 2:
                return "❌ Unable to parse disk space information"
            
            # Header: Filesystem      Size  Used Avail Use% Mounted on
            # Data:   /dev/sda1       100G   50G   45G  53% /
            header = lines[0].split()
            data = lines[1].split()
            
            if len(data) < 6:
                return "❌ Unable to parse disk space information"
            
            filesystem = data[0]
            size = data[1]
            used = data[2]
            available = data[3]
            use_percent = data[4]
            mountpoint = data[5]
            
            result = f"💾 **Espacio en disco ({mountpoint}):**\n\n"
            result += f"• **Total:** {size}\n"
            result += f"• **Usado:** {used} ({use_percent})\n"
            result += f"• **Disponible:** {available}\n"
            result += f"• **Sistema:** {filesystem}"
            
            return result
            
        except asyncio.TimeoutError:
            return "❌ Timeout getting disk space information"
        except Exception as e:
            logger.error(f"Error getting disk space: {e}")
            return f"❌ Error: {str(e)}"
    
    async def handle_magnet(self, sender: str, magnet_link: str, user_config: Optional[dict] = None, room_id: str = "") -> str:
        """Handle magnet link upload to RealDebrid.
        
        Usage: magnet magnet://blablabla...
        
        Args:
            sender: User ID
            magnet_link: Magnet link URI
            user_config: User configuration
            room_id: Matrix room ID for notifications
        """
        if not magnet_link:
            return "Usage: `magnet magnet://blablabla...`"
        
        if not user_config:
            return "❌ Unable to load user configuration."
        
        api_key = user_config.get("realdebrid_api_key")
        
        if not api_key:
            return "❌ RealDebrid API key not configured. Use `magnet-config <your_api_key>` to set it up."
        
        result = await self.realdebrid.add_magnet(api_key, magnet_link)
        
        if result.get("success"):
            torrent_id = result.get("torrent_id")
            filename = result.get("filename")
            
            # Register for monitoring
            self.download_monitor.add_torrent(
                user_id=sender,
                room_id=room_id,
                torrent_id=torrent_id,
                api_key=api_key,
                filename=filename
            )
            
            # Build response message
            response = (
                f"✅ **Torrent Added Successfully!**\n\n"
                f"• **Torrent ID:** `{torrent_id}`\n"
                f"• **Filename:** {filename}\n"
                f"• **Hash:** `{result.get('hash')}`\n\n"
            )
            
            # Add warning if manual selection is needed
            if result.get("needs_manual_selection"):
                response += (
                    f"⚠️ **Auto-start failed** - Please go to [RealDebrid Torrents](https://real-debrid.com/torrents) "
                    f"to manually select files and start the download.\n\n"
                )
            else:
                response += f"_Descarga iniciada automáticamente. Monitorando progreso..._ 📊\n\n"
            
            response += f"Use `magnet-list` to see download links when ready."
            
            return response
        else:
            return result.get("error", "❌ Unknown error occurred.")
    
    async def handle_magnet_config(self, sender: str, api_key: str) -> str:
        """Handle magnet RealDebrid API key configuration.
        
        Usage: magnet-config <your_real_debrid_api_key>
        """
        if not api_key:
            return "Usage: `magnet-config <your_real_debrid_api_key>`"
        
        # Load users.json
        try:
            with open("users.json", 'r') as f:
                users_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading users.json: {e}")
            return f"❌ Error loading configuration: {str(e)}"
        
        # Update user's API key
        if sender in users_data.get("users", {}):
            users_data["users"][sender]["realdebrid_api_key"] = api_key
            
            try:
                with open("users.json", 'w') as f:
                    json.dump(users_data, f, indent=4)
                return "✅ RealDebrid API key configured successfully!"
            except Exception as e:
                logger.error(f"Error saving users.json: {e}")
                return f"❌ Error saving configuration: {str(e)}"
        else:
            return f"❌ User {sender} not found in configuration."
    
    async def handle_magnet_list(self, sender: str, user_config: Optional[dict] = None) -> str:
        """List all torrents for the user with download links.
        
        Usage: magnet-list
        """
        if not user_config:
            return "❌ Unable to load user configuration."
        
        api_key = user_config.get("realdebrid_api_key")
        
        if not api_key:
            return "❌ RealDebrid API key not configured."
        
        result = await self.realdebrid.list_torrents(api_key)
        
        if result.get("success"):
            torrents = result.get("torrents", [])
            if not torrents:
                return "📭 No torrents found."
            
            response = f"📊 **Your Torrents ({result.get('count')})**\n\n"
            
            for torrent in torrents[:10]:  # Show first 10
                status = torrent.get("status", "unknown")
                filename = torrent.get("filename", "Unknown")
                torrent_id = torrent.get("id")
                
                # Get download links if torrent is completed
                if status == "downloaded":
                    # Get the links directly from the torrent data
                    links = torrent.get("links", [])
                    
                    if links:
                        response += f"✅ **{filename}**\n"
                        
                        # Get unrestricted link for files
                        for link in links[:3]:  # Show up to 3 links
                            unrestrict = await self.realdebrid.unrestrict_link(api_key, link)
                            if unrestrict.get("success"):
                                download_link = unrestrict.get("download")
                                file_name = unrestrict.get("filename", "file")
                                response += f"  📥 [{file_name}]({download_link})\n"
                        
                        if len(links) > 3:
                            response += f"  ... and {len(links) - 3} more files\n"
                    else:
                        # No links available yet, might still be processing
                        response += f"⏳ **{filename}** - Processing... (ID: `{torrent_id}`)\n"
                else:
                    # Show status for non-completed torrents
                    status_emoji = {
                        "downloading": "⏳",
                        "queued": "⏸️",
                        "magnet_conversion": "🔄",
                        "waiting_files_selection": "⏸️",
                        "error": "❌"
                    }.get(status, "📦")
                    
                    response += f"{status_emoji} **{filename}** - Status: `{status}`\n"
                
                response += "\n"
            
            if len(torrents) > 10:
                response += f"... and {len(torrents) - 10} more\n"
            
            return response
        else:
            return result.get("error", "❌ Unknown error occurred.")
    
    async def handle_magnet_info(self, sender: str, torrent_id: str, user_config: Optional[dict] = None) -> str:
        """Get information about a specific torrent or download.
        
        Usage: magnet-info <torrent_id>
        """
        if not torrent_id:
            return "Usage: `magnet-info <torrent_id>`"
        
        if not user_config:
            return "❌ Unable to load user configuration."
        
        api_key = user_config.get("realdebrid_api_key")
        
        if not api_key:
            return "❌ RealDebrid API key not configured."
        
        # First try to get it as a torrent
        result = await self.realdebrid.get_torrent_info(api_key, torrent_id)
        
        if result.get("success"):
            data = result.get("data", {})
            return (
                f"📋 **Torrent Info (ID: {torrent_id})**\n\n"
                f"• **Name:** {data.get('filename')}\n"
                f"• **Status:** {data.get('status')}\n"
                f"• **Progress:** {data.get('progress', 0)}%\n"
                f"• **Bytes:** {data.get('bytes', 0)}\n"
                f"• **Added:** {data.get('added_date')}"
            )
        
        # If not found in torrents, search in downloads
        downloads_result = await self.realdebrid.get_downloads(api_key)
        
        if downloads_result.get("success"):
            downloads = downloads_result.get("downloads", [])
            
            # Search for the torrent ID in downloads
            for download in downloads:
                download_id = download.get("id", "")
                # Compare both the full ID and the torrent ID if it exists
                if str(download_id) == torrent_id or download.get("torrent_id") == torrent_id:
                    return (
                        f"✅ **Download Ready (ID: {download_id})**\n\n"
                        f"• **Filename:** {download.get('filename')}\n"
                        f"• **Link:** {download.get('link')}\n"
                        f"• **Size:** {download.get('filesize', 0)} bytes\n"
                        f"• **Added:** {download.get('generated')}\n\n"
                        f"📥 **Direct Download:**\n{download.get('download')}"
                    )
        
        # Not found in either location
        error_msg = result.get("error", "❌ Unknown error occurred.")
        
        if "404" in error_msg:
            return (
                f"❌ **Torrent/Download not found** (ID: `{torrent_id}`)\n\n"
                f"Possible reasons:\n"
                f"• Torrent was deleted from RealDebrid\n"
                f"• ID is incorrect (check with `magnet-list`)\n"
                f"• Torrent expired or failed to add\n\n"
                f"Use `magnet-list` to see your active torrents and downloads."
            )
        
        return error_msg
    
    def generate_help(self, sender: str) -> str:
        """Generate help message showing available commands."""
        help_text = "**Available Commands:**\n\n"
        
        for cmd, config in sorted(self.commands.items()):
            # Check if user has permission
            allowed_users = config.get("allowed_users", [])
            if allowed_users and sender not in allowed_users:
                continue
            
            description = config.get("description", "No description")
            help_text += f"• `{cmd}` - {description}\n"
        
        help_text += "\n**AI Commands:**\n"
        help_text += "• Just send a message without `!` to chat with AI (if enabled for your user)\n"
        
        return help_text
    
    async def execute_script(self, script: str, args: str = "") -> str:
        """Execute a shell script/command and return the output."""
        try:
            # Combine script and args
            full_command = f"{script} {args}".strip()
            
            logger.info(f"Executing command: {full_command}")
            
            # Execute the command with timeout
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                process.kill()
                return "Error: Command execution timed out (30s)"
            
            # Format output
            output = ""
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                output += "\n[stderr]\n" + stderr.decode('utf-8', errors='replace')
            
            if not output:
                output = "Command executed successfully (no output)"
            
            # Limit output length
            max_length = 4000
            if len(output) > max_length:
                output = output[:max_length] + f"\n\n[Output truncated, {len(output) - max_length} characters omitted]"
            
            return f"```\n{output}\n```"
            
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return f"Error executing command: {str(e)}"
