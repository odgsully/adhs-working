#!/usr/bin/env python3
"""
Test BatchData V2 CSV Upload API with wallet credits
According to SYNC_MIGRATION_IMPLEMENTATION.md, V2 should support CSV upload
"""
import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def create_test_csv():
    """Create a test CSV file with proper V2 format"""
    data = {
        'first_name': ['John', 'Jane'],
        'last_name': ['Doe', 'Smith'],
        'address': ['123 Main St', '456 Oak Ave'],
        'city': ['Phoenix', 'Scottsdale'],
        'state': ['AZ', 'AZ'],
        'zip': ['85001', '85251']
    }
    df = pd.DataFrame(data)
    csv_path = '/tmp/test_v2_upload.csv'
    df.to_csv(csv_path, index=False)
    return csv_path

def test_v2_csv_endpoints():
    """Test various V2 endpoint configurations"""

    api_key = os.getenv('BD_SKIPTRACE_KEY', '')
    if not api_key:
        print("ERROR: BD_SKIPTRACE_KEY not found in environment")
        return

    print("="*60)
    print("BatchData V2 CSV Upload API Test")
    print("="*60)

    # Create test CSV
    csv_path = create_test_csv()
    print(f"Created test CSV: {csv_path}")

    # Test different endpoint variations
    endpoints = [
        # As documented in SYNC_MIGRATION_IMPLEMENTATION.md
        "https://api.batchdata.com/api/v2/property/skip-trace/async",
        "https://api.batchdata.com/api/v2/csv-upload",
        "https://api.batchdata.com/api/v2/upload",
        "https://api.batchdata.com/api/v2/skip-trace/upload",
        # Try V1 endpoints (sometimes V2 uses V1 patterns)
        "https://api.batchdata.com/api/v1/property/skip-trace/async",
        "https://api.batchdata.com/api/v1/csv-upload",
        # Try without version
        "https://api.batchdata.com/property/skip-trace/async",
        "https://api.batchdata.com/csv-upload",
    ]

    # Different auth header formats to try
    auth_headers = [
        {'Authorization': f'Bearer {api_key}'},
        {'Authorization': f'{api_key}'},
        {'X-API-Key': api_key},
        {'Api-Key': api_key},
    ]

    for endpoint in endpoints:
        print(f"\n Testing endpoint: {endpoint}")

        for auth_header in auth_headers:
            auth_type = list(auth_header.keys())[0]
            print(f"  Auth type: {auth_type}")

            try:
                with open(csv_path, 'rb') as f:
                    files = {'file': ('test.csv', f, 'text/csv')}

                    response = requests.post(
                        endpoint,
                        files=files,
                        headers=auth_header,
                        timeout=10
                    )

                    print(f"    Status: {response.status_code}")

                    if response.status_code == 200:
                        print(f"    ✅ SUCCESS! Found working endpoint")
                        print(f"    Response: {response.text[:200]}")
                        return endpoint, auth_header
                    elif response.status_code == 401:
                        print(f"    ❌ Authentication failed")
                    elif response.status_code == 404:
                        print(f"    ❌ Endpoint not found")
                    elif response.status_code == 402:
                        print(f"    ⚠️ Payment required (check wallet credits)")
                    else:
                        print(f"    ❌ Error: {response.status_code}")

            except requests.exceptions.Timeout:
                print(f"    ❌ Timeout")
            except requests.exceptions.RequestException as e:
                print(f"    ❌ Request failed: {e}")

    print("\n" + "="*60)
    print("No working V2 CSV upload endpoint found")
    print("\nPossible issues:")
    print("1. V2 might not support CSV upload (only V3 does)")
    print("2. Wallet credits might only work with V3 API")
    print("3. Different authentication method required")
    print("4. CSV format might be incorrect")

    # Clean up
    os.remove(csv_path)

if __name__ == "__main__":
    test_v2_csv_endpoints()