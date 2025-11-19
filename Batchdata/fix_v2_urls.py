#!/usr/bin/env python3
"""
Fix all base URLs to use V2 API instead of V3
"""

import pandas as pd
import os
from pathlib import Path

print("="*60)
print("Fixing Base URLs to V2 API")
print("="*60)

# Files to update
excel_files = [
    "Batchdata/template_config.xlsx",
    "Batchdata/tests/batchdata_local_input.xlsx"
]

# Also check Upload files
upload_files = list(Path("Batchdata/Upload").glob("*.xlsx"))

all_files = excel_files + [str(f) for f in upload_files]

for file_path in all_files:
    if not os.path.exists(file_path):
        print(f"\n❌ File not found: {file_path}")
        continue

    print(f"\nProcessing: {file_path}")

    try:
        # Read all sheets
        sheets = pd.read_excel(file_path, sheet_name=None)

        # Check if CONFIG sheet exists
        if 'CONFIG' in sheets:
            config_df = sheets['CONFIG']
            print(f"  Found CONFIG sheet with {len(config_df)} rows")

            # Find and update api.base_url
            updated = False
            for idx, row in config_df.iterrows():
                if 'api.base_url' in str(row.get('key', '')):
                    old_value = row.get('value', '')
                    if 'api/v3' in str(old_value):
                        new_value = str(old_value).replace('api/v3', 'api/v2')
                        config_df.at[idx, 'value'] = new_value
                        print(f"  ✅ Updated: {old_value} → {new_value}")
                        updated = True
                    elif 'api/v2' in str(old_value):
                        print(f"  ✓ Already V2: {old_value}")
                    else:
                        print(f"  ⚠️  Unexpected URL: {old_value}")

            # Save if updated
            if updated:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    for sheet_name, df in sheets.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  💾 Saved changes")

    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*60)
print("Python Files to Check")
print("="*60)

# Check Python files
python_files = [
    "Batchdata/src/batchdata.py",
    "src/adhs_etl/batchdata_bridge.py"
]

for py_file in python_files:
    if os.path.exists(py_file):
        with open(py_file, 'r') as f:
            content = f.read()

        if 'api/v3' in content:
            print(f"\n⚠️  {py_file} contains v3 references")
            # Count occurrences
            count = content.count('api/v3')
            print(f"  Found {count} occurrences of 'api/v3'")
        elif 'api/v2' in content:
            print(f"\n✅ {py_file} already using v2")
        else:
            print(f"\n✓ {py_file} uses base_url variable")

print("\n" + "="*60)
print("Summary")
print("="*60)
print("""
✅ Base URL should now be: https://api.batchdata.com/api/v2

Next steps:
1. Fix the state field issue in transform.py
2. Test the async pipeline with wallet credits
3. Run: python3 scripts/process_months_local.py
""")

# Create a test CSV for V2
print("\nCreating test CSV for V2 API...")
test_csv = pd.DataFrame({
    'first_name': ['John', 'Jane'],
    'last_name': ['Doe', 'Smith'],
    'address': ['123 Main St', '456 Oak Ave'],
    'city': ['Phoenix', 'Scottsdale'],
    'state': ['AZ', 'AZ'],
    'zip': ['85001', '85250']
})

test_csv.to_csv('Batchdata/test_v2.csv', index=False)
print("✅ Created Batchdata/test_v2.csv for testing")