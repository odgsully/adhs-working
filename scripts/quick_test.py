#!/usr/bin/env python3
"""
Quick test script to verify the ETL pipeline is working.
"""

import os
import sys
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from adhs_etl.transform_enhanced import (
    EnhancedFieldMapper, 
    ProviderGrouper,
    process_month_data,
    create_reformat_output
)

def main():
    print("🧪 Quick ETL Test")
    
    # Setup
    raw_dir = Path("Raw-New-Month")
    
    # Copy one file for testing
    source_file = Path("ALL-MONTHS/Raw 9.24/NURSING_HOME.xlsx")
    dest_file = raw_dir / "NURSING_HOME.xlsx"
    
    # Clear and copy
    for f in raw_dir.glob("*.xlsx"):
        f.unlink()
    
    shutil.copy2(source_file, dest_file)
    print(f"✅ Copied {source_file.name} for testing")
    
    # Initialize components
    field_mapper = EnhancedFieldMapper(
        Path("field_map.yml"),
        Path("field_map.TODO.yml")
    )
    provider_grouper = ProviderGrouper()
    
    # Process data
    print("🔄 Processing data...")
    df = process_month_data(
        raw_dir,
        field_mapper,
        provider_grouper,
        month=9,
        year=2024
    )
    
    print(f"✅ Processed {len(df)} records")
    print(f"📊 Columns: {list(df.columns)}")
    
    # Save to Reformat
    reformat_path = create_reformat_output(df, 9, 2024, Path("Reformat"))
    print(f"💾 Saved to: {reformat_path}")
    
    # Check file exists
    if reformat_path.exists():
        print(f"✅ File created successfully: {reformat_path.stat().st_size} bytes")
        
        # Quick verification
        import pandas as pd
        test_df = pd.read_excel(reformat_path)
        print(f"✅ File readable: {len(test_df)} rows, {len(test_df.columns)} columns")
    else:
        print("❌ File not created")
    
    # Cleanup
    dest_file.unlink()
    print("🧹 Cleaned up test file")

if __name__ == "__main__":
    main()