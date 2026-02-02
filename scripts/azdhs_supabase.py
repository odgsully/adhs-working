#!/usr/bin/env python3
"""
AZDHS Supabase Sync Module

Syncs downloaded AZDHS provider data to Supabase for centralized storage.

Tables Created:
    azdhs_raw_providers - Raw provider data with month/year partitioning
    azdhs_download_log - Log of download events

Usage:
    from scripts.azdhs_supabase import sync_to_supabase
    sync_to_supabase("/path/to/Raw 1.25/")

Environment Variables:
    SUPABASE_URL - Supabase project URL
    SUPABASE_KEY - Supabase service role key (for inserts)
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not installed. Run: poetry add supabase")
    create_client = None
    Client = None

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


# ============================================================================
# SQL Schema for Reference
# ============================================================================

SCHEMA_SQL = """
-- AZDHS Raw Providers Table
-- Stores raw provider data from each monthly download

CREATE TABLE IF NOT EXISTS azdhs_raw_providers (
    id BIGSERIAL PRIMARY KEY,

    -- Temporal partitioning
    month_code VARCHAR(10) NOT NULL,  -- e.g., "1.25"
    month INTEGER NOT NULL,           -- 1-12
    year INTEGER NOT NULL,            -- e.g., 2025

    -- Provider identification
    provider_type VARCHAR(100) NOT NULL,
    license_number VARCHAR(50),
    provider_name TEXT,
    dba_name TEXT,

    -- Location
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(10) DEFAULT 'AZ',
    zip VARCHAR(20),
    county VARCHAR(100),

    -- Coordinates
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),

    -- Provider details
    capacity INTEGER,
    license_status VARCHAR(50),
    license_effective_date DATE,
    license_expiration_date DATE,

    -- Raw data (for fields we don't explicitly map)
    raw_data JSONB,

    -- Metadata
    downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_file VARCHAR(255),

    -- Prevent duplicates
    UNIQUE(month_code, provider_type, license_number)
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_azdhs_raw_month ON azdhs_raw_providers(month_code);
CREATE INDEX IF NOT EXISTS idx_azdhs_raw_provider_type ON azdhs_raw_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_azdhs_raw_county ON azdhs_raw_providers(county);
CREATE INDEX IF NOT EXISTS idx_azdhs_raw_license ON azdhs_raw_providers(license_number);

-- Download Log Table
-- Tracks when downloads occurred

CREATE TABLE IF NOT EXISTS azdhs_download_log (
    id BIGSERIAL PRIMARY KEY,
    month_code VARCHAR(10) NOT NULL,
    download_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    download_completed_at TIMESTAMP WITH TIME ZONE,
    files_downloaded INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    errors TEXT[],
    status VARCHAR(20) DEFAULT 'started',  -- started, completed, failed

    UNIQUE(month_code, download_started_at)
);

-- Enable Row Level Security (optional, for multi-tenant)
-- ALTER TABLE azdhs_raw_providers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE azdhs_download_log ENABLE ROW LEVEL SECURITY;
"""


# ============================================================================
# Supabase Client
# ============================================================================

def get_supabase_client() -> Optional[Client]:
    """Get Supabase client from environment variables."""
    if create_client is None:
        print("[SUPABASE] Client not installed")
        return None

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("[SUPABASE] Missing SUPABASE_URL or SUPABASE_KEY")
        return None

    return create_client(url, key)


# ============================================================================
# Data Mapping
# ============================================================================

# Common column name variations in AZDHS Excel files
COLUMN_MAP = {
    # License info
    "license #": "license_number",
    "license number": "license_number",
    "license_number": "license_number",
    "lic #": "license_number",

    # Provider name
    "provider name": "provider_name",
    "provider": "provider_name",
    "facility name": "provider_name",
    "name": "provider_name",

    # DBA
    "dba": "dba_name",
    "dba name": "dba_name",
    "doing business as": "dba_name",

    # Address
    "address": "address",
    "street address": "address",
    "physical address": "address",

    # City
    "city": "city",

    # Zip
    "zip": "zip",
    "zip code": "zip",
    "zipcode": "zip",

    # County
    "county": "county",

    # Coordinates
    "latitude": "latitude",
    "lat": "latitude",
    "longitude": "longitude",
    "long": "longitude",
    "lng": "longitude",

    # Capacity
    "capacity": "capacity",
    "bed capacity": "capacity",
    "licensed capacity": "capacity",

    # Status
    "status": "license_status",
    "license status": "license_status",

    # Dates
    "effective date": "license_effective_date",
    "license effective date": "license_effective_date",
    "expiration date": "license_expiration_date",
    "license expiration date": "license_expiration_date",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to standard format."""
    df.columns = [str(c).lower().strip() for c in df.columns]

    rename_map = {}
    for col in df.columns:
        if col in COLUMN_MAP:
            rename_map[col] = COLUMN_MAP[col]

    return df.rename(columns=rename_map)


def parse_month_code(month_code: str) -> tuple[int, int]:
    """Parse M.YY format to (month, year)."""
    parts = month_code.split(".")
    month = int(parts[0])
    year = 2000 + int(parts[1])
    return month, year


def excel_to_records(
    file_path: Path,
    provider_type: str,
    month_code: str
) -> list[dict]:
    """Convert Excel file to list of records for Supabase."""
    df = pd.read_excel(file_path)
    df = normalize_columns(df)

    month, year = parse_month_code(month_code)

    records = []
    for _, row in df.iterrows():
        # Extract known fields
        record = {
            "month_code": month_code,
            "month": month,
            "year": year,
            "provider_type": provider_type,
            "source_file": file_path.name,
        }

        # Map known columns
        for col in ["license_number", "provider_name", "dba_name", "address",
                    "city", "zip", "county", "latitude", "longitude",
                    "capacity", "license_status"]:
            if col in df.columns:
                value = row.get(col)
                if pd.notna(value):
                    record[col] = str(value) if col not in ["latitude", "longitude", "capacity"] else value

        # Store remaining columns as raw_data JSON
        raw_data = {}
        for col in df.columns:
            if col not in COLUMN_MAP.values() and pd.notna(row.get(col)):
                raw_data[col] = str(row[col])

        if raw_data:
            record["raw_data"] = raw_data

        records.append(record)

    return records


# ============================================================================
# Sync Functions
# ============================================================================

def sync_file_to_supabase(
    client: Client,
    file_path: Path,
    month_code: str,
    dry_run: bool = False
) -> int:
    """Sync a single Excel file to Supabase."""
    provider_type = file_path.stem  # e.g., ASSISTED_LIVING_CENTER

    print(f"  [SYNC] {provider_type}...")

    records = excel_to_records(file_path, provider_type, month_code)

    if dry_run:
        print(f"  [DRY-RUN] Would insert {len(records)} records")
        return len(records)

    if not records:
        print(f"  [SKIP] No records in {file_path.name}")
        return 0

    # Upsert records (insert or update on conflict)
    try:
        # Batch insert in chunks of 100
        chunk_size = 100
        inserted = 0

        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            result = client.table("azdhs_raw_providers").upsert(
                chunk,
                on_conflict="month_code,provider_type,license_number"
            ).execute()
            inserted += len(chunk)

        print(f"  [OK] Inserted {inserted} records")
        return inserted

    except Exception as e:
        print(f"  [ERROR] Failed to sync {provider_type}: {e}")
        return 0


def sync_to_supabase(
    raw_dir: Path,
    dry_run: bool = False
) -> dict:
    """Sync all files in a Raw M.YY directory to Supabase."""
    raw_dir = Path(raw_dir)

    if not raw_dir.exists():
        print(f"[ERROR] Directory not found: {raw_dir}")
        return {"status": "error", "message": "Directory not found"}

    # Extract month code from directory name (e.g., "Raw 1.25" -> "1.25")
    month_code = raw_dir.name.replace("Raw ", "")

    print(f"\n{'='*60}")
    print(f"Supabase Sync: {month_code}")
    print(f"Source: {raw_dir}")
    print(f"{'='*60}\n")

    client = get_supabase_client()
    if not client and not dry_run:
        return {"status": "error", "message": "Could not connect to Supabase"}

    # Log download start
    log_id = None
    if client and not dry_run:
        try:
            log_result = client.table("azdhs_download_log").insert({
                "month_code": month_code,
                "status": "started"
            }).execute()
            log_id = log_result.data[0]["id"] if log_result.data else None
        except Exception as e:
            print(f"[WARN] Could not create log entry: {e}")

    # Sync each Excel file
    excel_files = list(raw_dir.glob("*.xlsx"))
    total_records = 0
    errors = []

    for file_path in excel_files:
        try:
            count = sync_file_to_supabase(client, file_path, month_code, dry_run)
            total_records += count
        except Exception as e:
            errors.append(f"{file_path.name}: {str(e)}")
            print(f"  [ERROR] {file_path.name}: {e}")

    # Update log entry
    if client and log_id and not dry_run:
        try:
            client.table("azdhs_download_log").update({
                "download_completed_at": datetime.now().isoformat(),
                "files_downloaded": len(excel_files),
                "records_inserted": total_records,
                "errors": errors if errors else None,
                "status": "completed" if not errors else "completed_with_errors"
            }).eq("id", log_id).execute()
        except Exception as e:
            print(f"[WARN] Could not update log entry: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Sync Complete: {len(excel_files)} files, {total_records} records")
    if errors:
        print(f"Errors: {len(errors)}")
    print(f"{'='*60}\n")

    return {
        "status": "success" if not errors else "completed_with_errors",
        "month_code": month_code,
        "files_synced": len(excel_files),
        "records_inserted": total_records,
        "errors": errors
    }


def print_schema():
    """Print the SQL schema for manual table creation."""
    print("="*60)
    print("SUPABASE SCHEMA")
    print("Run this SQL in your Supabase SQL Editor:")
    print("="*60)
    print(SCHEMA_SQL)


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="AZDHS Supabase Sync")
    parser.add_argument("--dir", type=str, help="Raw M.YY directory to sync")
    parser.add_argument("--month", type=str, help="Month code (e.g., 1.25)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually insert data")
    parser.add_argument("--schema", action="store_true", help="Print SQL schema")

    args = parser.parse_args()

    if args.schema:
        print_schema()
        return

    if args.dir:
        raw_dir = Path(args.dir)
    elif args.month:
        raw_dir = PROJECT_ROOT / "ALL-MONTHS" / f"Raw {args.month}"
    else:
        print("Please specify --dir or --month")
        return

    sync_to_supabase(raw_dir, args.dry_run)


if __name__ == "__main__":
    main()
