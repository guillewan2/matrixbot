"""
Login monitor for system authentication logs.
Monitors /var/log/auth.log for SSH logins and sudo commands.
"""

import asyncio
import re
import logging
import os
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class LoginMonitor:
    """Monitors system auth logs for login events."""
    
    def __init__(self, log_file: str = "/var/log/auth.log"):
        """
        Initialize the login monitor.
        
        Args:
            log_file: Path to auth log file (default: /var/log/auth.log)
        """
        self.log_file = log_file
        self.callback = None
        self.monitor_task = None
        self.last_position = 0
        self.last_inode = None  # Track inode to detect file rotation
        
        # Regex patterns for different login types
        self.patterns = {
            "ssh_success": re.compile(r"sshd\[\d+\]: Accepted .+ for (\S+) from (\S+) port (\d+)"),
            "ssh_failed": re.compile(r"sshd\[\d+\]: Failed .+ for (?:invalid user )?(\S+) from (\S+) port (\d+)"),
            "sudo_command": re.compile(r"sudo:\s+(\S+)\s+:.*COMMAND=(.+)"),
            "session_opened": re.compile(r"systemd-logind\[\d+\]: New session .+ of user (\S+)"),
        }
    
    def set_callback(self, callback: Callable):
        """
        Set the callback function to call when login detected.
        
        Args:
            callback: Async function to call with (event_type, user, details)
        """
        self.callback = callback
    
    async def start_monitoring(self):
        """Start monitoring the auth log file."""
        logger.info(f"Starting login monitor on {self.log_file}")
        
        # Get initial file position and inode
        try:
            stat_info = os.stat(self.log_file)
            self.last_inode = stat_info.st_ino
            
            with open(self.log_file, 'r') as f:
                f.seek(0, 2)  # Seek to end
                self.last_position = f.tell()
                logger.info(f"Starting from position {self.last_position}, inode {self.last_inode}")
        except Exception as e:
            logger.error(f"Failed to initialize log monitoring for {self.log_file}: {e}")
            return
        
        while True:
            try:
                await self._check_new_lines()
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                logger.error(f"Error in login monitor loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_new_lines(self):
        """Check for new lines in the log file."""
        try:
            # Get current inode to detect file rotation
            try:
                stat_info = os.stat(self.log_file)
                current_inode = stat_info.st_ino
                
                # File was rotated (inode changed)
                if self.last_inode is not None and current_inode != self.last_inode:
                    logger.warning(f"Log file rotation detected! Old inode: {self.last_inode}, New inode: {current_inode}")
                    self.last_inode = current_inode
                    self.last_position = 0  # Reset position to start reading from beginning
                else:
                    self.last_inode = current_inode
            except FileNotFoundError:
                logger.error(f"Log file {self.log_file} not found!")
                return
            
            with open(self.log_file, 'r') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
                
                for line in new_lines:
                    await self._process_line(line)
        
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
    
    async def _process_line(self, line: str):
        """Process a log line and detect login events."""
        if not self.callback:
            return
        
        # Check SSH successful login
        match = self.patterns["ssh_success"].search(line)
        if match:
            user = match.group(1)
            ip = match.group(2)
            port = match.group(3)
            
            await self.callback(
                event_type="ssh_login",
                user=user,
                details={
                    "ip": ip,
                    "port": port,
                    "status": "success",
                    "timestamp": self._extract_timestamp(line)
                }
            )
            return
        
        # Check SSH failed login
        match = self.patterns["ssh_failed"].search(line)
        if match:
            user = match.group(1)
            ip = match.group(2)
            port = match.group(3)
            
            await self.callback(
                event_type="ssh_failed",
                user=user,
                details={
                    "ip": ip,
                    "port": port,
                    "status": "failed",
                    "timestamp": self._extract_timestamp(line)
                }
            )
            return
        
        # Check sudo command
        match = self.patterns["sudo_command"].search(line)
        if match:
            user = match.group(1)
            command = match.group(2)
            
            await self.callback(
                event_type="sudo_command",
                user=user,
                details={
                    "command": command,
                    "timestamp": self._extract_timestamp(line)
                }
            )
            return
        
        # Check systemd session (console login)
        match = self.patterns["session_opened"].search(line)
        if match:
            user = match.group(1)
            
            # Only report for non-system users
            if user not in ["root", "gdm", "lightdm"]:
                await self.callback(
                    event_type="console_login",
                    user=user,
                    details={
                        "timestamp": self._extract_timestamp(line)
                    }
                )
    
    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp from log line."""
        # auth.log format: Nov  7 17:00:00
        try:
            parts = line.split()
            if len(parts) >= 3:
                month = parts[0]
                day = parts[1]
                time = parts[2]
                year = datetime.now().year
                return f"{year}-{month}-{day} {time}"
        except:
            pass
        return datetime.now().isoformat()
    
    async def stop_monitoring(self):
        """Stop the monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            logger.info("Login monitor stopped")
