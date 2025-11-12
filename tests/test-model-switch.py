#!/usr/bin/env python3
"""Test model switching with automatic Ramalama restart"""

from dasbus.connection import SessionMessageBus
from dasbus.error import DBusError
import time

SERVICE_NAME = "org.gnome.henzai"
OBJECT_PATH = "/org/gnome/henzai"

bus = SessionMessageBus()
proxy = bus.get_proxy(SERVICE_NAME, OBJECT_PATH)

print("=== henzai Model Switching Test ===\n")

try:
    # Get current model
    current = proxy.GetCurrentModel()
    print(f"Current model: {current}")
    
    # List available models
    models_json = proxy.ListModels()
    import json
    models = json.loads(models_json)
    print(f"\nAvailable models: {len(models)}")
    for model in models[:5]:  # Show first 5
        print(f"  - {model['id']} ({model.get('name', 'unknown')})")
    
    print("\n--- Testing Model Switch ---")
    print("Note: This will restart Ramalama, which takes a few seconds")
    print("(Not actually switching for this test to avoid disruption)")
    
    # Uncomment to actually test switching:
    # result = proxy.SetModel("llama3.2")
    # print(f"\nResult: {result}")
    
except DBusError as e:
    print(f"Error: {e}")

