#!/usr/bin/env python3
"""Compare Excel outputs between branches for golden test validation."""
import sys
from pathlib import Path
import pandas as pd


def compare_excel_files(file1: Path, file2: Path) -> dict:
    """Compare two Excel files and return comparison results."""
    results = {
        "file1": str(file1),
        "file2": str(file2),
        "file1_exists": file1.exists(),
        "file2_exists": file2.exists(),
    }

    if not file1.exists() or not file2.exists():
        results["match"] = False
        results["error"] = "One or both files missing"
        return results

    try:
        df1 = pd.read_excel(file1)
        df2 = pd.read_excel(file2)

        results["file1_rows"] = len(df1)
        results["file2_rows"] = len(df2)
        results["file1_cols"] = list(df1.columns)
        results["file2_cols"] = list(df2.columns)
        results["rows_match"] = len(df1) == len(df2)
        results["cols_match"] = list(df1.columns) == list(df2.columns)
        results["data_match"] = df1.equals(df2)
        results["match"] = (
            results["rows_match"] and results["cols_match"] and results["data_match"]
        )

        if not results["cols_match"]:
            results["cols_only_in_file1"] = set(df1.columns) - set(df2.columns)
            results["cols_only_in_file2"] = set(df2.columns) - set(df1.columns)

    except Exception as e:
        results["match"] = False
        results["error"] = str(e)

    return results


def compare_directories(dir1: Path, dir2: Path) -> None:
    """Compare all Excel files in two directories."""
    print(f"\n{'='*60}")
    print(f"Comparing: {dir1.name} vs {dir2.name}")
    print(f"{'='*60}")

    if not dir1.exists() and not dir2.exists():
        print("  Both directories missing - skipping")
        return

    files1 = set(f.name for f in dir1.glob("*.xlsx")) if dir1.exists() else set()
    files2 = set(f.name for f in dir2.glob("*.xlsx")) if dir2.exists() else set()

    all_files = files1 | files2

    if not all_files:
        print("  No Excel files found in either directory")
        return

    for filename in sorted(all_files):
        file1 = dir1 / filename
        file2 = dir2 / filename

        result = compare_excel_files(file1, file2)

        status = "MATCH" if result.get("match") else "DIFFER"
        print(f"\n{filename}: {status}")

        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            print(
                f"  Rows: {result.get('file1_rows', 'N/A')} vs {result.get('file2_rows', 'N/A')}"
            )
            print(f"  Columns match: {result.get('cols_match', 'N/A')}")

            if not result.get("cols_match"):
                if result.get("cols_only_in_file1"):
                    print(f"  Only in file1: {result['cols_only_in_file1']}")
                if result.get("cols_only_in_file2"):
                    print(f"  Only in file2: {result['cols_only_in_file2']}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_excel_outputs.py <dir1> <dir2>")
        print(
            "Example: python compare_excel_outputs.py test-outputs/branch1_abc/ test-outputs/branch2_def/"
        )
        sys.exit(1)

    dir1 = Path(sys.argv[1])
    dir2 = Path(sys.argv[2])

    print(f"Comparing test outputs:")
    print(f"  Dir 1: {dir1}")
    print(f"  Dir 2: {dir2}")

    # Compare each output directory
    for subdir in ["Reformat", "All-to-Date", "Analysis"]:
        subdir1 = dir1 / subdir
        subdir2 = dir2 / subdir
        compare_directories(subdir1, subdir2)

    print("\n" + "=" * 60)
    print("Comparison complete")
