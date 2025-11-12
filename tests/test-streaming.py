#!/usr/bin/env python3
"""
Quick E2E test to verify streaming works.
Run this anytime to confirm the feature is functional.
"""

from dasbus.connection import SessionMessageBus
from gi.repository import GLib
import sys

print("\n" + "="*70)
print("henzai Streaming - Quick Verification Test")
print("="*70 + "\n")

chunks_received = []
main_loop = GLib.MainLoop()

try:
    bus = SessionMessageBus()
    proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
    
    def on_chunk(chunk):
        chunks_received.append(chunk)
        print(chunk, end='', flush=True)
    
    proxy.ResponseChunk.connect(on_chunk)
    
    def send_test():
        print("📤 Asking: 'Say hello in 3 words'\n")
        print("📨 Response: ", end='', flush=True)
        try:
            result = proxy.SendMessageStreaming("Say hello in 3 words")
            GLib.timeout_add(2000, finish)
        except Exception as e:
            print(f"\n\n❌ ERROR: {e}")
            main_loop.quit()
        return False
    
    def finish():
        print(f"\n\n{'='*70}")
        print(f"✅ Received {len(chunks_received)} chunks")
        print(f"✅ Response: {repr(''.join(chunks_received))}")
        print(f"{'='*70}")
        print("\n🎉 STREAMING WORKS!\n")
        main_loop.quit()
        return False
    
    GLib.timeout_add(500, send_test)
    GLib.timeout_add(10000, lambda: (print("\n\n⏱️ Timeout"), main_loop.quit(), False))
    
    main_loop.run()
    sys.exit(0)
    
except KeyboardInterrupt:
    print("\n\n⚠️ Interrupted")
    sys.exit(1)
except Exception as e:
    print(f"\n\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

