"""D-Bus service interface for henzai.

Provides the main communication layer between the GNOME Shell extension
and the Python daemon.
"""

import logging
from dasbus.connection import SessionMessageBus
from dasbus.server.interface import dbus_interface, dbus_signal
from dasbus.typing import Str
import json
from gi.repository import GLib
from .tools import ToolExecutor

logger = logging.getLogger(__name__)

# D-Bus service information
SERVICE_NAME = "org.gnome.henzai"
OBJECT_PATH = "/org/gnome/henzai"


@dbus_interface(SERVICE_NAME)
class henzaiService:
    """henzai D-Bus service implementation."""
    
    def __init__(self, llm_client, memory_store):
        """
        Initialize the henzai service.
        
        Args:
            llm_client: LLM client instance for AI inference
            memory_store: Memory store for conversation history
        """
        self.llm = llm_client
        self.memory = memory_store
        self.tool_executor = ToolExecutor()
        self.status = "initializing"
        self._stop_generation = False  # Flag for stopping generation
        self._current_generation_id = None  # Track current generation
        
        # Cache for Ramalama status checks to reduce HTTP overhead
        self._ramalama_status_cache = None
        self._ramalama_status_cache_time = 0
        self._ramalama_status_cache_ttl = 2.0  # Cache for 2 seconds
        
        # Register the service on D-Bus
        self.bus = SessionMessageBus()
        self.bus.publish_object(OBJECT_PATH, self)
        self.bus.register_service(SERVICE_NAME)
        
        self.status = "ready"
        logger.info(f"D-Bus service registered: {SERVICE_NAME}")
    
    def SendMessage(self, message: str) -> str:
        """
        Process a user message and return AI response.
        
        This is the main entry point for chat interactions. The flow is:
        1. Store user message in memory
        2. Get conversation context
        3. Send to LLM with available tools
        4. Check if LLM wants to call a tool
        5. Execute tool if needed
        6. Get final response from LLM
        7. Store response in memory
        8. Return to user
        
        Args:
            message: User's input message
            
        Returns:
            AI assistant's response
        """
        try:
            self.status = "thinking"
            logger.info(f"Received message: {message[:50]}...")
            
            # Get conversation context from memory
            context = self.memory.get_recent_context(limit=10)
            
            # First LLM call - check if action needed
            response = self.llm.generate_response(message, context)
            
            # Check if response contains tool calls
            tool_calls = self._extract_tool_calls(response)
            
            if tool_calls:
                logger.info(f"Executing {len(tool_calls)} tool call(s)")
                
                # Execute tools and collect results
                tool_results = []
                for tool_call in tool_calls:
                    result = self._execute_tool(tool_call)
                    tool_results.append(result)
                
                # Send tool results back to LLM for final response
                final_response = self.llm.generate_with_tool_results(
                    message, tool_results, context
                )
            else:
                final_response = response
            
            # Store conversation in memory
            self.memory.add_conversation(message, final_response)
            
            self.status = "ready"
            logger.info("Response generated successfully")
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            self.status = "error"
            return f"Sorry, I encountered an error: {str(e)}"
    
    def GetStatus(self) -> str:
        """
        Get the current status of the daemon and Ramalama.
        
        Returns:
            JSON string with:
            - daemon_status: "ready", "thinking", "error"
            - ramalama_status: "ready", "loading", "unavailable", "not_installed"
            - ramalama_message: Human-readable status message
            - ready: Boolean indicating if system is ready
        """
        import requests
        import time
        import subprocess
        
        # Check cache first to avoid excessive HTTP requests
        current_time = time.time()
        if (self._ramalama_status_cache is not None and 
            current_time - self._ramalama_status_cache_time < self._ramalama_status_cache_ttl):
            # Return cached status
            cached_status = self._ramalama_status_cache.copy()
            cached_status["daemon_status"] = self.status
            cached_status["ready"] = self.status == "ready" and cached_status["ramalama_status"] == "ready"
            import json
            return json.dumps(cached_status)
        
        # Check Ramalama availability (not cached or cache expired)
        ramalama_status = "unavailable"
        ramalama_message = ""
        
        # First, check if Ramalama service exists and is active
        try:
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', 'ramalama.service'],
                capture_output=True,
                text=True,
                timeout=1
            )
            service_active = result.stdout.strip() == 'active'
            
            if not service_active:
                # Service not running - check why
                state_result = subprocess.run(
                    ['systemctl', '--user', 'show', 'ramalama.service', '-p', 'ActiveState,SubState'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if 'ActiveState=failed' in state_result.stdout:
                    ramalama_status = "error"
                    ramalama_message = "Ramalama service failed to start"
                elif 'ActiveState=inactive' in state_result.stdout:
                    ramalama_status = "not_started"
                    ramalama_message = "Ramalama service is not running. Start it with: systemctl --user start ramalama.service"
                else:
                    ramalama_status = "starting"
                    ramalama_message = "Ramalama service is starting..."
            else:
                # Service is active, check if API is ready
                try:
                    # Check /health endpoint (using 127.0.0.1 to avoid IPv6 issues with pasta)
                    health_response = requests.get(
                        f"{self.llm.api_url}/health",
                        timeout=2
                    )
                    if health_response.status_code == 200 and health_response.json().get('status') == 'ok':
                        # Health OK - model is loaded and ready
                        ramalama_status = "ready"
                        ramalama_message = "Model loaded and ready"
                    else:
                        ramalama_status = "loading"
                        ramalama_message = "Service starting, model loading..."
                except requests.exceptions.ConnectionError:
                    # Service running but API not responding yet (model still loading)
                    ramalama_status = "loading"
                    ramalama_message = "Loading model into memory (large models take 2-3 minutes)..."
                except requests.exceptions.Timeout:
                    ramalama_status = "slow"
                    ramalama_message = "Ramalama is slow to respond"
                except Exception as e:
                    ramalama_status = "error"
                    ramalama_message = f"API error: {str(e)}"
                    
        except FileNotFoundError:
            ramalama_status = "not_installed"
            ramalama_message = "Ramalama service not found. Install with: sudo dnf install ramalama"
        except subprocess.TimeoutExpired:
            ramalama_status = "error"
            ramalama_message = "Failed to check service status (timeout)"
        except Exception as e:
            ramalama_status = "error"
            ramalama_message = f"System error: {str(e)}"
        
        # Cache the ramalama status portion
        self._ramalama_status_cache = {
            "ramalama_status": ramalama_status,
            "ramalama_message": ramalama_message
        }
        self._ramalama_status_cache_time = current_time
        
        # Build status response
        status_data = {
            "daemon_status": self.status,
            "ramalama_status": ramalama_status,
            "ramalama_message": ramalama_message,
            "ready": self.status == "ready" and ramalama_status == "ready"
        }
        
        import json
        return json.dumps(status_data)
    
    def ClearHistory(self) -> None:
        """Clear conversation history."""
        try:
            self.memory.clear_history()
            logger.info("Conversation history cleared")
            # Emit signal to notify UI
            def emit():
                try:
                    self.HistoryCleared()
                    logger.info("HistoryCleared signal emitted")
                except Exception as e:
                    logger.error(f"Error emitting HistoryCleared: {e}", exc_info=True)
                return False
            GLib.idle_add(emit)
        except Exception as e:
            logger.error(f"Error clearing history: {e}", exc_info=True)
    
    def NewConversation(self) -> str:
        """
        Start a new conversation.
        Clears current context without deleting history.
        
        Returns:
            Status message
        """
        try:
            # Note: This clears all history. In future, could save current conversation
            # and start fresh without losing old chats
            self.memory.clear_history()
            logger.info("Started new conversation")
            # Emit signal to notify UI
            def emit():
                try:
                    self.HistoryCleared()
                    logger.info("HistoryCleared signal emitted")
                except Exception as e:
                    logger.error(f"Error emitting HistoryCleared: {e}", exc_info=True)
                return False
            GLib.idle_add(emit)
            return "New conversation started"
        except Exception as e:
            logger.error(f"Error starting new conversation: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    def ListModels(self) -> str:
        """
        List available models from Ramalama.
        
        Returns:
            JSON string containing list of models with metadata
        """
        try:
            logger.info("ListModels called")
            models = self.llm.list_available_models()
            logger.info(f"Returning {len(models)} models")
            return json.dumps(models)
        except Exception as e:
            logger.error(f"Error listing models: {e}", exc_info=True)
            return json.dumps([])
    
    def SetModel(self, model_id: str) -> str:
        """
        Change the current LLM model and restart Ramalama.
        
        This method:
        1. Updates the Ramalama systemd service with the new model
        2. Reloads systemd
        3. Restarts the Ramalama service
        
        Args:
            model_id: Full model ID to switch to (e.g., "llama3.2", "deepseek-r1")
            
        Returns:
            Status message
        """
        try:
            import subprocess
            import os
            
            old_model = self.llm.model
            self.llm.model = model_id
            logger.info(f"Model change requested: {old_model} → {model_id}")
            
            # Update reasoning mode based on new model capabilities
            if self.llm.supports_reasoning():
                self.llm.reasoning_enabled = True
                logger.info(f"Reasoning mode enabled for {model_id}")
            else:
                self.llm.reasoning_enabled = False
                logger.info(f"Reasoning mode disabled for {model_id}")
            
            # Path to ramalama service file
            service_file = os.path.expanduser("~/.config/systemd/user/ramalama.service")
            
            # Check if service file exists
            if not os.path.exists(service_file):
                logger.warning(f"Service file not found: {service_file}")
                return f"Model preference set to {model_id}, but could not update Ramalama service. Please restart manually."
            
            # Read current service file
            with open(service_file, 'r') as f:
                service_content = f.read()
            
            # Update the ExecStart line with new model
            # Format: ollama://library/MODEL:latest or just MODEL
            if '://' in model_id:
                # Already has full format (e.g., "ollama://library/deepseek-r1:latest")
                model_spec = model_id
            elif '/' in model_id and not model_id.startswith('ollama://'):
                # Has library/ prefix but no ollama:// (e.g., "library/deepseek-r1")
                model_spec = f"ollama://{model_id}:latest" if ':latest' not in model_id else f"ollama://{model_id}"
            else:
                # Simple model name (e.g., "llama3.2")
                model_spec = f"ollama://library/{model_id}:latest" if ':latest' not in model_id else f"ollama://library/{model_id}"
            
            # Replace the model in ExecStart line
            import re
            new_content = re.sub(
                r'(ExecStart=.*ramalama serve.*?)(ollama://[^\s]+|[a-zA-Z0-9._-]+:latest)',
                rf'\1{model_spec}',
                service_content
            )
            
            # Write updated service file
            with open(service_file, 'w') as f:
                f.write(new_content)
            
            logger.info(f"Updated service file with model: {model_spec}")
            
            # Reload systemd and restart ramalama
            try:
                # Reload systemd daemon
                subprocess.run(
                    ['systemctl', '--user', 'daemon-reload'],
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                
                # Restart ramalama service
                subprocess.run(
                    ['systemctl', '--user', 'restart', 'ramalama'],
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                
                logger.info(f"Ramalama service restarted with model: {model_id}")
                
                # Invalidate status cache to force fresh check
                self._ramalama_status_cache = None
                self._ramalama_status_cache_time = 0
                
                # Emit signal to notify UI
                def emit():
                    try:
                        self.ModelChanged(model_id)
                        logger.info(f"ModelChanged signal emitted: {model_id}")
                    except Exception as e:
                        logger.error(f"Error emitting ModelChanged: {e}", exc_info=True)
                    return False
                GLib.idle_add(emit)
                return f"Model changed to {model_id} and Ramalama restarted successfully"
                
            except subprocess.TimeoutExpired:
                logger.error("Timeout while restarting Ramalama")
                return f"Model updated but restart timed out. Check: systemctl --user status ramalama"
            except subprocess.CalledProcessError as e:
                logger.error(f"Error restarting Ramalama: {e.stderr}")
                return f"Model updated but restart failed: {e.stderr.decode()}"
                
        except Exception as e:
            logger.error(f"Error setting model: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    def GetCurrentModel(self) -> str:
        """
        Get the currently active model.
        
        Returns:
            Current model ID
        """
        logger.info(f"GetCurrentModel called, returning: {self.llm.model}")
        return self.llm.model
    
    def SupportsReasoning(self) -> bool:
        """
        Check if the current model supports reasoning/thinking mode.
        
        Returns:
            True if model supports reasoning
        """
        return self.llm.supports_reasoning()
    
    def GetReasoningEnabled(self) -> bool:
        """
        Check if reasoning mode is currently enabled.
        
        Returns:
            True if reasoning is enabled
        """
        return self.llm.reasoning_enabled
    
    def SetReasoningEnabled(self, enabled: bool) -> str:
        """
        Enable or disable reasoning mode.
        
        NOTE: Currently not functional due to Ramalama limitation.
        Reasoning is always enabled for reasoning-capable models until Ramalama
        implements --reasoning-budget support.
        See: https://github.com/containers/ramalama/issues/XXX
        TODO: Implement proper control once Ramalama adds --reasoning-budget
        
        Args:
            enabled: Whether to enable reasoning (currently ignored)
            
        Returns:
            Status message
        """
        # For now, just update the daemon state (though it's not actually used)
        self.llm.reasoning_enabled = enabled
        logger.info(f"Reasoning mode toggle requested: {'enabled' if enabled else 'disabled'} (not functional yet)")
        
        # Emit signal to notify UI (for consistency)
        def emit():
            try:
                self.ReasoningChanged(enabled)
                logger.info(f"ReasoningChanged signal emitted: {enabled}")
            except Exception as e:
                logger.error(f"Error emitting ReasoningChanged: {e}", exc_info=True)
            return False
        GLib.idle_add(emit)
        
        return "Reasoning control not available yet (waiting for Ramalama update)"
    
    def ListSessions(self, limit: int = 50) -> str:
        """
        List all saved chat sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            JSON string containing list of sessions
        """
        try:
            sessions = self.memory.list_sessions(limit)
            return json.dumps(sessions)
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return json.dumps([])
    
    def LoadSession(self, session_id: int) -> str:
        """
        Load a previous chat session.
        
        Args:
            session_id: ID of session to load
            
        Returns:
            JSON string containing conversation history
        """
        try:
            # Save current session first
            self.memory.save_current_session()
            
            # Load requested session
            context = self.memory.load_session(session_id)
            logger.info(f"Loaded session {session_id} with {len(context)} messages")
            return json.dumps(context)
        except Exception as e:
            logger.error(f"Error loading session: {e}", exc_info=True)
            return json.dumps([])
    
    def DeleteSession(self, session_id: int) -> str:
        """
        Delete a chat session.
        
        Args:
            session_id: ID of session to delete
            
        Returns:
            Status message
        """
        try:
            self.memory.delete_session(session_id)
            return f"Session {session_id} deleted"
        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _extract_tool_calls(self, response: str) -> list:
        """
        Extract tool calls from LLM response.
        
        Expects tool calls in format:
        <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        
        Args:
            response: LLM response text
            
        Returns:
            List of tool call dictionaries
        """
        tool_calls = []
        
        # Simple parsing for tool calls
        # Format: <tool_call>JSON</tool_call>
        import re
        pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                tool_calls.append(tool_call)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse tool call: {e}")
        
        return tool_calls
    
    def _execute_tool(self, tool_call: dict) -> dict:
        """
        Execute a tool call.
        
        Args:
            tool_call: Dictionary with 'name' and 'parameters'
            
        Returns:
            Dictionary with 'success', 'result', and optional 'error'
        """
        tool_name = tool_call.get('name')
        parameters = tool_call.get('parameters', {})
        
        logger.info(f"Executing tool: {tool_name}")
        
        try:
            result = self.tool_executor.execute(tool_name, parameters)
            return {
                'success': True,
                'tool': tool_name,
                'result': result
            }
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return {
                'success': False,
                'tool': tool_name,
                'error': str(e)
            }
    
    @dbus_signal
    def ResponseChunk(self, generation_id: Str, chunk: Str):
        """
        Signal emitted when a chunk of streaming response is received.
        
        Args:
            generation_id: Unique ID for this generation
            chunk: Text chunk from the LLM
        """
        pass
    
    @dbus_signal
    def ThinkingChunk(self, generation_id: Str, chunk: Str):
        """
        Signal emitted when a chunk of reasoning/thinking is received.
        Only emitted when reasoning mode is enabled.
        
        Args:
            generation_id: Unique ID for this generation
            chunk: Text chunk from the reasoning process
        """
        pass
    
    @dbus_signal
    def StreamingComplete(self, generation_id: Str):
        """
        Signal emitted when streaming response is complete.
        
        Args:
            generation_id: Unique ID for the completed generation
        """
        pass
    
    @dbus_signal
    def ModelChanged(self, model_id: Str):
        """
        Signal emitted when the active model is changed.
        
        Args:
            model_id: The new model ID
        """
        pass
    
    @dbus_signal
    def ReasoningChanged(self, enabled: bool):
        """
        Signal emitted when reasoning mode is enabled or disabled.
        
        Args:
            enabled: Whether reasoning is now enabled
        """
        pass
    
    @dbus_signal
    def HistoryCleared(self):
        """Signal emitted when conversation history is cleared."""
        pass
    
    def SendMessageStreaming(self, message: str) -> str:
        """
        Process a user message with streaming response.
        Emits ResponseChunk signals as text is generated.
        Emits ThinkingChunk signals for reasoning when enabled.
        
        IMPORTANT: This method returns immediately and processes in background.
        The actual response comes via ResponseChunk and ThinkingChunk signals.
        
        Args:
            message: User's input message
            
        Returns:
            Generation ID (actual response comes via signals)
        """
        import threading
        import time
        
        # Generate unique ID for this generation
        generation_id = f"gen_{int(time.time() * 1000000)}"  # Microsecond timestamp
        self._current_generation_id = generation_id
        logger.info(f"Starting generation: {generation_id}")
        
        def background_streaming():
            """Process streaming in background thread to avoid D-Bus timeout."""
            logger.info(f"=== BACKGROUND STREAMING STARTED: {generation_id} ===")
            try:
                self.status = "thinking"
                self._stop_generation = False
                logger.info(f"Received streaming message: {message[:50]}...")
                
                # Get conversation context from memory
                context = self.memory.get_recent_context(limit=10)
                logger.info(f"Got context: {len(context)} items")
                
                def chunk_handler(chunk):
                    logger.info(f"!!! chunk_handler CALLED with: {chunk[:30]}...")
                    if self._stop_generation or self._current_generation_id != generation_id:
                        logger.info(f"Skipping chunk - stopped or old generation")
                        return
                    # Emit from main loop thread for proper D-Bus signal delivery
                    def emit():
                        try:
                            self.ResponseChunk(generation_id, chunk)
                            logger.info(f"ResponseChunk signal emitted via GLib.idle_add: {generation_id}")
                        except Exception as e:
                            logger.error(f"Error emitting ResponseChunk: {e}", exc_info=True)
                        return False  # Don't repeat
                    GLib.idle_add(emit)
                
                def reasoning_handler(reasoning_chunk):
                    logger.info(f"!!! reasoning_handler CALLED with: {reasoning_chunk[:30]}...")
                    if self._stop_generation or self._current_generation_id != generation_id:
                        logger.info(f"Skipping thinking chunk - stopped or old generation")
                        return
                    # Emit from main loop thread for proper D-Bus signal delivery
                    def emit():
                        try:
                            self.ThinkingChunk(generation_id, reasoning_chunk)
                            logger.info(f"ThinkingChunk signal emitted via GLib.idle_add: {generation_id}")
                        except Exception as e:
                            logger.error(f"Error emitting ThinkingChunk: {e}", exc_info=True)
                        return False  # Don't repeat
                    GLib.idle_add(emit)
                
                logger.info("About to call generate_response_streaming...")
                # Generate streaming response
                full_response = self.llm.generate_response_streaming(
                    message, 
                    context,
                    chunk_callback=chunk_handler,
                    reasoning_callback=reasoning_handler
                )
                logger.info(f"generate_response_streaming returned: {len(full_response)} chars")
                
                if self._stop_generation or self._current_generation_id != generation_id:
                    logger.info(f"Generation stopped or superseded: {generation_id}")
                    self.status = "ready"
                    # Emit completion signal even if stopped
                    def emit_complete():
                        try:
                            self.StreamingComplete(generation_id)
                            logger.info(f"StreamingComplete signal emitted (stopped): {generation_id}")
                        except Exception as e:
                            logger.error(f"Error emitting StreamingComplete: {e}", exc_info=True)
                        return False
                    GLib.idle_add(emit_complete)
                    return
                
                # Check for tool calls in complete response (rest of method continues below)
                logger.info(f"Full response generated ({len(full_response)} chars)")
                
                # Save to memory
                self.memory.add_conversation(message, full_response)
                
                self.status = "ready"
                logger.info("Streaming response completed")
                
                # Emit completion signal
                def emit_complete():
                    try:
                        self.StreamingComplete(generation_id)
                        logger.info(f"StreamingComplete signal emitted (success): {generation_id}")
                    except Exception as e:
                        logger.error(f"Error emitting StreamingComplete: {e}", exc_info=True)
                    return False
                GLib.idle_add(emit_complete)
                
            except Exception as e:
                logger.error(f"Error in streaming response: {e}", exc_info=True)
                # Emit error as a chunk so UI sees it (via main loop)
                error_msg = f"\n\n❌ Error: {str(e)}\n\nPlease check if Ramalama is running:\n  systemctl --user status ramalama\n\nOr restart the daemon:\n  systemctl --user restart henzai-daemon"
                def emit_error():
                    try:
                        self.ResponseChunk(generation_id, error_msg)
                    except Exception as emit_err:
                        logger.error(f"Error emitting error message: {emit_err}")
                    return False
                GLib.idle_add(emit_error)
                
                # Emit completion signal after error
                def emit_complete_error():
                    try:
                        self.StreamingComplete(generation_id)
                        logger.info(f"StreamingComplete signal emitted (error): {generation_id}")
                    except Exception as e:
                        logger.error(f"Error emitting StreamingComplete: {e}", exc_info=True)
                    return False
                GLib.idle_add(emit_complete_error)
                
                self.status = "ready"
        
        # Start background thread
        thread = threading.Thread(target=background_streaming, daemon=True)
        thread.start()
        
        # Return generation ID immediately - signals will deliver the actual response
        return generation_id
    
    def StopGeneration(self) -> bool:
        """
        Stop the current LLM generation.
        
        Returns:
            True if stop signal was sent
        """
        logger.info("Stop generation requested")
        self._stop_generation = True
        self.llm.stop_current_generation()
        self.status = "ready"
        return True

