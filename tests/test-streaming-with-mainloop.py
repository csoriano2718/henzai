#!/usr/bin/env python3
"""
Test D-Bus streaming WITH a GLib main loop.
"""

from dasbus.connection import SessionMessageBus
from gi.repository import GLib
import signal

response_chunks = []
thinking_chunks = []
loop = None

def on_response(chunk):
    response_chunks.append(chunk)
    print(f"  📦 Response chunk #{len(response_chunks)}: {chunk[:30]}...")

def on_thinking(chunk):
    thinking_chunks.append(chunk)
    print(f"  🧠 Thinking chunk #{len(thinking_chunks)}: {chunk[:30]}...")

def timeout_check():
    """Check if we should stop waiting."""
    if len(response_chunks) + len(thinking_chunks) > 0:
        # Got some chunks, wait a bit more
        return True
    return True

def final_timeout():
    """Stop the loop after 20 seconds."""
    print("\n⏱️  Timeout reached, stopping...")
    loop.quit()
    return False

def main():
    global loop
    
    print("🔌 Connecting to henzai daemon...")
    bus = SessionMessageBus()
    proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
    
    # Connect signals
    proxy.ResponseChunk.connect(on_response)
    proxy.ThinkingChunk.connect(on_thinking)
    print("✅ Signals connected!\n")
    
    # Send message
    print("📤 Sending: 'Explain gravity in 20 words'")
    result = proxy.SendMessageStreaming("Explain gravity in 20 words")
    print(f"📬 Method returned: {result}\n")
    print("⏳ Running GLib main loop to receive signals...\n")
    
    # Create and run GLib main loop
    loop = GLib.MainLoop()
    
    # Set a timeout to stop the loop
    GLib.timeout_add_seconds(20, final_timeout)
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: loop.quit())
    
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    
    print(f"\n{'='*60}")
    print(f"✅ Main loop stopped!")
    print(f"   Response chunks: {len(response_chunks)}")
    print(f"   Thinking chunks: {len(thinking_chunks)}")
    
    if len(response_chunks) > 0:
        full = ''.join(response_chunks)
        print(f"\n💬 Full response:\n{full}")

if __name__ == "__main__":
    main()




