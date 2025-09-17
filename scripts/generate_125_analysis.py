#!/usr/bin/env python3
"""
Generate missing 1.25 Analysis file.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, 'src')

def main():
    """Generate 1.25 Analysis file from existing Reformat data."""
    print("🔄 Generating 1.25 Analysis file...")
    
    # Read the existing 1.25 Reformat file
    reformat_path = Path("Reformat/1.25 Reformat.xlsx")
    if not reformat_path.exists():
        print("❌ 1.25 Reformat.xlsx not found!")
        return
    
    df = pd.read_excel(reformat_path)
    print(f"✅ Loaded {len(df)} records from 1.25 Reformat.xlsx")
    
    # Create analysis file
    analysis_dir = Path("Analysis")
    analysis_dir.mkdir(exist_ok=True)
    analysis_path = analysis_dir / "1.25 Analysis.xlsx"
    
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
    
    print(f"💾 Saved: 1.25 Analysis.xlsx")
    print("✅ Done!")

if __name__ == "__main__":
    main()