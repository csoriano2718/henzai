#!/usr/bin/env python3
"""
End-to-End RAG Testing Suite

Tests RAG functionality including:
- Document indexing
- Query with different modes (augment, strict, hybrid)
- Document relevance
- Mode-specific behavior
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Test configuration
TEST_DOCS_DIR = None
TEST_RESULTS = []


def log(message, status="INFO"):
    """Log test message"""
    symbol = {
        "INFO": "ℹ️",
        "PASS": "✅",
        "FAIL": "❌",
        "WARN": "⚠️"
    }.get(status, "•")
    print(f"{symbol} {message}")


def create_test_documents():
    """Create test documents for RAG indexing"""
    global TEST_DOCS_DIR
    TEST_DOCS_DIR = tempfile.mkdtemp(prefix="henzai-rag-test-")
    
    # Document 1: About henzai project
    doc1 = TEST_DOCS_DIR + "/henzai-info.txt"
    with open(doc1, "w") as f:
        f.write("""
henzai Project Information

henzai is a GNOME Shell extension that provides an AI assistant.
It was created by csoriano and uses Ramalama for model management.
The extension is written in JavaScript (GJS) for the UI and Python for the daemon.
It supports RAG (Retrieval-Augmented Generation) for document-based queries.
The project was started in November 2024.
        """.strip())
    
    # Document 2: Technical details
    doc2 = TEST_DOCS_DIR + "/technical-details.md"
    with open(doc2, "w") as f:
        f.write("""
# henzai Technical Architecture

## Components
- **henzai-daemon**: Python D-Bus service
- **henzai-extension**: GNOME Shell extension (GJS)
- **Ramalama**: LLM server backend

## RAG Implementation
- Uses llama.cpp for embeddings
- Stores vectors in ChromaDB
- Supports three modes: augment, strict, hybrid

## D-Bus Interface
- Service: org.gnome.henzai
- Methods: SendMessage, SendMessageStreaming, StopGeneration
- Signals: MessageChunk, MessageComplete, StatusChanged
        """.strip())
    
    # Document 3: Unrelated content (to test relevance)
    doc3 = TEST_DOCS_DIR + "/recipes.txt"
    with open(doc3, "w") as f:
        f.write("""
Chocolate Chip Cookie Recipe

Ingredients:
- 2 cups flour
- 1 cup butter
- 1 cup sugar
- 2 eggs
- 2 cups chocolate chips

Instructions:
1. Mix butter and sugar
2. Add eggs
3. Mix in flour
4. Fold in chocolate chips
5. Bake at 350°F for 12 minutes
        """.strip())
    
    log(f"Created test documents in {TEST_DOCS_DIR}")
    return TEST_DOCS_DIR


def cleanup_test_documents():
    """Remove test documents"""
    global TEST_DOCS_DIR
    if TEST_DOCS_DIR and os.path.exists(TEST_DOCS_DIR):
        shutil.rmtree(TEST_DOCS_DIR)
        log(f"Cleaned up test documents")


def call_dbus_method(method, *args):
    """Call D-Bus method and return output"""
    import subprocess
    
    # Build busctl command
    cmd = ["busctl", "--user", "call", 
           "org.gnome.henzai", 
           "/org/gnome/henzai", 
           "org.gnome.henzai", 
           method]
    
    # Build signature and values
    signature = ""
    values = []
    
    for arg in args:
        if isinstance(arg, str):
            signature += "s"
            values.append(arg)
        elif isinstance(arg, bool):
            signature += "b"
            values.append("true" if arg else "false")
        elif isinstance(arg, int):
            signature += "i"
            values.append(str(arg))
    
    if signature:
        cmd.append(signature)
        cmd.extend(values)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)


def check_service_running():
    """Check if henzai-daemon is running"""
    import subprocess
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "henzai-daemon"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def get_rag_status():
    """Get current RAG status"""
    # GetRAGStatus takes source_path and rag_enabled as args
    success, stdout, stderr = call_dbus_method("GetRAGStatus", "", True)
    if success:
        # Parse output: s "status_string"
        parts = stdout.split('"')
        if len(parts) >= 2:
            status_str = parts[1]
            # Parse status string (e.g., "RAG enabled in augment mode")
            if "enabled" in status_str.lower():
                # Extract mode
                if "augment" in status_str.lower():
                    return "enabled", "augment"
                elif "strict" in status_str.lower():
                    return "enabled", "strict"
                elif "hybrid" in status_str.lower():
                    return "enabled", "hybrid"
                return "enabled", "unknown"
            else:
                return "disabled", None
    return None, None


def test_service_running():
    """Test 1: Verify henzai-daemon is running"""
    log("Test 1: Check henzai-daemon service", "INFO")
    
    if check_service_running():
        log("henzai-daemon is running", "PASS")
        TEST_RESULTS.append(("Service Running", True))
        return True
    else:
        log("henzai-daemon is NOT running - start it first!", "FAIL")
        TEST_RESULTS.append(("Service Running", False))
        return False


def test_rag_indexing():
    """Test 2: Index test documents"""
    log("Test 2: Index test documents", "INFO")
    
    docs_dir = create_test_documents()
    
    # Call SetRAGConfig method (folder_path, format, enable_ocr)
    # format: RAG database format (qdrant/json/markdown/milvus)
    # enable_ocr: false
    log(f"Indexing documents from {docs_dir}")
    success, stdout, stderr = call_dbus_method("SetRAGConfig", docs_dir, "markdown", False)
    
    if not success:
        log(f"Failed to index documents: {stderr}", "FAIL")
        TEST_RESULTS.append(("RAG Indexing", False))
        return False
    
    # Wait for indexing to complete (ramalama rag can take time)
    log("Waiting for indexing to complete...")
    time.sleep(15)
    
    # Check RAG status
    status, mode = get_rag_status()
    if status == "enabled":
        log(f"RAG indexing completed (mode: {mode})", "PASS")
        TEST_RESULTS.append(("RAG Indexing", True))
        return True
    else:
        log(f"RAG status is '{status}' (expected 'enabled')", "FAIL")
        TEST_RESULTS.append(("RAG Indexing", False))
        return False


def test_rag_query(query, expected_keywords, mode="augment", should_find=True):
    """Test RAG query with specific mode"""
    log(f"Query in '{mode}' mode: {query}", "INFO")
    
    # Set RAG mode using SetRagEnabled (enabled, mode)
    success, _, _ = call_dbus_method("SetRagEnabled", True, mode)
    if not success:
        log(f"Failed to set RAG mode to '{mode}'", "WARN")
    
    # Wait for mode change
    time.sleep(2)
    
    # Send query
    success, stdout, stderr = call_dbus_method("SendMessage", query)
    
    if not success:
        log(f"Query failed: {stderr}", "FAIL")
        return False
    
    # Parse response (format: s "response_text")
    response = ""
    if '"' in stdout:
        parts = stdout.split('"')
        if len(parts) >= 2:
            response = parts[1]
    
    if not response:
        log("Empty response received", "FAIL")
        return False
    
    log(f"Response: {response[:200]}...")
    
    # Check if expected keywords are in response
    found_keywords = [kw for kw in expected_keywords if kw.lower() in response.lower()]
    
    if should_find:
        if len(found_keywords) >= len(expected_keywords) // 2:  # At least half
            log(f"Found relevant keywords: {found_keywords}", "PASS")
            return True
        else:
            log(f"Missing expected keywords. Found: {found_keywords}, Expected: {expected_keywords}", "FAIL")
            return False
    else:
        if len(found_keywords) == 0:
            log(f"Correctly avoided irrelevant content", "PASS")
            return True
        else:
            log(f"Response contains irrelevant keywords: {found_keywords}", "FAIL")
            return False


def test_rag_augment_mode():
    """Test 3: RAG augment mode (docs + general knowledge)"""
    log("Test 3: RAG Augment Mode", "INFO")
    
    # Query about henzai (should use docs)
    result1 = test_rag_query(
        "Who created henzai?",
        ["csoriano"],
        mode="augment",
        should_find=True
    )
    
    # Query general knowledge (should still work)
    result2 = test_rag_query(
        "What is Python?",
        ["programming", "language"],
        mode="augment",
        should_find=True
    )
    
    success = result1 and result2
    TEST_RESULTS.append(("RAG Augment Mode", success))
    return success


def test_rag_strict_mode():
    """Test 4: RAG strict mode (docs only)"""
    log("Test 4: RAG Strict Mode", "INFO")
    
    # Query about henzai (should use docs)
    result1 = test_rag_query(
        "What programming languages is henzai written in?",
        ["JavaScript", "Python", "GJS"],
        mode="strict",
        should_find=True
    )
    
    # Query general knowledge (should say "not in documents")
    log("Testing general knowledge query (should fail in strict mode)", "INFO")
    success, stdout, stderr = call_dbus_method("SendMessage", "What is the capital of France?")
    
    if success and '"' in stdout:
        response = stdout.split('"')[1].lower()
        # In strict mode, it should either refuse or not mention Paris
        if "document" in response or "information" not in response or "paris" not in response:
            log("Strict mode correctly limited to documents", "PASS")
            result2 = True
        else:
            log("Strict mode allowed general knowledge (incorrect)", "FAIL")
            result2 = False
    else:
        result2 = False
    
    success = result1 and result2
    TEST_RESULTS.append(("RAG Strict Mode", success))
    return success


def test_rag_hybrid_mode():
    """Test 5: RAG hybrid mode"""
    log("Test 5: RAG Hybrid Mode", "INFO")
    
    # Query about henzai
    result = test_rag_query(
        "What is the architecture of henzai?",
        ["daemon", "extension", "D-Bus", "Python", "JavaScript"],
        mode="hybrid",
        should_find=True
    )
    
    TEST_RESULTS.append(("RAG Hybrid Mode", result))
    return result


def test_rag_relevance():
    """Test 6: Check if RAG returns relevant documents"""
    log("Test 6: Document Relevance", "INFO")
    
    # Query about henzai (should NOT mention cookies)
    success, stdout, stderr = call_dbus_method("SendMessage", "Tell me about henzai")
    
    if success and '"' in stdout:
        response = stdout.split('"')[1].lower()
        
        # Should mention henzai-related terms
        has_relevant = any(term in response for term in ["henzai", "extension", "gnome", "daemon"])
        
        # Should NOT mention cookies
        has_irrelevant = any(term in response for term in ["cookie", "chocolate", "flour", "recipe"])
        
        if has_relevant and not has_irrelevant:
            log("RAG correctly returned relevant documents", "PASS")
            TEST_RESULTS.append(("Document Relevance", True))
            return True
        else:
            log(f"RAG relevance issue: relevant={has_relevant}, irrelevant={has_irrelevant}", "FAIL")
            TEST_RESULTS.append(("Document Relevance", False))
            return False
    
    log("Failed to get response", "FAIL")
    TEST_RESULTS.append(("Document Relevance", False))
    return False


def test_rag_disable():
    """Test 7: Disable RAG and verify"""
    log("Test 7: Disable RAG", "INFO")
    
    success, stdout, stderr = call_dbus_method("DisableRAG")
    
    if not success:
        log(f"Failed to disable RAG: {stderr}", "FAIL")
        TEST_RESULTS.append(("RAG Disable", False))
        return False
    
    # Check status
    status, mode = get_rag_status()
    if status == "disabled":
        log("RAG successfully disabled", "PASS")
        TEST_RESULTS.append(("RAG Disable", True))
        return True
    else:
        log(f"RAG status is '{status}' (expected 'disabled')", "FAIL")
        TEST_RESULTS.append(("RAG Disable", False))
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("RAG E2E TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in TEST_RESULTS if success)
    total = len(TEST_RESULTS)
    
    for test_name, success in TEST_RESULTS:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("="*60)
    print(f"TOTAL: {passed}/{total} tests passed ({passed*100//total}%)")
    print("="*60)
    
    return passed == total


def main():
    """Run all RAG tests"""
    print("="*60)
    print("henzai RAG End-to-End Test Suite")
    print("="*60)
    print()
    
    try:
        # Test 1: Service running
        if not test_service_running():
            log("Cannot continue without henzai-daemon running", "FAIL")
            print_summary()
            return 1
        
        # Test 2: Index documents
        if not test_rag_indexing():
            log("Cannot continue without successful indexing", "FAIL")
            print_summary()
            cleanup_test_documents()
            return 1
        
        # Test 3-5: Test different modes
        test_rag_augment_mode()
        test_rag_strict_mode()
        test_rag_hybrid_mode()
        
        # Test 6: Relevance
        test_rag_relevance()
        
        # Test 7: Disable RAG
        test_rag_disable()
        
        # Print summary
        all_passed = print_summary()
        
        # Cleanup
        cleanup_test_documents()
        
        return 0 if all_passed else 1
        
    except KeyboardInterrupt:
        log("\nTest interrupted by user", "WARN")
        cleanup_test_documents()
        return 2
    except Exception as e:
        log(f"Unexpected error: {e}", "FAIL")
        cleanup_test_documents()
        return 3


if __name__ == "__main__":
    sys.exit(main())

