#!/usr/bin/env python3
"""
Standalone MCAO Test Script
===========================

Tests MCAO enrichment using existing APN_Complete files
WITHOUT modifying production code or data.

This script safely tests the MCAO integration by:
1. Reading existing APN_Complete files
2. Processing them through MCAO enrichment
3. Outputting results to test or production directories
4. Providing various test modes for validation
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import production functions (no duplication)
try:
    # Import from process_months_local.py
    from scripts.process_months_local import (
        extract_mcao_upload,
        process_mcao_complete,
        safe_write_excel,
        Colors,
        print_colored
    )
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Error importing from process_months_local.py: {e}")
    print("Defining minimal versions for testing...")
    IMPORTS_SUCCESSFUL = False

    # Minimal fallback definitions if imports fail
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

    def print_colored(text: str, color: str = '\033[97m') -> None:
        print(f"{color}{text}\033[0m")

def find_apn_complete_files() -> List[Tuple[str, Path, int]]:
    """
    Find all APN_Complete files and group by month, keeping only most recent.

    Returns:
        List of tuples: (month_code, file_path, record_count)
    """
    complete_dir = Path("APN/Complete")
    if not complete_dir.exists():
        return []

    # Find all APN_Complete files
    files_by_month = {}

    for file_path in complete_dir.glob("*_APN_Complete*.xlsx"):
        # Skip temp files
        if file_path.name.startswith("~$"):
            continue

        # Extract month code from filename
        # Format: M.YY_APN_Complete timestamp.xlsx
        try:
            month_code = file_path.name.split("_APN_Complete")[0]

            # Validate month code format
            parts = month_code.split('.')
            if len(parts) == 2:
                month_num = int(parts[0])
                year_num = int(parts[1])
                if 1 <= month_num <= 12 and 0 <= year_num <= 99:
                    # Keep the most recent file for this month
                    if month_code not in files_by_month or \
                       file_path.stat().st_mtime > files_by_month[month_code].stat().st_mtime:
                        files_by_month[month_code] = file_path
        except (ValueError, IndexError):
            continue

    # Get record counts and prepare result
    result = []
    for month_code, file_path in files_by_month.items():
        try:
            df = pd.read_excel(file_path, nrows=0)  # Just read headers
            total_rows = len(pd.read_excel(file_path))
            result.append((month_code, file_path, total_rows))
        except Exception as e:
            print_colored(f"Warning: Could not read {file_path.name}: {e}", Colors.YELLOW)

    # Sort by year then month
    result.sort(key=lambda x: (int(x[0].split('.')[1]), int(x[0].split('.')[0])))

    return result

def display_test_menu(available_files: List[Tuple[str, Path, int]]) -> Tuple[List[int], str]:
    """
    Display interactive menu for test configuration.

    Returns:
        Tuple of (selected_indices, test_mode)
    """
    print_colored("\n" + "="*60, Colors.BOLD + Colors.CYAN)
    print_colored("MCAO Integration Test", Colors.BOLD + Colors.CYAN)
    print_colored("="*60, Colors.BOLD + Colors.CYAN)

    if not available_files:
        print_colored("No APN_Complete files found!", Colors.RED)
        return [], ""

    print_colored("\nFound APN_Complete files:", Colors.BOLD)
    for i, (month_code, file_path, count) in enumerate(available_files, 1):
        month_parts = month_code.split('.')
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_name = month_names[int(month_parts[0])] if int(month_parts[0]) <= 12 else month_parts[0]
        year = 2000 + int(month_parts[1])

        print(f"{i:2d}. {month_code:6s} - {file_path.name:50s} ({count:,} records)")

    # Get selection
    print_colored("\n" + "-"*60, Colors.CYAN)
    print_colored("Select month(s) to test:", Colors.BOLD)
    print("   • Enter numbers: 1,3,5 or 1-3 or 'all'")
    print("   • Press Enter to cancel")

    selection = input("\nYour selection: ").strip()

    if not selection:
        return [], ""

    selected_indices = []

    if selection.lower() == 'all':
        selected_indices = list(range(len(available_files)))
    else:
        # Parse selection
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                # Range
                try:
                    start, end = part.split('-')
                    start_idx = int(start) - 1
                    end_idx = int(end) - 1
                    selected_indices.extend(range(start_idx, end_idx + 1))
                except ValueError:
                    print_colored(f"Invalid range: {part}", Colors.RED)
            else:
                # Single number
                try:
                    idx = int(part) - 1
                    selected_indices.append(idx)
                except ValueError:
                    print_colored(f"Invalid number: {part}", Colors.RED)

    # Validate indices
    selected_indices = [i for i in selected_indices if 0 <= i < len(available_files)]

    if not selected_indices:
        print_colored("No valid selection made", Colors.RED)
        return [], ""

    # Get test mode
    print_colored("\n" + "-"*60, Colors.CYAN)
    print_colored("Select test mode:", Colors.BOLD)
    print("  (f) Full processing - Same as production")
    print("  (s) Sample mode - First 5 records only")
    print("  (t) Test directory - Output to MCAO/Test/")
    print("  (d) Dry run - Show what would happen (no API calls)")
    print("  (q) Quit")

    mode = input("\nTest mode [f/s/t/d/q]: ").strip().lower()

    if mode == 'q':
        return [], ""

    if mode not in ['f', 's', 't', 'd']:
        mode = 'f'  # Default to full

    return selected_indices, mode

def run_test_pipeline(month_code: str, file_path: Path, test_mode: str) -> bool:
    """
    Run MCAO pipeline for a single APN_Complete file.

    Args:
        month_code: Month code (e.g., "1.25")
        file_path: Path to APN_Complete file
        test_mode: 'f'=full, 's'=sample, 't'=test dir, 'd'=dry run

    Returns:
        True if successful, False otherwise
    """
    print_colored(f"\n{'='*60}", Colors.BLUE)
    print_colored(f"Processing {month_code} - {file_path.name}", Colors.BOLD + Colors.PURPLE)
    mode_names = {'f': 'Full', 's': 'Sample (5 records)', 't': 'Test Directory', 'd': 'Dry Run'}
    print_colored(f"Mode: {mode_names.get(test_mode, 'Unknown')}", Colors.CYAN)
    print_colored(f"{'='*60}", Colors.BLUE)

    try:
        # For dry run, just show what would happen
        if test_mode == 'd':
            df = pd.read_excel(file_path)
            print_colored(f"Would process {len(df)} records from {file_path.name}", Colors.YELLOW)

            # Count valid APNs
            if len(df.columns) >= 3:
                df.columns = ['FULL_ADDRESS', 'COUNTY', 'APN'] + list(df.columns[3:])
                valid_apns = df[df['APN'].notna() & (df['APN'] != '')].shape[0]
                print_colored(f"Would filter to {valid_apns} valid APNs", Colors.YELLOW)
                print_colored(f"Would make ~{valid_apns * 6} API calls (6 per APN)", Colors.YELLOW)
                print_colored(f"Estimated time: ~{(valid_apns * 6 / 5) / 60:.1f} minutes at 5 req/sec", Colors.YELLOW)

            return True

        # For sample mode, create a temporary reduced file
        if test_mode == 's':
            print_colored("Creating sample subset (first 5 records)...", Colors.CYAN)
            df = pd.read_excel(file_path)
            df_sample = df.head(5)

            # Create temp file
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"sample_{file_path.name}"
            df_sample.to_excel(temp_path, index=False)
            file_path = temp_path
            print_colored(f"Using sample file with {len(df_sample)} records", Colors.CYAN)

        # For test directory mode, temporarily modify paths
        if test_mode == 't':
            print_colored("Using test directories (MCAO/Test/)...", Colors.CYAN)
            # Create test directories
            Path("MCAO/Test/Upload").mkdir(parents=True, exist_ok=True)
            Path("MCAO/Test/Complete").mkdir(parents=True, exist_ok=True)
            Path("MCAO/Test/Logs").mkdir(parents=True, exist_ok=True)

            # We'll need to handle this differently since we're using imported functions
            # For now, we'll process normally and move files afterward

        # Check if we can use imported functions
        if not IMPORTS_SUCCESSFUL:
            print_colored("Cannot proceed without successful imports from process_months_local.py", Colors.RED)
            return False

        # Step 1: Extract MCAO Upload
        print_colored("\nStep 1: Creating MCAO Upload file...", Colors.BLUE)
        mcao_upload_path = extract_mcao_upload(month_code, file_path)

        if not mcao_upload_path:
            print_colored("Failed to create MCAO Upload file", Colors.RED)
            return False

        # Step 2: Process MCAO Complete
        print_colored("\nStep 2: Processing MCAO API enrichment...", Colors.BLUE)
        success = process_mcao_complete(month_code, mcao_upload_path)

        if not success:
            print_colored("Failed to create MCAO Complete file", Colors.RED)
            return False

        # For test directory mode, move files to test location
        if test_mode == 't':
            print_colored("\nMoving files to test directories...", Colors.CYAN)
            import shutil

            # Move Upload file
            if mcao_upload_path.exists():
                test_upload = Path("MCAO/Test/Upload") / mcao_upload_path.name
                shutil.move(str(mcao_upload_path), str(test_upload))
                print_colored(f"Moved to: {test_upload}", Colors.GREEN)

            # Move Complete file (find it based on naming pattern)
            complete_dir = Path("MCAO/Complete")
            if complete_dir.exists():
                pattern = f"{month_code}_MCAO_Complete*.xlsx"
                matches = list(complete_dir.glob(pattern))
                if matches:
                    latest = max(matches, key=lambda p: p.stat().st_mtime)
                    test_complete = Path("MCAO/Test/Complete") / latest.name
                    shutil.move(str(latest), str(test_complete))
                    print_colored(f"Moved to: {test_complete}", Colors.GREEN)

            # Copy logs
            logs_dir = Path("MCAO/Logs")
            if logs_dir.exists():
                pattern = f"{month_code}_MCAO_errors*.xlsx"
                for log_file in logs_dir.glob(pattern):
                    test_log = Path("MCAO/Test/Logs") / log_file.name
                    shutil.copy2(str(log_file), str(test_log))
                    print_colored(f"Copied log to: {test_log}", Colors.YELLOW)

        # Clean up temp file if created
        if test_mode == 's' and 'temp_path' in locals():
            temp_path.unlink()

        print_colored(f"\n✅ Successfully processed {month_code}", Colors.GREEN)
        return True

    except Exception as e:
        print_colored(f"❌ Error processing {month_code}: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return False

def verify_environment() -> bool:
    """Verify environment is properly configured for testing."""
    print_colored("\nVerifying environment...", Colors.CYAN)

    # Check .env file
    env_path = Path(".env")
    if not env_path.exists():
        print_colored("❌ .env file not found", Colors.RED)
        print_colored("   Run setup_env.py to create it", Colors.YELLOW)
        return False

    # Check MCAO_API_KEY
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("MCAO_API_KEY")
    if not api_key:
        print_colored("❌ MCAO_API_KEY not set in .env", Colors.RED)
        return False

    print_colored(f"✅ MCAO_API_KEY configured: {api_key[:8]}...", Colors.GREEN)

    # Check imports
    if not IMPORTS_SUCCESSFUL:
        print_colored("⚠️  Could not import from process_months_local.py", Colors.YELLOW)
        print_colored("   Some functionality may be limited", Colors.YELLOW)
    else:
        print_colored("✅ Successfully imported production functions", Colors.GREEN)

    # Check APN/Complete directory
    if not Path("APN/Complete").exists():
        print_colored("⚠️  APN/Complete directory not found", Colors.YELLOW)
        print_colored("   No files to test", Colors.YELLOW)
        return False

    return True

def main():
    """Main test execution function."""
    print_colored("\n🧪 MCAO Standalone Test Script", Colors.BOLD + Colors.PURPLE)
    print_colored("="*60, Colors.PURPLE)

    # Verify environment
    if not verify_environment():
        print_colored("\n❌ Environment verification failed", Colors.RED)
        print_colored("   Please fix the issues above and try again", Colors.YELLOW)
        return

    # Find available files
    available_files = find_apn_complete_files()

    if not available_files:
        print_colored("\n❌ No APN_Complete files found in APN/Complete/", Colors.RED)
        return

    # Display menu and get selection
    selected_indices, test_mode = display_test_menu(available_files)

    if not selected_indices:
        print_colored("\n🚫 Test cancelled", Colors.YELLOW)
        return

    # Confirm selection
    print_colored("\n" + "="*60, Colors.CYAN)
    print_colored("Test Configuration:", Colors.BOLD)
    mode_descriptions = {'f': 'Full Processing', 's': 'Sample (5 records)', 't': 'Test Directory', 'd': 'Dry Run'}
    print_colored(f"Mode: {mode_descriptions.get(test_mode)}", Colors.CYAN)
    print_colored(f"Files to process: {len(selected_indices)}", Colors.CYAN)

    for idx in selected_indices:
        month_code, file_path, count = available_files[idx]
        print(f"  • {month_code}: {file_path.name} ({count:,} records)")

    # Final confirmation
    if test_mode != 'd':  # Don't need confirmation for dry run
        response = input(f"\n{Colors.BOLD}Proceed with test? (y/N): {Colors.END}").strip().lower()
        if response not in ['y', 'yes']:
            print_colored("\n🚫 Test cancelled", Colors.YELLOW)
            return

    # Process selected files
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("Starting MCAO Test Processing", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)

    successful = []
    failed = []

    start_time = time.time()

    for idx in selected_indices:
        month_code, file_path, _ = available_files[idx]

        if run_test_pipeline(month_code, file_path, test_mode):
            successful.append(month_code)
        else:
            failed.append(month_code)

    # Summary
    elapsed = time.time() - start_time

    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("Test Complete", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)

    if successful:
        print_colored(f"\n✅ Successful: {', '.join(successful)}", Colors.GREEN)

    if failed:
        print_colored(f"\n❌ Failed: {', '.join(failed)}", Colors.RED)

    print_colored(f"\nTotal time: {elapsed/60:.1f} minutes", Colors.CYAN)

    # Output locations
    if test_mode != 'd':
        print_colored("\n📁 Output locations:", Colors.BOLD)
        if test_mode == 't':
            print_colored("  • MCAO/Test/Upload/", Colors.WHITE)
            print_colored("  • MCAO/Test/Complete/", Colors.WHITE)
            print_colored("  • MCAO/Test/Logs/", Colors.WHITE)
        else:
            print_colored("  • MCAO/Upload/", Colors.WHITE)
            print_colored("  • MCAO/Complete/", Colors.WHITE)
            print_colored("  • MCAO/Logs/", Colors.WHITE)

if __name__ == "__main__":
    main()