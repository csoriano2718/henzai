#!/usr/bin/env python3
"""
Test chat history/sessions via D-Bus
"""
import sys
import json
from dasbus.connection import SessionMessageBus
import time

def main():
    print("🧪 Testing Chat History/Sessions...\n")
    
    try:
        # Connect to daemon
        bus = SessionMessageBus()
        proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
        print("✅ Connected to henzai daemon")
        
        # Send some messages to create history
        print("\n📤 Creating test conversations...")
        proxy.SendMessageStreaming("Remember: my name is Alice")
        time.sleep(1)
        proxy.SendMessageStreaming("What's 2+2?")
        time.sleep(1)
        
        # Start new conversation
        print("\n🔄 Starting new conversation...")
        proxy.NewConversation()
        time.sleep(0.5)
        
        # Send message in new session
        proxy.SendMessageStreaming("Remember: my name is Bob")
        time.sleep(1)
        
        # List sessions
        print("\n📋 Listing saved sessions:")
        sessions_json = proxy.ListSessions(50)
        sessions = json.loads(sessions_json)
        
        if not sessions:
            print("   ⚠️  No sessions found")
        else:
            for i, session in enumerate(sessions):
                print(f"   {i+1}. ID: {session['id']}")
                print(f"      Title: {session['title']}")
                print(f"      Messages: {session['message_count']}")
                print(f"      Updated: {session['updated_at']}")
                print()
        
        # Load first session
        if sessions and len(sessions) > 0:
            session_id = sessions[0]['id']
            print(f"\n📂 Loading session {session_id}...")
            context_json = proxy.LoadSession(session_id)
            context = json.loads(context_json)
            
            print(f"   Loaded {len(context)} messages:")
            for msg in context:
                print(f"   👤 User: {msg['user'][:50]}...")
                print(f"   🤖 Assistant: {msg['assistant'][:50]}...")
                print()
        
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

