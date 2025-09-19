#!/usr/bin/env python3
"""
Batch Processing Script for ADHS ETL Pipeline
=============================================

This script automates the process of running the ADHS ETL pipeline for multiple months
in chronological order. It handles copying files, running the pipeline, and cleanup.

Usage:
    python scripts/batch_process_months.py

The script will present a menu to select start and end months, then process all months
in between automatically.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

# Color codes for better output formatting
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

def print_step(step: int, text: str) -> None:
    """Print a formatted step."""
    print_colored(f"\n📋 Step {step}: {text}", Colors.CYAN)

def print_success(text: str) -> None:
    """Print success message."""
    print_colored(f"✅ {text}", Colors.GREEN)

def print_error(text: str) -> None:
    """Print error message."""
    print_colored(f"❌ {text}", Colors.RED)

def print_warning(text: str) -> None:
    """Print warning message."""
    print_colored(f"⚠️  {text}", Colors.YELLOW)

def get_available_months() -> List[Tuple[str, str]]:
    """
    Scan ALL-MONTHS directory for available month folders.
    Returns list of (folder_name, month_code) tuples sorted chronologically.
    """
    all_months_dir = Path("ALL-MONTHS")
    
    if not all_months_dir.exists():
        print_error("ALL-MONTHS directory not found!")
        return []
    
    months = []
    
    # Look for Raw M.YY folders
    for folder in all_months_dir.iterdir():
        if folder.is_dir() and folder.name.startswith("Raw "):
            try:
                # Extract month code from folder name (e.g., "Raw 1.25" -> "1.25")
                month_code = folder.name.replace("Raw ", "")
                
                # Validate format
                parts = month_code.split('.')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    month_num = int(parts[0])
                    year_num = int(parts[1])
                    
                    if 1 <= month_num <= 12 and 20 <= year_num <= 99:
                        months.append((folder.name, month_code))
            except:
                continue
    
    # Sort chronologically
    def sort_key(item):
        month_code = item[1]
        parts = month_code.split('.')
        month_num = int(parts[0])
        year_num = int(parts[1])
        return (year_num, month_num)
    
    months.sort(key=sort_key)
    return months

def display_available_months(months: List[Tuple[str, str]]) -> None:
    """Display available months in a formatted table."""
    print_colored("\n📅 Available Months:", Colors.BOLD)
    print_colored("-" * 40, Colors.BLUE)
    
    for i, (folder_name, month_code) in enumerate(months):
        parts = month_code.split('.')
        month_num = int(parts[0])
        year_num = 2000 + int(parts[1])
        
        month_names = ["", "January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        
        month_name = month_names[month_num]
        print_colored(f"{i+1:2d}. {month_code:>6} - {month_name} {year_num} ({folder_name})", Colors.WHITE)

def get_user_selection(prompt: str, max_value: int) -> int:
    """Get user selection with validation."""
    while True:
        try:
            choice = input(f"\n{prompt} (1-{max_value}): ").strip()
            if choice.lower() in ['q', 'quit', 'exit']:
                print_colored("Goodbye! 👋", Colors.YELLOW)
                sys.exit(0)
            
            choice_num = int(choice)
            if 1 <= choice_num <= max_value:
                return choice_num - 1  # Convert to 0-based index
            else:
                print_error(f"Please enter a number between 1 and {max_value}")
        except ValueError:
            print_error("Please enter a valid number")

def validate_month_range(start_idx: int, end_idx: int) -> bool:
    """Validate that start month comes before end month chronologically."""
    return start_idx <= end_idx

def copy_month_files(source_folder: Path, dest_folder: Path) -> bool:
    """Copy Excel files from source to destination folder."""
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
            print_warning(f"No Excel files found in {source_folder}")
            return False
        
        for file in excel_files:
            shutil.copy2(file, dest_folder)
        
        print_success(f"Copied {len(excel_files)} Excel files")
        return True
        
    except Exception as e:
        print_error(f"Error copying files: {e}")
        return False

def run_etl_pipeline(month_code: str, dry_run: bool = False) -> bool:
    """Run the ETL pipeline for a specific month."""
    try:
        # Use direct Python execution instead of Poetry
        cmd = [
            "python3", "-m", "adhs_etl.cli_enhanced", "run",
            "--month", month_code,
            "--raw-dir", "./Raw-New-Month"
        ]
        
        if dry_run:
            cmd.append("--dry-run")
        
        # Set PYTHONPATH to include src directory
        env = os.environ.copy()
        env['PYTHONPATH'] = 'src'
        
        print_colored(f"Running: {' '.join(cmd)}", Colors.BLUE)
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            print_success(f"ETL pipeline completed successfully for {month_code}")
            return True
        else:
            print_error(f"ETL pipeline failed for {month_code}")
            print_error(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        print_error(f"Error running ETL pipeline: {e}")
        return False

def cleanup_temp_files() -> None:
    """Clean up temporary files in Raw-New-Month directory."""
    try:
        temp_dir = Path("Raw-New-Month")
        if temp_dir.exists():
            for file in temp_dir.glob("*.xlsx"):
                file.unlink()
            print_success("Cleaned up temporary files")
    except Exception as e:
        print_warning(f"Error cleaning up: {e}")

def check_prerequisites() -> bool:
    """Check if all required directories and tools are available."""
    print_step(1, "Checking prerequisites")
    
    # Check required directories
    required_dirs = ["ALL-MONTHS", "Reformat", "All-to-Date", "Analysis"]
    missing_dirs = []
    
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print_error(f"Missing required directories: {', '.join(missing_dirs)}")
        print_colored("Creating missing directories...", Colors.YELLOW)
        
        for dir_name in missing_dirs:
            Path(dir_name).mkdir(exist_ok=True)
            print_success(f"Created {dir_name}/")
    
    # Check if Python is available
    try:
        result = subprocess.run(["python3", "--version"], capture_output=True)
        if result.returncode == 0:
            print_success("Python 3 is available")
        else:
            print_error("Python 3 is not available. Please install Python 3 first.")
            return False
    except:
        print_error("Python 3 is not available. Please install Python 3 first.")
        return False
    
    # Check if Raw-New-Month directory exists
    raw_new_month = Path("Raw-New-Month")
    if not raw_new_month.exists():
        raw_new_month.mkdir()
        print_success("Created Raw-New-Month directory")
    
    return True

def main():
    """Main function to run the batch processing script."""
    print_header("ADHS ETL Batch Processing Script")
    print_colored("This script will process multiple months of ADHS data in chronological order.", Colors.WHITE)
    print_colored("Press Ctrl+C at any time to stop, or type 'q' to quit.", Colors.YELLOW)
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            sys.exit(1)
        
        # Get available months
        print_step(2, "Scanning for available months")
        months = get_available_months()
        
        if not months:
            print_error("No valid month folders found in ALL-MONTHS directory!")
            print_colored("Expected format: 'Raw M.YY' (e.g., 'Raw 1.25' for January 2025)", Colors.YELLOW)
            sys.exit(1)
        
        print_success(f"Found {len(months)} available months")
        
        # Display available months
        display_available_months(months)
        
        # Get user selection for start and end months
        print_step(3, "Selecting month range")
        
        start_idx = get_user_selection("Select START month", len(months))
        end_idx = get_user_selection("Select END month", len(months))
        
        if not validate_month_range(start_idx, end_idx):
            print_error("End month must be the same as or after start month!")
            sys.exit(1)
        
        # Confirm selection
        selected_months = months[start_idx:end_idx + 1]
        print_colored(f"\n📋 Selected months to process:", Colors.BOLD)
        for folder_name, month_code in selected_months:
            print_colored(f"  • {month_code} ({folder_name})", Colors.WHITE)
        
        # Ask for dry run
        dry_run_choice = input(f"\nRun in dry-run mode? (y/N): ").strip().lower()
        dry_run = dry_run_choice in ['y', 'yes']
        
        if dry_run:
            print_warning("Running in DRY RUN mode - no files will be written")
        
        # Confirm before processing
        print_colored(f"\n🚀 Ready to process {len(selected_months)} months", Colors.BOLD)
        confirm = input("Continue? (y/N): ").strip().lower()
        
        if confirm not in ['y', 'yes']:
            print_colored("Operation cancelled.", Colors.YELLOW)
            sys.exit(0)
        
        # Process each month
        print_step(4, "Processing months")
        
        successful_months = []
        failed_months = []
        
        for i, (folder_name, month_code) in enumerate(selected_months, 1):
            print_colored(f"\n📊 Processing month {i}/{len(selected_months)}: {month_code}", Colors.PURPLE)
            
            # Copy files
            source_folder = Path("ALL-MONTHS") / folder_name
            dest_folder = Path("Raw-New-Month")
            
            if copy_month_files(source_folder, dest_folder):
                # Run ETL pipeline
                if run_etl_pipeline(month_code, dry_run):
                    successful_months.append(month_code)
                else:
                    failed_months.append(month_code)
            else:
                failed_months.append(month_code)
            
            # Clean up temp files
            cleanup_temp_files()
            
            # Brief pause between months
            if i < len(selected_months):
                print_colored("⏳ Pausing briefly before next month...", Colors.BLUE)
                import time
                time.sleep(1)
        
        # Final summary
        print_header("BATCH PROCESSING COMPLETE")
        
        if successful_months:
            print_colored(f"✅ Successfully processed {len(successful_months)} months:", Colors.GREEN)
            for month in successful_months:
                print_colored(f"  • {month}", Colors.WHITE)
        
        if failed_months:
            print_colored(f"❌ Failed to process {len(failed_months)} months:", Colors.RED)
            for month in failed_months:
                print_colored(f"  • {month}", Colors.WHITE)
        
        if not dry_run:
            print_colored(f"\n📁 Output files are available in:", Colors.BOLD)
            print_colored(f"  • Reformat/ - Individual month files", Colors.WHITE)
            print_colored(f"  • All-to-Date/ - Cumulative data files", Colors.WHITE)
            print_colored(f"  • Analysis/ - Analysis files with lost license detection", Colors.WHITE)
        
        print_colored(f"\n🎉 Batch processing completed!", Colors.GREEN)
        
    except KeyboardInterrupt:
        print_colored(f"\n\n⏹️  Operation cancelled by user", Colors.YELLOW)
        cleanup_temp_files()
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        cleanup_temp_files()
        sys.exit(1)

if __name__ == "__main__":
    main()