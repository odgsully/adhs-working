#!/usr/bin/env python3
"""
Test BatchData API directly to diagnose 403 error
"""

import os
import requests
import json
from datetime import datetime

print(f"\n{'='*60}")
print(f"BatchData API Direct Test")
print(f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}")
print(f"{'='*60}\n")

# Check API keys
api_key = os.getenv('BD_SKIPTRACE_KEY')
if not api_key:
    print("❌ BD_SKIPTRACE_KEY not set in environment")
    exit(1)

print(f"✅ API Key found: {api_key[:10]}...")
print()

# Test request with proper state field
test_request = {
    "requests": [
        {
            "requestId": "test_001",
            "propertyAddress": {
                "street": "8888 E Raintree Drive",
                "city": "Scottsdale",
                "state": "AZ",  # Added proper state
                "zip": "85260"
            },
            "name": {
                "first": "Bruce",
                "last": "Grimm"
            }
        }
    ]
}

print("Request being sent:")
print(json.dumps(test_request, indent=2))
print()

# Make API call
url = "https://api.batchdata.com/api/v1/property/skip-trace"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

print(f"URL: {url}")
print(f"Headers: Authorization: Bearer {api_key[:10]}...")
print()

try:
    print("Making API call...")
    response = requests.post(url, json=test_request, headers=headers, timeout=30)

    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        print("\n✅ SUCCESS! API call worked")
        data = response.json()
        print("\nResponse data:")
        print(json.dumps(data, indent=2)[:1000])  # First 1000 chars

        # Check if we got results
        if 'result' in data and 'data' in data['result']:
            results = data['result']['data']
            print(f"\nGot {len(results)} result(s)")

            if results:
                first_result = results[0]
                if 'persons' in first_result:
                    persons = first_result['persons']
                    print(f"Found {len(persons)} person(s)")

                    for person in persons:
                        if 'phones' in person:
                            print(f"  - {len(person['phones'])} phone(s)")
                        if 'emails' in person:
                            print(f"  - {len(person['emails'])} email(s)")

    elif response.status_code == 403:
        print("\n❌ 403 FORBIDDEN - API key issue")
        print("Response body:")
        print(response.text)

        print("\nPossible issues:")
        print("1. API key is invalid or expired")
        print("2. API key doesn't have skip-trace permissions")
        print("3. Account has insufficient credits")
        print("4. Wrong API key type (need skip-trace specific key)")

    elif response.status_code == 400:
        print("\n❌ 400 BAD REQUEST - Request format issue")
        print("Response body:")
        print(response.text)

    else:
        print(f"\n❌ Unexpected status: {response.status_code}")
        print("Response body:")
        print(response.text)

except requests.exceptions.Timeout:
    print("❌ Request timed out")
except requests.exceptions.RequestException as e:
    print(f"❌ Request error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n" + "="*60)

# Also test what happens with missing state
print("\nTesting with missing state field:")
print("="*60)

bad_request = {
    "requests": [
        {
            "requestId": "test_002",
            "propertyAddress": {
                "street": "8888 E Raintree Drive",
                "city": "Scottsdale",
                "state": "",  # Empty state
                "zip": "85260"
            }
        }
    ]
}

print("Request with empty state:")
print(json.dumps(bad_request, indent=2))

try:
    response = requests.post(url, json=bad_request, headers=headers, timeout=30)
    print(f"\nResponse Status: {response.status_code}")

    if response.status_code != 200:
        print("Response body:")
        print(response.text[:500])

except Exception as e:
    print(f"Error: {e}")