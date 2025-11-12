"""Tests for D-Bus service streaming functionality.

Note: These tests focus on the business logic of streaming rather than
D-Bus signal emission mechanics, as dasbus signals are difficult to mock.
"""

import pytest
from unittest.mock import Mock, patch

from henzai.dbus_service import henzaiService


@pytest.fixture
def mock_llm():
    """Create a mock LLM client."""
    llm = Mock()
    llm.generate_response_streaming = Mock()
    llm.stop_current_generation = Mock()
    return llm


@pytest.fixture
def mock_memory():
    """Create a mock memory store."""
    memory = Mock()
    memory.get_recent_context = Mock(return_value=[])
    memory.add_conversation = Mock()
    return memory


@pytest.fixture
def dbus_service(mock_llm, mock_memory):
    """Create a henzai D-Bus service for testing."""
    with patch('henzai.dbus_service.SessionMessageBus'):
        service = henzaiService(mock_llm, mock_memory)
        return service


class TestDBusStreamingLogic:
    """Test D-Bus streaming business logic."""
    
    def test_service_initializes_with_stop_flag(self, dbus_service):
        """Test that service initializes with stop generation flag."""
        assert hasattr(dbus_service, '_stop_generation')
        assert dbus_service._stop_generation is False
    
    def test_send_message_streaming_calls_llm(self, dbus_service, mock_llm, mock_memory):
        """Test that streaming message calls LLM with correct parameters."""
        mock_llm.generate_response_streaming.return_value = "Response"
        
        result = dbus_service.SendMessageStreaming("Test message")
        
        # Verify LLM was called
        assert result == "OK"
        assert mock_llm.generate_response_streaming.called
        call_args = mock_llm.generate_response_streaming.call_args
        assert call_args[0][0] == "Test message"  # message
        assert callable(call_args[1]['chunk_callback'])  # callback provided
    
    def test_send_message_streaming_sets_thinking_status(self, dbus_service, mock_llm):
        """Test that streaming sets status to 'thinking' then 'ready'."""
        status_during = None
        
        def capture_status(message, context, chunk_callback):
            nonlocal status_during
            status_during = dbus_service.status
            return "Response"
        
        mock_llm.generate_response_streaming.side_effect = capture_status
        
        dbus_service.SendMessageStreaming("Test")
        
        # Status should have been 'thinking' during generation
        assert status_during == "thinking"
        # And 'ready' after
        assert dbus_service.status == "ready"
    
    def test_send_message_streaming_with_context(self, dbus_service, mock_llm, mock_memory):
        """Test that streaming includes conversation context."""
        mock_context = [{'user': 'Previous', 'assistant': 'Response'}]
        mock_memory.get_recent_context.return_value = mock_context
        mock_llm.generate_response_streaming.return_value = "New response"
        
        dbus_service.SendMessageStreaming("New message")
        
        # Verify context was passed
        call_args = mock_llm.generate_response_streaming.call_args
        assert call_args[0][1] == mock_context
    
    def test_send_message_streaming_handles_errors(self, dbus_service, mock_llm):
        """Test error handling in streaming."""
        mock_llm.generate_response_streaming.side_effect = Exception("Test error")
        
        result = dbus_service.SendMessageStreaming("Test")
        
        assert result == "ERROR"
        assert dbus_service.status == "error"
    
    def test_send_message_streaming_with_tool_calls(self, dbus_service, mock_llm, mock_memory):
        """Test streaming with tool calls in response."""
        tool_call_response = 'Sure! <tool_call>{"name": "test_tool", "parameters": {}}</tool_call>'
        
        mock_llm.generate_response_streaming.return_value = tool_call_response
        mock_llm.generate_with_tool_results.return_value = "Tool executed"
        
        with patch.object(dbus_service, '_execute_tool') as mock_execute:
            mock_execute.return_value = {'success': True, 'tool': 'test_tool', 'result': 'OK'}
            
            result = dbus_service.SendMessageStreaming("Test")
            
            assert result == "OK"
            assert mock_execute.called
            mock_memory.add_conversation.assert_called()
    
    def test_stop_generation_sets_flag(self, dbus_service, mock_llm):
        """Test that StopGeneration sets the stop flag."""
        result = dbus_service.StopGeneration()
        
        assert result is True
        assert dbus_service._stop_generation is True
        assert dbus_service.status == "ready"
        mock_llm.stop_current_generation.assert_called_once()
    
    def test_stop_generation_aborts_streaming(self, dbus_service, mock_llm):
        """Test that stop flag causes early return."""
        def mock_stream(message, context, chunk_callback):
            # Simulate stop during streaming
            dbus_service._stop_generation = True
            return "Partial"
        
        mock_llm.generate_response_streaming.side_effect = mock_stream
        
        result = dbus_service.SendMessageStreaming("Test")
        
        # Should detect stop flag and return early
        assert result == "Generation stopped"
    
    def test_stop_flag_resets_on_new_message(self, dbus_service, mock_llm):
        """Test that new message resets stop flag."""
        dbus_service._stop_generation = True
        mock_llm.generate_response_streaming.return_value = "Response"
        
        dbus_service.SendMessageStreaming("New message")
        
        # Should complete successfully (flag was reset)
        assert dbus_service.status == "ready"
    
    def test_response_saves_to_memory(self, dbus_service, mock_llm, mock_memory):
        """Test that complete response is saved to memory."""
        test_message = "Test message"
        test_response = "This is the response"
        
        mock_llm.generate_response_streaming.return_value = test_response
        
        dbus_service.SendMessageStreaming(test_message)
        
        mock_memory.add_conversation.assert_called_once_with(test_message, test_response)
    
    def test_empty_response_still_saves(self, dbus_service, mock_llm, mock_memory):
        """Test that empty responses are still saved."""
        mock_llm.generate_response_streaming.return_value = ""
        
        result = dbus_service.SendMessageStreaming("Test")
        
        assert result == "OK"
        mock_memory.add_conversation.assert_called_once()
    
    def test_callback_receives_chunks(self, dbus_service, mock_llm):
        """Test that chunk callback is invoked properly."""
        chunks_received = []
        
        def mock_stream(message, context, chunk_callback):
            chunk_callback("chunk1")
            chunk_callback("chunk2")
            return "chunk1chunk2"
        
        mock_llm.generate_response_streaming.side_effect = mock_stream
        
        result = dbus_service.SendMessageStreaming("Test")
        
        # Just verify it completed successfully
        # (we can't easily test signal emission with dasbus)
        assert result == "OK"


class TestDBusStreamingIntegration:
    """Integration tests for D-Bus streaming."""
    
    def test_full_workflow(self, dbus_service, mock_llm, mock_memory):
        """Test complete streaming workflow."""
        test_message = "Hello"
        test_response = "Hi there"
        test_context = [{'user': 'prev', 'assistant': 'resp'}]
        
        mock_memory.get_recent_context.return_value = test_context
        mock_llm.generate_response_streaming.return_value = test_response
        
        # Execute
        result = dbus_service.SendMessageStreaming(test_message)
        
        # Verify all steps
        assert result == "OK"
        mock_memory.get_recent_context.assert_called_once()
        mock_llm.generate_response_streaming.assert_called_once()
        mock_memory.add_conversation.assert_called_once_with(test_message, test_response)
        assert dbus_service.status == "ready"
    
    def test_error_recovery(self, dbus_service, mock_llm):
        """Test that service recovers from errors."""
        # First request fails
        mock_llm.generate_response_streaming.side_effect = Exception("Error")
        result1 = dbus_service.SendMessageStreaming("First")
        assert result1 == "ERROR"
        assert dbus_service.status == "error"
        
        # Second request succeeds
        mock_llm.generate_response_streaming.side_effect = None
        mock_llm.generate_response_streaming.return_value = "Success"
        result2 = dbus_service.SendMessageStreaming("Second")
        assert result2 == "OK"
        assert dbus_service.status == "ready"
