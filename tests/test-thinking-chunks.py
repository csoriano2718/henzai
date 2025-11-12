#!/usr/bin/env python3
"""Test if thinking chunks are being emitted by the daemon."""

import sys
import time
from dasbus.connection import SessionMessageBus
from gi.repository import GLib

# Connect to session bus
bus = SessionMessageBus()

# Get proxy to henzai daemon
proxy = bus.get_proxy(
    "org.gnome.henzai",
    "/org/gnome/henzai"
)

print("Connected to henzai daemon")

# Check if reasoning is enabled
try:
    reasoning_enabled = proxy.GetReasoningEnabled()
    print(f"Reasoning enabled: {reasoning_enabled}")
except Exception as e:
    print(f"Error getting reasoning status: {e}")

# Get current model
try:
    model = proxy.GetCurrentModel()
    print(f"Current model: {model}")
except Exception as e:
    print(f"Error getting model: {e}")

# Track received chunks
response_chunks = []
thinking_chunks = []
streaming_complete = False

def on_response_chunk(chunk):
    response_chunks.append(chunk)
    print(f"[RESPONSE] {chunk[:50]}...")

def on_thinking_chunk(chunk):
    thinking_chunks.append(chunk)
    print(f"[THINKING] {chunk[:50]}...")

def on_streaming_complete():
    global streaming_complete
    streaming_complete = True
    print("[COMPLETE] Streaming finished")

# Subscribe to signals
proxy.ResponseChunk.connect(on_response_chunk)
proxy.ThinkingChunk.connect(on_thinking_chunk)
proxy.StreamingComplete.connect(on_streaming_complete)

print("\nSending test query (complex reasoning question)...")
print("Query: 'Explain the Monty Hall problem step by step with your reasoning'")

# Send a message that should trigger reasoning
try:
    proxy.SendMessageStreaming("Explain the Monty Hall problem step by step with your reasoning")
    print("Message sent, waiting for response...\n")
except Exception as e:
    print(f"Error sending message: {e}")
    sys.exit(1)

# Run main loop
loop = GLib.MainLoop()

# Timeout after 60 seconds
def timeout():
    print("\n=== TIMEOUT ===")
    print(f"Received {len(thinking_chunks)} thinking chunks")
    print(f"Received {len(response_chunks)} response chunks")
    print(f"Streaming complete: {streaming_complete}")
    loop.quit()
    return False

GLib.timeout_add_seconds(60, timeout)

# Also stop when streaming completes
def check_complete():
    if streaming_complete:
        print("\n=== RESULTS ===")
        print(f"Thinking chunks: {len(thinking_chunks)}")
        print(f"Response chunks: {len(response_chunks)}")
        if thinking_chunks:
            print(f"\nFirst thinking chunk: {thinking_chunks[0][:100]}")
        else:
            print("\nNO THINKING CHUNKS RECEIVED!")
        loop.quit()
        return False
    return True

GLib.timeout_add(500, check_complete)

try:
    loop.run()
except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    print(f"Received {len(thinking_chunks)} thinking chunks")
    print(f"Received {len(response_chunks)} response chunks")

