"""
AI handler for the Matrix bot using Google Gemini.
Each user can have their own API key and preferred model.
"""

import json
import logging
import os
import asyncio
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

logger = logging.getLogger(__name__)


class AIHandler:
    def __init__(self, config_file: str = "config/users.json", send_message_callback: Optional[Callable] = None):
        """Initialize the AI handler."""
        self.config_file = config_file
        self.send_message_callback = send_message_callback
        self.users = {}
        self.history_file = Path("store/ai_history.json")
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        
        self.load_users()
        self.load_history()
    
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
            
    def load_history(self):
        """Load conversation history from JSON file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                logger.info(f"Loaded AI history for {len(self.history)} sessions")
            else:
                self.history = {}
        except Exception as e:
            logger.error(f"Error loading AI history: {e}")
            self.history = {}

    def save_history(self):
        """Save conversation history to JSON file."""
        try:
            # Ensure store directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving AI history: {e}")
    
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
    
    def _send_message_tool(self):
        """Define the send_message tool for Gemini."""
        return {
            "function_declarations": [
                {
                    "name": "send_message_on_behalf",
                    "description": "Send a message to another user on behalf of the current user. Use this when the user asks you to tell something to someone else.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "target_username": {
                                "type": "STRING",
                                "description": "The username of the recipient (e.g., 'jaimeloncio74'). Do not include the domain if not provided."
                            },
                            "message_content": {
                                "type": "STRING",
                                "description": "The content of the message to send."
                            }
                        },
                        "required": ["target_username", "message_content"]
                    }
                }
            ]
        }

    async def execute_tool(self, tool_name: str, args: dict) -> dict:
        """Execute a tool called by the AI."""
        if tool_name == "send_message_on_behalf":
            target_username = args.get("target_username")
            message_content = args.get("message_content")
            
            if not target_username or not message_content:
                return {"error": "Missing arguments"}
            
            # Construct full user ID if domain is missing
            if ":" not in target_username:
                target_user_id = f"@{target_username}:matrix.nasfurui.cat"
            else:
                target_user_id = target_username
                
            logger.info(f"Tool execution: Sending message to {target_user_id}: {message_content}")
            
            if self.send_message_callback:
                try:
                    # Send the message
                    await self.send_message_callback(target_user_id, message_content)
                    return {"status": "success", "message": f"Message sent to {target_user_id}"}
                except Exception as e:
                    logger.error(f"Failed to send message via tool: {e}")
                    return {"status": "error", "message": f"Failed to send message: {str(e)}"}
            else:
                return {"status": "error", "message": "Send message callback not configured"}
        
        return {"error": f"Unknown tool: {tool_name}"}

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
        max_history = trigger_config.get("max_history", 10)
        
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            return f"⚠️ AI is enabled but no valid API key is configured for trigger '{trigger}'. Please contact the administrator."
        
        # Generate AI response
        try:
            response_text = await self.generate_ai_response(
                api_key=api_key,
                model=model,
                message=message,
                system_prompt=system_prompt,
                user_id=user_id,
                trigger=trigger,
                max_history=max_history
            )
            return response_text
        except Exception as e:
            logger.error(f"Error generating AI response for {user_id} with trigger '{trigger}': {e}", exc_info=True)
            return f"❌ Error generating AI response: {str(e)}"
    
    async def generate_ai_response(
        self,
        api_key: str,
        model: str,
        message: str,
        system_prompt: str,
        user_id: str,
        trigger: str,
        max_history: int
    ) -> str:
        """Generate a response using Google Gemini API with memory and tools."""
        
        try:
            # Configure API key
            genai.configure(api_key=api_key)
            
            # Create model instance with tools
            tools = self._send_message_tool()
            model_instance = genai.GenerativeModel(model, tools=[tools])
            
            # Retrieve history
            session_key = f"{user_id}:{trigger}"
            history_data = self.history.get(session_key, [])
            
            # Convert stored history to Gemini format
            chat_history = []
            
            # Add system prompt as the first part of history if possible, 
            # or just prepend it to the context. 
            # Gemini python SDK handles system instructions in the model config usually,
            # but here we can just rely on the chat session.
            # Ideally, we should set system_instruction on GenerativeModel if supported,
            # but let's stick to the prompt context or history.
            
            # Note: Gemini 1.5+ supports system_instruction in constructor.
            # We will try to use it if we re-instantiate, but we are doing it per request.
            model_instance = genai.GenerativeModel(
                model, 
                tools=[tools],
                system_instruction=system_prompt
            )
            
            # Convert history
            for entry in history_data:
                role = entry.get("role")
                parts = entry.get("parts", [])
                if role and parts:
                    chat_history.append({"role": role, "parts": parts})
            
            # Start chat session
            chat = model_instance.start_chat(history=chat_history)
            
            # Send message with timeout
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(chat.send_message, message),
                    timeout=90.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Gemini API timeout after 90 seconds")
                return "⏱️ La respuesta de la IA tardó demasiado (>90 segundos)."

            # Handle tool calls
            final_response_text = ""
            
            # Loop to handle multiple tool calls if needed (though usually one turn)
            # Gemini SDK automatically handles the turn structure if we use chat.
            # We need to check if the response contains a function call.
            
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if fn := part.function_call:
                        # Execute tool
                        tool_name = fn.name
                        tool_args = dict(fn.args)
                        
                        tool_result = await self.execute_tool(tool_name, tool_args)
                        
                        # Send result back to model
                        try:
                            response = await asyncio.wait_for(
                                asyncio.to_thread(
                                    chat.send_message,
                                    genai.protos.Content(
                                        parts=[genai.protos.Part(
                                            function_response=genai.protos.FunctionResponse(
                                                name=tool_name,
                                                response=tool_result
                                            )
                                        )]
                                    )
                                ),
                                timeout=90.0
                            )
                        except asyncio.TimeoutError:
                             return "⏱️ Timeout waiting for tool confirmation."

            # Get final text response
            if response.text:
                final_response_text = response.text
            
            # Update history
            # We need to serialize the chat history for storage
            # chat.history contains the full history including the new exchange
            new_history = []
            for event in chat.history:
                # Serialize parts
                parts_data = []
                for part in event.parts:
                    if part.text:
                        parts_data.append({"text": part.text})
                    # We skip function calls/responses in stored history to keep it simple for now,
                    # or we can store them if we want full fidelity.
                    # For simple text memory, text is enough.
                    # If we strip function calls, we might break context for the model next time.
                    # Let's try to store text only for now to avoid complex serialization of protobufs.
                
                if parts_data:
                    new_history.append({
                        "role": event.role,
                        "parts": parts_data
                    })
            
            # Truncate history
            if len(new_history) > max_history * 2:  # *2 because user+model = 1 turn
                new_history = new_history[-(max_history * 2):]
            
            self.history[session_key] = new_history
            self.save_history()
            
            return final_response_text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise

    def reload_users(self):
        """Reload user configurations from file."""
        self.load_users()
