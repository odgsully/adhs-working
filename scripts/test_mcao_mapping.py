#!/usr/bin/env python3
"""
Test MCAO Field Mapping
========================

Directly tests the updated field mapping with a known APN.
"""

import sys
import os
sys.path.insert(0, 'src')

from adhs_etl.mcao_client import MCAAOAPIClient
import json
import pandas as pd

def test_mapping():
    """Test the field mapping with a known APN."""

    print("🧪 Testing MCAO Field Mapping")
    print("="*60)

    # Initialize client
    client = MCAAOAPIClient(rate_limit=5.0)

    # Test APN
    test_apn = "165-28-054"
    print(f"Testing with APN: {test_apn}\n")

    # Get all data
    print("Step 1: Fetching data from API...")
    api_data = client.get_all_property_data(test_apn)

    print(f"Data complete: {api_data.get('data_complete')}")
    print(f"Errors: {api_data.get('errors')}")

    # Check what we got
    endpoints_with_data = []
    for key in ['parcel', 'property_info', 'address', 'valuations', 'residential', 'owner']:
        if key in api_data and api_data[key]:
            endpoints_with_data.append(key)
            print(f"✅ {key}: Got data")
        else:
            print(f"❌ {key}: No data")

    print(f"\nStep 2: Mapping to MAX_HEADERS...")
    mapped = client.map_to_max_headers(api_data)

    # Count populated fields
    populated = [(k, v) for k, v in mapped.items() if v and str(v).strip()]
    empty = [(k, v) for k, v in mapped.items() if not v or not str(v).strip()]

    print(f"\nResults:")
    print(f"  Populated fields: {len(populated)} out of 106")
    print(f"  Empty fields: {len(empty)} out of 106")

    print(f"\nSample populated fields:")
    for key, value in populated[:20]:
        print(f"  • {key}: {value}")

    # Save to test file
    output_path = "MCAO/test_mapping_result.xlsx"
    test_df = pd.DataFrame([mapped])
    test_df.to_excel(output_path, index=False)
    print(f"\n💾 Saved test result to: {output_path}")

    # Debug: Save raw API response
    debug_path = "MCAO/test_api_response.json"
    with open(debug_path, 'w') as f:
        json.dump(api_data, f, indent=2)
    print(f"💾 Saved raw API response to: {debug_path}")

if __name__ == "__main__":
    test_mapping()