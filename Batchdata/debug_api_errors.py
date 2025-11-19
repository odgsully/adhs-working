#!/usr/bin/env python3
"""
Debug script to examine API errors in the Complete file
"""

import pandas as pd
import json
from pathlib import Path

# File to examine
complete_file = Path("Batchdata/Complete/10.24_BatchData_Complete_11.17.03-08-01.xlsx")

print(f"\n{'='*60}")
print(f"API Error Analysis")
print(f"{'='*60}\n")

# Read OUTPUT_MASTER sheet
df = pd.read_excel(complete_file, sheet_name='OUTPUT_MASTER')

# Display all records with their errors
for idx, row in df.iterrows():
    print(f"Record {idx + 1}:")
    print(f"  record_id: {row['record_id']}")
    print(f"  owner_name: {row['owner_name_full']}")
    print(f"  address: {row['address_line1']}")
    print(f"  city: {row['city']}")
    print(f"  state: {row['state'] if pd.notna(row['state']) else '[EMPTY]'}")
    print(f"  zip: {row['zip'] if pd.notna(row['zip']) else '[EMPTY]'}")
    print(f"  api_status: {row['api_status']}")

    if 'api_error' in row and pd.notna(row['api_error']):
        print(f"  api_error: {row['api_error']}")

    if 'stages_applied' in row and pd.notna(row['stages_applied']):
        try:
            stages = json.loads(row['stages_applied'])
            print(f"  stages_applied: {stages}")
        except:
            print(f"  stages_applied: {row['stages_applied']}")

    print()

# Check for missing critical fields
print(f"\n{'='*60}")
print("Missing Critical Fields Analysis")
print(f"{'='*60}\n")

critical_fields = ['address_line1', 'city', 'state', 'zip']
for field in critical_fields:
    missing = df[field].isna() | (df[field] == '')
    missing_count = missing.sum()
    print(f"{field}: {missing_count}/{len(df)} records missing")

# Check what data we're actually sending
print(f"\n{'='*60}")
print("Data Being Sent to API")
print(f"{'='*60}\n")

for idx, row in df.head(2).iterrows():
    print(f"Record {idx + 1} would send:")
    print(f"  requestId: {row['record_id']}")
    print(f"  propertyAddress:")
    print(f"    street: {row['address_line1'] if pd.notna(row['address_line1']) else ''}")
    print(f"    city: {row['city'] if pd.notna(row['city']) else ''}")
    print(f"    state: {row['state'] if pd.notna(row['state']) else ''}")
    print(f"    zip: {row['zip'] if pd.notna(row['zip']) else ''}")

    if pd.notna(row.get('target_first_name')) or pd.notna(row.get('target_last_name')):
        print(f"  name:")
        print(f"    first: {row.get('target_first_name', '')}")
        print(f"    last: {row.get('target_last_name', '')}")
    elif pd.notna(row.get('owner_name_full')):
        # Would parse full name
        name = str(row['owner_name_full']).strip()
        parts = name.split(' ', 1)
        if len(parts) == 2:
            print(f"  name:")
            print(f"    first: {parts[0]}")
            print(f"    last: {parts[1]}")
    print()