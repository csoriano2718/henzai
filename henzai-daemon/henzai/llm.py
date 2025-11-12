"""LLM client for interacting with Ramalama.

Handles all LLM inference, prompt management, and response generation.
"""

import logging
import subprocess
import json
import requests
from typing import List, Dict, Any, Optional, Union, Generator

logger = logging.getLogger(__name__)

# System prompt template (model info will be inserted dynamically)
SYSTEM_PROMPT_TEMPLATE = """You are henzai, an AI assistant integrated into the GNOME desktop environment.

**System Information:**
- OS: Fedora Linux 42 (Workstation Edition)
- Desktop: GNOME Shell 48.6
- Kernel: 6.17.6-200.fc42.x86_64
- AI Stack: Ramalama + llama.cpp running {model_name}
- Container Runtime: Podman
- Context Window: 8192 tokens with KV cache shifting

**Important:** When asked about yourself or the system, provide accurate information from the above. Be honest about your capabilities and limitations as a locally running model.

**Guidelines:**
- Be helpful, concise, and friendly
- Provide clear and accurate information
- If you don't know something, say so
- Focus on answering questions and having natural conversations
"""


class LLMClient:
    """Client for interacting with Ramalama LLM."""
    
    # Models known to support reasoning/thinking
    REASONING_MODELS = [
        'deepseek-r1',
        'deepseek-reasoner',
        'qwen-qwq',
        'qwq',
        'o1',
        'o3',
        'claude-3-5-sonnet',  # With extended thinking
        'claude-3-opus',       # With extended thinking
    ]
    
    def __init__(self, model: Optional[str] = None, api_url: str = "http://127.0.0.1:8080", reasoning_enabled: bool = False):
        """
        Initialize the LLM client.
        
        Args:
            model: Model name to use (default: auto-detect or use llama3.2)
            api_url: Ramalama API endpoint URL
            reasoning_enabled: Whether to enable reasoning mode for capable models
        """
        self.api_url = api_url
        self.model = model or "llama3.2"
        self.reasoning_enabled = reasoning_enabled
        self._current_request = None  # Track current streaming request for cancellation
        logger.info(f"Initialized LLM client with model: {self.model}, API: {api_url}, reasoning: {reasoning_enabled}")
    
    def supports_reasoning(self) -> bool:
        """
        Check if the current model supports reasoning/thinking.
        
        Checks both Ramalama's capabilities field (if available) and
        known reasoning model patterns.
        
        Returns:
            True if model supports reasoning
        """
        # First, try to check Ramalama's model metadata
        try:
            response = requests.get(
                f"{self.api_url}/v1/models",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                # Check if any model matches and has 'reasoning' capability
                for model_data in data.get('models', []):
                    if self.model in model_data.get('name', '') or self.model in model_data.get('model', ''):
                        capabilities = model_data.get('capabilities', [])
                        if 'reasoning' in capabilities or 'thinking' in capabilities:
                            return True
        except:
            pass  # Fall back to pattern matching
        
        # Fall back to pattern matching for known reasoning models
        model_lower = self.model.lower()
        return any(reasoning_model in model_lower for reasoning_model in self.REASONING_MODELS)
    
    def parse_reasoning_response(self, text: str) -> Dict[str, str]:
        """
        Parse a response that may contain reasoning tokens.
        
        Supports formats like:
        - <think>reasoning here</think>final answer
        - <reasoning>thinking</reasoning>answer
        
        Args:
            text: Raw response text
            
        Returns:
            Dict with 'thinking' and 'answer' keys
        """
        import re
        
        # Try to find reasoning tags
        think_match = re.search(r'<think>(.*?)</think>(.*)', text, re.DOTALL)
        if think_match:
            return {
                'thinking': think_match.group(1).strip(),
                'answer': think_match.group(2).strip()
            }
        
        reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>(.*)', text, re.DOTALL)
        if reasoning_match:
            return {
                'thinking': reasoning_match.group(1).strip(),
                'answer': reasoning_match.group(2).strip()
            }
        
        # No reasoning tags found
        return {
            'thinking': '',
            'answer': text
        }
    
    def _get_default_model(self) -> str:
        """
        Get the default Ramalama model.
        
        Returns:
            Model name string
        """
        try:
            # Try to list available models
            result = subprocess.run(
                ['ramalama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse output and get first model
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    first_model = lines[1].split()[0]
                    logger.info(f"Found model: {first_model}")
                    return first_model
            
            # Fallback to a common default
            logger.warning("No models found, using default: llama3.2")
            return "llama3.2"
            
        except Exception as e:
            logger.error(f"Error detecting model: {e}")
            return "llama3.2"  # Safe fallback
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        List all available models from Ramalama.
        Uses CLI first to get ALL downloaded models, falls back to API if CLI unavailable.
        
        Returns:
            List of model dictionaries with name, size, and other metadata
        """
        # Try CLI first (shows ALL downloaded models)
        try:
            import subprocess
            import re
            
            result = subprocess.run(
                ['ramalama', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                models = []
                lines = result.stdout.strip().split('\n')
                
                # Skip header line
                for line in lines[1:]:
                    # Parse: NAME MODIFIED SIZE
                    # Example: ollama://library/deepseek-r1:14b    2 hours ago 8.37 GB
                    match = re.match(r'(\S+)\s+(.+?)\s+(\S+\s+\S+)\s*$', line.strip())
                    if match:
                        model_name = match.group(1)
                        size_str = match.group(3)
                        
                        # Parse size (e.g., "8.37 GB" -> bytes)
                        size_bytes = 0
                        size_match = re.match(r'([\d.]+)\s*(GB|MB|KB)', size_str)
                        if size_match:
                            size_val = float(size_match.group(1))
                            size_unit = size_match.group(2)
                            if size_unit == 'GB':
                                size_bytes = int(size_val * 1024 * 1024 * 1024)
                            elif size_unit == 'MB':
                                size_bytes = int(size_val * 1024 * 1024)
                            elif size_unit == 'KB':
                                size_bytes = int(size_val * 1024)
                        
                        model_info = {
                            'id': model_name,
                            'name': model_name.split('/')[-1],  # Short name with variant
                            'full_name': model_name,
                            'size': size_bytes,
                            'size_str': size_str,
                            'params': 0,  # Not available from CLI
                            'context': 0,  # Not available from CLI
                        }
                        models.append(model_info)
                
                logger.info(f"Found {len(models)} available models from CLI (ramalama list)")
                return models
            else:
                logger.warning(f"ramalama list failed with code {result.returncode}")
                
        except Exception as e:
            logger.warning(f"CLI unavailable, falling back to API: {e}")
        
        # Fallback to API (only shows currently served model)
        try:
            response = requests.get(
                f"{self.api_url}/v1/models",
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            # Extract model info from 'data' array (more detailed)
            for model_data in data.get('data', []):
                model_info = {
                    'id': model_data.get('id', 'unknown'),
                    'name': model_data.get('id', 'unknown').split('/')[-1],  # Short name
                    'full_name': model_data.get('id', 'unknown'),
                    'size': model_data.get('meta', {}).get('size', 0),
                    'params': model_data.get('meta', {}).get('n_params', 0),
                    'context': model_data.get('meta', {}).get('n_ctx_train', 0),
                }
                models.append(model_info)
            
            # Fallback to 'models' array if 'data' is empty
            if not models:
                for model_data in data.get('models', []):
                    model_info = {
                        'id': model_data.get('model', 'unknown'),
                        'name': model_data.get('name', 'unknown').split('/')[-1],
                        'full_name': model_data.get('model', 'unknown'),
                        'size': 0,
                        'params': 0,
                        'context': 0,
                    }
                    models.append(model_info)
            
            logger.info(f"Found {len(models)} available models from API (fallback)")
            return models
            
        except Exception as e:
            logger.error(f"Both CLI and API failed to list models: {e}")
            return []
    
    def call(self, messages: List[Dict[str, str]], stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """
        Call the LLM with a list of messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: If True, returns a generator that yields response chunks
        
        Returns:
            Complete response text, or generator yielding chunks if streaming
        """
        if stream:
            return self._call_ramalama_api_streaming(messages)
        else:
            return self._call_ramalama_api(messages)
    
    def generate_response(self, message: str, context: List[Dict[str, str]] = None) -> str:
        """
        Generate a response to a user message.
        
        Args:
            message: User's input message
            context: Previous conversation context (list of {role, content} dicts)
            
        Returns:
            AI-generated response
        """
        try:
            # Build messages for chat completion API
            messages = self._build_messages(message, context)
            
            # Call Ramalama API
            response = self._call_ramalama_api(messages)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return f"I encountered an error: {str(e)}"
    
    def generate_with_tool_results(
        self, 
        original_message: str,
        tool_results: List[Dict[str, Any]],
        context: List[Dict[str, str]] = None
    ) -> str:
        """
        Generate a final response after tool execution.
        
        Args:
            original_message: Original user message
            tool_results: Results from tool execution
            context: Previous conversation context
            
        Returns:
            Final AI response incorporating tool results
        """
        try:
            # Build messages with tool results
            tool_results_text = self._format_tool_results(tool_results)
            
            follow_up_message = f"""The user asked: {original_message}

I executed the following actions:
{tool_results_text}

Please provide a natural language response to the user about what was done."""
            
            messages = self._build_messages(follow_up_message, context)
            response = self._call_ramalama_api(messages)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response with tool results: {e}", exc_info=True)
            return "I completed the actions but encountered an error generating a response."
    
    def _build_messages(self, message: str, context: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        Build the messages array for chat completion API.
        
        Args:
            message: Current user message
            context: Previous conversation context
            
        Returns:
            List of message dicts with role and content
        """
        # Generate system prompt with current model name
        model_display_name = self.model.split('/')[-1].replace(':latest', '')
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(model_name=model_display_name)
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation context
        if context:
            for turn in context[-5:]:  # Last 5 turns
                if turn.get('user'):
                    messages.append({"role": "user", "content": turn['user']})
                if turn.get('assistant'):
                    messages.append({"role": "assistant", "content": turn['assistant']})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _call_ramalama_api(self, messages: List[Dict[str, str]]) -> str:
        """
        Call Ramalama HTTP API to generate response.
        
        Args:
            messages: List of message dicts for chat completion
            
        Returns:
            Generated response
        """
        try:
            logger.debug(f"Calling Ramalama API at {self.api_url}")
            
            # Use temperature 0.6 for reasoning models (DeepSeek recommendation)
            temp = 0.6 if (self.reasoning_enabled and self.supports_reasoning()) else 0.7
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "temperature": temp
            }
            
            # Enable reasoning mode in API if supported
            if self.reasoning_enabled and self.supports_reasoning():
                payload["reasoning"] = True
            
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json=payload,
                timeout=(30, 300)  # (connection timeout, read timeout) - 5 minutes for non-streaming
            )
            
            if response.status_code != 200:
                error_msg = f"API error {response.status_code}"
                if response.status_code == 503:
                    error_msg += " - Model is still loading, please wait a moment and try again"
                else:
                    try:
                        error_details = response.json()
                        error_msg += f": {error_details.get('error', {}).get('message', response.text[:200])}"
                    except:
                        error_msg += f": {response.text[:200]}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            message = result['choices'][0]['message']
            content = message.get('content', '')
            
            # Extract reasoning_content if present
            reasoning_content = message.get('reasoning_content', '')
            if reasoning_content:
                logger.info(f"Extracted reasoning content ({len(reasoning_content)} chars)")
                # For non-streaming, we can't emit signals, so prepend as <think> tags
                # This allows the response to be parsed by existing logic
                content = f"<think>\n{reasoning_content}\n</think>\n\n{content}"
            
            logger.debug(f"Received response ({len(content)} chars)")
            return content
            
        except requests.exceptions.Timeout:
            logger.error("Ramalama API call timed out")
            raise Exception("Sorry, the request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ramalama API")
            raise Exception("Cannot connect to Ramalama. Is it running? Check: systemctl --user status ramalama")
        except Exception as e:
            logger.error(f"Error calling Ramalama API: {e}", exc_info=True)
            raise
    
    def _format_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """
        Format tool execution results for inclusion in prompt.
        
        Args:
            tool_results: List of tool result dictionaries
            
        Returns:
            Formatted string
        """
        formatted = []
        for result in tool_results:
            tool_name = result.get('tool', 'unknown')
            if result.get('success'):
                formatted.append(f"✓ {tool_name}: {result.get('result', 'Success')}")
            else:
                formatted.append(f"✗ {tool_name}: {result.get('error', 'Failed')}")
        
        return "\n".join(formatted)
    
    def generate_response_streaming(
        self, 
        message: str, 
        context: List[Dict[str, str]] = None,
        chunk_callback = None,
        reasoning_callback = None
    ) -> str:
        """
        Generate a streaming response to a user message.
        Calls chunk_callback for each chunk received.
        Calls reasoning_callback for reasoning content (if reasoning mode enabled).
        
        Args:
            message: User's input message
            context: Previous conversation context
            chunk_callback: Function to call with each chunk of text
            reasoning_callback: Function to call with each reasoning chunk
            
        Returns:
            Complete AI-generated response
        """
        try:
            # Build messages for chat completion API
            messages = self._build_messages(message, context)
            
            # Call Ramalama API with streaming
            response = self._call_ramalama_api_streaming(messages, chunk_callback, reasoning_callback)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating streaming response: {e}", exc_info=True)
            return f"I encountered an error: {str(e)}"
    
    def _call_ramalama_api_streaming(
        self, 
        messages: List[Dict[str, str]],
        chunk_callback = None,
        reasoning_callback = None
    ) -> str:
        """
        Call Ramalama HTTP API with streaming to generate response.
        
        Args:
            messages: List of message dicts for chat completion
            chunk_callback: Function to call with each chunk
            reasoning_callback: Function to call with each reasoning chunk
            
        Returns:
            Complete generated response
        """
        try:
            logger.debug(f"Calling Ramalama API (streaming) at {self.api_url}")
            
            # Use temperature 0.6 for reasoning models (DeepSeek recommendation)
            temp = 0.6 if (self.reasoning_enabled and self.supports_reasoning()) else 0.7
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,  # Enable streaming
                "temperature": temp
            }
            
            # Enable reasoning mode in API if supported
            if self.reasoning_enabled and self.supports_reasoning():
                payload["reasoning"] = True
                logger.info(f"Streaming: Reasoning enabled for API call (model: {self.model})")
            else:
                logger.info(f"Streaming: Reasoning NOT enabled (enabled={self.reasoning_enabled}, supports={self.supports_reasoning()})")
            
            # Make streaming request
            # timeout=None means no timeout on initial connection
            # We'll handle read timeouts separately in the streaming loop
            self._current_request = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json=payload,
                timeout=(30, None),  # (connection timeout, read timeout) - None means infinite read timeout
                stream=True  # Important: enable streaming response
            )
            
            if self._current_request.status_code != 200:
                error_msg = f"API error {self._current_request.status_code}"
                if self._current_request.status_code == 503:
                    error_msg += " - Model is still loading, please wait a moment and try again"
                else:
                    try:
                        error_details = self._current_request.json()
                        error_msg += f": {error_details.get('error', {}).get('message', self._current_request.text[:200])}"
                    except:
                        error_msg += f": {self._current_request.text[:200]}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Process streaming response (SSE format)
            # No idle timeout needed - the stream will naturally end when complete
            # The connection timeout (30s) protects against initial connection failures
            full_response = ""
            
            # Use iter_lines to process Server-Sent Events
            for line in self._current_request.iter_lines(decode_unicode=True):
                if not line:
                    # Empty line - normal SSE heartbeat, just continue
                    continue
                
                # SSE format: "data: {json}"
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove "data: " prefix
                    
                    # Check for end marker
                    if data_str.strip() == '[DONE]':
                        break
                    
                    try:
                        # Parse JSON chunk
                        chunk_data = json.loads(data_str)
                        logger.debug(f"Parsed chunk: {chunk_data.keys() if isinstance(chunk_data, dict) else 'not a dict'}")
                        
                        # Extract content from delta
                        if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                            choice = chunk_data['choices'][0]
                            if 'delta' in choice:
                                delta = choice['delta']
                                logger.debug(f"Delta keys: {delta.keys()}")
                                
                                # Handle reasoning content (if present)
                                # NOTE: Always show reasoning for reasoning-capable models until Ramalama
                                # adds --reasoning-budget support to properly disable it.
                                # See: https://github.com/containers/ramalama/issues/XXX
                                if 'reasoning_content' in delta:
                                    reasoning_chunk = delta['reasoning_content']
                                    if reasoning_chunk is not None and reasoning_callback:
                                        logger.info(f"Found reasoning_content: {reasoning_chunk[:100]}...")
                                        logger.info(f"Calling reasoning_callback with {len(reasoning_chunk)} chars")
                                        reasoning_callback(reasoning_chunk)
                                
                                # Handle regular content
                                if 'content' in delta:
                                    content = delta['content']
                                    logger.info(f"Found content: {repr(content)}")
                                    # Skip null content (happens in first chunk with role assignment)
                                    if content is not None:
                                        full_response += content
                                        logger.info(f"Calling chunk_callback with {len(content)} chars")
                                        
                                        # Call chunk callback if provided
                                        if chunk_callback:
                                            chunk_callback(content)
                                        else:
                                            logger.warning("chunk_callback is None!")
                    
                    except json.JSONDecodeError:
                        # Skip invalid JSON chunks
                        continue
            
            logger.debug(f"Streaming complete ({len(full_response)} chars)")
            self._current_request = None
            return full_response
            
        except requests.exceptions.Timeout:
            logger.error("Ramalama API call timed out")
            self._current_request = None
            raise Exception("Sorry, the request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ramalama API")
            self._current_request = None
            raise Exception("Cannot connect to Ramalama. Is it running? Check: systemctl --user status ramalama")
        except requests.exceptions.ChunkedEncodingError:
            # This happens when connection is closed during streaming (e.g., stop button)
            logger.info("Streaming connection closed (likely stopped by user)")
            self._current_request = None
            return full_response  # Return partial response
        except Exception as e:
            logger.error(f"Error in streaming API call: {e}", exc_info=True)
            self._current_request = None
            raise
    
    def stop_current_generation(self):
        """Stop the current streaming generation if active."""
        if self._current_request:
            try:
                logger.info("Closing streaming connection")
                # Close the underlying connection to immediately abort streaming
                if hasattr(self._current_request, 'raw'):
                    self._current_request.raw.close()
                self._current_request.close()
            except Exception as e:
                logger.error(f"Error stopping generation: {e}")
            finally:
                # Always clear the request, even if close fails
                self._current_request = None


