#!/usr/bin/env python3
"""
Test MCAO Complete Flow
========================

Test the exact flow used in process_mcao_complete.
"""

import sys
import os
sys.path.insert(0, 'src')

from adhs_etl.mcao_client import MCAAOAPIClient
from adhs_etl.mcao_field_mapping import validate_mcao_record, MCAO_MAX_HEADERS
import pandas as pd

def test_flow():
    """Test the exact flow from process_mcao_complete."""

    print("🧪 Testing MCAO Complete Flow")
    print("="*60)

    # Create test data similar to MCAO_Upload
    test_data = pd.DataFrame([
        {'FULL_ADDRESS': '10010 NORTH 29TH STREET, PHOENIX, AZ 85028', 'COUNTY': 'MARICOPA', 'APN': '165-28-054'},
        {'FULL_ADDRESS': '9850 NORTH 31ST STREET, PHOENIX, AZ 85028', 'COUNTY': 'MARICOPA', 'APN': '301-97-837'}
    ])

    print(f"Test data shape: {test_data.shape}")

    # Initialize client
    client = MCAAOAPIClient(rate_limit=5.0)

    # Process each record (same as process_mcao_complete)
    results = []

    for idx, row in test_data.iterrows():
        print(f"\nProcessing row {idx}: APN={row['APN']}")

        apn = row['APN']

        # Get all property data from API
        print("  Getting API data...")
        api_data = client.get_all_property_data(str(apn))

        if api_data.get('data_complete', False):
            print(f"  ✅ API returned data")

            # Map API data to MAX_HEADERS structure
            mapped_data = client.map_to_max_headers(api_data)
            print(f"  📊 Mapped {len([v for v in mapped_data.values() if v])} fields")

            # Start with the original 3 columns
            record = {
                'FULL_ADDRESS': row['FULL_ADDRESS'],
                'COUNTY': row['COUNTY'],
                'APN': row['APN']
            }

            # Add mapped API data
            record.update(mapped_data)
            print(f"  📋 Record has {len(record)} keys")

            # Validate and clean record
            clean_record = validate_mcao_record(record)
            filled = len([v for v in clean_record.values() if v and str(v).strip()])
            print(f"  ✅ After validation: {filled} filled fields")

            results.append(clean_record)
        else:
            print(f"  ❌ API failed: {api_data.get('errors', [])}")

    # Create DataFrame with all columns in correct order
    print(f"\nCreating DataFrame with {len(results)} records...")
    df_complete = pd.DataFrame(results, columns=MCAO_MAX_HEADERS)

    print(f"Final shape: {df_complete.shape}")
    print(f"Columns: {len(df_complete.columns)}")

    # Check first row
    if len(df_complete) > 0:
        filled = sum(df_complete.iloc[0].notna() & (df_complete.iloc[0] != ''))
        print(f"Row 1 filled fields: {filled}")

        print("\nSample data from row 1:")
        row = df_complete.iloc[0]
        for col in df_complete.columns[:20]:
            val = row[col]
            if pd.notna(val) and str(val).strip():
                print(f"  {col}: {val}")

    # Save test output
    output_path = "MCAO/test_flow_result.xlsx"
    df_complete.to_excel(output_path, index=False)
    print(f"\n💾 Saved to: {output_path}")

if __name__ == "__main__":
    test_flow()