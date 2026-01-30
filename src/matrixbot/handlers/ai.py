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
        
        # Initialize Groq client
        self.groq_clients = {}
    
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
                    "description": "CRITICAL: Use this tool IMMEDIATELY when the user asks you to send a message to someone. Do not ask for confirmation. Do not roleplay sending it. Call this tool to actually send the message.",
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
        base_system_prompt = trigger_config.get("system_prompt", "You are a helpful assistant.")
        
        # Append tool instructions to system prompt
        system_prompt = (
            f"{base_system_prompt}\n\n"
            "SYSTEM INSTRUCTIONS:\n"
            "You have access to a tool called 'send_message_on_behalf'. "
            "When the user asks you to tell something to someone or send a message, "
            "you MUST use this tool. Do not just say you will do it; actually call the tool. "
            "If the user provides a username like 'jaimeloncio74', pass it as 'jaimeloncio74' (without domain) "
            "or the full ID if provided. The tool will handle the delivery."
        )
        max_history = trigger_config.get("max_history", 10)
        
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            return f"⚠️ AI is enabled but no valid API key is configured for trigger '{trigger}'. Please contact the administrator."
        
        # Get AI provider
        ai_provider = user_config.get("ai", "aistudio")
        
        # Generate AI response
        try:
            if ai_provider == "groq":
                response_text = await self.generate_groq_response(
                    api_key=api_key,
                    model=model,
                    message=message,
                    system_prompt=system_prompt,
                    user_id=user_id,
                    trigger=trigger,
                    max_history=max_history
                )
            else:
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
            logger.error(f"Error generating AI response for {user_id} with trigger '{trigger}' (provider: {ai_provider}): {e}", exc_info=True)
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
            
            # Create model instance
            tools = self._send_message_tool()
            try:
                # Try to initialize with tools
                model_instance = genai.GenerativeModel(
                    model, 
                    tools=[tools],
                    system_instruction=system_prompt
                )
                # Test checking if model supports tools by accessing valid properties or just proceed
                # The error usually happens when we try to use it or if the API rejects the config
            except Exception:
                # Fallback to no tools if initialization fails immediately (unlikely)
                model_instance = genai.GenerativeModel(
                    model, 
                    system_instruction=system_prompt
                )
                tools = None  # Flag that tools are disabled

            # Retrieve history
            session_key = f"{user_id}:{trigger}"
            history_data = self.history.get(session_key, [])
            
            # Convert stored history to Gemini format
            chat_history = []
            
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
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(chat.send_message, message),
                        timeout=90.0
                    )
                except Exception as e:
                    # Check for "Function calling is not enabled" error
                    if "Function calling is not enabled" in str(e) or "400" in str(e):
                        logger.warning(f"Model {model} does not support function calling. Retrying without tools.")
                        # Re-initialize without tools
                        model_instance = genai.GenerativeModel(
                            model, 
                            system_instruction=system_prompt
                        )
                        chat = model_instance.start_chat(history=chat_history)
                        response = await asyncio.wait_for(
                            asyncio.to_thread(chat.send_message, message),
                            timeout=90.0
                        )
                    else:
                        raise e
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

    def _send_message_tool_groq(self):
        """Define the send_message tool for Groq (OpenAI format)."""
        return {
            "type": "function",
            "function": {
                "name": "send_message_on_behalf",
                "description": "CRITICAL: Use this tool IMMEDIATELY when the user asks you to send a message to someone. Do not ask for confirmation. Do not roleplay sending it. Call this tool to actually send the message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_username": {
                            "type": "string",
                            "description": "The username of the recipient (e.g., 'jaimeloncio74'). Do not include the domain if not provided."
                        },
                        "message_content": {
                            "type": "string",
                            "description": "The content of the message to send."
                        }
                    },
                    "required": ["target_username", "message_content"]
                }
            }
        }

    async def generate_groq_response(
        self,
        api_key: str,
        model: str,
        message: str,
        system_prompt: str,
        user_id: str,
        trigger: str,
        max_history: int
    ) -> str:
        """Generate a response using Groq API."""
        try:
            # Get or create client
            client = self.groq_clients.get(api_key)
            if not client:
                client = AsyncGroq(api_key=api_key)
                self.groq_clients[api_key] = client
            
            # Prepare messages
            session_key = f"{user_id}:{trigger}"
            history_data = self.history.get(session_key, [])
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Convert history to OpenAI format
            # Gemini history: [{"role": "user", "parts": [{"text": "..."}]}, ...]
            # OpenAI history: [{"role": "user", "content": "..."}, ...]
            for entry in history_data:
                role = entry.get("role")
                parts = entry.get("parts", [])
                
                # Map role 'model' -> 'assistant'
                if role == "model":
                    role = "assistant"
                
                # Extract text
                content = ""
                for part in parts:
                    if part.get("text"):
                        content += part.get("text")
                
                if content:
                    messages.append({"role": role, "content": content})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Truncate if needed (basic truncation)
            # Keeping system prompt + last N messages
            if len(messages) > max_history + 2:  # +2 for system and current
                 # Keep system prompt (index 0) and the last relevant messages
                 messages = [messages[0]] + messages[-(max_history + 1):]

            # Call API
            tools = [self._send_message_tool_groq()]
            
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=4096
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # Check for tool calls
            if tool_calls:
                # Append assistant's message with tool calls
                messages.append(response_message)
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool
                    tool_result = await self.execute_tool(function_name, function_args)
                    
                    # Append tool result
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result)
                    })
                
                # Get follow-up response
                second_response = await client.chat.completions.create(
                    model=model,
                    messages=messages
                )
                final_response_text = second_response.choices[0].message.content
            else:
                final_response_text = response_message.content
            
            # Strip <think> tags if present (common in models like DeepSeek/Qwen)
            import re
            final_response_text = re.sub(r'<think>.*?</think>', '', final_response_text, flags=re.DOTALL).strip()
            
            # Update history (save the new turn)
            # We map back to Gemini-like format for consistency in storage
            # 'assistant' -> 'model'
            
            # Adding user message
            new_entry_user = {"role": "user", "parts": [{"text": message}]}
            
            # Adding model response
            new_entry_model = {"role": "model", "parts": [{"text": final_response_text}]}
            
            history_data.append(new_entry_user)
            history_data.append(new_entry_model)
            
            # Truncate stored history
            if len(history_data) > max_history * 2:
                history_data = history_data[-(max_history * 2):]
            
            self.history[session_key] = history_data
            self.save_history()
            
            return final_response_text
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    def reload_users(self):
        """Reload user configurations from file."""
        self.load_users()
