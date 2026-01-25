"""
RealDebrid handler for the Matrix bot.
Manages magnet link uploads and interaction with RealDebrid API.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
import aiohttp

logger = logging.getLogger(__name__)


class RealDebridHandler:
    """Handler for RealDebrid API interactions."""
    
    BASE_URL = "https://api.real-debrid.com/rest/1.0"
    
    def __init__(self):
        """Initialize the RealDebrid handler."""
        pass
    
    async def add_magnet(self, api_key: str, magnet_link: str) -> Dict[str, Any]:
        """
        Add a magnet link to RealDebrid.
        
        Args:
            api_key: RealDebrid API token
            magnet_link: Magnet link URI
        
        Returns:
            Dictionary with result data or error information
        """
        if not api_key:
            return {
                "success": False,
                "error": "❌ No RealDebrid API key configured. Use `magnet-config <your_api_key>` first."
            }
        
        if not magnet_link.startswith("magnet:"):
            return {
                "success": False,
                "error": f"❌ Invalid magnet link format. Must start with 'magnet:'"
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                # First, get unrestricted link
                headers = {"Authorization": f"Bearer {api_key}"}
                data = aiohttp.FormData()
                data.add_field("magnet", magnet_link)
                
                async with session.post(
                    f"{self.BASE_URL}/torrents/addMagnet",
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result = await response.json()
                    
                    if response.status == 201:
                        torrent_id = result.get("id")
                        
                        # Wait and retry to get torrent info (magnet conversion takes time)
                        logger.info(f"Torrent {torrent_id} added, waiting for magnet processing...")
                        
                        max_retries = 10
                        retry_delay = 2
                        torrent_data = None
                        
                        for attempt in range(max_retries):
                            await asyncio.sleep(retry_delay)
                            
                            info_result = await self.get_torrent_info(api_key, torrent_id)
                            
                            if info_result.get("success"):
                                torrent_data = info_result.get("data", {})
                                status = torrent_data.get("status", "unknown")
                                
                                logger.info(f"Torrent {torrent_id} status: {status} (attempt {attempt + 1}/{max_retries})")
                                
                                # If status is not magnet_conversion, we can proceed
                                if status != "magnet_conversion":
                                    break
                            else:
                                logger.warning(f"Failed to get torrent info (attempt {attempt + 1}/{max_retries}): {info_result.get('error')}")
                        
                        if torrent_data:
                            files = torrent_data.get("files", [])
                            status = torrent_data.get("status", "unknown")
                            
                            logger.info(f"Torrent {torrent_id} final status: {status}, files: {len(files)}")
                            
                            # Only select files if status is waiting_files_selection
                            if status == "waiting_files_selection" and files:
                                # Get all file IDs
                                file_ids = ",".join(str(f["id"]) for f in files)
                                logger.info(f"Auto-selecting {len(files)} files for torrent {torrent_id}")
                                
                                select_result = await self.select_files(api_key, torrent_id, file_ids)
                                
                                if not select_result.get("success"):
                                    logger.warning(f"Failed to auto-select files: {select_result.get('error')}")
                                    return {
                                        "success": True,
                                        "torrent_id": torrent_id,
                                        "filename": result.get("filename"),
                                        "hash": result.get("hash"),
                                        "message": f"⚠️ Torrent added but auto-start failed. Use web interface to select files.",
                                        "needs_manual_selection": True
                                    }
                            elif status == "downloading" or status == "downloaded":
                                logger.info(f"Torrent {torrent_id} already started automatically")
                            else:
                                logger.warning(f"Torrent {torrent_id} in unexpected status: {status}")
                        else:
                            # Failed to get torrent info after all retries
                            logger.error(f"Failed to get torrent info after {max_retries} attempts")
                            return {
                                "success": True,
                                "torrent_id": torrent_id,
                                "filename": result.get("filename"),
                                "hash": result.get("hash"),
                                "message": f"⚠️ Torrent added but couldn't verify status. Check RealDebrid web interface.",
                                "needs_manual_selection": True
                            }
                        
                        return {
                            "success": True,
                            "torrent_id": torrent_id,
                            "filename": result.get("filename"),
                            "hash": result.get("hash"),
                            "message": f"✅ Torrent added and started! ID: {torrent_id}"
                        }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "❌ Invalid RealDebrid API key."
                        }
                    elif response.status == 400:
                        return {
                            "success": False,
                            "error": f"❌ Invalid request: {result.get('error', 'Unknown error')}"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"❌ Error ({response.status}): {result.get('error', 'Unknown error')}"
                        }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "❌ Request timeout (30s). RealDebrid API might be slow."
            }
        except aiohttp.ClientError as e:
            logger.error(f"RealDebrid client error: {e}")
            return {
                "success": False,
                "error": f"❌ Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error adding magnet to RealDebrid: {e}")
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    async def get_torrent_info(self, api_key: str, torrent_id: str) -> Dict[str, Any]:
        """
        Get information about a specific torrent.
        
        Args:
            api_key: RealDebrid API token
            torrent_id: Torrent ID
        
        Returns:
            Dictionary with torrent information
        """
        if not api_key:
            return {
                "success": False,
                "error": "❌ No RealDebrid API key configured."
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                
                async with session.get(
                    f"{self.BASE_URL}/torrents/info?id={torrent_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "data": result
                        }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "❌ Invalid RealDebrid API key."
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"❌ Error ({response.status})"
                        }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "❌ Request timeout"
            }
        except Exception as e:
            logger.error(f"Error getting torrent info: {e}")
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    async def list_torrents(self, api_key: str) -> Dict[str, Any]:
        """
        List all torrents for the API key owner.
        
        Args:
            api_key: RealDebrid API token
        
        Returns:
            Dictionary with list of torrents
        """
        if not api_key:
            return {
                "success": False,
                "error": "❌ No RealDebrid API key configured."
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                
                async with session.get(
                    f"{self.BASE_URL}/torrents",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "torrents": result,
                            "count": len(result)
                        }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "❌ Invalid RealDebrid API key."
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"❌ Error ({response.status})"
                        }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "❌ Request timeout"
            }
        except Exception as e:
            logger.error(f"Error listing torrents: {e}")
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    async def select_files(self, api_key: str, torrent_id: str, file_ids: str = "all") -> Dict[str, Any]:
        """
        Select files from a torrent to download.
        
        Args:
            api_key: RealDebrid API token
            torrent_id: Torrent ID
            file_ids: Comma-separated file IDs or "all" (default: "all")
        
        Returns:
            Dictionary with result
        """
        if not api_key:
            return {
                "success": False,
                "error": "❌ No RealDebrid API key configured."
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                data = aiohttp.FormData()
                data.add_field("files", file_ids)
                
                async with session.post(
                    f"{self.BASE_URL}/torrents/selectFiles/{torrent_id}",
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204:
                        return {
                            "success": True,
                            "message": "Files selected successfully"
                        }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "❌ Invalid RealDebrid API key."
                        }
                    else:
                        result = await response.json()
                        return {
                            "success": False,
                            "error": f"❌ Error ({response.status}): {result.get('error', 'Unknown error')}"
                        }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "❌ Request timeout"
            }
        except Exception as e:
            logger.error(f"Error selecting files: {e}")
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    async def get_torrent_downloads(self, api_key: str, torrent_id: str) -> Dict[str, Any]:
        """
        Get download links for a completed torrent.
        
        Args:
            api_key: RealDebrid API token
            torrent_id: Torrent ID
        
        Returns:
            Dictionary with download links
        """
        if not api_key:
            return {
                "success": False,
                "error": "❌ No RealDebrid API key configured."
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                
                async with session.get(
                    f"{self.BASE_URL}/torrents/info?id={torrent_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        torrent = await response.json()
                        
                        # If status is "downloaded", get the links
                        if torrent.get("status") == "downloaded":
                            # Extract links from torrent data
                            links = torrent.get("links", [])
                            return {
                                "success": True,
                                "status": "downloaded",
                                "links": links,
                                "filename": torrent.get("filename"),
                                "progress": torrent.get("progress")
                            }
                        else:
                            return {
                                "success": True,
                                "status": torrent.get("status"),
                                "progress": torrent.get("progress", 0),
                                "links": []
                            }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "❌ Invalid RealDebrid API key."
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"❌ Error ({response.status})"
                        }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "❌ Request timeout"
            }
        except Exception as e:
            logger.error(f"Error getting torrent downloads: {e}")
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    async def unrestrict_link(self, api_key: str, link: str) -> Dict[str, Any]:
        """
        Get unrestricted download link from RealDebrid link.
        
        Args:
            api_key: RealDebrid API token
            link: RealDebrid link
        
        Returns:
            Dictionary with unrestricted download link
        """
        if not api_key:
            return {
                "success": False,
                "error": "❌ No RealDebrid API key configured."
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                data = aiohttp.FormData()
                data.add_field("link", link)
                
                async with session.post(
                    f"{self.BASE_URL}/unrestrict/link",
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "download": result.get("download"),
                            "filename": result.get("filename"),
                            "filesize": result.get("filesize")
                        }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "❌ Invalid RealDebrid API key."
                        }
                    else:
                        result = await response.json()
                        return {
                            "success": False,
                            "error": f"❌ Error ({response.status}): {result.get('error', 'Unknown')}"
                        }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "❌ Request timeout"
            }
        except Exception as e:
            logger.error(f"Error unrestricting link: {e}")
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    async def get_downloads(self, api_key: str) -> Dict[str, Any]:
        """
        Get user downloads list.
        
        Args:
            api_key: RealDebrid API token
        
        Returns:
            Dictionary with downloads list
        """
        if not api_key:
            return {
                "success": False,
                "error": "❌ No RealDebrid API key configured."
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                
                async with session.get(
                    f"{self.BASE_URL}/downloads",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "downloads": result
                        }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "❌ Invalid RealDebrid API key."
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"❌ Error ({response.status})"
                        }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "❌ Request timeout"
            }
        except Exception as e:
            logger.error(f"Error getting downloads: {e}")
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
