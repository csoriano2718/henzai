#!/usr/bin/env python3
"""
Simple streaming test that waits for signals.
"""

import sys
import time
from dasbus.connection import SessionMessageBus
from gi.repository import GLib

chunks = []
thinking = []
start_time = None

def on_chunk(chunk):
    chunks.append(chunk)
    if len(chunks) % 50 == 0:
        print(f"  📦 {len(chunks)} response chunks...")

def on_thinking(chunk):
    thinking.append(chunk)
    if len(thinking) % 50 == 0:
        print(f"  🧠 {len(thinking)} thinking chunks...")

def main():
    global start_time
    bus = SessionMessageBus()
    
    print("🔌 Connecting to henzai daemon...")
    proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
    
    # Connect signals
    proxy.ResponseChunk.connect(on_chunk)
    proxy.ThinkingChunk.connect(on_thinking)
    
    print("✅ Connected!")
    print("\n📤 Sending message...")
    start_time = time.time()
    
    status = proxy.SendMessageStreaming("Say hello in 3 words")
    print(f"📬 Method returned: {status}")
    print("⏳ Waiting for signals (will timeout after 10s of no activity)...\n")
    
    # Wait for signals with timeout
    last_count = 0
    timeout_counter = 0
    
    while timeout_counter < 10:  # 10 seconds of no new chunks = done
        time.sleep(1)
        current_count = len(chunks) + len(thinking)
        
        if current_count > last_count:
            last_count = current_count
            timeout_counter = 0  # Reset timeout
        else:
            timeout_counter += 1
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ Completed after {elapsed:.1f}s")
    print(f"   Response chunks: {len(chunks)}")
    print(f"   Thinking chunks: {len(thinking)}")
    
    if len(chunks) > 0:
        full = ''.join(chunks)
        print(f"\n💬 Response:\n{full[:200]}...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())




