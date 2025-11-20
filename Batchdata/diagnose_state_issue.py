#!/usr/bin/env python3
"""
Diagnose where the state field is getting lost in the transformation
"""

import pandas as pd
import glob
import sys
from pathlib import Path

print(f"\n{'='*60}")
print(f"State Field Diagnostic")
print(f"{'='*60}\n")

# Check Ecorp Complete files (source of BatchData Upload)
ecorp_files = sorted(glob.glob("Ecorp/Complete/10.24_Ecorp_Complete*.xlsx"), reverse=True)

if ecorp_files:
    print("Checking Ecorp Complete (source) files:")
    print("-" * 40)

    for ecorp_file in ecorp_files[:1]:  # Check latest
        print(f"\nFile: {Path(ecorp_file).name}")

        try:
            df = pd.read_excel(ecorp_file)
            print(f"Records: {len(df)}")

            # Check for state-related columns
            print("\nState-related columns found:")
            state_cols = [col for col in df.columns if 'state' in col.lower() or 'State' in col]
            for col in state_cols:
                non_empty = df[col].notna() & (df[col] != '') & (df[col] != 'nan')
                print(f"  {col}: {non_empty.sum()}/{len(df)} populated")

                if non_empty.sum() > 0:
                    sample_values = df[df[col].notna()][col].head(3).tolist()
                    print(f"    Sample: {sample_values}")

            # Check address columns
            print("\nAddress-related columns:")
            addr_cols = [col for col in df.columns if 'address' in col.lower() or 'Address' in col]
            for col in addr_cols[:5]:  # First 5 address columns
                non_empty = df[col].notna() & (df[col] != '') & (df[col] != 'nan')
                if non_empty.sum() > 0:
                    print(f"  {col}: {non_empty.sum()}/{len(df)} populated")

        except Exception as e:
            print(f"Error reading Ecorp file: {e}")
else:
    print("❌ No Ecorp Complete files found for 10.24")

# Now let's check the transform logic
print(f"\n{'='*60}")
print("Checking Transform Logic")
print(f"{'='*60}\n")

# Add Batchdata to path
sys.path.insert(0, "Batchdata")

try:
    from src.transform import ecorp_to_batchdata_records, prepare_ecorp_for_batchdata

    print("✅ Transform module loaded successfully")

    # Test with sample data
    sample_ecorp = pd.DataFrame({
        'ECORP_NAME_S': ['Test Corp'],
        'ECORP_ENTITY_ID_S': ['12345'],
        'ECORP_SEARCH_NAME': ['Test Search'],
        'Agent Address': ['123 Main St, Phoenix, AZ 85001'],  # Full address with state
        'ECORP_COUNTY': ['MARICOPA'],
        'COUNTY': ['MARICOPA'],
        'Title1': ['Manager'],
        'Name1': ['John Doe'],
        'Address1': ['456 Oak Ave, Scottsdale, AZ 85250']  # Another address with state
    })

    print("\nTesting transformation with sample data:")
    print(f"Input Agent Address: {sample_ecorp['Agent Address'].iloc[0]}")

    # Test the transformation
    prepared_df = prepare_ecorp_for_batchdata(sample_ecorp)
    print(f"\nAfter prepare_ecorp_for_batchdata:")
    print(f"  Columns: {list(prepared_df.columns)}")

    # Transform to records
    records = ecorp_to_batchdata_records(prepared_df.iloc[0])
    print(f"\nAfter ecorp_to_batchdata_records:")
    print(f"  Records generated: {len(records)}")

    if records:
        first_record = records[0]
        print(f"\nFirst record fields:")
        for key in ['address_line1', 'city', 'state', 'zip']:
            if key in first_record:
                print(f"  {key}: {first_record[key]}")
            else:
                print(f"  {key}: [MISSING]")

except ImportError as e:
    print(f"❌ Could not import transform module: {e}")
except Exception as e:
    print(f"❌ Error during transformation test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)