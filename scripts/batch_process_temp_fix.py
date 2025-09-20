#!/usr/bin/env python3
"""
Batch Processing Script with Temp Directory Fix for iCloud Sync Issues
======================================================================

This version writes files to /tmp first, then moves them to avoid iCloud sync timeouts.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

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
    """Print colored text to console."""
    print(f"{color}{text}{Colors.END}")

def print_header(text: str) -> None:
    """Print a formatted header."""
    print_colored(f"\n{'='*60}", Colors.BLUE)
    print_colored(f"{text:^60}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*60}", Colors.BLUE)

def print_success(text: str) -> None:
    """Print success message."""
    print_colored(f"✅ {text}", Colors.GREEN)

def print_error(text: str) -> None:
    """Print error message."""
    print_colored(f"❌ {text}", Colors.RED)

def print_warning(text: str) -> None:
    """Print warning message."""
    print_colored(f"⚠️  {text}", Colors.YELLOW)

def process_month_with_temp(month_code: str, folder_name: str) -> bool:
    """Process a month using temp directories to avoid iCloud sync issues."""

    print_colored(f"\n📊 Processing {month_code} using temp directory approach...", Colors.PURPLE)

    # Create temp directories
    temp_base = Path(tempfile.gettempdir()) / f"adhs_etl_{month_code.replace('.', '_')}"
    temp_base.mkdir(exist_ok=True)

    temp_raw = temp_base / "Raw-New-Month"
    temp_reformat = temp_base / "Reformat"
    temp_all_to_date = temp_base / "All-to-Date"
    temp_analysis = temp_base / "Analysis"

    for temp_dir in [temp_raw, temp_reformat, temp_all_to_date, temp_analysis]:
        temp_dir.mkdir(exist_ok=True)

    print_colored(f"Using temp directory: {temp_base}", Colors.BLUE)

    try:
        # Step 1: Copy input files to temp
        source_folder = Path("ALL-MONTHS") / folder_name
        excel_files = list(source_folder.glob("*.xlsx"))

        if not excel_files:
            print_error(f"No Excel files found in {source_folder}")
            return False

        for file in excel_files:
            shutil.copy2(file, temp_raw)

        print_success(f"Copied {len(excel_files)} files to temp")

        # Step 2: Run ETL with output to temp directories
        cmd = [
            "python3", "-m", "adhs_etl.cli_enhanced", "run",
            "--month", month_code,
            "--raw-dir", str(temp_raw)
        ]

        env = os.environ.copy()
        env['PYTHONPATH'] = 'src'
        # Override output directories via environment
        env['ADHS_ETL_TEMP_MODE'] = '1'
        env['ADHS_ETL_TEMP_BASE'] = str(temp_base)

        print_colored(f"Running ETL pipeline...", Colors.BLUE)

        # Create a modified CLI script that uses temp directories
        modified_cli = temp_base / "cli_temp.py"
        with open("src/adhs_etl/cli_enhanced.py", "r") as f:
            cli_content = f.read()

        # Inject temp directory logic
        cli_content = cli_content.replace(
            '    reformat_dir = Path("Reformat")',
            f'    reformat_dir = Path("{temp_reformat}")'
        )
        cli_content = cli_content.replace(
            '    all_to_date_dir = Path("All-to-Date")',
            f'    all_to_date_dir = Path("{temp_all_to_date}")'
        )
        cli_content = cli_content.replace(
            '    analysis_dir = Path("Analysis")',
            f'    analysis_dir = Path("{temp_analysis}")'
        )

        modified_cli.write_text(cli_content)

        # Run the modified CLI
        cmd = [
            "python3", str(modified_cli), "run",
            "--month", month_code,
            "--raw-dir", str(temp_raw)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            print_error(f"ETL failed: {result.stderr[:500]}")
            return False

        print_success("ETL pipeline completed in temp directory")

        # Step 3: Move files from temp to final locations
        print_colored("Moving files to final locations...", Colors.BLUE)

        # Ensure final directories exist
        Path("Reformat").mkdir(exist_ok=True)
        Path("All-to-Date").mkdir(exist_ok=True)
        Path("Analysis").mkdir(exist_ok=True)

        # Move Reformat files
        for file in temp_reformat.glob("*.xlsx"):
            dest = Path("Reformat") / file.name
            shutil.move(str(file), str(dest))
            print_success(f"Moved {file.name} to Reformat/")

        # Move All-to-Date files
        for file in temp_all_to_date.glob("*.xlsx"):
            dest = Path("All-to-Date") / file.name
            shutil.move(str(file), str(dest))
            print_success(f"Moved {file.name} to All-to-Date/")

        # Move Analysis files
        for file in temp_analysis.glob("*.xlsx"):
            dest = Path("Analysis") / file.name
            shutil.move(str(file), str(dest))
            print_success(f"Moved {file.name} to Analysis/")

        # Clean up temp directory
        shutil.rmtree(temp_base)
        print_success(f"Cleaned up temp directory")

        return True

    except subprocess.TimeoutExpired:
        print_error(f"ETL pipeline timed out after 10 minutes")
        shutil.rmtree(temp_base, ignore_errors=True)
        return False
    except Exception as e:
        print_error(f"Error processing {month_code}: {e}")
        shutil.rmtree(temp_base, ignore_errors=True)
        return False

def main():
    """Process specific months that are failing with regular batch processor."""
    print_header("ADHS ETL Batch Processing (Temp Directory Fix)")
    print_colored("This script processes months using /tmp to avoid iCloud sync timeouts", Colors.WHITE)

    # Process the three problematic months
    months_to_process = [
        ("Raw 9.24", "9.24"),
        ("Raw 10.24", "10.24"),
        ("Raw 11.24", "11.24")
    ]

    successful = []
    failed = []

    for folder_name, month_code in months_to_process:
        if process_month_with_temp(month_code, folder_name):
            successful.append(month_code)
        else:
            failed.append(month_code)

    # Summary
    print_header("PROCESSING COMPLETE")

    if successful:
        print_colored(f"✅ Successfully processed {len(successful)} months:", Colors.GREEN)
        for month in successful:
            print_colored(f"  • {month}", Colors.WHITE)

    if failed:
        print_colored(f"❌ Failed to process {len(failed)} months:", Colors.RED)
        for month in failed:
            print_colored(f"  • {month}", Colors.WHITE)

    print_colored(f"\n📁 Output files are available in:", Colors.BOLD)
    print_colored(f"  • Reformat/", Colors.WHITE)
    print_colored(f"  • All-to-Date/", Colors.WHITE)
    print_colored(f"  • Analysis/", Colors.WHITE)

if __name__ == "__main__":
    main()