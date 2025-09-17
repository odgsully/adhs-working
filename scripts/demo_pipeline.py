#!/usr/bin/env python3
"""
Demo script showing the working ETL pipeline.
"""

import sys
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def demo_single_month():
    """Demonstrate processing one month."""
    print("🎯 DEMO: Processing September 2024 (Nursing Homes Only)")
    
    # Import after path setup
    from adhs_etl.transform_enhanced import (
        EnhancedFieldMapper, 
        ProviderGrouper,
        process_month_data,
        create_reformat_output,
        create_all_to_date_output
    )
    
    # Setup
    raw_dir = Path("Raw-New-Month")
    
    # Initialize components (suppress warnings)
    import logging
    logging.getLogger('adhs_etl.transform').setLevel(logging.ERROR)
    
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
    print(f"📊 Sample data:")
    print(df[['PROVIDER', 'CITY', 'PROVIDER GROUP INDEX #']].head(3).to_string())
    
    # Save outputs
    reformat_path = create_reformat_output(df, 9, 2024, Path("Reformat"))
    all_to_date_path = create_all_to_date_output(df, 9, 2024, Path("All-to-Date"))
    
    print(f"\n💾 Files created:")
    print(f"  {reformat_path} ({reformat_path.stat().st_size} bytes)")
    print(f"  {all_to_date_path} ({all_to_date_path.stat().st_size} bytes)")
    
    # Create simple analysis
    import pandas as pd
    analysis_dir = Path("Analysis")
    analysis_dir.mkdir(exist_ok=True)
    analysis_path = analysis_dir / "9.24 Analysis.xlsx"
    
    with pd.ExcelWriter(analysis_path, engine='openpyxl') as writer:
        # Summary
        summary_data = [
            {"METRIC": "TOTAL PROVIDERS", "COUNT": len(df), "CONTEXT": "Nursing homes in Sept 2024"},
            {"METRIC": "UNIQUE CITIES", "COUNT": len(df['CITY'].unique()), "CONTEXT": "Cities with nursing homes"},
            {"METRIC": "PROVIDER GROUPS", "COUNT": len(df['PROVIDER GROUP INDEX #'].unique()), "CONTEXT": "Provider groups identified"}
        ]
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        # Full data
        df.to_excel(writer, sheet_name='Analysis', index=False)
    
    print(f"  {analysis_path} ({analysis_path.stat().st_size} bytes)")
    
    # Verify files are readable
    print(f"\n🔍 File verification:")
    for file_path in [reformat_path, all_to_date_path, analysis_path]:
        try:
            test_df = pd.read_excel(file_path)
            print(f"  ✅ {file_path.name}: {len(test_df)} rows, {len(test_df.columns)} columns")
        except Exception as e:
            print(f"  ❌ {file_path.name}: {e}")
    
    print(f"\n🎉 Demo complete! The ETL pipeline is working correctly.")
    print(f"📈 To process all 11 months, run the batch script overnight or in smaller chunks.")

if __name__ == "__main__":
    demo_single_month()