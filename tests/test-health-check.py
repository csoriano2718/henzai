#!/usr/bin/env python3
"""
Test Ramalama health check and status detection
Tests various scenarios to ensure robust status reporting
"""

import requests
import subprocess
import time
import json
import sys

def print_test(name):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)

def print_result(status, message):
    icon = "✅" if status else "❌"
    print(f"{icon} {message}")

def get_daemon_status():
    """Get status from daemon via D-Bus"""
    result = subprocess.run(
        ['busctl', '--user', 'call', 'org.gnome.henzai', '/org/gnome/henzai', 'org.gnome.henzai', 'GetStatus'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode != 0:
        return None
    # Parse the D-Bus response: s "json_string"
    output = result.stdout.strip()
    if output.startswith('s "') and output.endswith('"'):
        json_str = output[3:-1]
        # Unescape quotes
        json_str = json_str.replace('\\"', '"')
        return json.loads(json_str)
    return None

def check_ramalama_service():
    """Check if ramalama service is running"""
    result = subprocess.run(
        ['systemctl', '--user', 'is-active', 'ramalama.service'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip() == 'active'

def check_api_endpoint(endpoint, method='GET', timeout=2):
    """Check if API endpoint responds"""
    url = f"http://127.0.0.1:8080{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, timeout=timeout)
        else:
            response = requests.post(url, json={}, timeout=timeout)
        return response.status_code, response.text
    except requests.exceptions.ConnectionError:
        return None, "Connection refused/reset"
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def test_health_endpoint_ipv4():
    """Test /health endpoint with IPv4"""
    print_test("Health endpoint with IPv4 (127.0.0.1)")
    
    status_code, response = check_api_endpoint('/health')
    if status_code == 200:
        try:
            data = json.loads(response)
            if data.get('status') == 'ok':
                print_result(True, f"Health check OK: {response}")
                return True
            else:
                print_result(False, f"Unexpected response: {response}")
                return False
        except json.JSONDecodeError:
            print_result(False, f"Invalid JSON: {response}")
            return False
    else:
        print_result(False, f"Status: {status_code}, Response: {response}")
        return False

def test_health_endpoint_ipv6():
    """Test /health endpoint with IPv6 (should fail with pasta)"""
    print_test("Health endpoint with IPv6 (localhost) - Expected to FAIL")
    
    url = "http://localhost:8080/health"
    try:
        response = requests.get(url, timeout=2)
        print_result(False, f"Unexpected success! Status: {response.status_code}")
        return False
    except requests.exceptions.ConnectionError as e:
        if "Connection reset" in str(e) or "Connection refused" in str(e):
            print_result(True, f"Expected failure: {e}")
            return True
        else:
            print_result(False, f"Unexpected error: {e}")
            return False
    except Exception as e:
        print_result(False, f"Unexpected error type: {e}")
        return False

def test_models_endpoint():
    """Test /v1/models endpoint"""
    print_test("Models endpoint")
    
    status_code, response = check_api_endpoint('/v1/models')
    if status_code == 200:
        try:
            data = json.loads(response)
            if 'models' in data or 'data' in data:
                print_result(True, f"Models endpoint OK, got model list")
                return True
            else:
                print_result(False, f"No models in response: {response}")
                return False
        except json.JSONDecodeError:
            print_result(False, f"Invalid JSON: {response}")
            return False
    else:
        print_result(False, f"Status: {status_code}, Response: {response}")
        return False

def test_daemon_status_detection():
    """Test daemon's status detection"""
    print_test("Daemon status detection")
    
    status = get_daemon_status()
    if not status:
        print_result(False, "Could not get daemon status")
        return False
    
    print(f"Daemon status: {json.dumps(status, indent=2)}")
    
    # Check required fields
    required_fields = ['daemon_status', 'ramalama_status', 'ready']
    for field in required_fields:
        if field not in status:
            print_result(False, f"Missing field: {field}")
            return False
    
    # If ramalama service is active, daemon should detect it
    if check_ramalama_service():
        if status['ramalama_status'] != 'ready':
            print_result(False, f"Ramalama is active but daemon reports: {status['ramalama_status']}")
            return False
        if not status['ready']:
            print_result(False, "Ramalama ready but daemon reports not ready")
            return False
    
    print_result(True, "Daemon status detection working correctly")
    return True

def test_model_loading_detection():
    """Test detection during model loading"""
    print_test("Model loading detection (restart ramalama)")
    
    print("Restarting ramalama service...")
    subprocess.run(['systemctl', '--user', 'restart', 'ramalama.service'], check=True)
    
    # Wait a bit for cache to expire
    time.sleep(6)
    
    # Check status multiple times to see the loading -> ready transition
    for i in range(10):
        status = get_daemon_status()
        if status:
            print(f"  Check {i+1}/10: ramalama_status={status['ramalama_status']}, ready={status['ready']}")
            if status['ramalama_status'] == 'ready' and status['ready']:
                print_result(True, f"Model loaded and detected after {i+1} checks")
                return True
        time.sleep(2)
    
    print_result(False, "Model did not become ready within 20 seconds")
    return False

def test_cache_behavior():
    """Test that status is cached appropriately"""
    print_test("Status caching (5 second cache)")
    
    # Get status twice quickly
    status1 = get_daemon_status()
    time.sleep(0.5)
    status2 = get_daemon_status()
    
    if status1 == status2:
        print_result(True, "Status cached correctly (same within 0.5s)")
    else:
        print_result(False, "Status changed too quickly (cache not working?)")
        return False
    
    # Wait for cache to expire and check again
    print("Waiting 6 seconds for cache to expire...")
    time.sleep(6)
    status3 = get_daemon_status()
    
    print_result(True, "Cache expiry test complete")
    return True

def main():
    print("="*60)
    print("RAMALAMA HEALTH CHECK & STATUS DETECTION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Health endpoint with IPv4
    results.append(("IPv4 Health Check", test_health_endpoint_ipv4()))
    
    # Test 2: Health endpoint with IPv6 (should fail)
    results.append(("IPv6 Health Check (expect fail)", test_health_endpoint_ipv6()))
    
    # Test 3: Models endpoint
    results.append(("Models Endpoint", test_models_endpoint()))
    
    # Test 4: Daemon status detection
    results.append(("Daemon Status Detection", test_daemon_status_detection()))
    
    # Test 5: Model loading detection
    results.append(("Model Loading Detection", test_model_loading_detection()))
    
    # Test 6: Cache behavior
    results.append(("Status Caching", test_cache_behavior()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

