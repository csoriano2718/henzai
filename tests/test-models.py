#!/usr/bin/env python3
"""
Test model listing and selection via D-Bus
"""
import sys
import json
from dasbus.connection import SessionMessageBus

def main():
    print("🧪 Testing Model Selection D-Bus methods...\n")
    
    try:
        # Connect to daemon
        bus = SessionMessageBus()
        proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
        print("✅ Connected to henzai daemon")
        
        # Get current model
        print("\n📋 Current model:")
        current = proxy.GetCurrentModel()
        print(f"   {current}")
        
        # List available models
        print("\n📋 Available models:")
        models_json = proxy.ListModels()
        models = json.loads(models_json)
        
        if not models:
            print("   ⚠️  No models found")
        else:
            for i, model in enumerate(models):
                size_mb = model['size'] / (1024 * 1024) if model['size'] > 0 else 0
                params_b = model['params'] / 1e9 if model['params'] > 0 else 0
                print(f"   {i+1}. {model['name']}")
                print(f"      ID: {model['id']}")
                print(f"      Size: {size_mb:.1f} MB")
                if params_b > 0:
                    print(f"      Parameters: {params_b:.1f}B")
                print()
        
        # Test model switching
        if models and len(models) > 0:
            test_model = models[0]['id']
            print(f"\n🔄 Testing model switch to: {test_model}")
            status = proxy.SetModel(test_model)
            print(f"   {status}")
            
            # Verify change
            new_current = proxy.GetCurrentModel()
            print(f"   New current model: {new_current}")
            
            if new_current == test_model:
                print("   ✅ Model switch successful!")
            else:
                print(f"   ⚠️  Model mismatch: expected {test_model}, got {new_current}")
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

