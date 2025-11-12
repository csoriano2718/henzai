"""Tests for LLM client streaming functionality."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from henzai.llm import LLMClient


@pytest.fixture
def llm_client():
    """Create an LLM client for testing."""
    return LLMClient(model="test-model", api_url="http://test:8080")


class TestLLMStreaming:
    """Test streaming functionality in LLM client."""
    
    def test_init_with_streaming_support(self, llm_client):
        """Test that LLM client initializes with streaming support."""
        assert llm_client.model == "test-model"
        assert llm_client.api_url == "http://test:8080"
        assert llm_client._current_request is None
    
    @patch('henzai.llm.requests.post')
    def test_streaming_api_call_success(self, mock_post, llm_client):
        """Test successful streaming API call."""
        # Create mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Simulate SSE stream
        sse_data = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"!"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_response.iter_lines.return_value = sse_data
        mock_post.return_value = mock_response
        
        # Track chunks
        chunks = []
        
        def chunk_callback(chunk):
            chunks.append(chunk)
        
        # Call streaming method
        messages = [{"role": "user", "content": "test"}]
        result = llm_client._call_ramalama_api_streaming(messages, chunk_callback)
        
        # Assertions
        assert result == "Hello world!"
        assert chunks == ["Hello", " world", "!"]
        assert mock_post.called
        
        # Check request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['stream'] is True
        assert payload['model'] == "test-model"
        assert payload['messages'] == messages
    
    @patch('henzai.llm.requests.post')
    def test_streaming_with_no_callback(self, mock_post, llm_client):
        """Test streaming works without callback."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        sse_data = [
            b'data: {"choices":[{"delta":{"content":"Test"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_response.iter_lines.return_value = sse_data
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "test"}]
        result = llm_client._call_ramalama_api_streaming(messages, None)
        
        assert result == "Test"
    
    @patch('henzai.llm.requests.post')
    def test_streaming_handles_empty_content(self, mock_post, llm_client):
        """Test that streaming handles chunks with empty content."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        sse_data = [
            b'data: {"choices":[{"delta":{"content":""}}]}\n',
            b'data: {"choices":[{"delta":{"content":"Content"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_response.iter_lines.return_value = sse_data
        mock_post.return_value = mock_response
        
        chunks = []
        result = llm_client._call_ramalama_api_streaming(
            [{"role": "user", "content": "test"}],
            lambda c: chunks.append(c)
        )
        
        # Empty content should not trigger callback
        assert result == "Content"
        assert chunks == ["Content"]
    
    @patch('henzai.llm.requests.post')
    def test_streaming_handles_invalid_json(self, mock_post, llm_client):
        """Test that streaming gracefully handles invalid JSON chunks."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        sse_data = [
            b'data: {"choices":[{"delta":{"content":"Valid"}}]}\n',
            b'data: {invalid json}\n',  # Should be skipped
            b'data: {"choices":[{"delta":{"content":" chunk"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_response.iter_lines.return_value = sse_data
        mock_post.return_value = mock_response
        
        result = llm_client._call_ramalama_api_streaming(
            [{"role": "user", "content": "test"}],
            None
        )
        
        assert result == "Valid chunk"
    
    @patch('henzai.llm.requests.post')
    def test_streaming_api_error(self, mock_post, llm_client):
        """Test handling of API errors during streaming."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = llm_client._call_ramalama_api_streaming(
            [{"role": "user", "content": "test"}],
            None
        )
        
        assert "Error calling LLM" in result
        assert "500" in result
    
    @patch('henzai.llm.requests.post')
    def test_streaming_connection_error(self, mock_post, llm_client):
        """Test handling of connection errors."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        result = llm_client._call_ramalama_api_streaming(
            [{"role": "user", "content": "test"}],
            None
        )
        
        assert "Cannot connect to Ramalama" in result
    
    @patch('henzai.llm.requests.post')
    def test_streaming_timeout_error(self, mock_post, llm_client):
        """Test handling of timeout errors."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        result = llm_client._call_ramalama_api_streaming(
            [{"role": "user", "content": "test"}],
            None
        )
        
        assert "timed out" in result
    
    def test_stop_generation_with_active_request(self, llm_client):
        """Test stopping generation with an active request."""
        # Create a mock request
        mock_request = Mock()
        llm_client._current_request = mock_request
        
        llm_client.stop_current_generation()
        
        # Verify request was closed
        mock_request.close.assert_called_once()
        assert llm_client._current_request is None
    
    def test_stop_generation_without_active_request(self, llm_client):
        """Test stopping generation when no request is active."""
        llm_client._current_request = None
        
        # Should not raise an error
        llm_client.stop_current_generation()
        
        assert llm_client._current_request is None
    
    def test_stop_generation_handles_close_error(self, llm_client):
        """Test that stop_generation handles errors when closing."""
        mock_request = Mock()
        mock_request.close.side_effect = Exception("Close error")
        llm_client._current_request = mock_request
        
        # Should not raise, just log the error
        try:
            llm_client.stop_current_generation()
        except Exception as e:
            pytest.fail(f"stop_current_generation should handle close errors, but raised: {e}")
        
        # Request should still be cleared even if close fails
        assert llm_client._current_request is None
    
    @patch('henzai.llm.requests.post')
    def test_generate_response_streaming_integration(self, mock_post, llm_client):
        """Test the high-level generate_response_streaming method."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        sse_data = [
            b'data: {"choices":[{"delta":{"content":"Response"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_response.iter_lines.return_value = sse_data
        mock_post.return_value = mock_response
        
        chunks = []
        result = llm_client.generate_response_streaming(
            "Test message",
            context=[],
            chunk_callback=lambda c: chunks.append(c)
        )
        
        assert result == "Response"
        assert chunks == ["Response"]
    
    @patch('henzai.llm.requests.post')
    def test_streaming_sets_current_request(self, mock_post, llm_client):
        """Test that streaming sets and clears _current_request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [b'data: [DONE]\n']
        mock_post.return_value = mock_response
        
        assert llm_client._current_request is None
        
        llm_client._call_ramalama_api_streaming(
            [{"role": "user", "content": "test"}],
            None
        )
        
        # Should be cleared after completion
        assert llm_client._current_request is None
    
    @patch('henzai.llm.requests.post')
    def test_streaming_multiline_response(self, mock_post, llm_client):
        """Test streaming with newlines in content."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        sse_data = [
            b'data: {"choices":[{"delta":{"content":"Line 1\\n"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"Line 2\\n"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"Line 3"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_response.iter_lines.return_value = sse_data
        mock_post.return_value = mock_response
        
        result = llm_client._call_ramalama_api_streaming(
            [{"role": "user", "content": "test"}],
            None
        )
        
        assert result == "Line 1\nLine 2\nLine 3"
    
    @patch('henzai.llm.requests.post')
    def test_streaming_with_context(self, mock_post, llm_client):
        """Test streaming includes conversation context."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [b'data: [DONE]\n']
        mock_post.return_value = mock_response
        
        context = [
            {'user': 'Hello', 'assistant': 'Hi there'},
            {'user': 'How are you?', 'assistant': 'Good!'}
        ]
        
        llm_client.generate_response_streaming(
            "New message",
            context=context,
            chunk_callback=None
        )
        
        # Check that context was included in messages
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        messages = payload['messages']
        
        # Should have system + context + current message
        assert len(messages) == 6  # system + 2*2 context + current
        assert messages[1]['content'] == 'Hello'
        assert messages[2]['content'] == 'Hi there'

