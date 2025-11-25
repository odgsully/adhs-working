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
    print(f"  BD_RECORD_ID: {row['BD_RECORD_ID']}")
    print(f"  BD_OWNER_NAME_FULL: {row['BD_OWNER_NAME_FULL']}")
    print(f"  BD_ADDRESS: {row['BD_ADDRESS']}")
    print(f"  BD_CITY: {row['BD_CITY']}")
    print(f"  BD_STATE: {row['BD_STATE'] if pd.notna(row['BD_STATE']) else '[EMPTY]'}")
    print(f"  BD_ZIP: {row['BD_ZIP'] if pd.notna(row['BD_ZIP']) else '[EMPTY]'}")
    print(f"  BD_API_STATUS: {row['BD_API_STATUS']}")

    if 'BD_API_ERROR' in row and pd.notna(row['BD_API_ERROR']):
        print(f"  BD_API_ERROR: {row['BD_API_ERROR']}")

    if 'BD_STAGES_APPLIED' in row and pd.notna(row['BD_STAGES_APPLIED']):
        try:
            stages = json.loads(row['BD_STAGES_APPLIED'])
            print(f"  BD_STAGES_APPLIED: {stages}")
        except:
            print(f"  BD_STAGES_APPLIED: {row['BD_STAGES_APPLIED']}")

    print()

# Check for missing critical fields
print(f"\n{'='*60}")
print("Missing Critical Fields Analysis")
print(f"{'='*60}\n")

critical_fields = ['BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP']
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
    print(f"  requestId: {row['BD_RECORD_ID']}")
    print(f"  propertyAddress:")
    print(f"    street: {row['BD_ADDRESS'] if pd.notna(row['BD_ADDRESS']) else ''}")
    print(f"    city: {row['BD_CITY'] if pd.notna(row['BD_CITY']) else ''}")
    print(f"    state: {row['BD_STATE'] if pd.notna(row['BD_STATE']) else ''}")
    print(f"    zip: {row['BD_ZIP'] if pd.notna(row['BD_ZIP']) else ''}")

    if pd.notna(row.get('BD_TARGET_FIRST_NAME')) or pd.notna(row.get('BD_TARGET_LAST_NAME')):
        print(f"  name:")
        print(f"    first: {row.get('BD_TARGET_FIRST_NAME', '')}")
        print(f"    last: {row.get('BD_TARGET_LAST_NAME', '')}")
    elif pd.notna(row.get('BD_OWNER_NAME_FULL')):
        # Would parse full name
        name = str(row['BD_OWNER_NAME_FULL']).strip()
        parts = name.split(' ', 1)
        if len(parts) == 2:
            print(f"  name:")
            print(f"    first: {parts[0]}")
            print(f"    last: {parts[1]}")
    print()