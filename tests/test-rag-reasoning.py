#!/usr/bin/env python3
"""
RAG + Reasoning Integration Test

Tests that reasoning models work correctly with RAG enabled:
- Reasoning content is preserved through RAG proxy
- Strict mode still enforces document-only responses
- Reasoning appears for both in-context and out-of-context queries
"""

import sys
import time
import json
import subprocess
from pathlib import Path


def log(message, status="INFO"):
    """Log test message"""
    symbol = {
        "INFO": "ℹ️",
        "PASS": "✅",
        "FAIL": "❌",
        "WARN": "⚠️"
    }.get(status, "•")
    print(f"{symbol} {message}")


def check_service_running():
    """Check if henzai-daemon is running"""
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "henzai-daemon"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def check_ramalama_has_rag():
    """Check if ramalama is running with RAG enabled"""
    result = subprocess.run(
        ["systemctl", "--user", "cat", "ramalama.service"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.strip().startswith("ExecStart=") and "--rag" in line:
                return True
    return False


def get_current_model():
    """Get the currently running model"""
    result = subprocess.run(
        ["systemctl", "--user", "cat", "ramalama.service"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.strip().startswith("ExecStart="):
                # Model is the last argument
                parts = line.strip().split()
                if len(parts) > 0:
                    return parts[-1]
    return None


def test_api_streaming(query, expect_reasoning=True):
    """Test API directly with streaming to check for reasoning_content"""
    log(f"Testing API with query: {query}")
    
    # Build curl command
    cmd = [
        "curl", "-s",
        "http://127.0.0.1:8080/v1/chat/completions",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "messages": [{"role": "user", "content": query}],
            "stream": True
        })
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            log(f"API call failed: {result.stderr}", "FAIL")
            return False
        
        # Check for reasoning_content in response
        has_reasoning = "reasoning_content" in result.stdout and \
                       'reasoning_content":null' not in result.stdout or \
                       'reasoning_content":""' not in result.stdout
        
        # Count chunks with actual reasoning content (not null/empty)
        reasoning_chunks = 0
        for line in result.stdout.splitlines():
            if "reasoning_content" in line and \
               "null" not in line and \
               '""' not in line:
                reasoning_chunks += 1
        
        if expect_reasoning:
            if reasoning_chunks > 5:  # Should have multiple reasoning chunks
                log(f"Found {reasoning_chunks} reasoning chunks", "PASS")
                return True
            else:
                log(f"Expected reasoning but found only {reasoning_chunks} chunks", "FAIL")
                return False
        else:
            if reasoning_chunks == 0:
                log("Correctly no reasoning for non-reasoning model", "PASS")
                return True
            else:
                log(f"Unexpected reasoning chunks: {reasoning_chunks}", "FAIL")
                return False
                
    except subprocess.TimeoutExpired:
        log("API call timeout", "FAIL")
        return False
    except Exception as e:
        log(f"API test error: {e}", "FAIL")
        return False


def test_strict_mode_with_reasoning():
    """Test that strict mode works with reasoning models"""
    log("Testing strict mode with reasoning model")
    
    # Enable RAG in strict mode
    result = subprocess.run(
        ["busctl", "--user", "call",
         "org.gnome.henzai", "/org/gnome/henzai", "org.gnome.henzai",
         "SetRagEnabled", "bs", "true", "strict"],
        capture_output=True, text=True, timeout=5
    )
    
    if result.returncode != 0:
        log("Failed to enable strict mode", "FAIL")
        return False
    
    time.sleep(3)
    
    # Query something not in documents
    log("Query: What is the capital of Germany?")
    cmd = [
        "curl", "-s",
        "http://127.0.0.1:8080/v1/chat/completions",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "messages": [{"role": "user", "content": "What is the capital of Germany?"}],
            "stream": False
        })
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    
    if result.returncode != 0:
        log("API call failed", "FAIL")
        return False
    
    try:
        response_data = json.loads(result.stdout)
        content = response_data["choices"][0]["message"]["content"].lower()
        
        # Should say "I don't know" in strict mode
        if "don't know" in content or "not in" in content:
            log(f"Correct strict mode response: {content}", "PASS")
            return True
        else:
            log(f"Expected 'I don't know', got: {content}", "FAIL")
            return False
    except Exception as e:
        log(f"Failed to parse response: {e}", "FAIL")
        return False


def test_augment_mode_with_reasoning():
    """Test that augment mode works with reasoning"""
    log("Testing augment mode with reasoning model")
    
    # Enable RAG in augment mode
    result = subprocess.run(
        ["busctl", "--user", "call",
         "org.gnome.henzai", "/org/gnome/henzai", "org.gnome.henzai",
         "SetRagEnabled", "bs", "true", "augment"],
        capture_output=True, text=True, timeout=5
    )
    
    if result.returncode != 0:
        log("Failed to enable augment mode", "FAIL")
        return False
    
    time.sleep(3)
    
    # Query general knowledge (should work in augment mode)
    return test_api_streaming("What is 17 plus 23?", expect_reasoning=True)


def main():
    """Run RAG + reasoning integration tests"""
    print("="*60)
    print("henzai RAG + Reasoning Integration Test")
    print("="*60)
    print()
    
    results = []
    
    # Check prerequisites
    log("Checking prerequisites...")
    
    if not check_service_running():
        log("henzai-daemon is not running", "FAIL")
        return 1
    
    if not check_ramalama_has_rag():
        log("Ramalama is not running with RAG enabled", "FAIL")
        log("Enable RAG in settings first", "WARN")
        return 1
    
    model = get_current_model()
    log(f"Current model: {model}")
    
    # Check if it's a reasoning model
    if "deepseek-r1" not in model and "qwq" not in model:
        log("Current model is not a reasoning model", "WARN")
        log("Switch to deepseek-r1:14b or similar to test reasoning", "WARN")
        # Don't fail - just warn and test what we can
    
    log("Prerequisites OK")
    print()
    
    # Test 1: Reasoning content passes through RAG proxy
    log("Test 1: Reasoning content with RAG", "INFO")
    result1 = test_api_streaming("What is 25 + 37?", expect_reasoning=True)
    results.append(("Reasoning through RAG", result1))
    print()
    
    # Test 2: Strict mode with reasoning
    log("Test 2: Strict mode enforcement", "INFO")
    result2 = test_strict_mode_with_reasoning()
    results.append(("Strict mode + reasoning", result2))
    print()
    
    # Test 3: Augment mode with reasoning
    log("Test 3: Augment mode with reasoning", "INFO")
    result3 = test_augment_mode_with_reasoning()
    results.append(("Augment mode + reasoning", result3))
    print()
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("="*60)
    print(f"TOTAL: {passed}/{total} tests passed ({passed*100//total if total > 0 else 0}%)")
    print("="*60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

