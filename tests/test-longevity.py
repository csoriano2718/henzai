#!/usr/bin/env python3
"""
Longevity test for henzai streaming with a complex reasoning query.

This test sends a query that should generate a long response with extensive
reasoning, perfect for testing:
- Long-running D-Bus connections
- Extended streaming (several minutes)
- Large amounts of thinking/reasoning chunks
- No timeouts during extended operations
"""

from dasbus.connection import SessionMessageBus
from gi.repository import GLib
import signal
import time

response_chunks = []
thinking_chunks = []
loop = None
start_time = None

def on_response(chunk):
    response_chunks.append(chunk)
    if len(response_chunks) % 50 == 0:
        elapsed = time.time() - start_time
        print(f"  📦 {len(response_chunks)} response chunks ({elapsed:.1f}s elapsed)")

def on_thinking(chunk):
    thinking_chunks.append(chunk)
    if len(thinking_chunks) % 100 == 0:
        elapsed = time.time() - start_time
        print(f"  🧠 {len(thinking_chunks)} thinking chunks ({elapsed:.1f}s elapsed)")

def timeout_check():
    """Check if we should stop waiting (no new chunks for 10 seconds)."""
    global last_chunk_time
    
    if time.time() - last_chunk_time > 10:
        print("\n⏱️  No new chunks for 10s, assuming complete...")
        loop.quit()
        return False
    
    return True

def update_last_chunk_time():
    """Update the last chunk timestamp."""
    global last_chunk_time
    last_chunk_time = time.time()

def final_timeout():
    """Hard timeout after 5 minutes."""
    print("\n⏱️  Hard timeout (5 minutes) reached, stopping...")
    loop.quit()
    return False

def main():
    global loop, start_time, last_chunk_time
    
    print("="*70)
    print("henzai LONGEVITY TEST - Complex Reasoning Query")
    print("="*70)
    print()
    
    print("🔌 Connecting to henzai daemon...")
    bus = SessionMessageBus()
    proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
    
    # Wrap callbacks to update last chunk time
    def response_callback(chunk):
        update_last_chunk_time()
        on_response(chunk)
    
    def thinking_callback(chunk):
        update_last_chunk_time()
        on_thinking(chunk)
    
    # Connect signals
    proxy.ResponseChunk.connect(response_callback)
    proxy.ThinkingChunk.connect(thinking_callback)
    print("✅ Signals connected!\n")
    
    # The big test query - should generate extensive reasoning and a long response
    query = """Write a comprehensive 5-page blog post brainstorming about Zeno's Paradox of Infinite Splits (Dichotomy Paradox). 

The post should:
1. Explain the paradox clearly with examples
2. Discuss historical context and Zeno's intent
3. Explore mathematical resolutions (infinite series, calculus)
4. Cover philosophical implications for motion and infinity
5. Present modern interpretations and relevance
6. Include thought experiments and analogies
7. Address common misconceptions
8. Conclude with insights about infinity and reality

Please be thorough and detailed, making this suitable for an educated audience interested in philosophy and mathematics."""
    
    # Send message
    print("📤 Sending longevity test query:")
    print(f"   '{query[:100]}...'")
    print()
    start_time = time.time()
    last_chunk_time = start_time
    
    result = proxy.SendMessageStreaming(query)
    print(f"📬 Method returned: {result}")
    print()
    print("⏳ Running GLib main loop to receive streaming response...")
    print("   Expected: Several minutes of reasoning + extensive response")
    print("   This tests long-running D-Bus connections and streaming\n")
    
    # Create and run GLib main loop
    loop = GLib.MainLoop()
    
    # Check for completion every 2 seconds
    GLib.timeout_add_seconds(2, timeout_check)
    
    # Hard timeout after 5 minutes
    GLib.timeout_add_seconds(300, final_timeout)
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: loop.quit())
    
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    
    # Calculate stats
    elapsed = time.time() - start_time
    full_response = ''.join(response_chunks)
    full_thinking = ''.join(thinking_chunks)
    
    print(f"\n{'='*70}")
    print(f"✅ LONGEVITY TEST COMPLETED!")
    print(f"{'='*70}")
    print(f"   Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"   Response chunks: {len(response_chunks)}")
    print(f"   Thinking chunks: {len(thinking_chunks)}")
    print(f"   Response length: {len(full_response)} chars ({len(full_response.split())} words)")
    print(f"   Thinking length: {len(full_thinking)} chars")
    print(f"\n   Average chunks/second: {(len(response_chunks) + len(thinking_chunks)) / elapsed:.1f}")
    
    # Estimate pages (roughly 500 words per page)
    pages = len(full_response.split()) / 500
    print(f"   Estimated pages: {pages:.1f}")
    
    print(f"\n{'='*70}")
    
    if len(response_chunks) > 1000:
        print("🎉 SUCCESS: Long-running streaming worked perfectly!")
    else:
        print("⚠️  WARNING: Response seems short, may have been interrupted")
    
    # Show a preview
    if len(full_response) > 0:
        print(f"\n📄 Response preview (first 500 chars):")
        print("-" * 70)
        print(full_response[:500])
        if len(full_response) > 500:
            print("...")
        print("-" * 70)
    
    # Show thinking preview if available
    if len(full_thinking) > 0:
        print(f"\n🧠 Thinking preview (first 300 chars):")
        print("-" * 70)
        print(full_thinking[:300])
        if len(full_thinking) > 300:
            print("...")
        print("-" * 70)
    
    return 0 if len(response_chunks) > 100 else 1

if __name__ == "__main__":
    exit(main())




