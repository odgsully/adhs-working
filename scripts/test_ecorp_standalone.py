#!/usr/bin/env python3
"""
Standalone Ecorp Processing Script
===================================

Process MCAO_Complete files through the Ecorp pipeline with interactive menu.

Features:
- Interactive menu for file selection
- Multiple processing modes (full, sample, test directory, dry run)
- Progress tracking and checkpointing
- Graceful interrupt handling

Usage:
    python scripts/test_ecorp_standalone.py
    python scripts/test_ecorp_standalone.py --month 1.25
    python scripts/test_ecorp_standalone.py --mcao-file MCAO/Complete/1.25_MCAO_Complete.xlsx
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adhs_etl.ecorp import generate_ecorp_upload, generate_ecorp_complete

# Color codes for terminal output
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
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.END}")


def find_mcao_complete_files() -> List[Tuple[str, Path, int, int]]:
    """
    Find all MCAO_Complete files and get metadata.

    Returns:
        List of tuples: (month_code, file_path, total_records, non_blank_owners)
    """
    complete_dir = Path("MCAO/Complete")
    if not complete_dir.exists():
        return []

    # Find all MCAO_Complete files
    files_by_month = {}

    for file_path in complete_dir.glob("*_MCAO_Complete*.xlsx"):
        # Skip temp files
        if file_path.name.startswith("~$"):
            continue

        # Extract month code from filename
        try:
            month_code = file_path.name.split("_MCAO_Complete")[0]

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

    # Get record counts and owner counts
    result = []
    for month_code, file_path in files_by_month.items():
        try:
            df = pd.read_excel(file_path)
            total_rows = len(df)

            # Count non-blank owners (column E, 0-indexed = 4)
            non_blank = 0
            if len(df.columns) > 4:
                non_blank = df.iloc[:, 4].notna().sum()

            result.append((month_code, file_path, total_rows, non_blank))
        except Exception as e:
            print_colored(f"Warning: Could not read {file_path.name}: {e}", Colors.YELLOW)

    # Sort by year then month
    result.sort(key=lambda x: (int(x[0].split('.')[1]), int(x[0].split('.')[0])))

    return result


def display_menu(available_files: List[Tuple[str, Path, int, int]]) -> Tuple[List[int], str, bool]:
    """
    Display interactive menu for file selection and options.

    Returns:
        Tuple of (selected_indices, processing_mode, headless)
    """
    print_colored("\n" + "="*60, Colors.BOLD + Colors.CYAN)
    print_colored("ECORP Processing Menu", Colors.BOLD + Colors.CYAN)
    print_colored("="*60, Colors.BOLD + Colors.CYAN)

    if not available_files:
        print_colored("No MCAO_Complete files found!", Colors.RED)
        return [], "", True

    print_colored("\nFound MCAO_Complete files:", Colors.BOLD)
    for i, (month_code, file_path, total, owners) in enumerate(available_files, 1):
        month_parts = month_code.split('.')
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_name = month_names[int(month_parts[0])] if int(month_parts[0]) <= 12 else month_parts[0]
        year = 2000 + int(month_parts[1])

        print(f"{i:2d}. {month_code:6s} ({month_name} {year}) - "
              f"{total:5,} records, {owners:5,} with owners - "
              f"{file_path.name[:40]}")

    # Get selection
    print_colored("\n" + "-"*60, Colors.CYAN)
    print_colored("Select month(s) to process:", Colors.BOLD)
    print("   • Enter numbers: 1,3,5 or 1-3 or 'all'")
    print("   • Press Enter to cancel")

    selection = input("\nYour selection: ").strip()

    if not selection:
        return [], "", True

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
        return [], "", True

    # Get processing mode
    print_colored("\n" + "-"*60, Colors.CYAN)
    print_colored("Select processing mode:", Colors.BOLD)
    print("  (f) Full processing - Upload + ACC lookup")
    print("  (u) Upload only - Generate Upload file, skip ACC lookup")
    print("  (s) Sample mode - First 5 records only")
    print("  (t) Test directory - Output to Ecorp/Test/")
    print("  (d) Dry run - Show what would happen")
    print("  (q) Quit")

    mode = input("\nProcessing mode [f/u/s/t/d/q]: ").strip().lower()

    if mode == 'q':
        return [], "", True

    if mode not in ['f', 'u', 's', 't', 'd']:
        mode = 'f'  # Default to full

    # Get browser mode (unless upload-only or dry-run)
    headless = True
    if mode not in ['u', 'd']:
        print_colored("\n" + "-"*60, Colors.CYAN)
        print_colored("Browser mode:", Colors.BOLD)
        print("  (h) Headless - Run in background (faster)")
        print("  (v) Visible - Show browser window (for debugging)")

        browser = input("\nBrowser mode [h/v]: ").strip().lower()
        headless = (browser != 'v')

    return selected_indices, mode, headless


def process_single_file(month_code: str, mcao_path: Path, mode: str, headless: bool) -> bool:
    """
    Process a single MCAO_Complete file through Ecorp pipeline.

    Args:
        month_code: Month code (e.g., "1.25")
        mcao_path: Path to MCAO_Complete file
        mode: Processing mode ('f', 'u', 's', 't', 'd')
        headless: Run browser in headless mode

    Returns:
        True if successful, False otherwise
    """
    print_colored(f"\n{'='*60}", Colors.BLUE)
    print_colored(f"Processing {month_code} - {mcao_path.name}", Colors.BOLD + Colors.PURPLE)
    mode_names = {
        'f': 'Full (Upload + ACC)',
        'u': 'Upload Only',
        's': 'Sample (5 records)',
        't': 'Test Directory',
        'd': 'Dry Run'
    }
    print_colored(f"Mode: {mode_names.get(mode, 'Unknown')}", Colors.CYAN)
    if mode not in ['u', 'd']:
        print_colored(f"Browser: {'Headless' if headless else 'Visible'}", Colors.CYAN)
    print_colored(f"{'='*60}", Colors.BLUE)

    try:
        # For dry run, just show what would happen
        if mode == 'd':
            df = pd.read_excel(mcao_path)
            print_colored(f"Would process {len(df)} records from {mcao_path.name}", Colors.YELLOW)

            # Count owners
            if len(df.columns) > 4:
                non_blank = df.iloc[:, 4].notna().sum()
                print_colored(f"Would extract {non_blank} non-blank owners", Colors.YELLOW)
                print_colored(f"Estimated ACC lookup time: {non_blank * 4 / 60:.1f} minutes @ ~4 sec/record", Colors.YELLOW)

            print_colored(f"Would create: Ecorp/Upload/{month_code}_Ecorp_Upload *.xlsx", Colors.YELLOW)
            if mode != 'u':
                print_colored(f"Would create: Ecorp/Complete/{month_code}_Ecorp_Complete *.xlsx", Colors.YELLOW)
            return True

        # For sample mode, create temporary reduced file
        if mode == 's':
            print_colored("Creating sample subset (first 5 records)...", Colors.CYAN)
            df = pd.read_excel(mcao_path)
            df_sample = df.head(5)

            # Create temp file
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"sample_{mcao_path.name}"
            df_sample.to_excel(temp_path, index=False)
            mcao_path = temp_path
            print_colored(f"Using sample file with {len(df_sample)} records", Colors.CYAN)

        # For test directory mode, create test dirs
        if mode == 't':
            print_colored("Using test directories (Ecorp/Test/)...", Colors.CYAN)
            Path("Ecorp/Test/Upload").mkdir(parents=True, exist_ok=True)
            Path("Ecorp/Test/Complete").mkdir(parents=True, exist_ok=True)

        # Step 1: Generate Ecorp Upload
        print_colored("\n📋 Step 1: Generating Ecorp Upload file...", Colors.BLUE)

        upload_path = generate_ecorp_upload(month_code, mcao_path)

        if not upload_path:
            print_colored("❌ Failed to generate Ecorp Upload file", Colors.RED)
            return False

        print_colored(f"✅ Created: {upload_path}", Colors.GREEN)

        # For test mode, move to test directory
        if mode == 't':
            import shutil
            test_upload = Path("Ecorp/Test/Upload") / upload_path.name
            shutil.move(str(upload_path), str(test_upload))
            upload_path = test_upload
            print_colored(f"   Moved to: {test_upload}", Colors.CYAN)

        # If upload-only mode, stop here
        if mode == 'u':
            print_colored("\n✨ Upload-only mode - skipping ACC lookup", Colors.YELLOW)
            return True

        # Step 2: Run ACC Entity Lookup
        print_colored("\n🔍 Step 2: Running ACC entity lookup...", Colors.BLUE)

        # Get record count for time estimate
        df = pd.read_excel(upload_path)
        num_records = len(df)
        non_blank = df['Owner_Ownership'].notna().sum()

        print_colored(f"📊 Processing {num_records} total records ({non_blank} non-blank)", Colors.CYAN)
        print_colored(f"⏱️  Estimated time: {non_blank * 4 / 60:.1f} minutes @ ~4 sec/record", Colors.CYAN)
        print_colored(f"💡 Tip: Press Ctrl+C to interrupt and save progress", Colors.YELLOW)

        success = generate_ecorp_complete(month_code, upload_path, headless=headless)

        if success:
            # For test mode, move Complete file
            if mode == 't':
                complete_dir = Path("Ecorp/Complete")
                pattern = f"{month_code}_Ecorp_Complete*.xlsx"
                matches = list(complete_dir.glob(pattern))
                if matches:
                    latest = max(matches, key=lambda p: p.stat().st_mtime)
                    test_complete = Path("Ecorp/Test/Complete") / latest.name
                    shutil.move(str(latest), str(test_complete))
                    print_colored(f"   Moved to: {test_complete}", Colors.CYAN)

            print_colored(f"\n✅ Successfully processed {month_code}", Colors.GREEN)
        else:
            print_colored(f"\n⚠️  Processing interrupted or incomplete for {month_code}", Colors.YELLOW)
            return False

        # Clean up temp file if created
        if mode == 's' and 'temp_path' in locals():
            temp_path.unlink()

        return True

    except Exception as e:
        print_colored(f"❌ Error processing {month_code}: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Process MCAO_Complete files through Ecorp pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interactive Mode (default):
  python scripts/test_ecorp_standalone.py

Command Line Mode:
  python scripts/test_ecorp_standalone.py --month 1.25
  python scripts/test_ecorp_standalone.py --mcao-file MCAO/Complete/file.xlsx
  python scripts/test_ecorp_standalone.py --month 1.25 --upload-only
  python scripts/test_ecorp_standalone.py --month 1.25 --no-headless
        """
    )

    # Optional arguments for command-line mode
    parser.add_argument("--month", help="Process specific month (bypasses menu)")
    parser.add_argument("--mcao-file", type=Path, help="Process specific file (bypasses menu)")
    parser.add_argument("--upload-only", action="store_true", help="Only generate Upload file")
    parser.add_argument("--no-headless", action="store_true", help="Run browser in visible mode")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")

    args = parser.parse_args()

    print_colored("\n🏢 ECORP Processing Script", Colors.BOLD + Colors.PURPLE)
    print_colored("="*60, Colors.PURPLE)

    # Command-line mode (backwards compatible)
    if args.month or args.mcao_file:
        try:
            # Determine file and month
            if args.mcao_file:
                mcao_path = args.mcao_file
                if not mcao_path.exists():
                    print_colored(f"❌ File not found: {mcao_path}", Colors.RED)
                    return 1

                # Extract month from filename
                stem = mcao_path.stem
                if "_MCAO_Complete" in stem:
                    month_code = stem.split("_MCAO_Complete")[0]
                else:
                    month_code = datetime.now().strftime("%-m.%y")
                    print_colored(f"⚠️  Could not extract month, using {month_code}", Colors.YELLOW)
            else:
                month_code = args.month
                # Find MCAO_Complete file
                complete_dir = Path("MCAO/Complete")
                pattern = f"{month_code}_MCAO_Complete*.xlsx"
                matches = list(complete_dir.glob(pattern))

                if not matches:
                    print_colored(f"❌ No MCAO_Complete file found for {month_code}", Colors.RED)
                    return 1

                mcao_path = max(matches, key=lambda p: p.stat().st_mtime)

            # Determine mode
            if args.dry_run:
                mode = 'd'
            elif args.upload_only:
                mode = 'u'
            else:
                mode = 'f'

            # Process
            success = process_single_file(
                month_code,
                mcao_path,
                mode,
                headless=not args.no_headless
            )

            return 0 if success else 1

        except Exception as e:
            print_colored(f"❌ Error: {e}", Colors.RED)
            return 1

    # Interactive menu mode (default)
    else:
        # Find available files
        available_files = find_mcao_complete_files()

        if not available_files:
            print_colored("\n❌ No MCAO_Complete files found in MCAO/Complete/", Colors.RED)
            print_colored("   Run MCAO processing first to generate these files", Colors.YELLOW)
            return 1

        # Display menu and get selection
        selected_indices, mode, headless = display_menu(available_files)

        if not selected_indices:
            print_colored("\n🚫 Processing cancelled", Colors.YELLOW)
            return 0

        # Confirm selection
        print_colored("\n" + "="*60, Colors.CYAN)
        print_colored("Processing Configuration:", Colors.BOLD)
        mode_descriptions = {
            'f': 'Full Processing (Upload + ACC)',
            'u': 'Upload Only',
            's': 'Sample (5 records)',
            't': 'Test Directory',
            'd': 'Dry Run'
        }
        print_colored(f"Mode: {mode_descriptions.get(mode)}", Colors.CYAN)
        if mode not in ['u', 'd']:
            print_colored(f"Browser: {'Headless' if headless else 'Visible'}", Colors.CYAN)
        print_colored(f"Files to process: {len(selected_indices)}", Colors.CYAN)

        for idx in selected_indices:
            month_code, file_path, total, owners = available_files[idx]
            print(f"  • {month_code}: {owners:,} owners from {total:,} records")

        # Final confirmation (except for dry run)
        if mode != 'd':
            response = input(f"\n{Colors.BOLD}Proceed with processing? (y/N): {Colors.END}").strip().lower()
            if response not in ['y', 'yes']:
                print_colored("\n🚫 Processing cancelled", Colors.YELLOW)
                return 0

        # Process selected files
        print_colored("\n" + "="*60, Colors.BLUE)
        print_colored("Starting Ecorp Processing", Colors.BOLD + Colors.BLUE)
        print_colored("="*60, Colors.BLUE)

        successful = []
        failed = []
        start_time = time.time()

        for idx in selected_indices:
            month_code, file_path, _, _ = available_files[idx]

            if process_single_file(month_code, file_path, mode, headless):
                successful.append(month_code)
            else:
                failed.append(month_code)

        # Summary
        elapsed = time.time() - start_time

        print_colored("\n" + "="*60, Colors.BLUE)
        print_colored("Processing Complete", Colors.BOLD + Colors.BLUE)
        print_colored("="*60, Colors.BLUE)

        if successful:
            print_colored(f"\n✅ Successful: {', '.join(successful)}", Colors.GREEN)

        if failed:
            print_colored(f"\n❌ Failed: {', '.join(failed)}", Colors.RED)

        print_colored(f"\nTotal time: {elapsed/60:.1f} minutes", Colors.CYAN)

        # Output locations
        if mode != 'd':
            print_colored("\n📁 Output locations:", Colors.BOLD)
            if mode == 't':
                print_colored("  • Ecorp/Test/Upload/", Colors.WHITE)
                if mode != 'u':
                    print_colored("  • Ecorp/Test/Complete/", Colors.WHITE)
            else:
                print_colored("  • Ecorp/Upload/", Colors.WHITE)
                if mode != 'u':
                    print_colored("  • Ecorp/Complete/", Colors.WHITE)

        return 0


if __name__ == "__main__":
    sys.exit(main())