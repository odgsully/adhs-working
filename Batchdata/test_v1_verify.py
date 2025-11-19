#!/usr/bin/env python3
"""
Verify BatchData API v1 endpoint works with your API key.
Run: python3 Batchdata/test_v1_verify.py
"""

import os
import requests
import json
from datetime import datetime

print(f"\n{'='*60}")
print(f"BatchData v1 API Verification Test")
print(f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}")
print(f"{'='*60}\n")

# Get API key
api_key = os.getenv('BD_SKIPTRACE_KEY')
if not api_key:
    print("❌ BD_SKIPTRACE_KEY not set")
    print("Run: export BD_SKIPTRACE_KEY='your-key'")
    exit(1)

print(f"✅ API Key: {api_key[:10]}...")

# Test v1 endpoint (correct)
url = "https://api.batchdata.com/api/v1/property/skip-trace"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

test_request = {
    "requests": [{
        "requestId": "verify_001",
        "propertyAddress": {
            "street": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip": "85001"
        }
    }]
}

print(f"\nTesting: {url}")
print(f"Request: {json.dumps(test_request, indent=2)}")

try:
    response = requests.post(url, json=test_request, headers=headers, timeout=30)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        print("✅ SUCCESS - v1 API endpoint works!")
        data = response.json()
        print(f"\nResponse preview:\n{json.dumps(data, indent=2)[:500]}")
    elif response.status_code == 403:
        print("❌ 403 Forbidden")
        print(f"Response: {response.text}")
        print("\nCheck:")
        print("1. API key has skip-trace permission")
        print("2. Account has credits")
    else:
        print(f"❌ Error {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n{'='*60}")
