"""D-Bus service interface for henzai.

Provides the main communication layer between the GNOME Shell extension
and the Python daemon.
"""

import logging
import threading
from dasbus.connection import SessionMessageBus
from dasbus.server.interface import dbus_interface, dbus_signal
from dasbus.typing import Str
import json
from pathlib import Path
from gi.repository import GLib
from .tools import ToolExecutor

logger = logging.getLogger(__name__)

# D-Bus service information
SERVICE_NAME = "org.gnome.henzai"
OBJECT_PATH = "/org/gnome/henzai"


@dbus_interface(SERVICE_NAME)
class henzaiService:
    """henzai D-Bus service implementation."""
    
    def __init__(self, llm_client, memory_store, rag_manager=None):
        """
        Initialize the henzai service.
        
        Args:
            llm_client: LLM client instance for AI inference
            memory_store: Memory store for conversation history
            rag_manager: RAG manager instance (optional)
        """
        self.llm = llm_client
        self.memory = memory_store
        self.tool_executor = ToolExecutor()
        self.rag = rag_manager  # RAG manager
        self.status = "initializing"
        self._stop_generation = False  # Flag for stopping generation
        self._current_generation_id = None  # Track current generation
        
        # RAG indexing state tracking (prevent concurrent indexing)
        self._rag_indexing_active = False
        self._rag_indexing_thread = None
        self._pending_service_restart = False  # Deferred restart flag
        self._rag_mode = "augment"  # Default RAG mode
        
        # Service restart protection
        self._service_restarting = False
        self._service_restart_lock = threading.Lock()
        self._pending_rag_change = None  # Store pending RAG mode change
        self._rag_mode_change_timer = None  # Debounce timer for rapid changes
        
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
    
    def cleanup(self):
        """
        Cleanup resources when daemon shuts down.
        Cancels any pending timers to prevent resource leaks.
        """
        logger.info("Cleaning up henzai service resources...")
        
        # Cancel any pending RAG mode change timer
        if self._rag_mode_change_timer:
            logger.info("Canceling pending RAG mode change timer")
            self._rag_mode_change_timer.cancel()
            self._rag_mode_change_timer = None
        
        # Wait for any active RAG indexing to complete
        if self._rag_indexing_active and self._rag_indexing_thread:
            logger.info("Waiting for RAG indexing to complete...")
            self._rag_indexing_thread.join(timeout=5)
        
        logger.info("Service cleanup complete")
    
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
            - status: Combined status for UI ("ready", "loading", "error")
            - message: Human-readable combined message
            - rag_enabled: Boolean indicating if RAG is active
            - rag_port: Port for RAG queries (8080 if RAG enabled, None otherwise)
            - llm_port: Port for direct LLM queries (8081 if RAG enabled, 8080 otherwise)
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
            cached_status["ready"] = self.status == "ready" and cached_status.get("ramalama_status") == "ready"
            import json
            return json.dumps(cached_status)
        
        # Check Ramalama availability (not cached or cache expired)
        ramalama_status = "unavailable"
        ramalama_message = ""
        rag_enabled = False
        rag_healthy = False
        llm_healthy = False
        
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
                    # Use "loading" for consistency (service is activating = model will load soon)
                    ramalama_status = "loading"
                    ramalama_message = "Loading model into memory..."
            else:
                # Service is active, check if API is ready and detect RAG mode
                try:
                    # Check /health endpoint on port 8080 (using 127.0.0.1 to avoid IPv6 issues)
                    health_response_8080 = requests.get(
                        "http://127.0.0.1:8080/health",
                        timeout=2
                    )
                    
                    if health_response_8080.status_code == 200:
                        health_data = health_response_8080.json()
                        
                        # Check if this is RAG proxy or direct LLM
                        if health_data.get('rag') == 'ok':
                            # RAG proxy is responding - check if both ports are healthy
                            rag_enabled = True
                            rag_healthy = True
                            
                            # Check port 8081 (direct LLM) health
                            try:
                                health_response_8081 = requests.get(
                                    "http://127.0.0.1:8081/health",
                                    timeout=2
                                )
                                llm_healthy = (health_response_8081.status_code == 200)
                            except:
                                llm_healthy = False
                            
                            # Both ports must be healthy for RAG to be ready
                            if rag_healthy and llm_healthy:
                                ramalama_status = "ready"
                                ramalama_message = "Model loaded and ready (RAG enabled)"
                            else:
                                ramalama_status = "loading"
                                ramalama_message = "Loading model with RAG..."
                        else:
                            # Direct LLM mode (no RAG)
                            rag_enabled = False
                            if health_data.get('status') == 'ok':
                                ramalama_status = "ready"
                                ramalama_message = "Model loaded and ready"
                            else:
                                ramalama_status = "loading"
                                ramalama_message = "Service starting, model loading..."
                    else:
                        ramalama_status = "loading"
                        ramalama_message = "Service starting, model loading..."
                        
                except requests.exceptions.ConnectionError:
                    # Service running but API not responding yet (model still loading)
                    ramalama_status = "loading"
                    ramalama_message = "Loading model into memory..."
                except requests.exceptions.Timeout:
                    ramalama_status = "slow"
                    ramalama_message = "Ramalama is slow to respond"
                except Exception as e:
                    # Treat connection-related errors as loading
                    if "connection" in str(e).lower() or "refused" in str(e).lower():
                        ramalama_status = "loading"
                        ramalama_message = "Loading model into memory..."
                    else:
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
        
        # Determine overall ready state
        ready = self.status == "ready" and ramalama_status == "ready"
        
        # Determine combined status for UI
        if ready:
            combined_status = "ready"
            combined_message = ramalama_message
        elif ramalama_status == "loading":
            combined_status = "loading"
            combined_message = ramalama_message
        elif ramalama_status in ["error", "not_installed", "not_started"]:
            combined_status = "error"
            combined_message = ramalama_message
        else:
            combined_status = "unavailable"
            combined_message = ramalama_message
        
        # Build status response
        status_data = {
            "daemon_status": self.status,
            "ramalama_status": ramalama_status,
            "ramalama_message": ramalama_message,
            "ready": ready,
            "status": combined_status,
            "message": combined_message,
            "rag_enabled": rag_enabled,
            "rag_port": 8080 if rag_enabled else None,
            "llm_port": 8081 if rag_enabled else 8080
        }
        
        # Cache the status
        self._ramalama_status_cache = status_data.copy()
        self._ramalama_status_cache_time = current_time
        
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
    
    def GetConversationHistory(self) -> Str:
        """
        Get the current conversation history.
        
        Returns:
            JSON string containing the conversation history as a list of messages.
            Each message has 'role' and 'content' fields.
        """
        try:
            history = self.memory.get_history()
            return json.dumps(history)
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return json.dumps([])
    
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
                    self._current_generation_id = None  # Clear generation ID
                    self.status = "ready"
                    # Emit completion signal even if stopped
                    def emit_complete():
                        try:
                            self.StreamingComplete(generation_id)
                            logger.info(f"StreamingComplete signal emitted (stopped): {generation_id}")
                            # P0 FIX #2b: Check for pending service restart after generation
                            self._check_pending_service_restart()
                        except Exception as e:
                            logger.error(f"Error emitting StreamingComplete: {e}", exc_info=True)
                        return False
                    GLib.idle_add(emit_complete)
                    return
                
                # Check for tool calls in complete response (rest of method continues below)
                logger.info(f"Full response generated ({len(full_response)} chars)")
                
                # Save to memory
                self.memory.add_conversation(message, full_response)
                
                self._current_generation_id = None  # Clear generation ID
                self.status = "ready"
                logger.info("Streaming response completed")
                
                # Emit completion signal
                def emit_complete():
                    try:
                        self.StreamingComplete(generation_id)
                        logger.info(f"StreamingComplete signal emitted (success): {generation_id}")
                        # P0 FIX #2b: Check for pending service restart after generation
                        self._check_pending_service_restart()
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
                        # P0 FIX #2b: Check for pending service restart after generation
                        self._check_pending_service_restart()
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
    
    # RAG Methods
    #
    # NOTE: Current implementation uses wrapper script + service restart
    # This is temporary until Ramalama adds runtime RAG API
    # Future implementation (when API available):
    #   - Remove service restart logic
    #   - Call POST /v1/rag/enable API instead
    #   - Call POST /v1/rag/disable API instead
    #   - Zero downtime, instant enable/disable
    # See: https://github.com/containers/ramalama/issues/XXX (TODO: update with issue number)
    
    def SetRAGConfig(self, folder_path: str, format: str, enable_ocr: bool) -> bool:
        """
        Configure and index RAG documents.
        
        Args:
            folder_path: Path to documents folder
            format: RAG format (qdrant/json/markdown/milvus)
            enable_ocr: Enable OCR for PDFs
            
        Returns:
            True if indexing started successfully
        """
        if not self.rag:
            logger.error("RAG manager not initialized")
            return False
        
        # P0 FIX #1: Prevent concurrent indexing
        if self._rag_indexing_active:
            logger.warning("RAG indexing already in progress, rejecting new request")
            # Emit error signal
            def emit_error():
                try:
                    self.RAGIndexingFailed("Indexing already in progress")
                except Exception as e:
                    logger.error(f"Error emitting signal: {e}")
                return False
            GLib.idle_add(emit_error)
            return False
        
        logger.info(f"SetRAGConfig called: folder={folder_path}, format={format}, ocr={enable_ocr}")
        
        # ALWAYS check for and stop any running RAG containers before indexing
        # (they might be lingering even if RAG is "disabled" in our state)
        logger.info("Checking for running RAG containers")
        try:
            import subprocess
            # Find all RAG containers (ramalama doesn't clean them up properly)
            result = subprocess.run(
                ['podman', 'ps', '-a', '--format', '{{.ID}}'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                all_containers = result.stdout.strip().split('\n')
                for container_id in all_containers:
                    # Check if it's a RAG container by inspecting its command
                    inspect_result = subprocess.run(
                        ['podman', 'inspect', '--format', '{{.Config.Cmd}}', container_id],
                        capture_output=True, text=True, timeout=5
                    )
                    if 'rag_framework' in inspect_result.stdout:
                        logger.info(f"Found RAG container {container_id} - stopping it")
                        subprocess.run(['podman', 'stop', '-t', '2', container_id], timeout=10)
                        subprocess.run(['podman', 'rm', '-f', container_id], timeout=10)
                        logger.info(f"Stopped and removed RAG container {container_id}")
                logger.info("RAG containers cleanup complete")
            else:
                logger.info("No containers found")
        except Exception as e:
            logger.warning(f"Error stopping RAG containers (continuing anyway): {e}")
        
        # Wait for the lock file to be released
        import time
        time.sleep(2)
        
        # Check if RAG is currently enabled - need to disable it first
        rag_was_enabled = self.llm.rag_enabled
        if rag_was_enabled:
            logger.info("RAG is currently enabled - disabling temporarily for indexing")
            # Disable RAG (restarts ramalama without --rag flag)
            self._restart_ramalama_service(enable_rag=False)
            self.llm.set_rag_enabled(False)
            logger.info("RAG disabled")
        
        # Mark indexing as active
        self._rag_indexing_active = True
        
        # Start indexing in background thread
        import threading
        
        def background_indexing():
            try:
                # Emit indexing started signal
                def emit_started():
                    try:
                        self.RAGIndexingStarted(f"Indexing documents from {folder_path}")
                    except Exception as e:
                        logger.error(f"Error emitting RAGIndexingStarted: {e}")
                    return False
                GLib.idle_add(emit_started)
                
                # Progress callback
                def on_progress(message: str, percent: int):
                    def emit_progress():
                        try:
                            self.RAGIndexingProgress(message, percent)
                        except Exception as e:
                            logger.error(f"Error emitting RAGIndexingProgress: {e}")
                        return False
                    GLib.idle_add(emit_progress)
                
                # Index documents
                result = self.rag.index_documents(
                    folder_path, 
                    format=format,
                    enable_ocr=enable_ocr,
                    on_progress=on_progress
                )
                
                if result.success:
                    # Emit success signal
                    def emit_complete():
                        try:
                            self.RAGIndexingComplete(
                                f"Indexed {result.file_count} files successfully",
                                result.file_count
                            )
                        except Exception as e:
                            logger.error(f"Error emitting RAGIndexingComplete: {e}")
                        return False
                    GLib.idle_add(emit_complete)
                    
                    # Re-enable RAG if it was enabled before indexing
                    if rag_was_enabled:
                        logger.info("Re-enabling RAG after successful indexing")
                        self._restart_ramalama_service(enable_rag=True)
                        self.llm.set_rag_enabled(True)
                        logger.info("RAG re-enabled successfully")
                else:
                    # Emit error signal
                    def emit_error():
                        try:
                            self.RAGIndexingFailed(result.error or "Unknown error")
                        except Exception as e:
                            logger.error(f"Error emitting RAGIndexingFailed: {e}")
                        return False
                    GLib.idle_add(emit_error)
                    
            except Exception as e:
                logger.error(f"Error in background indexing: {e}", exc_info=True)
                def emit_error():
                    try:
                        self.RAGIndexingFailed(str(e))
                    except Exception as e:
                        logger.error(f"Error emitting RAGIndexingFailed: {e}")
                    return False
                GLib.idle_add(emit_error)
            finally:
                # Clear indexing state
                self._rag_indexing_active = False
                logger.info("RAG indexing thread finished")
        
        thread = threading.Thread(target=background_indexing, daemon=True)
        self._rag_indexing_thread = thread
        thread.start()
        
        return True
    
    def DisableRAG(self) -> bool:
        """
        Disable RAG and clear index.
        
        Returns:
            True if disabled successfully
        """
        if not self.rag:
            logger.error("RAG manager not initialized")
            return False
        
        logger.info("DisableRAG called")
        
        try:
            self.rag.clear_index()
            
            # Restart ramalama.service to deactivate RAG
            # The wrapper script will detect missing RAG database and run without --rag flag
            logger.info("Restarting ramalama.service to deactivate RAG...")
            try:
                subprocess.run(
                    ['systemctl', '--user', 'restart', 'ramalama.service'],
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                logger.info("✓ Ramalama service restarted with RAG disabled")
            except subprocess.TimeoutExpired:
                logger.error("Timeout restarting ramalama.service")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restart ramalama.service: {e.stderr.decode()}")
            except Exception as e:
                logger.error(f"Error restarting ramalama.service: {e}")
            
            logger.info("RAG disabled successfully")
            return True
        except Exception as e:
            logger.error(f"Error disabling RAG: {e}", exc_info=True)
            return False
    
    def GetRAGStatus(self, source_path: str, rag_enabled: bool) -> str:
        """
        Get RAG status as JSON.
        
        Args:
            source_path: Current configured source path
            rag_enabled: Whether RAG is enabled in settings
            
        Returns:
            JSON string with RAG status
        """
        if not self.rag:
            return json.dumps({
                "enabled": False,
                "indexed": False,
                "file_count": 0,
                "last_indexed": None,
                "format": "qdrant",
                "db_path": "",
                "source_path": "",
                "ocr_enabled": False,
                "error": "RAG manager not initialized"
            })
        
        try:
            status = self.rag.get_status(source_path, rag_enabled)
            return status.to_json()
        except Exception as e:
            logger.error(f"Error getting RAG status: {e}", exc_info=True)
            return json.dumps({
                "enabled": False,
                "indexed": False,
                "file_count": 0,
                "last_indexed": None,
                "format": "qdrant",
                "db_path": "",
                "source_path": source_path,
                "ocr_enabled": False,
                "error": str(e)
            })
    
    def ReindexRAG(self) -> bool:
        """
        Trigger RAG reindexing with current config.
        
        Returns:
            True if reindexing started
        """
        if not self.rag:
            logger.error("RAG manager not initialized")
            return False
        
        logger.info("ReindexRAG called")
        
        # Load current config from metadata
        metadata = self.rag._load_metadata()
        if metadata is None:
            logger.error("No existing RAG configuration found")
            return False
        
        source_path = metadata.get('source_path')
        format = metadata.get('format', 'qdrant')
        enable_ocr = metadata.get('ocr_enabled', False)
        
        # Call SetRAGConfig with existing config
        return self.SetRAGConfig(source_path, format, enable_ocr)
    
    def SetRagEnabled(self, enabled: bool, mode: str = "augment") -> Str:
        """
        Enable or disable RAG mode.
        
        Args:
            enabled: True to enable RAG, False to disable
            mode: RAG mode - "augment" (docs + knowledge), "strict" (docs only), or "hybrid" (docs preferred)
        
        Returns:
            JSON with success status
        """
        try:
            logger.info(f"SetRagEnabled called: {enabled}, mode: {mode}")
            
            # Priority 1: Check if service is already restarting
            with self._service_restart_lock:
                if self._service_restarting:
                    logger.warning("Service restart already in progress")
                    return Str(json.dumps({
                        "success": False,
                        "error": "Service restart already in progress, please wait"
                    }))
            
            # Validate mode
            if mode not in ['augment', 'strict', 'hybrid']:
                logger.warning(f"Invalid RAG mode '{mode}', defaulting to 'augment'")
                mode = 'augment'
            
            # Check if RAG database exists
            rag_db_path = Path.home() / '.local' / 'share' / 'henzai' / 'rag-db'
            has_rag_db = (rag_db_path / 'collection').exists()
            
            if enabled and not has_rag_db:
                return Str(json.dumps({
                    "success": False,
                    "error": "No RAG database found. Please index documents first."
                }))
            
            # Priority 2: Check if generation is active - defer restart if so
            if self._current_generation_id is not None:
                logger.warning("Generation active, deferring RAG mode change")
                
                # Cancel any pending timer
                if self._rag_mode_change_timer:
                    self._rag_mode_change_timer.cancel()
                    self._rag_mode_change_timer = None
                
                # Store pending change
                self._pending_rag_change = {
                    'enabled': enabled,
                    'mode': mode
                }
                
                return Str(json.dumps({
                    "success": True,
                    "message": f"RAG mode change scheduled (will apply after current response finishes)"
                }))
            
            # Priority 3: Debounce rapid changes
            # Cancel any pending timer
            if self._rag_mode_change_timer:
                self._rag_mode_change_timer.cancel()
                self._rag_mode_change_timer = None
            
            # If another restart is pending, debounce this change
            if self._service_restarting:
                logger.info("Service restart pending, debouncing RAG mode change")
                
                def apply_change():
                    self._apply_rag_change(enabled, mode)
                
                self._rag_mode_change_timer = threading.Timer(1.0, apply_change)
                self._rag_mode_change_timer.start()
                
                return Str(json.dumps({
                    "success": True,
                    "message": "RAG mode change scheduled"
                }))
            
            # Apply the change immediately
            return self._apply_rag_change(enabled, mode)
                
        except Exception as e:
            logger.error(f"Error in SetRagEnabled: {e}", exc_info=True)
            return Str(json.dumps({
                "success": False,
                "error": str(e)
            }))
    
    def _apply_rag_change(self, enabled: bool, mode: str) -> Str:
        """
        Apply RAG mode change (internal helper).
        
        Args:
            enabled: True to enable RAG, False to disable
            mode: RAG mode
            
        Returns:
            JSON response string
        """
        with self._service_restart_lock:
            if self._service_restarting:
                # Another restart started, abort
                return Str(json.dumps({
                    "success": False,
                    "error": "Service restart already in progress"
                }))
            self._service_restarting = True
        
        try:
            # Store the mode for use in _restart_ramalama_service
            self._rag_mode = mode
            
            # Priority 4: Check if custom RAG image exists (if enabling)
            if enabled and mode in ['augment', 'strict', 'hybrid']:
                if not self._check_rag_image_exists():
                    logger.warning("Custom RAG image not found, RAG may not work correctly")
                    # Continue anyway - let it fail with proper error from podman
            
            # Restart ramalama service with new configuration
            success = self._restart_ramalama_service(enable_rag=enabled)
            
            if success:
                # Update LLM client
                self.llm.set_rag_enabled(enabled)
                
                return Str(json.dumps({
                    "success": True,
                    "message": f"RAG {'enabled' if enabled else 'disabled'} successfully (mode: {mode})"
                }))
            else:
                return Str(json.dumps({
                    "success": False,
                    "error": "Failed to restart ramalama service"
                }))
        finally:
            with self._service_restart_lock:
                self._service_restarting = False
    
    def _check_rag_image_exists(self) -> bool:
        """
        Check if custom RAG image exists locally.
        
        Returns:
            True if image exists, False otherwise
        """
        try:
            import subprocess
            result = subprocess.run(
                ['podman', 'image', 'exists', 'localhost/ramalama/cuda-rag:augment'],
                capture_output=True,
                timeout=5
            )
            exists = result.returncode == 0
            if not exists:
                logger.warning("Custom RAG image 'localhost/ramalama/cuda-rag:augment' not found")
            return exists
        except Exception as e:
            logger.error(f"Error checking RAG image: {e}")
            return False  # Assume doesn't exist if we can't check
    
    def _check_ramalama_has_rag(self) -> bool:
        """
        Check if ramalama service is currently configured with --rag flag.
        
        Returns:
            True if ramalama has --rag in its ExecStart, False otherwise
        """
        try:
            service_file = Path.home() / '.config' / 'systemd' / 'user' / 'ramalama.service'
            
            if not service_file.exists():
                logger.warning(f"Service file not found: {service_file}")
                return False
            
            with open(service_file, 'r') as f:
                content = f.read()
                # Check if --rag or --rag-image is in the ExecStart line
                return '--rag' in content
        except Exception as e:
            logger.error(f"Error checking ramalama RAG status: {e}")
            return False
    
    def _restart_ramalama_service(self, enable_rag: bool = False) -> bool:
        """
        Restart ramalama.service with or without RAG.
        
        Args:
            enable_rag: If True, add --rag flag to service command
        
        Returns:
            True if restart succeeded, False otherwise
        """
        import subprocess
        
        logger.info(f"Restarting ramalama.service with RAG={'enabled' if enable_rag else 'disabled'}...")
        
        try:
            # Check if RAG database exists
            rag_db_path = Path.home() / '.local' / 'share' / 'henzai' / 'rag-db'
            has_rag_db = (rag_db_path / 'collection').exists()
            
            if enable_rag and not has_rag_db:
                logger.warning("RAG enabled but no database found at %s", rag_db_path)
                return False
            
            # Get service file path
            service_file = Path.home() / '.config' / 'systemd' / 'user' / 'ramalama.service'
            
            if not service_file.exists():
                logger.error("Service file not found: %s", service_file)
                return False
            
            # Read current service file
            with open(service_file, 'r') as f:
                lines = f.readlines()
            
            # Detect ramalama binary location
            ramalama_bin = "/usr/bin/ramalama"  # default
            for line in lines:
                if line.strip().startswith('ExecStart='):
                    # Extract binary path from existing command
                    parts = line.strip().split()
                    if parts and 'ramalama' in parts[0]:
                        ramalama_bin = parts[0].replace('ExecStart=', '')
                    break
            
            # Build new ExecStart command
            # NOTE: We intentionally do NOT use --port flag with --rag due to ramalama bug
            # (see RAMALAMA_RFE.md Issue #2). Ramalama will default to 8080/8081 anyway.
            base_cmd = f"{ramalama_bin} serve --ctx-size 8192 --cache-reuse 512"
            
            # Get current model from service file
            model = "ollama://library/deepseek-r1:14b"  # default
            for line in lines:
                if line.strip().startswith('ExecStart='):
                    # Extract model from existing command
                    parts = line.strip().split()
                    if parts and parts[-1].startswith('ollama://'):
                        model = parts[-1]
                    break
            
            if enable_rag and has_rag_db:
                # Use custom RAG image with chosen mode
                # Pass RAG_MODE as environment variable to the RAG container
                rag_mode = getattr(self, '_rag_mode', 'augment')  # Default to augment if not set
                exec_start = f"{base_cmd} --env RAG_MODE={rag_mode} --rag-image localhost/ramalama/cuda-rag:augment --rag {rag_db_path} {model}"
            else:
                exec_start = f"{base_cmd} {model}"
            
            # Replace ExecStart and add/update Environment lines
            new_lines = []
            found_exec_start = False
            found_environment = False
            in_service_section = False
            
            for line in lines:
                # Track if we're in [Service] section
                if line.strip() == '[Service]':
                    in_service_section = True
                    new_lines.append(line)
                    continue
                elif line.strip().startswith('['):
                    # Entering a new section - if we were in [Service] and didn't find Environment, add it
                    if in_service_section and enable_rag and has_rag_db and not found_environment:
                        new_lines.append('# RAG Mode: augment = use general knowledge + documents, strict = documents only\n')
                        new_lines.append('Environment="RAG_MODE=augment"\n')
                        new_lines.append('# Use custom RAG image with augment mode support\n')
                        new_lines.append('Environment="RAMALAMA_RAG_IMAGE=localhost/ramalama/cuda-rag:augment"\n')
                    in_service_section = False
                    new_lines.append(line)
                    continue
                
                # Handle ExecStart line
                if line.strip().startswith('ExecStart='):
                    new_lines.append(f'ExecStart={exec_start}\n')
                    found_exec_start = True
                    continue
                
                # Handle existing Environment lines
                if in_service_section and line.strip().startswith('Environment='):
                    # Skip existing RAG_MODE or RAMALAMA_RAG_IMAGE environment variables
                    if 'RAG_MODE' in line or 'RAMALAMA_RAG_IMAGE' in line:
                        found_environment = True
                        if enable_rag and has_rag_db:
                            # Replace with new RAG configuration
                            if 'RAG_MODE' in line:
                                new_lines.append('Environment="RAG_MODE=augment"\n')
                            elif 'RAMALAMA_RAG_IMAGE' in line:
                                new_lines.append('Environment="RAMALAMA_RAG_IMAGE=localhost/ramalama/cuda-rag:augment"\n')
                        # else: skip these lines (remove them when RAG disabled)
                    else:
                        new_lines.append(line)
                    continue
                
                # Keep all other lines
                new_lines.append(line)
            
            # If we're at end of file and in service section, add environment if needed
            if in_service_section and enable_rag and has_rag_db and not found_environment:
                new_lines.append('# RAG Mode: augment = use general knowledge + documents, strict = documents only\n')
                new_lines.append('Environment="RAG_MODE=augment"\n')
                new_lines.append('# Use custom RAG image with augment mode support\n')
                new_lines.append('Environment="RAMALAMA_RAG_IMAGE=localhost/ramalama/cuda-rag:augment"\n')
            
            # Write updated service file
            with open(service_file, 'w') as f:
                f.writelines(new_lines)
            
            logger.info("Updated service file: %s", exec_start)
            
            # Stop current service
            subprocess.run(
                ['systemctl', '--user', 'stop', 'ramalama.service'],
                check=False,  # Don't fail if already stopped
                capture_output=True,
                timeout=5
            )
            
            # Reload systemd daemon
            subprocess.run(
                ['systemctl', '--user', 'daemon-reload'],
                check=True,
                capture_output=True,
                timeout=5
            )
            
            # Start service with new configuration
            subprocess.run(
                ['systemctl', '--user', 'start', 'ramalama.service'],
                check=True,
                capture_output=True,
                timeout=10
            )
            
            logger.info("✓ Ramalama service restarted successfully with RAG=%s", enable_rag)
            self._pending_service_restart = False
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout restarting ramalama.service")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart ramalama.service: {e}")
            return False
        except Exception as e:
            logger.error(f"Error restarting ramalama.service: {e}", exc_info=True)
            return False
    
    def _check_pending_service_restart(self):
        """Check if we have a pending service restart or RAG change after generation completes."""
        if self._current_generation_id is None:
            # Check for pending RAG mode change first
            if self._pending_rag_change:
                logger.info("Generation finished, applying pending RAG mode change")
                change = self._pending_rag_change
                self._pending_rag_change = None
                
                # Apply the deferred change
                self._apply_rag_change(change['enabled'], change['mode'])
                return
            
            # Check for pending service restart (from indexing)
            if self._pending_service_restart:
                logger.info("Generation finished, executing pending service restart")
                self._restart_ramalama_service()
                self._pending_service_restart = False
    
    # RAG Signals
    
    @dbus_signal
    def RAGIndexingStarted(self, message: Str):
        """Emitted when RAG indexing starts."""
        pass
    
    @dbus_signal
    def RAGIndexingProgress(self, message: Str, percent: int):
        """Emitted during RAG indexing."""
        pass
    
    @dbus_signal
    def RAGIndexingComplete(self, message: Str, file_count: int):
        """Emitted when RAG indexing completes."""
        pass
    
    @dbus_signal
    def RAGIndexingFailed(self, error: Str):
        """Emitted when RAG indexing fails."""
        pass

