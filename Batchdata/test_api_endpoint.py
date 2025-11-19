#!/usr/bin/env python3
"""
Direct test of BatchData V2 API endpoint to diagnose 404 error
"""
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

api_key = os.getenv('BD_SKIPTRACE_KEY', '')

if not api_key:
    print("❌ No API key found in environment")
    exit(1)

print("=" * 60)
print("BatchData V2 API Endpoint Test")
print("=" * 60)
print(f"✓ API Key found (starts with: {api_key[:10]}...)")

# Test different possible endpoints
endpoints = [
    "https://api.batchdata.com/api/v2/property/skip-trace/async",
    "https://api.batchdata.com/api/v2/skip-trace/async",
    "https://api.batchdata.com/api/v2/async/skip-trace",
    "https://api.batchdata.com/v2/property/skip-trace/async",
    "https://api.batchdata.com/api/v2/batch/skip-trace",
]

# Create test CSV
test_csv_path = Path(__file__).parent / 'test_api_endpoint.csv'
print(f"\n📄 Using test CSV: {test_csv_path}")

# Test each endpoint
print("\n🔍 Testing different endpoint variations...")
print("-" * 60)

for endpoint in endpoints:
    print(f"\nTesting: {endpoint}")

    try:
        with open(test_csv_path, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            headers = {'Authorization': f'Bearer {api_key}'}

            response = requests.post(endpoint, headers=headers, files=files, timeout=10)

            print(f"  Status Code: {response.status_code}")

            if response.status_code == 200:
                print(f"  ✓ SUCCESS! This is the correct endpoint")
                print(f"  Response: {response.text[:200]}")
                break
            elif response.status_code == 404:
                print(f"  ✗ Not Found - endpoint doesn't exist")
            elif response.status_code == 401:
                print(f"  ✗ Unauthorized - API key issue")
            elif response.status_code == 403:
                print(f"  ✗ Forbidden - might need subscription")
            else:
                print(f"  Response: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error: {e}")

# Also check what the API says about available endpoints
print("\n" + "=" * 60)
print("Checking API base URL for available endpoints...")
print("-" * 60)

try:
    # Try to get API info
    base_urls = [
        "https://api.batchdata.com/api/v2",
        "https://api.batchdata.com/api/v2/",
        "https://api.batchdata.com",
    ]

    for base_url in base_urls:
        print(f"\nChecking: {base_url}")
        headers = {'Authorization': f'Bearer {api_key}'}
        response = requests.get(base_url, headers=headers, timeout=5)
        print(f"  Status: {response.status_code}")
        if response.status_code != 404:
            print(f"  Response: {response.text[:300]}")

except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 60)
print("Test complete. Check results above for correct endpoint.")