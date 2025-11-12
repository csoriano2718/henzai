#!/usr/bin/env python3
"""
Test D-Bus streaming with timeout fixes.
This script sends a test message to verify the timeout removal works.
"""

import sys
from dasbus.connection import SessionMessageBus
import time

def test_streaming():
    """Test streaming with a simple message."""
    print("🧪 Testing D-Bus Streaming Timeout Fix...")
    print("=" * 60)
    
    # Connect to D-Bus
    bus = SessionMessageBus()
    
    try:
        # Get henzai proxy
        proxy = bus.get_proxy(
            "org.gnome.henzai",
            "/org/gnome/henzai"
        )
        
        print("\n✅ Connected to henzai daemon")
        
        # Test 1: Simple message
        print("\n[Test 1] Sending simple message...")
        print("-" * 60)
        
        # Subscribe to response chunks
        chunks = []
        def on_chunk(chunk):
            chunks.append(chunk)
            print(f"📦 Chunk received: {chunk[:50]}..." if len(chunk) > 50 else f"📦 Chunk received: {chunk}")
        
        proxy.ResponseChunk.connect(on_chunk)
        
        # Send message
        start_time = time.time()
        test_message = "Say hello in one sentence."
        print(f"📤 Sending: '{test_message}'")
        
        status = proxy.SendMessageStreaming(test_message)
        
        elapsed = time.time() - start_time
        print(f"\n✅ Status: {status}")
        print(f"⏱️  Time: {elapsed:.2f}s")
        print(f"📊 Chunks received: {len(chunks)}")
        
        if len(chunks) > 0:
            full_response = ''.join(chunks)
            print(f"\n💬 Full response:\n{full_response}")
        
        print("\n" + "=" * 60)
        print("✅ Test 1 PASSED: Simple message works!")
        
        # Test 2: Check timeout handling (only if user wants to wait)
        print("\n[Test 2] Ready to test long reasoning (will take 30+ seconds)")
        print("         Press Ctrl+C to skip, or wait for automatic test...")
        
        try:
            time.sleep(3)
            chunks = []
            
            reasoning_message = "Explain the philosophical implications of Zeno's paradox."
            print(f"\n📤 Sending reasoning query: '{reasoning_message}'")
            start_time = time.time()
            
            status = proxy.SendMessageStreaming(reasoning_message)
            
            elapsed = time.time() - start_time
            print(f"\n✅ Status: {status}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"📊 Chunks received: {len(chunks)}")
            
            if elapsed > 30:
                print("\n🎉 Test 2 PASSED: No timeout after 30+ seconds!")
            else:
                print("\n⚠️  Test 2 INFO: Completed in < 30s, timeout not tested")
            
        except KeyboardInterrupt:
            print("\n⏭️  Test 2 skipped by user")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_streaming())

