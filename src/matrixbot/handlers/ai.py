"""
AI handler for the Matrix bot using Google Gemini.
Each user can have their own API key and preferred model.
"""

import json
import logging
import os
from typing import Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AIHandler:
    def __init__(self, config_file: str = "config/users.json"):
        """Initialize the AI handler."""
        self.config_file = config_file
        self.users = {}
        self.load_users()
    
    def load_users(self):
        """Load user configurations from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.users = data.get("users", {})
                logger.info(f"Loaded {len(self.users)} users from {self.config_file}")
        except FileNotFoundError:
            logger.warning(f"Users file {self.config_file} not found. Creating default...")
            self.create_default_config()
            self.load_users()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing {self.config_file}: {e}")
            self.users = {}
    
    def create_default_config(self):
        """Create a default users configuration file."""
        default_config = {
            "users": {
                "@admin:matrix.example.com": {
                    "ai_enabled": True,
                    "triggers": {
                        "subaru": {
                            "api_key": "YOUR_GEMINI_API_KEY_HERE",
                            "model": "gemini-2.5-flash",
                            "system_prompt": "You are Natsuki Subaru from Re:Zero.",
                            "max_history": 10
                        },
                        "!prompt": {
                            "api_key": "YOUR_GEMINI_API_KEY_HERE",
                            "model": "gemini-2.0-flash-exp",
                            "system_prompt": "You are a helpful assistant.",
                            "max_history": 5
                        }
                    }
                },
                "@user:matrix.example.com": {
                    "ai_enabled": True,
                    "triggers": {
                        "subaru": {
                            "api_key": "ANOTHER_GEMINI_API_KEY",
                            "model": "gemini-1.5-flash",
                            "system_prompt": "You are a friendly assistant.",
                            "max_history": 5
                        }
                    }
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        logger.info(f"Created default users config at {self.config_file}")
    
    def get_user_config(self, user_id: str) -> Optional[dict]:
        """Get configuration for a specific user."""
        return self.users.get(user_id)
    
    def is_ai_enabled(self, user_id: str) -> bool:
        """Check if AI is enabled for a user."""
        user_config = self.get_user_config(user_id)
        if not user_config:
            return False
        return user_config.get("ai_enabled", False)
    
    async def handle_message(self, user_id: str, message: str, trigger: str = "subaru") -> Optional[str]:
        """Handle an AI message from a user with a specific trigger."""
        # Check if user has AI enabled
        if not self.is_ai_enabled(user_id):
            return None  # Don't respond if AI is not enabled
        
        user_config = self.get_user_config(user_id)
        if not user_config:
            return None
        
        # Get trigger configuration
        triggers = user_config.get("triggers", {})
        trigger_config = triggers.get(trigger)
        
        if not trigger_config:
            return f"⚠️ Trigger '{trigger}' no configurado para tu usuario."
        
        # Get trigger-specific API key (each trigger can have its own key)
        api_key = trigger_config.get("api_key")
        
        # Fallback to user-level API key if trigger doesn't have one
        if not api_key:
            api_key = user_config.get("api_key")
        
        # Get trigger-specific configuration
        model = trigger_config.get("model", "gemini-2.0-flash-exp")
        system_prompt = trigger_config.get("system_prompt", "You are a helpful assistant.")
        
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            return f"⚠️ AI is enabled but no valid API key is configured for trigger '{trigger}'. Please contact the administrator."
        
        # Generate AI response
        try:
            response_text = await self.generate_ai_response(
                api_key=api_key,
                model=model,
                message=message,
                system_prompt=system_prompt
            )
            return response_text
        except Exception as e:
            logger.error(f"Error generating AI response for {user_id} with trigger '{trigger}': {e}")
            return f"❌ Error generating AI response: {str(e)}"
    
    async def generate_ai_response(
        self,
        api_key: str,
        model: str,
        message: str,
        system_prompt: str
    ) -> str:
        """Generate a response using Google Gemini API with timeout."""
        import asyncio
        
        try:
            # Configure API key
            genai.configure(api_key=api_key)
            
            # Create model instance
            model_instance = genai.GenerativeModel(model)
            
            # Prepare the full prompt with system instructions
            full_message = f"{system_prompt}\n\nUser: {message}"
            
            # Generate content with timeout (90 seconds max)
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        model_instance.generate_content,
                        full_message
                    ),
                    timeout=90.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Gemini API timeout after 90 seconds")
                return "⏱️ La respuesta de la IA tardó demasiado (>90 segundos). Por favor, intenta con una pregunta más simple."
            
            # Extract text from response
            if hasattr(response, 'text'):
                return response.text
            else:
                logger.error(f"Unexpected response format: {response}")
                return "Error: Unexpected response format from AI"
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def reload_users(self):
        """Reload user configurations from file."""
        self.load_users()
