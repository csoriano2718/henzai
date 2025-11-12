#!/usr/bin/env python3
"""
Live D-Bus streaming test that actually waits for completion.
This test will catch timeout issues by streaming a long response.
"""

import sys
import time
from dasbus.connection import SessionMessageBus
from dasbus.loop import EventLoop

def test_long_streaming():
    """Test streaming with a query that takes 30+ seconds."""
    print("=" * 70)
    print("LIVE D-BUS STREAMING TEST - Will wait for full response")
    print("=" * 70)
    
    bus = SessionMessageBus()
    
    try:
        # Get henzai proxy
        proxy = bus.get_proxy(
            "org.gnome.henzai",
            "/org/gnome/henzai"
        )
        
        print("\n✅ Connected to henzai daemon")
        
        # Track chunks
        chunks_received = []
        thinking_chunks_received = []
        last_chunk_time = None
        
        def on_response_chunk(chunk):
            nonlocal last_chunk_time
            last_chunk_time = time.time()
            chunks_received.append(chunk)
            print(f"📦 Response chunk #{len(chunks_received)}: {chunk[:30]}..." if len(chunk) > 30 else f"📦 Response chunk #{len(chunks_received)}: {chunk}")
        
        def on_thinking_chunk(chunk):
            nonlocal last_chunk_time
            last_chunk_time = time.time()
            thinking_chunks_received.append(chunk)
            print(f"🧠 Thinking chunk #{len(thinking_chunks_received)}: {chunk[:30]}..." if len(chunk) > 30 else f"🧠 Thinking chunk #{len(thinking_chunks_received)}: {chunk}")
        
        # Subscribe to signals
        proxy.ResponseChunk.connect(on_response_chunk)
        proxy.ThinkingChunk.connect(on_thinking_chunk)
        
        print("\n🎯 Sending long reasoning query...")
        print("   Query: 'Explain Zeno's paradox in detail with mathematical analysis'")
        print("   Expected: 30+ seconds with reasoning")
        print("\n" + "-" * 70)
        
        start_time = time.time()
        last_chunk_time = start_time
        
        # Create event loop to keep receiving signals
        loop = EventLoop()
        
        # Send message in a separate thread
        def send_message():
            try:
                status = proxy.SendMessageStreaming("Explain Zeno's paradox in detail with mathematical analysis")
                elapsed = time.time() - start_time
                
                print("\n" + "-" * 70)
                print(f"\n✅ COMPLETED!")
                print(f"   Status: {status}")
                print(f"   Time: {elapsed:.2f}s")
                print(f"   Response chunks: {len(chunks_received)}")
                print(f"   Thinking chunks: {len(thinking_chunks_received)}")
                
                if elapsed > 25:
                    print(f"\n🎉 SUCCESS: Streamed for {elapsed:.2f}s > 25s (default timeout)")
                    print("   No timeout error occurred!")
                else:
                    print(f"\n⚠️  Completed too fast ({elapsed:.2f}s) to test timeout")
                
                loop.quit()
                
            except Exception as e:
                elapsed = time.time() - start_time
                print("\n" + "-" * 70)
                print(f"\n❌ ERROR after {elapsed:.2f}s:")
                print(f"   {e}")
                
                if "timeout" in str(e).lower():
                    print("\n🔴 TIMEOUT ERROR DETECTED!")
                    print(f"   The D-Bus call timed out after ~{elapsed:.2f}s")
                    print(f"   Response chunks before timeout: {len(chunks_received)}")
                    print(f"   Thinking chunks before timeout: {len(thinking_chunks_received)}")
                
                import traceback
                traceback.print_exc()
                loop.quit()
        
        # Run in event loop
        import threading
        thread = threading.Thread(target=send_message)
        thread.daemon = True
        thread.start()
        
        # Monitor for stalled stream
        def check_activity():
            if last_chunk_time and (time.time() - last_chunk_time) > 60:
                print(f"\n⚠️  No chunks for 60s, stream may be stalled")
                print(f"   Last chunk at: {time.time() - last_chunk_time:.1f}s ago")
            return True
        
        # Check every 5 seconds
        from gi.repository import GLib
        GLib.timeout_add_seconds(5, check_activity)
        
        # Run event loop (will process signals)
        print("   Listening for chunks...\n")
        loop.run()
        
        # Wait for thread
        thread.join(timeout=1)
        
        return 0 if len(chunks_received) > 0 else 1
        
    except Exception as e:
        print(f"\n❌ Setup error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_long_streaming())

