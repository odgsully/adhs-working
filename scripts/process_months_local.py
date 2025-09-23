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
import tempfile
import subprocess
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

    while True:
        response = input(f"\n{Colors.BOLD}Ready to proceed? (y/N): {Colors.END}").strip().lower()
        if response in ['y', 'yes']:
            return True, process_apn
        elif response in ['n', 'no', '']:
            return False, False
        else:
            print_colored("Please enter 'y' for yes or 'n' for no", Colors.YELLOW)

def process_single_month(month_code: str, folder_name: str):
    """Process a single month directly. (UNCHANGED FROM ORIGINAL)"""
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
        return False, None

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
        return False, None

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
        return False, None

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
        return False, None  # Block processing completely
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
        return False, None

    print_colored(f"✅ Successfully processed {month_code}", Colors.GREEN)

    # Return analysis_df so we can extract APN data from it
    return True, analysis_df

def extract_apn_upload(month_code: str, analysis_df: pd.DataFrame):
    """Extract MARICOPA-only records from Analysis file for APN processing.

    Args:
        month_code: Month code (e.g., "1.25")
        analysis_df: The Analysis dataframe with all columns

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

        # Generate timestamp
        now = datetime.now()
        timestamp = now.strftime("%m.%d.%I-%M-%S")  # M.DD.HH-MM-SS (12-hour format)

        # Create output filename
        output_filename = f"{month_code}_APN_Upload {timestamp}.xlsx"
        output_path = upload_dir / output_filename

        # Write to Excel
        if safe_write_excel(maricopa_df, output_path):
            print_colored(f"✅ Created APN Upload file: {output_path}", Colors.GREEN)
            return output_path
        else:
            return None

    except Exception as e:
        print_colored(f"❌ Error extracting APN data: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return None

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
    print_colored("\n" + "="*60, Colors.BOLD + Colors.CYAN)
    print_colored("🚀 ADHS ETL Interactive Month Processor", Colors.BOLD + Colors.CYAN)
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

    # Get confirmation
    confirmed, process_apn = get_confirmation(start_month, end_month, months_to_process)
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

    for month_code, folder_name, _, _ in months_to_process:
        try:
            result = process_single_month(month_code, folder_name)
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
                    upload_path = extract_apn_upload(month_code, analysis_df)

                    # Run APN lookup if requested
                    if upload_path and process_apn:
                        if not run_apn_lookup(upload_path):
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

    print_colored("\n📁 Output directories:", Colors.BOLD)
    print_colored("  • Reformat/", Colors.WHITE)
    print_colored("  • All-to-Date/", Colors.WHITE)
    print_colored("  • Analysis/", Colors.WHITE)
    print_colored("  • APN/Upload/ (MARICOPA extracts)", Colors.WHITE)
    if process_apn:
        print_colored("  • APN/Complete/ (with APN lookups)", Colors.WHITE)

if __name__ == "__main__":
    main()