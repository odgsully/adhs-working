#!/usr/bin/env python3
"""
Check the Upload file to trace where state field is lost
"""

import pandas as pd
import glob
from pathlib import Path

print(f"\n{'='*60}")
print(f"Checking Upload Files for State Field")
print(f"{'='*60}\n")

# Find the most recent 10.24 Upload file
upload_files = sorted(glob.glob("Batchdata/Upload/10.24_*.xlsx"), reverse=True)

if not upload_files:
    print("❌ No 10.24 Upload files found")
    exit(1)

for upload_file in upload_files[:2]:  # Check latest 2 files
    print(f"\nFile: {Path(upload_file).name}")
    print("-" * 40)

    try:
        sheets = pd.read_excel(upload_file, sheet_name=None)

        if 'INPUT_MASTER' in sheets:
            df = sheets['INPUT_MASTER']
            print(f"Records: {len(df)}")

            # Check critical fields
            print("\nField Analysis:")
            fields_to_check = ['BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP', 'BD_COUNTY']
            for field in fields_to_check:
                if field in df.columns:
                    non_empty = df[field].notna() & (df[field] != '') & (df[field] != 'nan')
                    print(f"  {field}: {non_empty.sum()}/{len(df)} populated")

                    # Show unique values for state
                    if field == 'BD_STATE' and field in df.columns:
                        unique_states = df[field].dropna().unique()
                        if len(unique_states) > 0:
                            print(f"    Unique values: {unique_states[:5]}")
                else:
                    print(f"  {field}: COLUMN MISSING")

            # Sample first 3 records
            print("\nSample Records:")
            for idx in range(min(3, len(df))):
                row = df.iloc[idx]
                print(f"\n  Record {idx + 1}:")
                print(f"    BD_OWNER_NAME_FULL: {row.get('BD_OWNER_NAME_FULL', 'N/A')}")
                print(f"    BD_ADDRESS: {row.get('BD_ADDRESS', 'N/A')}")
                print(f"    BD_CITY: {row.get('BD_CITY', 'N/A')}")
                print(f"    BD_STATE: {row.get('BD_STATE', 'N/A')}")
                print(f"    BD_ZIP: {row.get('BD_ZIP', 'N/A')}")
                print(f"    BD_COUNTY: {row.get('BD_COUNTY', 'N/A')}")

    except Exception as e:
        print(f"  Error reading file: {e}")

print("\n" + "="*60)