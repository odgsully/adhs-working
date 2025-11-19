#!/usr/bin/env python3
"""
Quick fix to use async endpoint since that's what your API key has permission for
"""

print("""
============================================================
QUICK FIX: Use Async Endpoint (Your Key Has Permission!)
============================================================

Your API key has permission for property-skip-trace-async but NOT property-skip-trace.

Two options:

OPTION 1 (EASIEST): Enable sync permission in BatchData dashboard
-----------------------------------------------------------------
1. Go to your BatchData dashboard
2. Click on "skiptrace bulk" token
3. Check the box for "property-skip-trace"
4. Click UPDATE
5. Done! The sync client will work.

OPTION 2: Modify sync client to use async endpoint
---------------------------------------------------
Edit: Batchdata/src/batchdata_sync.py

Find this line (around line 186):
    url = f"{self.base_url}/property/skip-trace"

Change to:
    url = f"{self.base_url}/property/skip-trace-async"

The async endpoint in V3 can return immediate results without webhook,
so it should work with our sync client.

============================================================
""")

# Test which endpoints your key has access to
import os
import requests

api_key = os.getenv('BD_SKIPTRACE_KEY')
if api_key:
    print("Testing your API key permissions...")
    print("-" * 40)

    base_url = "https://api.batchdata.com/api/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Minimal test request
    test_request = {
        "requests": [{
            "requestId": "test",
            "propertyAddress": {
                "street": "123 Main St",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85001"
            }
        }]
    }

    # Test sync endpoint
    print("\n1. Testing SYNC endpoint (/property/skip-trace):")
    response = requests.post(
        f"{base_url}/property/skip-trace",
        json=test_request,
        headers=headers,
        timeout=10
    )
    if response.status_code == 403:
        print("   ❌ No permission (403 Forbidden)")
    elif response.status_code == 200:
        print("   ✅ Has permission (200 OK)")
    else:
        print(f"   ⚠️  Status: {response.status_code}")

    # Test async endpoint
    print("\n2. Testing ASYNC endpoint (/property/skip-trace-async):")
    response = requests.post(
        f"{base_url}/property/skip-trace-async",
        json=test_request,
        headers=headers,
        timeout=10
    )
    if response.status_code == 403:
        print("   ❌ No permission (403 Forbidden)")
    elif response.status_code == 200:
        print("   ✅ Has permission (200 OK)")
    else:
        print(f"   ⚠️  Status: {response.status_code}")

    print("\n" + "="*40)
    print("RECOMMENDATION:")
    if response.status_code == 200:
        print("Use Option 2 - Your key works with async endpoint!")
        print("Just change the URL in batchdata_sync.py as shown above.")
    else:
        print("Use Option 1 - Enable sync permission in dashboard.")
else:
    print("Set BD_SKIPTRACE_KEY environment variable to test")