#!/usr/bin/env python3
"""
Automated version of batch processing script for testing.
Processes all available months from September 2024 to July 2025.
"""

import os
import shutil
import subprocess
from pathlib import Path

def process_all_months():
    """Process all available months automatically."""
    
    # Available months in chronological order
    months = [
        ("Raw 9.24", "9.24"),
        ("Raw 10.24", "10.24"),
        ("Raw 11.24", "11.24"),
        ("Raw 12.24", "12.24"),
        ("Raw 1.25", "1.25"),
        ("Raw 2.25", "2.25"),
        ("Raw 3.25", "3.25"),
        ("Raw 4.25", "4.25"),
        ("Raw 5.25", "5.25"),
        ("Raw 6.25", "6.25"),
        ("Raw 7.25", "7.25"),
    ]
    
    print("🚀 Starting batch processing of all 11 months...")
    
    successful_months = []
    failed_months = []
    
    for i, (folder_name, month_code) in enumerate(months, 1):
        print(f"\n📊 Processing month {i}/11: {month_code}")
        
        # Copy files
        source_folder = Path("ALL-MONTHS") / folder_name
        dest_folder = Path("Raw-New-Month")
        
        try:
            # Clear destination folder
            if dest_folder.exists():
                for file in dest_folder.glob("*.xlsx"):
                    file.unlink()
            else:
                dest_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy Excel files
            excel_files = list(source_folder.glob("*.xlsx"))
            if not excel_files:
                print(f"❌ No Excel files found in {source_folder}")
                failed_months.append(month_code)
                continue
            
            for file in excel_files:
                shutil.copy2(file, dest_folder)
            
            print(f"✅ Copied {len(excel_files)} Excel files")
            
            # Run ETL pipeline
            cmd = [
                "python", "-m", "adhs_etl.cli_enhanced", "run",
                "--month", month_code,
                "--raw-dir", "./Raw-New-Month"
            ]
            
            # Set PYTHONPATH
            env = os.environ.copy()
            env['PYTHONPATH'] = 'src'
            
            print(f"🔄 Running ETL pipeline for {month_code}...")
            result = subprocess.run(cmd, env=env, timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                print(f"✅ Successfully processed {month_code}")
                successful_months.append(month_code)
            else:
                print(f"❌ Failed to process {month_code}")
                failed_months.append(month_code)
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout processing {month_code}")
            failed_months.append(month_code)
        except Exception as e:
            print(f"❌ Error processing {month_code}: {e}")
            failed_months.append(month_code)
        
        # Clean up temp files
        try:
            for file in dest_folder.glob("*.xlsx"):
                file.unlink()
        except:
            pass
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"🎉 BATCH PROCESSING COMPLETE!")
    print(f"{'='*60}")
    
    if successful_months:
        print(f"✅ Successfully processed {len(successful_months)} months:")
        for month in successful_months:
            print(f"  • {month}")
    
    if failed_months:
        print(f"❌ Failed to process {len(failed_months)} months:")
        for month in failed_months:
            print(f"  • {month}")
    
    print(f"\n📁 Output files should be in:")
    print(f"  • Reformat/ - Individual month files")
    print(f"  • All-to-Date/ - Cumulative data files")
    print(f"  • Analysis/ - Analysis files with lost license detection")

if __name__ == "__main__":
    process_all_months()