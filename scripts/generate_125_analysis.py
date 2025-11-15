#!/usr/bin/env python3
"""
Generate missing 1.25 Analysis file.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, 'src')

from adhs_etl.utils import (
    get_standard_timestamp,
    format_output_filename,
    get_legacy_filename,
    save_excel_with_legacy_copy
)

def main():
    """Generate 1.25 Analysis file from existing Reformat data."""
    print("🔄 Generating 1.25 Analysis file...")

    # Try to find the 1.25 Reformat file (support both old and new formats)
    reformat_dir = Path("Reformat")
    old_format_path = reformat_dir / "1.25 Reformat.xlsx"
    new_format_files = list(reformat_dir.glob("1.25_Reformat_*.xlsx"))

    # Prefer new format if available
    if new_format_files:
        reformat_path = max(new_format_files, key=lambda p: p.stat().st_mtime)
        print(f"📋 Found new format file: {reformat_path.name}")
    elif old_format_path.exists():
        reformat_path = old_format_path
        print(f"📋 Found old format file: {reformat_path.name}")
    else:
        print("❌ 1.25 Reformat.xlsx not found!")
        return

    df = pd.read_excel(reformat_path)
    print(f"✅ Loaded {len(df)} records from {reformat_path.name}")

    # Generate timestamp for new naming convention
    timestamp = get_standard_timestamp()

    # Create analysis file paths (new format + legacy)
    analysis_dir = Path("Analysis")
    analysis_dir.mkdir(exist_ok=True)

    new_filename = format_output_filename("1.25", "Analysis", timestamp)
    legacy_filename = get_legacy_filename("1.25", "Analysis")
    new_path = analysis_dir / new_filename
    legacy_path = analysis_dir / legacy_filename

    # Write with new format
    with pd.ExcelWriter(new_path, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = [
            {"METRIC": "TOTAL PROVIDERS", "COUNT": len(df), "CONTEXT": "Total providers in this month"},
            {"METRIC": "PROVIDER TYPES", "COUNT": len(df['PROVIDER TYPE'].unique()), "CONTEXT": "Number of different provider types"},
            {"METRIC": "PROVIDER GROUPS", "COUNT": len(df['PROVIDER GROUP INDEX #'].unique()), "CONTEXT": "Number of provider groups identified"}
        ]
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        # Main data sheet
        df.to_excel(writer, sheet_name='Analysis', index=False)

    print(f"💾 Saved: {new_path.name}")

    # Create legacy copy
    save_excel_with_legacy_copy(new_path, legacy_path)
    print(f"💾 Created legacy copy: {legacy_path.name}")

    print("✅ Done!")

if __name__ == "__main__":
    main()