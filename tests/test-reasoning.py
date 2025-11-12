#!/usr/bin/env python3
"""Test reasoning mode functionality"""

from dasbus.connection import SessionMessageBus
from dasbus.error import DBusError
import time

SERVICE_NAME = "org.gnome.henzai"
OBJECT_PATH = "/org/gnome/henzai"

bus = SessionMessageBus()
proxy = bus.get_proxy(SERVICE_NAME, OBJECT_PATH)

print("=== henzai Reasoning Mode Test ===\n")

# Check if model supports reasoning
try:
    supports = proxy.SupportsReasoning()
    print(f"Current model supports reasoning: {supports}")
    
    if supports:
        # Enable reasoning
        result = proxy.SetReasoningEnabled(True)
        print(f"Enable reasoning: {result}")
        
        enabled = proxy.GetReasoningEnabled()
        print(f"Reasoning enabled: {enabled}\n")
        
        print("Note: Reasoning detection works with models like:")
        print("  - DeepSeek-R1")
        print("  - Qwen-QwQ")
        print("  - Claude with extended thinking")
        print("\nThe model must output <think> or <reasoning> tags for it to work.")
    else:
        model = proxy.GetCurrentModel()
        print(f"\nModel '{model}' does not support reasoning mode")
        print("Reasoning mode requires models like:")
        print("  - deepseek-r1 or deepseek-reasoner")
        print("  - qwen-qwq or qwq")
        print("  - o1, o3")
        print("  - claude-3-5-sonnet or claude-3-opus")
        
except DBusError as e:
    print(f"Error: {e}")

