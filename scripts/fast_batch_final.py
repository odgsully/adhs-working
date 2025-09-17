#!/usr/bin/env python3
"""
Fast batch processing script - final remaining months.
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
    create_reformat_output,
    create_all_to_date_output
)

def process_month(month_folder, month_code, month_num, year_num):
    """Process a single month quickly."""
    print(f"\n🔄 Processing {month_code}...")
    
    # Setup
    raw_dir = Path("Raw-New-Month")
    source_dir = Path("ALL-MONTHS") / month_folder
    
    # Clear and copy files
    for f in raw_dir.glob("*.xlsx"):
        f.unlink()
    
    excel_files = list(source_dir.glob("*.xlsx"))
    for f in excel_files:
        shutil.copy2(f, raw_dir)
    
    print(f"📁 Copied {len(excel_files)} files")
    
    # Initialize components (suppress warnings)
    import logging
    logging.getLogger('adhs_etl.transform').setLevel(logging.ERROR)
    
    field_mapper = EnhancedFieldMapper(
        Path("field_map.yml"),
        Path("field_map.TODO.yml")
    )
    provider_grouper = ProviderGrouper()
    
    # Process data
    df = process_month_data(
        raw_dir,
        field_mapper,
        provider_grouper,
        month=month_num,
        year=year_num
    )
    
    print(f"✅ Processed {len(df)} records")
    
    # Save outputs
    reformat_path = create_reformat_output(df, month_num, year_num, Path("Reformat"))
    all_to_date_path = create_all_to_date_output(df, month_num, year_num, Path("All-to-Date"))
    
    print(f"💾 Saved: {reformat_path.name}")
    print(f"💾 Saved: {all_to_date_path.name}")
    
    # Basic analysis (simplified - just summary)
    analysis_dir = Path("Analysis")
    analysis_dir.mkdir(exist_ok=True)
    
    analysis_filename = f"{month_num}.{year_num % 100} Analysis.xlsx"
    analysis_path = analysis_dir / analysis_filename
    
    # Create basic analysis file
    import pandas as pd
    with pd.ExcelWriter(analysis_path, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = [
            {"METRIC": "TOTAL PROVIDERS", "COUNT": len(df), "CONTEXT": "Total providers in this month"},
            {"METRIC": "PROVIDER TYPES", "COUNT": len(df['PROVIDER TYPE'].unique()), "CONTEXT": "Number of different provider types"},
            {"METRIC": "PROVIDER GROUPS", "COUNT": len(df['PROVIDER GROUP INDEX #'].unique()), "CONTEXT": "Number of provider groups identified"}
        ]
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        # Main data sheet
        df.to_excel(writer, sheet_name='Analysis', index=False)
    
    print(f"💾 Saved: {analysis_filename}")
    
    # Cleanup
    for f in raw_dir.glob("*.xlsx"):
        f.unlink()
    
    return True

def main():
    """Process final months."""
    print("🚀 Fast Batch Processing - Final Months")
    
    # Process final months only
    months = [
        ("Raw 5.25", "5.25", 5, 2025),
        ("Raw 6.25", "6.25", 6, 2025),
        ("Raw 7.25", "7.25", 7, 2025),
    ]
    
    successful = []
    failed = []
    
    for month_folder, month_code, month_num, year_num in months:
        try:
            if process_month(month_folder, month_code, month_num, year_num):
                successful.append(month_code)
        except Exception as e:
            print(f"❌ Failed {month_code}: {e}")
            failed.append(month_code)
    
    print(f"\n{'='*50}")
    print(f"🎉 BATCH PROCESSING COMPLETE")
    print(f"{'='*50}")
    print(f"✅ Successful: {len(successful)} months")
    print(f"❌ Failed: {len(failed)} months")
    
    # Show what was created
    print(f"\n📁 Output files:")
    for dir_name in ["Reformat", "All-to-Date", "Analysis"]:
        files = list(Path(dir_name).glob("*.xlsx"))
        print(f"  {dir_name}/: {len(files)} files")

if __name__ == "__main__":
    main()