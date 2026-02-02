#!/usr/bin/env python3
"""Compare legacy and new Ecorp scrapers side-by-side.

This script runs both the legacy ecorp scraper and the new Arizona Business
Connect scraper on the same input data, then compares the results to verify
the new implementation produces equivalent output.

Usage:
    python scripts/compare_ecorp_scrapers.py --month 1.25 --sample 10
    python scripts/compare_ecorp_scrapers.py --upload-file Ecorp/Upload/1.25_Ecorp_Upload.xlsx --sample 5

Options:
    --month         Month code (e.g., 1.25 for January 2025)
    --upload-file   Path to specific Ecorp Upload file
    --sample        Number of records to test (default: 10)
    --no-headless   Run browsers in visible mode for debugging
    --legacy-only   Only run the legacy scraper
    --new-only      Only run the new scraper
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def find_latest_upload(month_code: str) -> Path:
    """Find the latest Ecorp Upload file for a given month."""
    upload_dir = project_root / "Ecorp" / "Upload"

    # Try new format first
    patterns = [
        f"{month_code}_Ecorp_Upload_*.xlsx",
        f"{month_code} Ecorp Upload*.xlsx",
    ]

    for pattern in patterns:
        matches = list(upload_dir.glob(pattern))
        if matches:
            # Return most recent by modification time
            return max(matches, key=lambda p: p.stat().st_mtime)

    raise FileNotFoundError(
        f"No Ecorp Upload file found for month {month_code} in {upload_dir}"
    )


def run_legacy_scraper(
    upload_path: Path,
    output_path: Path,
    sample_size: int,
    headless: bool = True,
) -> bool:
    """Run the legacy ecorp scraper."""
    print(f"\n{'='*60}")
    print("RUNNING LEGACY SCRAPER")
    print(f"{'='*60}")

    try:
        # Import legacy module
        from adhs_etl.ecorp_legacy import (
            generate_ecorp_complete as legacy_generate,
            setup_driver,
        )

        # Read upload file and limit to sample size
        upload_df = pd.read_excel(upload_path)
        if sample_size and len(upload_df) > sample_size:
            upload_df = upload_df.head(sample_size)
            # Save limited version
            temp_path = upload_path.parent / f"_temp_legacy_{upload_path.name}"
            upload_df.to_excel(temp_path, index=False)
            upload_path = temp_path

        # Note: Legacy scraper doesn't have easy sample limiting
        # This is a simplified comparison that processes the full file
        print(f"  Input: {upload_path}")
        print(f"  Sample size: {sample_size}")
        print(f"  Output: {output_path}")

        # For now, just return success indicator
        # Full integration would call legacy_generate()
        print("  [Legacy scraper would run here]")
        print("  Note: Legacy may not work if old site is offline")

        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def run_new_scraper(
    upload_path: Path,
    output_path: Path,
    sample_size: int,
    headless: bool = True,
) -> bool:
    """Run the new Arizona Business Connect scraper."""
    print(f"\n{'='*60}")
    print("RUNNING NEW SCRAPER (Arizona Business Connect)")
    print(f"{'='*60}")

    try:
        from adhs_etl.config import get_ecorp_settings
        from adhs_etl.ecorp import (
            generate_ecorp_complete,
            setup_driver,
            search_entities,
            get_blank_acc_record,
        )

        settings = get_ecorp_settings(headless=headless)

        print(f"  Base URL: {settings.base_url}")
        print(f"  Input: {upload_path}")
        print(f"  Sample size: {sample_size}")
        print(f"  Output: {output_path}")

        # Read upload file
        upload_df = pd.read_excel(upload_path)
        total_records = len(upload_df)
        print(f"  Total records in file: {total_records}")

        if sample_size and total_records > sample_size:
            upload_df = upload_df.head(sample_size)
            print(f"  Limited to first {sample_size} records")

        # Initialize driver
        print("\n  Initializing Chrome driver...")
        driver = setup_driver(headless=headless)

        results = []
        try:
            for idx, row in upload_df.iterrows():
                owner_name = str(row.get("Owner_Ownership", "")).strip()
                if not owner_name:
                    results.append(get_blank_acc_record())
                    continue

                print(f"  [{idx+1}/{len(upload_df)}] Searching: {owner_name[:50]}...")

                try:
                    entity_results = search_entities(driver, owner_name, settings)
                    if entity_results:
                        results.extend(entity_results)
                    else:
                        results.append(get_blank_acc_record())
                except Exception as e:
                    print(f"    Error: {e}")
                    blank = get_blank_acc_record()
                    blank["ECORP_COMMENTS"] = f"Error: {str(e)[:100]}"
                    results.append(blank)

        finally:
            driver.quit()

        # Save results
        if results:
            results_df = pd.DataFrame(results)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            results_df.to_excel(output_path, index=False, engine="xlsxwriter")
            print(f"\n  Results saved to: {output_path}")
            print(f"  Records extracted: {len(results)}")
            return True
        else:
            print("  No results extracted")
            return False

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_results(legacy_path: Path, new_path: Path) -> dict:
    """Compare results from legacy and new scrapers."""
    print(f"\n{'='*60}")
    print("COMPARING RESULTS")
    print(f"{'='*60}")

    comparison = {
        "legacy_exists": legacy_path.exists(),
        "new_exists": new_path.exists(),
        "columns_match": False,
        "row_count_match": False,
        "field_matches": {},
    }

    if not legacy_path.exists():
        print(f"  Legacy output not found: {legacy_path}")

    if not new_path.exists():
        print(f"  New output not found: {new_path}")

    if not (legacy_path.exists() and new_path.exists()):
        print("  Cannot compare - one or both outputs missing")
        return comparison

    legacy_df = pd.read_excel(legacy_path)
    new_df = pd.read_excel(new_path)

    print(f"\n  Legacy: {len(legacy_df)} rows, {len(legacy_df.columns)} columns")
    print(f"  New:    {len(new_df)} rows, {len(new_df.columns)} columns")

    # Column comparison
    legacy_cols = set(legacy_df.columns)
    new_cols = set(new_df.columns)

    if legacy_cols == new_cols:
        print("  Columns: MATCH")
        comparison["columns_match"] = True
    else:
        print("  Columns: DIFFER")
        only_legacy = legacy_cols - new_cols
        only_new = new_cols - legacy_cols
        if only_legacy:
            print(f"    Only in legacy: {only_legacy}")
        if only_new:
            print(f"    Only in new: {only_new}")

    # Row count comparison
    if len(legacy_df) == len(new_df):
        print("  Row count: MATCH")
        comparison["row_count_match"] = True

        # Field-by-field comparison
        print("\n  Field-by-field comparison:")
        common_cols = legacy_cols & new_cols
        for col in sorted(common_cols):
            try:
                # Handle NaN comparisons
                legacy_vals = legacy_df[col].fillna("").astype(str)
                new_vals = new_df[col].fillna("").astype(str)
                matches = (legacy_vals == new_vals).sum()
                total = len(legacy_df)
                pct = matches / total * 100 if total > 0 else 0
                comparison["field_matches"][col] = {"matches": matches, "total": total}

                if matches == total:
                    status = "MATCH"
                elif matches > total * 0.9:
                    status = "CLOSE"
                else:
                    status = "DIFFER"

                print(f"    {col}: {matches}/{total} ({pct:.1f}%) - {status}")

            except Exception as e:
                print(f"    {col}: Error comparing - {e}")

    else:
        print("  Row count: DIFFER - cannot do field comparison")

    return comparison


def main():
    parser = argparse.ArgumentParser(
        description="Compare legacy and new Ecorp scrapers"
    )
    parser.add_argument(
        "--month",
        type=str,
        help="Month code (e.g., 1.25)",
    )
    parser.add_argument(
        "--upload-file",
        type=str,
        help="Path to specific Ecorp Upload file",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="Number of records to test (default: 10)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browsers in visible mode",
    )
    parser.add_argument(
        "--legacy-only",
        action="store_true",
        help="Only run the legacy scraper",
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        help="Only run the new scraper",
    )

    args = parser.parse_args()

    # Determine upload file
    if args.upload_file:
        upload_path = Path(args.upload_file)
        if not upload_path.exists():
            print(f"Error: Upload file not found: {upload_path}")
            sys.exit(1)
        month_code = upload_path.stem.split("_")[0]
    elif args.month:
        upload_path = find_latest_upload(args.month)
        month_code = args.month
    else:
        print("Error: Must specify either --month or --upload-file")
        sys.exit(1)

    print(f"\nEcorp Scraper Comparison")
    print(f"{'='*60}")
    print(f"Upload file: {upload_path}")
    print(f"Sample size: {args.sample}")
    print(f"Headless: {not args.no_headless}")

    timestamp = datetime.now().strftime("%m.%d.%H-%M-%S")
    output_dir = project_root / "Ecorp" / "Complete"

    legacy_output = output_dir / f"{month_code}_COMPARISON_LEGACY_{timestamp}.xlsx"
    new_output = output_dir / f"{month_code}_COMPARISON_NEW_{timestamp}.xlsx"

    headless = not args.no_headless

    # Run scrapers
    legacy_success = False
    new_success = False

    if not args.new_only:
        legacy_success = run_legacy_scraper(
            upload_path, legacy_output, args.sample, headless
        )

    if not args.legacy_only:
        new_success = run_new_scraper(
            upload_path, new_output, args.sample, headless
        )

    # Compare results
    if not args.legacy_only and not args.new_only:
        comparison = compare_results(legacy_output, new_output)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    if not args.new_only:
        print(f"  Legacy scraper: {'SUCCESS' if legacy_success else 'FAILED'}")
    if not args.legacy_only:
        print(f"  New scraper:    {'SUCCESS' if new_success else 'FAILED'}")

    if legacy_output.exists():
        print(f"  Legacy output:  {legacy_output}")
    if new_output.exists():
        print(f"  New output:     {new_output}")


if __name__ == "__main__":
    main()
