#!/usr/bin/env python3
"""
Debug script to examine the Complete file and understand data issues
"""

import pandas as pd
import sys
from pathlib import Path

# File to examine
complete_file = Path("Batchdata/Complete/10.24_BatchData_Complete_11.17.03-08-01.xlsx")

if not complete_file.exists():
    print(f"❌ File not found: {complete_file}")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"Examining BatchData Complete File")
print(f"{'='*60}")
print(f"File: {complete_file.name}")
print(f"Size: {complete_file.stat().st_size:,} bytes")

# Read all sheets
sheets = pd.read_excel(complete_file, sheet_name=None)

print(f"\nSheets found: {list(sheets.keys())}")
print()

for sheet_name, df in sheets.items():
    print(f"\n📋 Sheet: {sheet_name}")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")

    if sheet_name == "OUTPUT_MASTER":
        print(f"\n   Column Analysis:")

        # Check for phone columns
        phone_cols = [col for col in df.columns if col.startswith('phone_')]
        email_cols = [col for col in df.columns if col.startswith('email_')]

        print(f"   - Phone columns found: {len(phone_cols)}")
        print(f"   - Email columns found: {len(email_cols)}")

        # Check if any phones/emails have data
        phones_populated = 0
        emails_populated = 0

        for col in phone_cols:
            if col.endswith('_1') or col == 'phone_1':  # Check main phone columns
                non_empty = df[col].notna() & (df[col] != '')
                if non_empty.any():
                    phones_populated += non_empty.sum()

        for col in email_cols:
            if col.endswith('_1') or col == 'email_1':  # Check main email columns
                non_empty = df[col].notna() & (df[col] != '')
                if non_empty.any():
                    emails_populated += non_empty.sum()

        print(f"   - Records with phone_1: {phones_populated}/{len(df)}")
        print(f"   - Records with email_1: {emails_populated}/{len(df)}")

        # Check API status columns
        if 'api_status' in df.columns:
            print(f"\n   API Status Distribution:")
            status_counts = df['api_status'].value_counts()
            for status, count in status_counts.items():
                print(f"   - {status}: {count}")

        # Check if persons_found column exists and has data
        if 'persons_found' in df.columns:
            persons_counts = df['persons_found'].value_counts()
            print(f"\n   Persons Found Distribution:")
            for count, freq in persons_counts.items():
                print(f"   - {count} persons: {freq} records")

        # Sample first few rows to see actual data
        print(f"\n   Sample Data (first 3 rows):")
        print("   Key fields only:")

        sample_cols = ['record_id', 'owner_name_full', 'address_line1', 'city', 'state']
        if 'api_status' in df.columns:
            sample_cols.append('api_status')
        if 'persons_found' in df.columns:
            sample_cols.append('persons_found')
        if 'phone_1' in df.columns:
            sample_cols.append('phone_1')
        if 'email_1' in df.columns:
            sample_cols.append('email_1')

        # Filter to existing columns
        sample_cols = [col for col in sample_cols if col in df.columns]

        if sample_cols and len(df) > 0:
            sample_df = df[sample_cols].head(3)
            for idx, row in sample_df.iterrows():
                print(f"\n   Record {idx + 1}:")
                for col in sample_cols:
                    value = row[col]
                    if pd.isna(value) or value == '':
                        value = "[empty]"
                    print(f"     {col}: {value}")

        # Check all columns
        print(f"\n   All Columns Present:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i:3}. {col}")
            if i >= 20 and i < len(df.columns) - 10:
                print(f"   ... ({len(df.columns) - 30} more columns)")
                i = len(df.columns) - 10

print("\n" + "="*60)
print("Analysis Complete")
print("="*60)