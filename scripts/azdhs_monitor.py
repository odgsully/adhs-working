#!/usr/bin/env python3
"""
AZDHS Provider Database Monitor & Auto-Downloader

Monitors https://www.azdhs.gov/licensing/index.php#databases for new monthly data
and automatically downloads files for specified provider types.

URL Pattern: /documents/licensing/databases/{year}/{month}/{PROVIDER}.xlsx

Features:
- Daily monitoring for new month availability
- Auto-download to ALL-MONTHS/Raw M.YY/ directory
- Slack + Gmail notifications
- Optional Supabase sync

Usage:
    # Check for new data and download if available
    poetry run python scripts/azdhs_monitor.py

    # Force download specific month (even if already exists)
    poetry run python scripts/azdhs_monitor.py --month 1.25 --force

    # Dry run (check only, no download)
    poetry run python scripts/azdhs_monitor.py --dry-run

    # Check specific year
    poetry run python scripts/azdhs_monitor.py --year 2025
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.azdhs_notify import send_notifications

# ============================================================================
# Configuration
# ============================================================================

BASE_URL = "https://www.azdhs.gov"
DATABASE_PATH = "/documents/licensing/databases"

# Provider types to download (must match AZDHS file names exactly)
TARGET_PROVIDERS = [
    "ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME",
    "ASSISTED_LIVING_CENTER",
    "ASSISTED_LIVING_HOME",
    "BEHAVIORAL_HEALTH_INPATIENT_FACILITY",  # Note: may have FACILITY suffix
    "BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY",
    "CHILD_CARE_FACILITY_CENTER",  # CC_CENTERS equivalent
    "CHILD_CARE_GROUP_HOME",       # CC_GROUP_HOMES equivalent
    "GROUP_HOME_DD",               # DEVELOPMENTALLY_DISABLED_GROUP_HOME equivalent
    "HOSPITAL",                    # HOSPITAL_REPORT equivalent
    "NURSING_CARE_INSTITUTION",    # NURSING_HOME equivalent
    "NURSING_SUPPORTED_GROUP_HOME",
    "OUTPATIENT_TREATMENT_CENTER", # OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT equivalent
]

# Map AZDHS names to our local file names
AZDHS_TO_LOCAL_MAP = {
    "ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME": "ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME",
    "ASSISTED_LIVING_CENTER": "ASSISTED_LIVING_CENTER",
    "ASSISTED_LIVING_HOME": "ASSISTED_LIVING_HOME",
    "BEHAVIORAL_HEALTH_INPATIENT_FACILITY": "BEHAVIORAL_HEALTH_INPATIENT",
    "BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY": "BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY",
    "CHILD_CARE_FACILITY_CENTER": "CC_CENTERS",
    "CHILD_CARE_GROUP_HOME": "CC_GROUP_HOMES",
    "GROUP_HOME_DD": "DEVELOPMENTALLY_DISABLED_GROUP_HOME",
    "HOSPITAL": "HOSPITAL_REPORT",
    "NURSING_CARE_INSTITUTION": "NURSING_HOME",
    "NURSING_SUPPORTED_GROUP_HOME": "NURSING_SUPPORTED_GROUP_HOMES",
    "OUTPATIENT_TREATMENT_CENTER": "OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT",
}

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]

MONTH_NAMES_DISPLAY = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# ============================================================================
# Helper Functions
# ============================================================================

def get_current_month_year() -> tuple[int, int]:
    """Get current month and year."""
    now = datetime.now()
    return now.month, now.year


def month_to_code(month: int, year: int) -> str:
    """Convert month/year to M.YY format (e.g., 1.25 for January 2025)."""
    return f"{month}.{year % 100}"


def get_raw_dir(month_code: str) -> Path:
    """Get the Raw M.YY directory path."""
    return PROJECT_ROOT / "ALL-MONTHS" / f"Raw {month_code}"


def build_download_url(year: int, month: int, provider: str) -> str:
    """Build the download URL for a specific provider/month."""
    month_name = MONTH_NAMES[month - 1]
    return f"{BASE_URL}{DATABASE_PATH}/{year}/{month_name}/{provider}.xlsx"


def check_url_exists(url: str) -> bool:
    """Check if a URL exists (returns 200)."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'AZDHS-Monitor/1.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def download_file(url: str, output_path: Path) -> bool:
    """Download a file from URL to local path."""
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'AZDHS-Monitor/1.0')

        with urllib.request.urlopen(req, timeout=60) as response:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"      [ERROR] Download failed: {e}")
        return False


# ============================================================================
# Main Functions
# ============================================================================

async def discover_provider_names(year: int, month: int) -> dict[str, str]:
    """Discover actual provider file names on AZDHS for a given month.

    Returns dict mapping found AZDHS names to our local names.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[WARN] Playwright not installed, using predefined names")
        return AZDHS_TO_LOCAL_MAP

    found_providers = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(f"{BASE_URL}/licensing/index.php#databases", wait_until='networkidle')
        await page.wait_for_timeout(2000)

        # Find all Excel download links for this year/month
        month_name = MONTH_NAMES[month - 1]
        links = await page.query_selector_all(f'a[href*="/{year}/{month_name}/"]')

        for link in links:
            href = await link.get_attribute('href')
            if href and '.xlsx' in href:
                # Extract provider name from URL
                # /documents/licensing/databases/2025/january/PROVIDER_NAME.xlsx
                filename = href.split('/')[-1].split('?')[0].replace('.xlsx', '')

                # Check if this is one of our target providers (fuzzy match)
                for azdhs_name, local_name in AZDHS_TO_LOCAL_MAP.items():
                    if filename.upper() == azdhs_name or local_name in filename.upper():
                        found_providers[filename.upper()] = local_name
                        break
                    # Also try exact match
                    if filename.upper() == local_name:
                        found_providers[filename.upper()] = local_name
                        break

        await browser.close()

    return found_providers if found_providers else AZDHS_TO_LOCAL_MAP


async def check_month_available(year: int, month: int) -> bool:
    """Check if a month's data is available by testing one provider URL."""
    # Try a few different provider name variations
    test_providers = [
        "ASSISTED_LIVING_CENTER",
        "ASSISTED_LIVING_HOME",
        "BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY",
    ]

    for provider in test_providers:
        url = build_download_url(year, month, provider)
        if check_url_exists(url):
            return True

    return False


async def download_month_data(
    year: int,
    month: int,
    dry_run: bool = False,
    force: bool = False
) -> dict:
    """Download all provider types for a specific month."""
    month_code = month_to_code(month, year)
    output_dir = get_raw_dir(month_code)
    month_display = MONTH_NAMES_DISPLAY[month - 1]

    print(f"\n{'='*60}")
    print(f"AZDHS Data Download: {month_display} {year} ({month_code})")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    if output_dir.exists() and not force and not dry_run:
        existing_files = list(output_dir.glob("*.xlsx"))
        if len(existing_files) >= len(TARGET_PROVIDERS) * 0.8:
            print(f"[SKIP] Directory already has {len(existing_files)} files. Use --force to re-download.")
            return {"status": "skipped", "month": month_code, "files": []}

    results = {
        "status": "success",
        "month": month_code,
        "year": year,
        "files": [],
        "errors": []
    }

    # Discover actual provider names on AZDHS
    print("[INFO] Discovering provider file names...")
    provider_map = await discover_provider_names(year, month)
    print(f"[INFO] Found {len(provider_map)} provider types\n")

    # If discovery failed, use defaults
    if not provider_map:
        provider_map = AZDHS_TO_LOCAL_MAP

    # Download each provider type
    for idx, (azdhs_name, local_name) in enumerate(provider_map.items(), 1):
        print(f"[{idx}/{len(provider_map)}] {local_name}")

        url = build_download_url(year, month, azdhs_name)
        output_path = output_dir / f"{local_name}.xlsx"

        if output_path.exists() and not force:
            print(f"      [SKIP] Already exists")
            results["files"].append(str(output_path))
            continue

        if dry_run:
            # Check if URL exists
            exists = check_url_exists(url)
            status = "AVAILABLE" if exists else "NOT FOUND"
            print(f"      [DRY-RUN] {status}: {url}")
            if exists:
                results["files"].append(str(output_path))
            continue

        # Download the file
        print(f"      Downloading from {url}...")
        if download_file(url, output_path):
            print(f"      [OK] Saved to {output_path.name}")
            results["files"].append(str(output_path))
        else:
            print(f"      [FAIL] Could not download")
            results["errors"].append(local_name)

    # Summary
    print(f"\n{'='*60}")
    print(f"Download Complete: {len(results['files'])} files, {len(results['errors'])} errors")
    print(f"{'='*60}\n")

    if results["errors"]:
        results["status"] = "completed_with_errors"

    return results


async def check_for_new_month(year: Optional[int] = None) -> Optional[tuple[int, int]]:
    """Check if the current month's data is available."""
    current_month, current_year = get_current_month_year()

    if year is None:
        year = current_year

    month_code = month_to_code(current_month, year)
    output_dir = get_raw_dir(month_code)
    month_display = MONTH_NAMES_DISPLAY[current_month - 1]

    # If directory already exists with files, no new data needed
    if output_dir.exists():
        existing_files = list(output_dir.glob("*.xlsx"))
        if len(existing_files) >= len(TARGET_PROVIDERS) * 0.8:
            print(f"[INFO] {month_display} {year} data already downloaded ({len(existing_files)} files)")
            return None

    print(f"[CHECK] Looking for {month_display} {year} data...")

    # Check if data is available
    if await check_month_available(year, current_month):
        print(f"[NEW] {month_display} {year} data is available!")
        return (current_month, year)
    else:
        print(f"[INFO] {month_display} {year} data not yet available")

        # Check what months ARE available
        print("[INFO] Checking available months...")
        available = []
        for m in range(1, 13):
            if await check_month_available(year, m):
                available.append(MONTH_NAMES_DISPLAY[m - 1])

        if available:
            print(f"[INFO] Available: {', '.join(available)}")

        return None


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="AZDHS Provider Database Monitor")
    parser.add_argument("--month", type=str, help="Specific month to download (M.YY format, e.g., 1.25)")
    parser.add_argument("--year", type=int, help="Year to check (default: current year)")
    parser.add_argument("--dry-run", action="store_true", help="Check only, don't download")
    parser.add_argument("--force", action="store_true", help="Force re-download even if files exist")
    parser.add_argument("--check-only", action="store_true", help="Only check for new month, don't download")
    parser.add_argument("--notify", action="store_true", help="Send notifications on new data")

    args = parser.parse_args()

    if args.month:
        # Download specific month
        parts = args.month.split(".")
        month = int(parts[0])
        year = 2000 + int(parts[1])

        results = await download_month_data(year, month, args.dry_run, args.force)

        if args.notify and results["files"]:
            send_notifications(
                f"AZDHS Data Downloaded: {args.month}",
                f"Downloaded {len(results['files'])} files for {MONTH_NAMES_DISPLAY[month-1]} {year}",
                results
            )

    elif args.check_only:
        # Just check for new month
        new_month = await check_for_new_month(args.year)
        if new_month:
            month, year = new_month
            print(f"\n[ALERT] New data available: {MONTH_NAMES_DISPLAY[month-1]} {year}")
            if args.notify:
                send_notifications(
                    f"AZDHS New Month Available: {month_to_code(month, year)}",
                    f"{MONTH_NAMES_DISPLAY[month-1]} {year} data is now available for download!",
                    {"month": month_to_code(month, year), "available": True}
                )

    else:
        # Default: check for new month and download if available
        new_month = await check_for_new_month(args.year)

        if new_month:
            month, year = new_month

            if args.dry_run:
                print(f"\n[DRY-RUN] Would download {MONTH_NAMES_DISPLAY[month-1]} {year} data")
                results = await download_month_data(year, month, dry_run=True)
            else:
                results = await download_month_data(year, month, args.dry_run, args.force)

                if args.notify and results["files"]:
                    send_notifications(
                        f"AZDHS New Data: {month_to_code(month, year)}",
                        f"Automatically downloaded {len(results['files'])} provider files for {MONTH_NAMES_DISPLAY[month-1]} {year}",
                        results
                    )


if __name__ == "__main__":
    asyncio.run(main())
