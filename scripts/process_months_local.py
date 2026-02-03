#!/usr/bin/env python3
"""
Enhanced Month Processing Script with Interactive Menu
=======================================================

Processes any range of months with an interactive selection menu.
Preserves all existing processing logic from process_months_local.py
"""

import os
import shutil
import sys
import time
import tempfile
import subprocess
from pathlib import Path
import pandas as pd
from datetime import datetime
import pyfiglet

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
from adhs_etl.mcao_client import MCAAOAPIClient
from adhs_etl.mcao_field_mapping import (
    MCAO_MAX_HEADERS,
    get_empty_mcao_record,
    validate_mcao_record
)
from adhs_etl.utils import (
    get_standard_timestamp,
    format_output_filename,
    get_legacy_filename,
    save_with_legacy_copy,
    save_excel_with_legacy_copy,
    extract_timestamp_from_filename
)
from adhs_etl.batchdata_bridge import (
    create_batchdata_upload,
    run_batchdata_enrichment
)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
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

def scan_available_months():
    """Scan ALL-MONTHS directory for available months."""
    all_months_dir = Path("ALL-MONTHS")
    if not all_months_dir.exists():
        print_colored(f"❌ ALL-MONTHS directory not found!", Colors.RED)
        return []

    months = []
    for folder in sorted(all_months_dir.iterdir()):
        if folder.is_dir() and folder.name.startswith("Raw "):
            # Extract month code from folder name (e.g., "Raw 9.24" -> "9.24")
            month_code = folder.name.replace("Raw ", "")
            try:
                # Validate format
                parts = month_code.split('.')
                if len(parts) == 2:
                    month_num = int(parts[0])
                    year_num = int(parts[1])
                    if 1 <= month_num <= 12 and 0 <= year_num <= 99:
                        months.append((month_code, folder.name, month_num, year_num))
            except ValueError:
                continue

    # Sort by year then month
    months.sort(key=lambda x: (x[3], x[2]))
    return months

def display_available_months(months):
    """Display available months in a formatted way."""
    print_colored("\n📅 Available Months:", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 60, Colors.CYAN)

    for i, (month_code, folder_name, month_num, year_num) in enumerate(months, 1):
        # Format month name
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_name = month_names[month_num] if month_num <= 12 else str(month_num)
        year_full = 2000 + year_num

        # Color based on year
        if year_num == 24:
            color = Colors.YELLOW
        elif year_num == 25:
            color = Colors.GREEN
        else:
            color = Colors.WHITE

        print(f"{color}{i:3d}. {month_code:6s} - {month_name} {year_full}{Colors.END}")

def get_month_selection(months, prompt):
    """Get a valid month selection from user."""
    while True:
        try:
            selection = input(f"\n{Colors.BOLD}{prompt}{Colors.END} (1-{len(months)}): ").strip()
            if not selection:
                print_colored("❌ Please enter a number", Colors.RED)
                continue

            idx = int(selection) - 1
            if 0 <= idx < len(months):
                return idx
            else:
                print_colored(f"❌ Please enter a number between 1 and {len(months)}", Colors.RED)
        except ValueError:
            print_colored("❌ Invalid input. Please enter a number", Colors.RED)

def get_test_mode():
    """Get test mode selection from user.

    Returns:
        str: 'full', 'first5', or 'random5'
    """
    print_colored("\n" + "=" * 60, Colors.CYAN)
    print_colored("🧪 TEST MODE SELECTION", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 60, Colors.CYAN)

    print_colored("\nChoose processing mode:", Colors.YELLOW)
    print_colored("  1. Full processing (all records)", Colors.WHITE)
    print_colored("  2. Test mode - First 5 records", Colors.WHITE)
    print_colored("  3. Test mode - Random 5 records", Colors.WHITE)

    while True:
        try:
            selection = input(f"\n{Colors.BOLD}Enter mode (1-3): {Colors.END}").strip()
            if selection == '1':
                print_colored("  ✓ Full processing selected", Colors.GREEN)
                return 'full'
            elif selection == '2':
                print_colored("  ✓ Test mode (First 5) selected", Colors.YELLOW)
                return 'first5'
            elif selection == '3':
                print_colored("  ✓ Test mode (Random 5) selected", Colors.YELLOW)
                return 'random5'
            else:
                print_colored("❌ Please enter 1, 2, or 3", Colors.RED)
        except ValueError:
            print_colored("❌ Invalid input. Please enter 1, 2, or 3", Colors.RED)

def get_confirmation(start_month, end_month, months_to_process):
    """Get user confirmation before processing."""
    print_colored("\n" + "=" * 60, Colors.BLUE)
    print_colored("📋 PROCESSING SUMMARY", Colors.BOLD + Colors.BLUE)
    print_colored("=" * 60, Colors.BLUE)

    print_colored(f"\n📌 Start: {start_month}", Colors.CYAN)
    print_colored(f"📌 End:   {end_month}", Colors.CYAN)
    print_colored(f"📌 Total months to process: {len(months_to_process)}", Colors.CYAN)

    print_colored("\nMonths to process:", Colors.YELLOW)
    for month_code, _, _, _ in months_to_process:
        print(f"  • {month_code}")

    print_colored("\nOutput will be created in:", Colors.YELLOW)
    print_colored("  • Reformat/", Colors.WHITE)
    print_colored("  • All-to-Date/", Colors.WHITE)
    print_colored("  • Analysis/", Colors.WHITE)
    print_colored("  • APN/Upload/ (MARICOPA records only)", Colors.WHITE)

    # Get APN processing preference
    process_apn = False
    process_mcao = False

    while True:
        response = input(f"\n{Colors.BOLD}Process complete APNs (y/N)? {Colors.END}").strip().lower()
        if response in ['y', 'yes']:
            process_apn = True
            print_colored("  ✓ Will process complete APNs after extraction", Colors.GREEN)
            break
        elif response in ['n', 'no', '']:
            process_apn = False
            print_colored("  ✓ Will only create APN Upload files", Colors.YELLOW)
            break
        else:
            print_colored("Please enter 'y' for yes or 'n' for no", Colors.YELLOW)

    # Only ask about MCAO if APN processing is enabled
    if process_apn:
        while True:
            response = input(f"\n{Colors.BOLD}Process MCAO data enrichment (y/N)? {Colors.END}").strip().lower()
            if response in ['y', 'yes']:
                process_mcao = True
                print_colored("  ✓ Will enrich data with MCAO API", Colors.GREEN)
                print_colored("    • Output: MCAO/Upload/ (filtered APNs)", Colors.WHITE)
                print_colored("    • Output: MCAO/Complete/ (enriched with 106 fields)", Colors.WHITE)
                break
            elif response in ['n', 'no', '']:
                process_mcao = False
                print_colored("  ✓ Skipping MCAO enrichment", Colors.YELLOW)
                break
            else:
                print_colored("Please enter 'y' for yes or 'n' for no", Colors.YELLOW)

    # Only ask about Ecorp if MCAO processing is enabled
    process_ecorp = False
    if process_mcao:
        while True:
            response = input(f"\n{Colors.BOLD}Generate Ecorp entity files? (y/N): {Colors.END}").strip().lower()
            if response in ['y', 'yes']:
                process_ecorp = True
                print_colored("  ✓ Will generate Ecorp Upload and Complete files", Colors.GREEN)
                print_colored("    • Output: Ecorp/Upload/ (4 columns from MCAO)", Colors.WHITE)
                print_colored("    • Output: Ecorp/Complete/ (93 columns with ACC data)", Colors.WHITE)
                break
            elif response in ['n', 'no', '']:
                process_ecorp = False
                print_colored("  ✓ Skipping Ecorp generation", Colors.YELLOW)
                break
            else:
                print_colored("Please enter 'y' for yes or 'n' for no", Colors.YELLOW)

    # Only ask about BatchData if Ecorp processing is enabled
    process_batchdata = False
    if process_ecorp:
        while True:
            response = input(f"\n{Colors.BOLD}Run BatchData enrichment (contact discovery)? (y/N): {Colors.END}").strip().lower()
            if response in ['y', 'yes']:
                process_batchdata = True
                print_colored("  ✓ Will run BatchData contact discovery pipeline", Colors.GREEN)
                print_colored("    • Output: Batchdata/Upload/ (prepared for API)", Colors.WHITE)
                print_colored("    • Output: Batchdata/Complete/ (enriched with phone/email)", Colors.WHITE)
                print_colored("    • Note: Incurs API costs - estimate shown before processing", Colors.YELLOW)
                break
            elif response in ['n', 'no', '']:
                process_batchdata = False
                print_colored("  ✓ Skipping BatchData enrichment", Colors.YELLOW)
                break
            else:
                print_colored("Please enter 'y' for yes or 'n' for no", Colors.YELLOW)

    while True:
        response = input(f"\n{Colors.BOLD}Ready to proceed? (y/N): {Colors.END}").strip().lower()
        if response in ['y', 'yes']:
            return True, process_apn, process_mcao, process_ecorp, process_batchdata
        elif response in ['n', 'no', '']:
            return False, False, False, False, False
        else:
            print_colored("Please enter 'y' for yes or 'n' for no", Colors.YELLOW)

def process_single_month(month_code: str, folder_name: str, test_mode: str = 'full', session_timestamp: str = None):
    """Process a single month directly.

    Args:
        month_code: Month code (e.g., "1.25")
        folder_name: Folder name in ALL-MONTHS directory
        test_mode: 'full', 'first5', or 'random5'
        session_timestamp: Optional session timestamp for consistent naming across all outputs
    """
    print_colored(f"\n{'='*60}", Colors.BLUE)
    print_colored(f"Processing {month_code}", Colors.BOLD + Colors.PURPLE)
    if test_mode != 'full':
        mode_label = "First 5" if test_mode == 'first5' else "Random 5"
        print_colored(f"🧪 TEST MODE: {mode_label} records", Colors.YELLOW)
    print_colored(f"{'='*60}", Colors.BLUE)

    # Generate session timestamp for consistent naming across all outputs
    if session_timestamp is None:
        session_timestamp = get_standard_timestamp()

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
        return False, None

    log_step(f"Processed {len(current_month_df)} records")
    print_colored(f"✅ Processed {len(current_month_df)} records", Colors.GREEN)

    # Apply test mode filtering if requested
    selected_rows = None
    if test_mode != 'full' and len(current_month_df) > 0:
        original_count = len(current_month_df)

        if test_mode == 'first5':
            # Take first 5 records
            current_month_df = current_month_df.head(5).copy()
            selected_rows = list(range(min(5, original_count)))
            print_colored(f"🧪 Test mode: Selected first {len(current_month_df)} records (rows 0-{len(current_month_df)-1})", Colors.YELLOW)

        elif test_mode == 'random5':
            # Take random 5 records
            import random
            num_to_select = min(5, original_count)
            random.seed()  # Use system time for randomness
            selected_indices = sorted(random.sample(range(original_count), num_to_select))
            current_month_df = current_month_df.iloc[selected_indices].copy()
            selected_rows = selected_indices
            print_colored(f"🧪 Test mode: Selected {len(current_month_df)} random records", Colors.YELLOW)
            print_colored(f"   Selected rows: {selected_rows}", Colors.CYAN)

        print_colored(f"   (Original dataset had {original_count} records)", Colors.CYAN)

    # Create output directories
    Path("Reformat").mkdir(exist_ok=True)
    Path("All-to-Date").mkdir(exist_ok=True)
    Path("Analysis").mkdir(exist_ok=True)

    # 1. Save Reformat (new format + legacy copy)
    reformat_new_filename = format_output_filename(month_code, "Reformat", session_timestamp)
    reformat_legacy_filename = get_legacy_filename(month_code, "Reformat")
    reformat_new_path = Path("Reformat") / reformat_new_filename
    reformat_legacy_path = Path("Reformat") / reformat_legacy_filename

    log_step(f"Creating Reformat file at {reformat_new_path}...")
    print_colored("Creating Reformat file...", Colors.BLUE)

    # Save with legacy copy
    if not safe_write_excel(current_month_df, reformat_new_path):
        return False, None

    # Create legacy copy
    save_excel_with_legacy_copy(reformat_new_path, reformat_legacy_path)
    print_colored(f"✅ Created legacy copy: {reformat_legacy_path.name}", Colors.GREEN)

    # 2. Create All-to-Date (new format + legacy copy)
    log_step("Starting All-to-Date creation...")
    print_colored("Creating All-to-Date file...", Colors.BLUE)

    all_to_date_new_filename = format_output_filename(month_code, "Reformat_All_to_Date", session_timestamp)
    all_to_date_legacy_filename = get_legacy_filename(month_code, "Reformat_All_to_Date")
    all_to_date_new_path = Path("All-to-Date") / all_to_date_new_filename
    all_to_date_legacy_path = Path("All-to-Date") / all_to_date_legacy_filename

    # Get previous All-to-Date if exists (support both old and new formats)
    all_to_date_dir = Path("All-to-Date")
    old_format_files = list(all_to_date_dir.glob("Reformat All to Date *.xlsx"))
    new_format_files = list(all_to_date_dir.glob("*_Reformat_All_to_Date_*.xlsx"))
    existing_files = old_format_files + new_format_files

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

    # Save with both new and legacy format
    if not safe_write_excel(combined_df, all_to_date_new_path):
        return False, None

    # Create legacy copy
    save_excel_with_legacy_copy(all_to_date_new_path, all_to_date_legacy_path)
    print_colored(f"✅ Created legacy copy: {all_to_date_legacy_path.name}", Colors.GREEN)

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
        # Find the most recent month, then pick the LARGEST file for that month
        # (larger files have more complete data vs tiny test/failed runs)
        most_recent_month = max(relevant_files, key=lambda x: (x[1], x[2]))
        target_year, target_month = most_recent_month[1], most_recent_month[2]

        # Get all files for the most recent month
        same_month_files = [f for f in relevant_files if f[1] == target_year and f[2] == target_month]

        # Pick the largest file (most complete data)
        best_file = max(same_month_files, key=lambda x: x[0].stat().st_size)[0]

        try:
            historical_df = pd.read_excel(best_file)
            log_step(f"Using historical data from {best_file.name} ({best_file.stat().st_size:,} bytes)")
        except Exception as e:
            log_step(f"Warning: Could not load historical data: {e}")

    # If no previous All-to-Date exists, use previous month as historical
    if historical_df.empty and not previous_month_df.empty:
        historical_df = previous_month_df

    # Perform analysis with proper historical data (excluding current month)
    log_step("Calling analyzer.analyze_month_changes...")
    # Skip lost license processing in test mode to avoid bloating the dataset
    skip_lost = (test_mode != 'full')
    analysis_df = analyzer.analyze_month_changes(
        current_month_df,
        previous_month_df,
        historical_df,  # Pass truly historical data, not combined_df
        skip_lost_licenses=skip_lost
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
        return False, None  # Block processing completely
    else:
        print_colored(f"✅ Column count validated: {actual_columns} columns match v300Track_this.xlsx", Colors.GREEN)

    # Save Analysis with all sheets (new format + legacy copy)
    analysis_new_filename = format_output_filename(month_code, "Analysis", session_timestamp)
    analysis_legacy_filename = get_legacy_filename(month_code, "Analysis")
    analysis_new_path = Path("Analysis") / analysis_new_filename
    analysis_legacy_path = Path("Analysis") / analysis_legacy_filename

    log_step(f"Saving analysis to {analysis_new_path}...")
    sheet_data = {
        'Summary': summary_df,
        'Blanks Count': blanks_df,
        'Analysis': analysis_df
    }

    if not safe_write_excel(None, analysis_new_path, sheet_data):
        return False, None

    # Create legacy copy
    save_excel_with_legacy_copy(analysis_new_path, analysis_legacy_path)
    print_colored(f"✅ Created legacy copy: {analysis_legacy_path.name}", Colors.GREEN)

    print_colored(f"✅ Successfully processed {month_code}", Colors.GREEN)

    # Return analysis_df so we can extract APN data from it
    return True, analysis_df

def extract_apn_upload(month_code: str, analysis_df: pd.DataFrame, session_timestamp: str = None):
    """Extract MARICOPA-only records from Analysis file for APN processing.

    Args:
        month_code: Month code (e.g., "1.25")
        analysis_df: The Analysis dataframe with all columns
        session_timestamp: Optional session timestamp for consistent naming

    Returns:
        Path to the created Upload file, or None if failed
    """
    try:
        # Create APN/Upload directory if it doesn't exist
        upload_dir = Path("APN/Upload")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Check if required columns exist
        if 'FULL_ADDRESS' not in analysis_df.columns:
            print_colored(f"❌ 'FULL_ADDRESS' column not found in Analysis", Colors.RED)
            return None

        if 'COUNTY' not in analysis_df.columns:
            print_colored(f"❌ 'COUNTY' column not found in Analysis", Colors.RED)
            return None

        # Filter for MARICOPA records (case-insensitive)
        maricopa_mask = analysis_df['COUNTY'].fillna('').str.upper().str.contains('MARICOPA', na=False)
        maricopa_df = analysis_df[maricopa_mask][['FULL_ADDRESS', 'COUNTY']].copy()

        print_colored(f"📊 Found {len(maricopa_df)} MARICOPA records out of {len(analysis_df)} total", Colors.CYAN)

        # Use session timestamp for consistency
        if session_timestamp is None:
            session_timestamp = get_standard_timestamp()

        # Create output filenames (new format + legacy)
        new_filename = format_output_filename(month_code, "APN_Upload", session_timestamp)
        legacy_filename = get_legacy_filename(month_code, "APN_Upload", session_timestamp)
        new_path = upload_dir / new_filename
        legacy_path = upload_dir / legacy_filename

        # Write to Excel (new format)
        if safe_write_excel(maricopa_df, new_path):
            print_colored(f"✅ Created APN Upload file: {new_path}", Colors.GREEN)
            # Create legacy copy
            save_excel_with_legacy_copy(new_path, legacy_path)
            print_colored(f"✅ Created legacy copy: {legacy_path.name}", Colors.GREEN)
            return new_path
        else:
            return None

    except Exception as e:
        print_colored(f"❌ Error extracting APN data: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return None

def extract_mcao_upload(month_code: str, apn_complete_path: Path):
    """Extract MCAO Upload file from APN_Complete by filtering out empty APNs.

    Args:
        month_code: Month code (e.g., "1.25")
        apn_complete_path: Path to the APN_Complete file

    Returns:
        Path to the created MCAO_Upload file, or None if failed
    """
    try:
        # Create MCAO/Upload directory
        upload_dir = Path("MCAO/Upload")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Read APN_Complete file
        print_colored(f"📋 Reading APN_Complete: {apn_complete_path.name}", Colors.CYAN)
        df = pd.read_excel(apn_complete_path)

        # Check required columns exist
        if len(df.columns) < 3:
            print_colored(f"❌ APN_Complete must have at least 3 columns, found {len(df.columns)}", Colors.RED)
            return None

        # Ensure columns are named correctly
        df.columns = ['FULL_ADDRESS', 'COUNTY', 'APN'] + list(df.columns[3:])

        # Ensure APN column is string type for filtering (may be numeric from Excel)
        df['APN'] = df['APN'].astype(str)

        # Filter out rows where APN is empty/null
        original_count = len(df)
        df_filtered = df[df['APN'].notna() & (df['APN'] != '') & (df['APN'] != 'nan') & (~df['APN'].str.upper().isin(['NONE', 'NULL', 'NA', 'N/A']))].copy()
        filtered_count = len(df_filtered)
        removed_count = original_count - filtered_count

        print_colored(f"📊 Filtered APNs: {filtered_count} valid, {removed_count} empty/invalid removed", Colors.CYAN)

        if filtered_count == 0:
            print_colored(f"❌ No valid APNs found after filtering", Colors.RED)
            return None

        # Extract timestamp from APN_Complete filename for consistency
        timestamp = extract_timestamp_from_filename(apn_complete_path.name)

        # If no timestamp found, generate new one
        if not timestamp:
            timestamp = get_standard_timestamp()

        # Create output filenames (new format + legacy)
        new_filename = format_output_filename(month_code, "MCAO_Upload", timestamp)
        legacy_filename = get_legacy_filename(month_code, "MCAO_Upload", timestamp)
        new_path = upload_dir / new_filename
        legacy_path = upload_dir / legacy_filename

        # Save filtered data (only first 3 columns for Upload)
        df_upload = df_filtered[['FULL_ADDRESS', 'COUNTY', 'APN']].copy()

        # Save with both new and legacy format
        if safe_write_excel(df_upload, new_path):
            print_colored(f"✅ Created MCAO Upload file: {new_path}", Colors.GREEN)
            # Create legacy copy
            save_excel_with_legacy_copy(new_path, legacy_path)
            print_colored(f"✅ Created legacy copy: {legacy_path.name}", Colors.GREEN)
            return new_path
        else:
            return None

    except Exception as e:
        print_colored(f"❌ Error creating MCAO Upload: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return None

def process_mcao_complete(month_code: str, mcao_upload_path: Path):
    """Process MCAO Upload file and enrich with API data to create MCAO_Complete.

    Args:
        month_code: Month code (e.g., "1.25")
        mcao_upload_path: Path to the MCAO_Upload file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directories
        complete_dir = Path("MCAO/Complete")
        complete_dir.mkdir(parents=True, exist_ok=True)

        logs_dir = Path("MCAO/Logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Read MCAO_Upload file
        print_colored(f"📋 Processing MCAO enrichment for: {mcao_upload_path.name}", Colors.CYAN)
        df_upload = pd.read_excel(mcao_upload_path)
        total_records = len(df_upload)

        # Initialize MCAO API client
        try:
            client = MCAAOAPIClient(rate_limit=5.0)
        except ValueError as e:
            print_colored(f"❌ Failed to initialize MCAO API client: {e}", Colors.RED)
            print_colored("   Ensure MCAO_API_KEY is set in .env file", Colors.YELLOW)
            return False

        # Process each record
        results = []
        errors = []
        successful = 0
        failed = 0
        skipped = 0

        print_colored(f"⚡ Processing {total_records} records at 5 req/sec...", Colors.BLUE)
        print_colored(f"   Estimated time: ~{(total_records * 6 / 5) / 60:.1f} minutes (6 API calls per APN)", Colors.CYAN)

        start_time = time.time()

        for idx, row in df_upload.iterrows():
            # Progress indicator
            if idx % 10 == 0 and idx > 0:
                elapsed = time.time() - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                remaining = (total_records - idx) / rate if rate > 0 else 0
                print(f"   Progress: {idx}/{total_records} ({idx*100//total_records}%) | "
                      f"Success: {successful} | Failed: {failed} | "
                      f"Rate: {rate:.1f} rec/sec | ETA: {remaining/60:.1f} min", flush=True)

            apn = row['APN']

            # Skip if APN is invalid
            if not apn or str(apn).strip() == '':
                skipped += 1
                continue

            # Get all property data from API
            api_data = client.get_all_property_data(str(apn))

            if api_data.get('data_complete', False):
                # Map API data to MAX_HEADERS structure
                mapped_data = client.map_to_max_headers(api_data)

                # Start with the original 3 columns
                record = {
                    'FULL_ADDRESS': row['FULL_ADDRESS'],
                    'COUNTY': row['COUNTY'],
                    'APN': row['APN']
                }

                # Add mapped API data
                record.update(mapped_data)

                # Validate and clean record
                clean_record = validate_mcao_record(record)
                results.append(clean_record)
                successful += 1
            else:
                # Log error but don't include in output
                failed += 1
                error_entry = {
                    'FULL_ADDRESS': row['FULL_ADDRESS'],
                    'COUNTY': row['COUNTY'],
                    'APN': apn,
                    'ERRORS': '; '.join(api_data.get('errors', ['Unknown error'])),
                    'TIMESTAMP': datetime.now().isoformat()
                }
                errors.append(error_entry)

        elapsed_total = time.time() - start_time

        # Print summary
        print_colored(f"\n📊 MCAO Processing Complete:", Colors.BOLD + Colors.BLUE)
        print_colored(f"   Total records: {total_records}", Colors.CYAN)
        print_colored(f"   Successful: {successful} ({successful*100//max(total_records, 1)}%)", Colors.GREEN)
        print_colored(f"   Failed: {failed} ({failed*100//max(total_records, 1)}%)", Colors.YELLOW if failed > 0 else Colors.GREEN)
        print_colored(f"   Skipped: {skipped}", Colors.YELLOW if skipped > 0 else Colors.GREEN)
        print_colored(f"   Total time: {elapsed_total/60:.1f} minutes", Colors.CYAN)

        # Save MCAO_Complete if we have results
        if results:
            # Create DataFrame with all columns in correct order
            df_complete = pd.DataFrame(results, columns=MCAO_MAX_HEADERS)

            # Extract timestamp from upload filename for consistency
            timestamp = extract_timestamp_from_filename(mcao_upload_path.name)

            if not timestamp:
                timestamp = get_standard_timestamp()

            # Create output filenames (new format + legacy)
            new_filename = format_output_filename(month_code, "MCAO_Complete", timestamp)
            legacy_filename = get_legacy_filename(month_code, "MCAO_Complete", timestamp)
            new_path = complete_dir / new_filename
            legacy_path = complete_dir / legacy_filename

            # Save with both new and legacy format
            if safe_write_excel(df_complete, new_path):
                print_colored(f"✅ Created MCAO Complete file: {new_path}", Colors.GREEN)
                # Create legacy copy
                save_excel_with_legacy_copy(new_path, legacy_path)
                print_colored(f"✅ Created legacy copy: {legacy_path.name}", Colors.GREEN)
            else:
                print_colored(f"❌ Failed to save MCAO Complete file", Colors.RED)
                return False

        # Save error log if there were errors
        if errors:
            df_errors = pd.DataFrame(errors)
            error_filename = f"{month_code}_MCAO_errors_{timestamp}.xlsx"
            error_path = logs_dir / error_filename

            if safe_write_excel(df_errors, error_path):
                print_colored(f"📝 Error log saved: {error_path}", Colors.YELLOW)

            # Update cumulative error log
            cumulative_log = logs_dir / "MCAO_all_errors.xlsx"
            if cumulative_log.exists():
                df_existing = pd.read_excel(cumulative_log)
                df_all_errors = pd.concat([df_existing, df_errors], ignore_index=True)
            else:
                df_all_errors = df_errors

            safe_write_excel(df_all_errors, cumulative_log)

        return True

    except Exception as e:
        print_colored(f"❌ Error processing MCAO Complete: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return False

def run_apn_lookup(upload_path: Path):
    """Run apn_lookup.py on the upload file to generate Complete file.

    Args:
        upload_path: Path to the Upload file

    Returns:
        True if successful, False otherwise
    """
    try:
        apn_script = Path("APN/apn_lookup.py")
        if not apn_script.exists():
            print_colored(f"❌ apn_lookup.py not found at {apn_script}", Colors.RED)
            return False

        # Count records for time estimation
        num_records = len(pd.read_excel(upload_path))
        estimated_minutes = max(1, (num_records / 5) / 60)  # 5 requests per second

        print_colored(f"🔄 Running APN lookup on {upload_path.name}...", Colors.BLUE)
        print_colored(f"   Processing {num_records} records at 5 req/sec", Colors.CYAN)
        print_colored(f"   Estimated time: ~{estimated_minutes:.1f} minutes (if no cache hits)", Colors.CYAN)
        print_colored(f"   Press Ctrl+C to skip APN processing for remaining months", Colors.YELLOW)

        # Use Popen for real-time output streaming
        # Add -u flag for unbuffered Python output
        process = subprocess.Popen(
            [sys.executable, "-u", str(apn_script), "-i", str(upload_path), "--rate", "5.0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            env={**os.environ, "PYTHONUNBUFFERED": "1"}  # Force unbuffered output
        )

        # Stream output in real-time
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break

                # Color-code different types of output
                line = line.rstrip()
                if "Progress:" in line:
                    print(f"   {line}", flush=True)  # Show progress updates
                elif "Cache hits:" in line or "📊" in line:
                    print_colored(f"   {line}", Colors.CYAN)
                elif "ERROR" in line or "❌" in line:
                    print_colored(f"   {line}", Colors.RED)
                elif "✅" in line or "Wrote:" in line:
                    print_colored(f"   {line}", Colors.GREEN)
                elif line:
                    print(f"   {line}", flush=True)

            # Wait for process to complete
            process.wait()

            if process.returncode == 0:
                print_colored(f"✅ APN lookup completed successfully", Colors.GREEN)
                return True
            else:
                # Read any error output
                stderr_output = process.stderr.read()
                print_colored(f"❌ APN lookup failed with exit code {process.returncode}", Colors.RED)
                if stderr_output:
                    print_colored(f"Error output: {stderr_output}", Colors.RED)
                return False

        except KeyboardInterrupt:
            print_colored(f"\n⚠️  APN lookup interrupted by user", Colors.YELLOW)
            process.terminate()
            process.wait()
            return False

    except Exception as e:
        print_colored(f"❌ Error running APN lookup: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function with interactive menu."""
    # Display pyfiglet banner
    banner = pyfiglet.figlet_format("ADHS ETL", font="slant")
    print_colored("\n" + "="*60, Colors.BOLD + Colors.CYAN)
    for line in banner.split('\n'):
        print_colored(line, Colors.BOLD + Colors.CYAN)
    print_colored("Interactive Month Processor", Colors.BOLD + Colors.CYAN)
    print_colored("="*60, Colors.BOLD + Colors.CYAN)

    # Scan available months
    months = scan_available_months()

    if not months:
        print_colored("❌ No valid months found in ALL-MONTHS directory!", Colors.RED)
        return

    # Display available months
    display_available_months(months)

    # Get start month
    start_idx = get_month_selection(months, "Enter START month number")
    start_month = months[start_idx][0]

    # Get end month
    end_idx = get_month_selection(months, "Enter END month number")
    end_month = months[end_idx][0]

    # Validate range
    if start_idx > end_idx:
        print_colored("\n⚠️  Warning: Start month is after end month. Swapping them.", Colors.YELLOW)
        start_idx, end_idx = end_idx, start_idx
        start_month, end_month = end_month, start_month

    # Get months to process
    months_to_process = months[start_idx:end_idx + 1]

    # Get test mode selection
    test_mode = get_test_mode()

    # Get confirmation
    confirmed, process_apn, process_mcao, process_ecorp, process_batchdata = get_confirmation(start_month, end_month, months_to_process)
    if not confirmed:
        print_colored("\n🚫 Processing cancelled by user", Colors.YELLOW)
        return

    # Process months
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("🔄 STARTING BATCH PROCESSING", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)

    successful = []
    failed = []
    apn_errors = []
    mcao_errors = []
    ecorp_errors = []
    batchdata_errors = []

    for month_code, folder_name, _, _ in months_to_process:
        try:
            # Generate session timestamp once per month for consistency across all outputs
            session_timestamp = get_standard_timestamp()

            result = process_single_month(month_code, folder_name, test_mode, session_timestamp)
            if isinstance(result, tuple):
                success, analysis_df = result
            else:
                # Backward compatibility if process_single_month returns bool
                success = result
                analysis_df = None

            if success:
                successful.append(month_code)

                # Extract APN data if we have analysis_df
                if analysis_df is not None:
                    print_colored(f"\n📋 Extracting APN data for {month_code}...", Colors.CYAN)
                    upload_path = extract_apn_upload(month_code, analysis_df, session_timestamp)

                    # Run APN lookup if requested
                    if upload_path and process_apn:
                        apn_complete_path = None
                        if run_apn_lookup(upload_path):
                            # Find the generated APN_Complete file
                            complete_dir = Path("APN/Complete")
                            if complete_dir.exists():
                                # Look for most recent file matching pattern
                                pattern = f"{month_code}_APN_Complete*.xlsx"
                                matches = list(complete_dir.glob(pattern))
                                if matches:
                                    apn_complete_path = max(matches, key=lambda p: p.stat().st_mtime)

                            # Process MCAO if requested and APN_Complete exists
                            if apn_complete_path and process_mcao:
                                print_colored(f"\n🔄 Starting MCAO enrichment for {month_code}...", Colors.CYAN)
                                mcao_upload_path = extract_mcao_upload(month_code, apn_complete_path)

                                if mcao_upload_path:
                                    if process_mcao_complete(month_code, mcao_upload_path):
                                        # Process Ecorp if requested and MCAO completed successfully
                                        if process_ecorp:
                                            # Find most recent MCAO_Complete file
                                            mcao_complete_pattern = f"{month_code}_MCAO_Complete*.xlsx"
                                            complete_dir = Path("MCAO/Complete")
                                            matches = list(complete_dir.glob(mcao_complete_pattern))

                                            if matches:
                                                mcao_complete_path = max(matches, key=lambda p: p.stat().st_mtime)

                                                print_colored(f"\n🏢 Generating Ecorp Upload for {month_code}...", Colors.CYAN)
                                                from adhs_etl.ecorp import generate_ecorp_upload, generate_ecorp_complete

                                                try:
                                                    ecorp_upload_path = generate_ecorp_upload(month_code, mcao_complete_path)

                                                    if ecorp_upload_path:
                                                        print_colored(f"\n🔍 Running ACC entity lookup for {month_code}...", Colors.CYAN)
                                                        num_records = len(pd.read_excel(ecorp_upload_path))
                                                        estimated_minutes = max(1, (num_records * 4) / 60)
                                                        print_colored(f"   Processing {num_records} records at ~4 sec/record", Colors.CYAN)
                                                        print_colored(f"   Estimated time: ~{estimated_minutes:.0f} minutes", Colors.CYAN)
                                                        print_colored(f"   Press Ctrl+C to interrupt and save progress", Colors.YELLOW)

                                                        if generate_ecorp_complete(month_code, ecorp_upload_path):
                                                            print_colored(f"✅ Ecorp processing complete for {month_code}", Colors.GREEN)

                                                            # Process BatchData if requested
                                                            if process_batchdata:
                                                                # Find most recent Ecorp_Complete file
                                                                ecorp_complete_pattern = f"{month_code}_Ecorp_Complete*.xlsx"
                                                                ecorp_complete_dir = Path("Ecorp/Complete")
                                                                ecorp_matches = list(ecorp_complete_dir.glob(ecorp_complete_pattern))

                                                                if ecorp_matches:
                                                                    ecorp_complete_path = max(ecorp_matches, key=lambda p: p.stat().st_mtime)

                                                                    print_colored(f"\n📞 Starting BatchData contact discovery for {month_code}...", Colors.CYAN)

                                                                    try:
                                                                        # Create BatchData Upload from Ecorp Complete
                                                                        batchdata_upload_path = create_batchdata_upload(
                                                                            ecorp_complete_path=str(ecorp_complete_path),
                                                                            month_code=month_code,
                                                                            timestamp=session_timestamp
                                                                        )

                                                                        if batchdata_upload_path:
                                                                            # Run BatchData enrichment (with cost estimate and confirmation)
                                                                            batchdata_complete_path = run_batchdata_enrichment(
                                                                                upload_path=str(batchdata_upload_path),
                                                                                month_code=month_code,
                                                                                timestamp=session_timestamp,
                                                                                dry_run=False,
                                                                                dedupe=True,
                                                                                consolidate_families=True,
                                                                                filter_entities=True
                                                                            )

                                                                            if batchdata_complete_path:
                                                                                print_colored(f"✅ BatchData enrichment complete for {month_code}", Colors.GREEN)
                                                                            else:
                                                                                batchdata_errors.append(f"{month_code} (enrichment failed or cancelled)")
                                                                        else:
                                                                            batchdata_errors.append(f"{month_code} (Upload creation failed)")
                                                                    except Exception as e:
                                                                        print_colored(f"❌ BatchData error for {month_code}: {e}", Colors.RED)
                                                                        batchdata_errors.append(f"{month_code} (error: {str(e)})")
                                                                else:
                                                                    batchdata_errors.append(f"{month_code} (Ecorp_Complete not found)")
                                                        else:
                                                            ecorp_errors.append(f"{month_code} (ACC lookup interrupted)")
                                                    else:
                                                        ecorp_errors.append(f"{month_code} (Upload creation failed)")
                                                except Exception as e:
                                                    print_colored(f"❌ Ecorp error for {month_code}: {e}", Colors.RED)
                                                    ecorp_errors.append(f"{month_code} (error: {str(e)})")
                                            else:
                                                ecorp_errors.append(f"{month_code} (MCAO_Complete not found)")
                                    else:
                                        mcao_errors.append(f"{month_code} (MCAO enrichment failed)")
                                else:
                                    mcao_errors.append(f"{month_code} (MCAO upload creation failed)")
                        else:
                            apn_errors.append(f"{month_code} (lookup failed)")
                elif analysis_df is None:
                    apn_errors.append(f"{month_code} (no Analysis data)")
            else:
                failed.append(month_code)
        except Exception as e:
            print_colored(f"❌ Error processing {month_code}: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
            failed.append(month_code)

    # Summary
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("📊 PROCESSING COMPLETE", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)

    if successful:
        print_colored(f"\n✅ Successfully processed ({len(successful)}/{len(months_to_process)}): {', '.join(successful)}", Colors.GREEN)

    if failed:
        print_colored(f"\n❌ Failed ({len(failed)}/{len(months_to_process)}): {', '.join(failed)}", Colors.RED)

    if apn_errors:
        print_colored(f"\n⚠️  APN processing issues: {', '.join(apn_errors)}", Colors.YELLOW)

    if mcao_errors:
        print_colored(f"\n⚠️  MCAO processing issues: {', '.join(mcao_errors)}", Colors.YELLOW)

    if ecorp_errors:
        print_colored(f"\n⚠️  Ecorp processing issues: {', '.join(ecorp_errors)}", Colors.YELLOW)

    if batchdata_errors:
        print_colored(f"\n⚠️  BatchData processing issues: {', '.join(batchdata_errors)}", Colors.YELLOW)

    print_colored("\n📁 Output directories:", Colors.BOLD)
    print_colored("  • Reformat/", Colors.WHITE)
    print_colored("  • All-to-Date/", Colors.WHITE)
    print_colored("  • Analysis/", Colors.WHITE)
    print_colored("  • APN/Upload/ (MARICOPA extracts)", Colors.WHITE)
    if process_apn:
        print_colored("  • APN/Complete/ (with APN lookups)", Colors.WHITE)
    if process_mcao:
        print_colored("  • MCAO/Upload/ (filtered APNs)", Colors.WHITE)
        print_colored("  • MCAO/Complete/ (enriched with MCAO data)", Colors.WHITE)
        print_colored("  • MCAO/Logs/ (error tracking)", Colors.WHITE)
    if process_ecorp:
        print_colored("  • Ecorp/Upload/ (filtered MCAO data)", Colors.WHITE)
        print_colored("  • Ecorp/Complete/ (with ACC entity details)", Colors.WHITE)
    if process_batchdata:
        print_colored("  • Batchdata/Upload/ (prepared for API)", Colors.WHITE)
        print_colored("  • Batchdata/Complete/ (enriched with contact data)", Colors.WHITE)

if __name__ == "__main__":
    main()