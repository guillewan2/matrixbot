"""
Download monitor for RealDebrid torrents.
Polls torrent status and notifies when downloads complete.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from ..handlers.realdebrid import RealDebridHandler

logger = logging.getLogger(__name__)


class DownloadMonitor:
    """Monitors RealDebrid downloads and sends notifications."""
    
    def __init__(self):
        """Initialize the download monitor."""
        self.realdebrid = RealDebridHandler()
        self.active_torrents: Dict[str, Dict[str, Any]] = {}
        self.monitor_task = None
    
    def add_torrent(self, user_id: str, room_id: str, torrent_id: str, api_key: str, filename: str):
        """
        Register a torrent for monitoring.
        
        Args:
            user_id: Matrix user ID who requested the download
            room_id: Matrix room ID where to send the notification
            torrent_id: RealDebrid torrent ID
            api_key: RealDebrid API key
            filename: Torrent filename for reference
        """
        key = f"{user_id}_{torrent_id}"
        self.active_torrents[key] = {
            "user_id": user_id,
            "room_id": room_id,
            "torrent_id": torrent_id,
            "api_key": api_key,
            "filename": filename,
            "status": "downloading",
            "progress": 0,
            "links": [],
            "notified": False
        }
        logger.info(f"Registered torrent {torrent_id} for monitoring (user: {user_id})")
    
    async def start_monitoring(self, callback: Callable):
        """
        Start the monitoring loop.
        
        Args:
            callback: Async function to call when a download completes.
                     Should accept (user_id, room_id, torrent_data) as arguments
        """
        logger.info("Starting download monitor...")
        
        while True:
            try:
                # Check all active torrents
                completed = []
                failed = []
                
                for key, torrent_data in list(self.active_torrents.items()):
                    result = await self.realdebrid.get_torrent_downloads(
                        torrent_data["api_key"],
                        torrent_data["torrent_id"]
                    )
                    
                    if not result.get("success"):
                        error_msg = result.get('error', '')
                        
                        # If torrent not found (404), remove it from monitoring
                        if '404' in error_msg:
                            logger.warning(f"Torrent {key} not found (404), removing from monitoring")
                            failed.append(key)
                            continue
                        
                        logger.warning(f"Failed to check torrent {key}: {error_msg}")
                        continue
                    
                    # Update status
                    status = result.get("status", "unknown")
                    progress = result.get("progress", 0)
                    links = result.get("links", [])
                    
                    torrent_data["status"] = status
                    torrent_data["progress"] = progress
                    torrent_data["links"] = links
                    
                    # Log progress
                    logger.debug(f"Torrent {key}: {status} ({progress}%)")
                    
                    # Check if download is complete
                    if status == "downloaded" and not torrent_data["notified"]:
                        logger.info(f"Torrent {key} completed!")
                        torrent_data["notified"] = True
                        completed.append(key)
                        
                        # Call the callback
                        try:
                            await callback(
                                user_id=torrent_data["user_id"],
                                room_id=torrent_data["room_id"],
                                torrent_data=torrent_data
                            )
                        except Exception as e:
                            logger.error(f"Error in completion callback: {e}")
                
                # Remove completed torrents
                for key in completed:
                    del self.active_torrents[key]
                    logger.info(f"Removed completed torrent {key} from monitoring")
                
                # Remove failed/not found torrents
                for key in failed:
                    del self.active_torrents[key]
                    logger.info(f"Removed failed torrent {key} from monitoring")
                
                # Wait before next check (30 seconds)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
    
    def get_active_torrents_count(self) -> int:
        """Get number of currently monitored torrents."""
        return len(self.active_torrents)
    
    def get_torrent_status(self, user_id: str, torrent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific torrent."""
        key = f"{user_id}_{torrent_id}"
        return self.active_torrents.get(key)
