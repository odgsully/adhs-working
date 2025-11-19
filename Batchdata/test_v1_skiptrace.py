#!/usr/bin/env python3
"""
BatchData V1 API Test Script
Tests both sync and async endpoints with the V1 API
"""

import os
import sys
import requests
import json
import time
import tempfile
import csv
from pathlib import Path

# Configuration
API_KEY = os.getenv('BD_SKIPTRACE_KEY')
BASE_URL = "https://api.batchdata.com/api/v1"

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)

def test_sync_endpoint():
    """Test V1 sync skip-trace endpoint"""
    print_header("Testing V1 Sync Endpoint")

    url = f"{BASE_URL}/property/skip-trace"
    print(f"URL: {url}")

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    # Test data
    payload = {
        "requests": [{
            "requestId": "test_001",
            "propertyAddress": {
                "street": "123 Main St",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85001"
            },
            "name": {
                "first": "John",
                "last": "Doe"
            }
        }]
    }

    print("\nRequest payload:")
    print(json.dumps(payload, indent=2))

    try:
        print("\nSending request...")
        response = requests.post(url, headers=headers, json=payload)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ V1 Sync endpoint working!")
            print("\nResponse structure:")
            print(json.dumps(result, indent=2))

            # Validate response structure
            if 'result' in result and 'data' in result.get('result', {}):
                data = result['result']['data']
                if data and len(data) > 0:
                    first_result = data[0]
                    print("\n✅ Response has expected structure")
                    print(f"   - requestId echoed: {'input' in first_result}")
                    print(f"   - persons array present: {'persons' in first_result}")

                    if 'persons' in first_result and first_result['persons']:
                        person = first_result['persons'][0]
                        print(f"   - phones present: {'phones' in person}")
                        print(f"   - emails present: {'emails' in person}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")

        return response.status_code == 200

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_async_endpoint():
    """Test V1 async skip-trace endpoint"""
    print_header("Testing V1 Async Endpoint")

    url = f"{BASE_URL}/property/skip-trace/async"
    print(f"URL: {url}")

    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }

    # Create test CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(['record_id', 'first_name', 'last_name', 'address', 'city', 'state', 'zip'])
        writer.writerow(['test_002', 'Jane', 'Smith', '456 Oak Ave', 'Tucson', 'AZ', '85701'])
        csv_path = f.name

    print(f"Created test CSV: {csv_path}")

    try:
        print("\nSending async request...")

        with open(csv_path, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            response = requests.post(url, headers=headers, files=files)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ V1 Async endpoint working!")
            print("\nResponse:")
            print(json.dumps(result, indent=2))

            # Check for job ID
            if 'result' in result and 'jobId' in result.get('result', {}):
                job_id = result['result']['jobId']
                print(f"\n✅ Received Job ID: {job_id}")

                # Test job status endpoint
                status_url = f"{BASE_URL}/jobs/{job_id}"
                print(f"\nTesting job status endpoint: {status_url}")

                status_response = requests.get(status_url, headers=headers)
                if status_response.status_code == 200:
                    print("✅ Job status endpoint working")
                    print(f"Job Status: {json.dumps(status_response.json(), indent=2)}")
                else:
                    print(f"⚠️ Job status returned: {status_response.status_code}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")

        # Clean up
        os.unlink(csv_path)

        return response.status_code == 200

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        if os.path.exists(csv_path):
            os.unlink(csv_path)
        return False

def test_api_connectivity():
    """Basic connectivity test"""
    print_header("Testing API Connectivity")

    # Try a simple authenticated request
    url = f"{BASE_URL}/property/skip-trace"
    headers = {'Authorization': f'Bearer {API_KEY}'}

    print(f"Testing connectivity to: {BASE_URL}")
    print(f"API Key present: {'Yes' if API_KEY else 'No'}")

    if not API_KEY:
        print("❌ No API key found in BD_SKIPTRACE_KEY environment variable")
        return False

    print(f"API Key (first 10 chars): {API_KEY[:10]}...")

    # Test with empty request to check authentication
    try:
        response = requests.post(url, headers=headers, json={"requests": []})
        if response.status_code in [200, 400, 422]:  # These all indicate API is reachable
            print("✅ API is reachable and authentication working")
            return True
        elif response.status_code == 401:
            print("❌ Authentication failed - check API key")
            return False
        elif response.status_code == 404:
            print("❌ Endpoint not found - V1 API may not be available")
            return False
        else:
            print(f"⚠️ Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print_header("BatchData V1 API Test Suite")
    print(f"Base URL: {BASE_URL}")
    print(f"Environment: {os.getenv('ENV', 'production')}")

    if not API_KEY:
        print("\n❌ Error: BD_SKIPTRACE_KEY environment variable not set")
        print("\nTo set it:")
        print("  export BD_SKIPTRACE_KEY='your-api-key-here'")
        sys.exit(1)

    # Run tests
    tests_passed = []

    # Test 1: Connectivity
    if test_api_connectivity():
        tests_passed.append("API Connectivity")

    # Test 2: Sync endpoint
    if test_sync_endpoint():
        tests_passed.append("Sync Endpoint")

    # Test 3: Async endpoint
    if test_async_endpoint():
        tests_passed.append("Async Endpoint")

    # Summary
    print_header("Test Summary")
    print(f"\nTests Passed: {len(tests_passed)}/3")
    for test in tests_passed:
        print(f"  ✅ {test}")

    if len(tests_passed) == 3:
        print("\n🎉 All tests passed! V1 API is working correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())