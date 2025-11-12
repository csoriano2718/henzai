#!/usr/bin/env python3
"""
Quick test for NewConversation D-Bus method
"""
import sys
from dasbus.connection import SessionMessageBus

def main():
    print("🧪 Testing NewConversation D-Bus method...\n")
    
    try:
        # Connect to daemon
        bus = SessionMessageBus()
        proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
        print("✅ Connected to henzai daemon")
        
        # Send first message
        print("\n📤 Sending message: 'Remember the number 42'")
        proxy.SendMessageStreaming("Remember the number 42")
        print("✅ Message sent")
        
        # Start new conversation
        print("\n🔄 Starting new conversation...")
        status = proxy.NewConversation()
        print(f"✅ {status}")
        
        # Send second message (should not remember 42)
        print("\n📤 Sending message: 'What number did I tell you to remember?'")
        proxy.SendMessageStreaming("What number did I tell you to remember?")
        print("✅ Message sent")
        
        print("\n✅ Test completed!")
        print("💡 Check the assistant's response - it should NOT remember 42")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

