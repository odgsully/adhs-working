#!/usr/bin/env python3
"""
Direct Month Processing Script - Bypasses iCloud Sync Issues
=============================================================

Processes months 9.24, 10.24, 11.24 directly with local temp writes.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, 'src')

from adhs_etl.config import Settings
from adhs_etl.transform_enhanced import (
    EnhancedFieldMapper,
    ProviderGrouper,
    process_month_data,
    log_memory_usage
)
from adhs_etl.analysis import (
    ProviderAnalyzer,
    create_analysis_summary_sheet,
    create_blanks_count_sheet
)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(text: str, color: str = Colors.WHITE) -> None:
    print(f"{color}{text}{Colors.END}")

def safe_write_excel(df, path, sheet_data=None):
    """Write Excel file via temp to avoid iCloud issues."""
    # Create temp file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(temp_fd)

    try:
        if sheet_data:
            # Multiple sheets
            with pd.ExcelWriter(temp_path, engine='xlsxwriter') as writer:
                for sheet_name, sheet_df in sheet_data.items():
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            # Single sheet - use simple to_excel for reliability
            df.to_excel(temp_path, index=False, engine='xlsxwriter')

        # Move from temp to final location
        shutil.move(temp_path, str(path))
        print_colored(f"✅ Saved: {path}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"❌ Failed to save {path}: {e}", Colors.RED)
        if Path(temp_path).exists():
            os.unlink(temp_path)
        return False

def process_single_month(month_code: str, folder_name: str):
    """Process a single month directly."""
    print_colored(f"\n{'='*60}", Colors.BLUE)
    print_colored(f"Processing {month_code}", Colors.BOLD + Colors.PURPLE)
    print_colored(f"{'='*60}", Colors.BLUE)

    # Add timestamp for debugging
    from datetime import datetime
    def log_step(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}", flush=True)

    # Parse month/year
    parts = month_code.split('.')
    month_num = int(parts[0])
    year_num = 2000 + int(parts[1])

    # Setup paths
    source_dir = Path("ALL-MONTHS") / folder_name

    # Initialize components
    field_mapper = EnhancedFieldMapper(
        Path("field_map.yml"),
        Path("field_map.TODO.yml")
    )
    provider_grouper = ProviderGrouper()
    analyzer = ProviderAnalyzer()

    log_step("Processing data files...")
    print_colored("Processing data files...", Colors.BLUE)

    # Process month data directly from ALL-MONTHS
    log_step(f"Calling process_month_data for {source_dir}...")
    current_month_df = process_month_data(
        source_dir,
        field_mapper,
        provider_grouper,
        month_num,
        year_num,
        batch_size=1000
    )

    if current_month_df.empty:
        print_colored(f"❌ No data processed for {month_code}", Colors.RED)
        return False

    log_step(f"Processed {len(current_month_df)} records")
    print_colored(f"✅ Processed {len(current_month_df)} records", Colors.GREEN)

    # Create output directories
    Path("Reformat").mkdir(exist_ok=True)
    Path("All-to-Date").mkdir(exist_ok=True)
    Path("Analysis").mkdir(exist_ok=True)

    # 1. Save Reformat
    reformat_path = Path("Reformat") / f"{month_code} Reformat.xlsx"
    log_step(f"Creating Reformat file at {reformat_path}...")
    print_colored("Creating Reformat file...", Colors.BLUE)
    if not safe_write_excel(current_month_df, reformat_path):
        return False

    # 2. Create All-to-Date
    log_step("Starting All-to-Date creation...")
    print_colored("Creating All-to-Date file...", Colors.BLUE)
    all_to_date_path = Path("All-to-Date") / f"Reformat All to Date {month_code}.xlsx"

    # Get previous All-to-Date if exists
    all_to_date_dir = Path("All-to-Date")
    existing_files = list(all_to_date_dir.glob("Reformat All to Date *.xlsx"))

    if existing_files:
        # Find the most recent file before this month
        relevant_files = []
        for f in existing_files:
            try:
                file_month = f.stem.replace("Reformat All to Date ", "")
                file_parts = file_month.split('.')
                file_month_num = int(file_parts[0])
                file_year_num = int(file_parts[1])

                # Include if before current month
                if (file_year_num < year_num % 100) or (file_year_num == year_num % 100 and file_month_num < month_num):
                    relevant_files.append((f, file_year_num, file_month_num))
            except:
                continue

        if relevant_files:
            relevant_files.sort(key=lambda x: (x[1], x[2]))
            latest_file = relevant_files[-1][0]
            print_colored(f"Loading previous data from {latest_file.name}", Colors.BLUE)
            previous_df = pd.read_excel(latest_file)
            combined_df = pd.concat([previous_df, current_month_df], ignore_index=True)
        else:
            combined_df = current_month_df
    else:
        combined_df = current_month_df

    if not safe_write_excel(combined_df, all_to_date_path):
        return False

    # 3. Create Analysis
    log_step("Starting Analysis creation...")
    print_colored("Creating Analysis file...", Colors.BLUE)

    # Get previous month data if available
    if month_num == 1:
        prev_month = 12
        prev_year = year_num - 1
    else:
        prev_month = month_num - 1
        prev_year = year_num

    prev_folder = Path("ALL-MONTHS") / f"Raw {prev_month}.{prev_year % 100}"
    if prev_folder.exists():
        previous_month_df = process_month_data(
            prev_folder,
            field_mapper,
            provider_grouper,
            prev_month,
            prev_year,
            batch_size=1000
        )
    else:
        previous_month_df = pd.DataFrame()

    # Get historical data (All-to-Date from PREVIOUS month, not including current)
    # This is critical - we need historical data that doesn't include current month
    historical_df = pd.DataFrame()
    if existing_files and relevant_files:
        # Find the most recent All-to-Date file BEFORE current month
        for f, file_year, file_month in relevant_files:
            # Only use files from before current month
            if (file_year < year_num % 100) or (file_year == year_num % 100 and file_month < month_num):
                try:
                    historical_df = pd.read_excel(f)
                    log_step(f"Using historical data from {f.name}")
                    break
                except:
                    continue

    # If no previous All-to-Date exists, use previous month as historical
    if historical_df.empty and not previous_month_df.empty:
        historical_df = previous_month_df

    # Perform analysis with proper historical data (excluding current month)
    log_step("Calling analyzer.analyze_month_changes...")
    analysis_df = analyzer.analyze_month_changes(
        current_month_df,
        previous_month_df,
        historical_df  # Pass truly historical data, not combined_df
    )

    # Add required columns
    log_step("Calculating provider groups...")
    analysis_df = analyzer.calculate_provider_groups(analysis_df)

    # Add summary columns AFTER provider groups are calculated (needs Column M and N)
    analysis_df = analyzer.create_summary_columns(analysis_df)

    # Calculate enhanced tracking fields (EH:EY columns)
    analysis_df = analyzer.calculate_enhanced_tracking_fields(analysis_df, previous_month_df)

    analysis_df = analyzer.ensure_all_analysis_columns(analysis_df, month_num, year_num)

    # Ensure CAPACITY is formatted as integers (no decimals) - MOVED AFTER ensure_all_analysis_columns
    if 'CAPACITY' in analysis_df.columns:
        analysis_df['CAPACITY'] = pd.to_numeric(analysis_df['CAPACITY'], errors='coerce')
        # Convert to integers where not null, then to string
        mask = analysis_df['CAPACITY'].notna() & (analysis_df['CAPACITY'] != 0)
        analysis_df.loc[mask, 'CAPACITY'] = analysis_df.loc[mask, 'CAPACITY'].astype(int).astype(str)
        # Set null/0 values to empty string
        analysis_df.loc[~mask, 'CAPACITY'] = ''

    # Fix MONTH and YEAR
    analysis_df['MONTH'] = month_num
    analysis_df['YEAR'] = year_num

    # Optimize N/A values - FIXED: Use empty strings instead of pd.NA to prevent column dropping
    for col in analysis_df.columns:
        if analysis_df[col].dtype == 'object':
            analysis_df[col] = analysis_df[col].replace('N/A', '')
            # Don't replace empty strings - they're already correct

    # Create sheets - pass month and year for v300 compliance
    log_step("Creating analysis summary sheet...")
    summary_df = create_analysis_summary_sheet(analysis_df, current_month_df)  # Pass Reformat data
    log_step("Creating blanks count sheet...")
    blanks_df = create_blanks_count_sheet(current_month_df, month_num, year_num)  # Pass month/year for v300

    # Validate column count for v300Track_this.xlsx 1:1 alignment
    expected_columns = 155  # v300Track_this.xlsx has columns A through EY (155 columns)
    actual_columns = len(analysis_df.columns)

    log_step(f"Column validation: {actual_columns} columns (expected: {expected_columns})")
    print_colored(f"Analysis DataFrame has {actual_columns} columns", Colors.BLUE)
    print_colored(f"First 5 columns: {list(analysis_df.columns[:5])}", Colors.BLUE)
    print_colored(f"Last 5 columns: {list(analysis_df.columns[-5:])}", Colors.BLUE)

    if actual_columns != expected_columns:
        print_colored(f"❌ COLUMN COUNT MISMATCH: Expected {expected_columns} columns, got {actual_columns}", Colors.RED)
        print_colored(f"❌ NOT CONSISTENT WITH v300Track_this.xlsx - BLOCKING OUTPUT", Colors.RED)
        print_colored(f"❌ NO FILES WILL BE WRITTEN UNTIL COLUMN STRUCTURE MATCHES v300", Colors.RED)
        return False  # Block processing completely
    else:
        print_colored(f"✅ Column count validated: {actual_columns} columns match v300Track_this.xlsx", Colors.GREEN)

    # Save Analysis with all sheets
    analysis_path = Path("Analysis") / f"{month_code} Analysis.xlsx"
    log_step(f"Saving analysis to {analysis_path}...")
    sheet_data = {
        'Summary': summary_df,
        'Blanks Count': blanks_df,
        'Analysis': analysis_df
    }

    if not safe_write_excel(None, analysis_path, sheet_data):
        return False

    print_colored(f"✅ Successfully processed {month_code}", Colors.GREEN)
    return True

def main():
    """Process the three problematic months."""
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("ADHS ETL Direct Month Processing", Colors.BOLD + Colors.BLUE)
    print_colored("Processing months 9.24, 10.24, 11.24", Colors.BLUE)
    print_colored("="*60, Colors.BLUE)

    months = [
        ("9.24", "Raw 9.24"),
        ("10.24", "Raw 10.24"),
        ("11.24", "Raw 11.24")
    ]

    successful = []
    failed = []

    for month_code, folder_name in months:
        try:
            if process_single_month(month_code, folder_name):
                successful.append(month_code)
            else:
                failed.append(month_code)
        except Exception as e:
            print_colored(f"❌ Error processing {month_code}: {e}", Colors.RED)
            failed.append(month_code)

    # Summary
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("PROCESSING COMPLETE", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)

    if successful:
        print_colored(f"\n✅ Successfully processed: {', '.join(successful)}", Colors.GREEN)

    if failed:
        print_colored(f"\n❌ Failed: {', '.join(failed)}", Colors.RED)

    print_colored("\n📁 Check output directories:", Colors.BOLD)
    print_colored("  • Reformat/", Colors.WHITE)
    print_colored("  • All-to-Date/", Colors.WHITE)
    print_colored("  • Analysis/", Colors.WHITE)

if __name__ == "__main__":
    main()