#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Maricopa APN lookup with Caching (Excel → APN)
----------------------------------------------
Reads an Excel file named like "M.YY_APN_Upload *.xlsx" with Columns A = FULL_ADDRESS, B = COUNTY,
queries Maricopa County ArcGIS services, and writes a new workbook with APN results.
Implements intelligent caching to avoid redundant lookups.

Endpoints (public, no key):
- Parcels query:   https://gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/0/query
- Parcels identify:https://gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/identify
- Geocoder:        https://gis.mcassessor.maricopa.gov/arcgis/rest/services/AssessorCompositeLocator/GeocodeServer/findAddressCandidates
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests

# Add parent directory to path for utils imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from adhs_etl.utils import (
    get_standard_timestamp,
    format_output_filename,
    get_legacy_filename,
    save_excel_with_legacy_copy,
    extract_timestamp_from_filename
)

# Optional dependency: usaddress (if present, we use it)
try:
    import usaddress  # type: ignore
    HAS_USADDRESS = True
except Exception:
    HAS_USADDRESS = False

# Cache configuration
CACHE_DIR = Path("APN/Cache")
CACHE_FILE = CACHE_DIR / "apn_master.csv"
FAILED_CACHE = CACHE_DIR / "failed_lookups.csv"

# Rate-limited GET helper
def _sleep_for_rate(rps: float) -> None:
    if rps <= 0:
        return
    base = 1.0 / rps
    # small jitter 0–150ms
    jitter = random.uniform(0, 0.15)
    time.sleep(base + jitter)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "apn-lookup/1.0 (+https://mcassessor.maricopa.gov)"})
TIMEOUT = 20

PARCEL_QUERY = "https://gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/0/query"
PARCEL_IDENT = "https://gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/identify"
GEOCODER_URL = "https://gis.mcassessor.maricopa.gov/arcgis/rest/services/AssessorCompositeLocator/GeocodeServer/findAddressCandidates"

TYPE_MAP = {
    "STREET": "ST", "ST": "ST",
    "AVENUE": "AVE", "AVE": "AVE",
    "ROAD": "RD", "RD": "RD",
    "DRIVE": "DR", "DR": "DR",
    "BOULEVARD": "BLVD", "BLVD": "BLVD",
    "LANE": "LN", "LN": "LN",
    "COURT": "CT", "CT": "CT",
    "PLACE": "PL", "PL": "PL",
    "WAY": "WAY"
}
DIR_MAP = {
    "NORTH":"N","SOUTH":"S","EAST":"E","WEST":"W",
    "NORTHEAST":"NE","NORTHWEST":"NW","SOUTHEAST":"SE","SOUTHWEST":"SW",
    "NE":"NE","NW":"NW","SE":"SE","SW":"SW",
    "N":"N","S":"S","E":"E","W":"W"
}

UNIT_RE = re.compile(r"\s+(?:APT|UNIT|SUITE|STE|#)\s*\S+\b", re.I)
ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?$")
NUM_NAME_TYPE_CITY_RE = re.compile(
    r"^\s*(\d+)\s+(?:([NSEW]|NE|NW|SE|SW)\s+)?([\w\-']+)\s+([A-Z\.]+)\s+(.*)$"
)

class APNCache:
    """Manages APN cache for reusing previous lookups."""

    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_file = CACHE_FILE
        self.failed_cache = FAILED_CACHE
        self.cache = {}
        self.failed = {}
        self.load_cache()

    def load_cache(self):
        """Load existing cache from disk."""
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load successful lookups
        if self.cache_file.exists():
            try:
                df = pd.read_csv(self.cache_file)
                for _, row in df.iterrows():
                    self.cache[row['address'].upper()] = {
                        'apn': row.get('apn', ''),
                        'method': row.get('method', ''),
                        'confidence': row.get('confidence', 0),
                        'last_updated': row.get('last_updated', '')
                    }
                print(f"📚 Loaded {len(self.cache)} cached APNs")
            except Exception as e:
                print(f"⚠️  Could not load cache: {e}")

        # Load failed lookups
        if self.failed_cache.exists():
            try:
                df = pd.read_csv(self.failed_cache)
                for _, row in df.iterrows():
                    self.failed[row['address'].upper()] = {
                        'attempts': row.get('attempts', 1),
                        'last_attempt': row.get('last_attempt', '')
                    }
                print(f"📚 Loaded {len(self.failed)} failed lookups")
            except Exception as e:
                print(f"⚠️  Could not load failed cache: {e}")

    def save_cache(self):
        """Save cache to disk."""
        # Save successful lookups
        if self.cache:
            cache_data = []
            for addr, data in self.cache.items():
                cache_data.append({
                    'address': addr,
                    'apn': data.get('apn', ''),
                    'method': data.get('method', ''),
                    'confidence': data.get('confidence', 0),
                    'last_updated': data.get('last_updated', '')
                })
            pd.DataFrame(cache_data).to_csv(self.cache_file, index=False)

        # Save failed lookups
        if self.failed:
            failed_data = []
            for addr, data in self.failed.items():
                failed_data.append({
                    'address': addr,
                    'attempts': data.get('attempts', 1),
                    'last_attempt': data.get('last_attempt', '')
                })
            pd.DataFrame(failed_data).to_csv(self.failed_cache, index=False)

    def get(self, address: str) -> Optional[Tuple[str, str, float, str]]:
        """Get cached APN if available and valid.

        Returns None if:
        - Not in cache
        - APN is blank/null (needs re-lookup)
        - Failed too many times recently
        """
        addr_upper = address.upper().strip()

        # Check if it's a known failure (but always retry blanks)
        if addr_upper in self.failed:
            failed_data = self.failed[addr_upper]
            # If failed 3+ times in last 30 days, skip
            if failed_data['attempts'] >= 3:
                last_attempt = pd.to_datetime(failed_data['last_attempt'], errors='coerce')
                if pd.notna(last_attempt) and (datetime.datetime.now() - last_attempt).days < 30:
                    return None, "cached_failure", 0.0, "SKIP_KNOWN_FAILURE"

        # Check successful cache
        if addr_upper in self.cache:
            cached = self.cache[addr_upper]
            apn = cached.get('apn', '')

            # Always re-lookup if APN is blank or null
            if not apn or apn.upper() in ['NONE', 'NULL', 'NA', 'N/A', '']:
                return None  # Force re-lookup

            # Return cached APN
            return (
                apn,
                cached.get('method', 'cached'),
                cached.get('confidence', 1.0),
                "FROM_CACHE"
            )

        return None

    def put(self, address: str, apn: Optional[str], method: str, confidence: float):
        """Store APN in cache."""
        addr_upper = address.upper().strip()
        now = datetime.datetime.now().isoformat()

        if apn:
            # Successful lookup
            self.cache[addr_upper] = {
                'apn': apn,
                'method': method,
                'confidence': confidence,
                'last_updated': now
            }
            # Remove from failed if it was there
            self.failed.pop(addr_upper, None)
        else:
            # Failed lookup
            if addr_upper in self.failed:
                self.failed[addr_upper]['attempts'] += 1
                self.failed[addr_upper]['last_attempt'] = now
            else:
                self.failed[addr_upper] = {
                    'attempts': 1,
                    'last_attempt': now
                }

def find_latest_upload() -> Optional[Path]:
    """Pick the most recently modified M.YY_APN_Upload file in APN/Upload directory."""
    candidates = []

    # Look in APN/Upload directory for new pattern
    upload_dir = Path("APN/Upload")
    if not upload_dir.exists():
        upload_dir = Path("Upload")  # If running from within APN directory

    if upload_dir.exists():
        # Match both old and new naming patterns
        # New pattern: M.YY_APN_Upload_*.xlsx or M.YY_APN_Upload *.xlsx
        candidates.extend(upload_dir.glob("[1-9].[0-9][0-9]_APN_Upload*.xlsx"))
        candidates.extend(upload_dir.glob("1[0-2].[0-9][0-9]_APN_Upload*.xlsx"))
        # Old pattern: M.YY_APN_Upload *.xlsx (with space)
        candidates.extend(upload_dir.glob("[1-9].[0-9][0-9]_APN_Upload *.xlsx"))
        candidates.extend(upload_dir.glob("1[0-2].[0-9][0-9]_APN_Upload *.xlsx"))

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

def normalize_address(s: str) -> Dict[str, Optional[str]]:
    """
    Normalize a free-form address string and try to extract components.
    Returns dict with keys: number, predir, name, stype, city, raw.
    On failure to parse, many fields may be None. The algorithm will fall back to geocode.
    """
    raw = s.strip()

    # FIX: Remove .0 suffix from ZIP codes (e.g., "85379.0" -> "85379")
    # This handles legacy data where ZIP was stored as float
    raw = re.sub(r',\s*(\d{5})\.0\s*$', r', \1', raw)

    up = UNIT_RE.sub("", raw.upper()).strip()
    up = re.sub(r"\s+", " ", up)

    # attempt usaddress first
    if HAS_USADDRESS:
        try:
            tagged, _ = usaddress.tag(up)
            number = tagged.get("AddressNumber")
            predir = tagged.get("StreetNamePreDirectional")
            name = tagged.get("StreetName")
            stype = tagged.get("StreetNamePostType")
            city = tagged.get("PlaceName")
            if stype:
                stype = TYPE_MAP.get(stype.upper(), stype.upper())
            if predir:
                predir = DIR_MAP.get(predir.upper(), predir.upper())
            return {
                "number": number,
                "predir": predir,
                "name": name.upper() if name else None,
                "stype": TYPE_MAP.get(stype.upper(), stype.upper()) if stype else None,
                "city": city.upper() if city else None,
                "raw": raw,
            }
        except Exception:
            pass

    # regex fallback (works for "19829 N 27TH AVE PHOENIX AZ 85027")
    m = NUM_NAME_TYPE_CITY_RE.match(up)
    number = predir = name = stype = city = None
    if m:
        number, predir, name, stype, tail = m.groups()
        stype = TYPE_MAP.get(stype.upper().replace(".", ""), stype.upper().replace(".", ""))
        if predir:
            predir = DIR_MAP.get(predir.upper(), predir.upper())
        # infer city from tail (strip state/zip if present)
        # split on commas or spaces; drop AZ/ZIP
        tail = tail.replace(",", " ")
        parts = [t for t in tail.split() if t]
        # remove 2-letter state if present and ZIP
        parts = [p for p in parts if not ZIP_RE.match(p) and p not in {"AZ", "ARIZONA"}]
        if parts:
            city = parts[0].upper()

    return {
        "number": number,
        "predir": predir,
        "name": name.upper() if name else None,
        "stype": stype.upper() if isinstance(stype, str) else None,
        "city": city.upper() if city else None,
        "raw": raw,
    }

def _get_json(url: str, params: Dict[str, str], rps: float, max_retries: int) -> Dict:
    """GET JSON with basic retries on network errors and non-JSON responses."""
    tries = 0
    while True:
        tries += 1
        _sleep_for_rate(rps)
        try:
            resp = SESSION.get(url, params=params, timeout=TIMEOUT)
            if resp.status_code >= 500:
                raise requests.RequestException(f"server {resp.status_code}")
            data = resp.json()
            # ArcGIS sometimes returns {"error":{...}}
            if isinstance(data, dict) and "error" in data:
                raise requests.RequestException(str(data["error"]))
            return data
        except Exception as e:
            if tries >= max_retries:
                raise
            # exponential backoff up to ~8s
            time.sleep(min(2 ** tries, 8) + random.uniform(0, 0.25))

def build_where(components: Dict[str, Optional[str]], loose: bool = False) -> Optional[str]:
    """
    Build SQL where for Parcels query. If essential parts are missing, return None.
    Fields used: PHYSICAL_STREET_NUM, PHYSICAL_STREET_NAME, PHYSICAL_STREET_TYPE (optional), PHYSICAL_CITY
    """
    num = components.get("number")
    name = components.get("name")
    city = components.get("city")
    stype = components.get("stype")

    if not (num and name and city):
        return None

    # Name should not include quotes; escape single quotes
    def esc(x: str) -> str:
        return x.replace("'", "''")

    where = f"PHYSICAL_STREET_NUM='{esc(num)}' AND PHYSICAL_STREET_NAME='{esc(name)}' AND PHYSICAL_CITY='{esc(city)}'"
    if not loose and stype:
        where += f" AND PHYSICAL_STREET_TYPE='{esc(stype)}'"
    return where

def query_parcels(where: str, rps: float, max_retries: int) -> List[Dict]:
    params = {
        "f": "json",
        "where": where,
        "outFields": "APN,APN_DASH,PHYSICAL_ADDRESS,PHYSICAL_STREET_NUM,PHYSICAL_STREET_NAME,PHYSICAL_STREET_TYPE,PHYSICAL_CITY",
        "returnGeometry": "false",
    }
    data = _get_json(PARCEL_QUERY, params, rps, max_retries)
    return data.get("features", []) if isinstance(data, dict) else []

def geocode(address: str, rps: float, max_retries: int) -> Optional[Tuple[float, float]]:
    params = {
        "f": "json",
        "SingleLine": address,
        "outFields": "Match_addr,Addr_type,Score",
        "maxLocations": 5,
    }
    data = _get_json(GEOCODER_URL, params, rps, max_retries)
    candidates = data.get("candidates", []) if isinstance(data, dict) else []
    if not candidates:
        return None
    # choose highest score
    best = max(candidates, key=lambda c: c.get("score", 0))
    loc = best.get("location", {})
    x, y = loc.get("x"), loc.get("y")
    if x is None or y is None:
        return None
    return float(x), float(y)

def identify(x: float, y: float, rps: float, max_retries: int) -> Optional[Dict]:
    params = {
        "f": "json",
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "tolerance": 1,
        "mapExtent": f"{x-0.0001},{y-0.0001},{x+0.0001},{y+0.0001}",
        "imageDisplay": "400,400,96",
        "sr": 3857,
        "layers": "all:0",
        "returnGeometry": "false",
    }
    data = _get_json(PARCEL_IDENT, params, rps, max_retries)
    res = data.get("results", []) if isinstance(data, dict) else []
    if not res:
        return None
    # result attributes should contain APN/APN_DASH
    return res[0].get("attributes")

def choose_feature(features: List[Dict], norm_addr: str) -> Tuple[Optional[str], str]:
    """Pick an APN from features; prefer exact PHYSICAL_ADDRESS match (after simple normalization)."""
    if not features:
        return None, "NO_FEATURES"
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.upper().strip())
    # Prefer exact PHYSICAL_ADDRESS match
    for f in features:
        attrs = f.get("attributes", {})
        if norm(attrs.get("PHYSICAL_ADDRESS", "") or "") == norm(norm_addr):
            apn = attrs.get("APN_DASH") or attrs.get("APN")
            if apn:
                return str(apn), "EXACT_ADDRESS"
    # else take the first
    attrs = features[0].get("attributes", {})
    apn = attrs.get("APN_DASH") or attrs.get("APN")
    return (str(apn) if apn else None), "FIRST_FEATURE"

def should_skip_address(address: str) -> bool:
    """Pre-filter addresses that definitely won't have APNs."""
    addr_upper = address.upper().strip()

    # Skip PO Boxes
    if re.search(r'\bP\.?O\.?\s*BOX\b', addr_upper):
        return True

    # Skip addresses without numbers
    if not re.search(r'^\d+', addr_upper):
        return True

    # Skip obviously incomplete addresses
    if len(addr_upper) < 10:
        return True

    return False

def lookup_one(address: str, rps: float, max_retries: int, cache: APNCache, debug: bool = False) -> Tuple[Optional[str], str, float, str]:
    """
    Returns (apn, method, confidence, notes)
    method ∈ {exact_where, loose_where, geocode_identify, not_found, cached, skipped}
    """
    if debug:
        print(f"\n{'='*80}", flush=True)
        print(f"LOOKUP: {address}", flush=True)

    # Check if should skip
    if should_skip_address(address):
        if debug:
            print(f"  SKIPPED: PO Box or invalid format", flush=True)
        return None, "skipped", 0.0, "PRE_FILTERED"

    # Check cache first
    cached_result = cache.get(address)
    if cached_result and cached_result[0]:  # Has valid APN
        if debug:
            print(f"  CACHED: {cached_result[0]} (method={cached_result[1]}, conf={cached_result[2]})", flush=True)
        return cached_result

    # Perform actual lookup
    start = time.time()
    notes = []
    comps = normalize_address(address)

    if debug:
        print(f"  PARSED: {comps}", flush=True)

    if not comps or not comps.get("number"):
        if debug:
            print(f"  PARSE FAILED: Could not extract address components", flush=True)
        return None, "parse_failed", 0.0, "PARSE_FAILED"

    where = build_where(comps, loose=False)

    apn = None
    method = "not_found"
    confidence = 0.0

    # Try exact WHERE
    if debug:
        print(f"  Trying exact WHERE query...", flush=True)
        print(f"    WHERE: {where}", flush=True)

    if where:
        feats = query_parcels(where, rps, max_retries)
        if debug:
            print(f"    Results: {len(feats) if feats else 0} parcels", flush=True)

        if feats:
            apn, picked = choose_feature(feats, comps.get("raw", address))
            if apn:
                method = "exact_where"
                confidence = 1.0
                if len(feats) > 1:
                    notes.append(f"MULTI_APN_CANDIDATES={len(feats)} pick={picked}")
                if debug:
                    print(f"  ✓ SUCCESS (exact): {apn}", flush=True)
            elif debug:
                print(f"    No valid APN in results", flush=True)

    # loose WHERE (drop street type)
    if not apn:
        if debug:
            print(f"  Trying loose WHERE query (no street type)...", flush=True)
        where_loose = build_where(comps, loose=True)
        if debug:
            print(f"    WHERE: {where_loose}", flush=True)

        if where_loose:
            feats = query_parcels(where_loose, rps, max_retries)
            if debug:
                print(f"    Results: {len(feats) if feats else 0} parcels", flush=True)

            if feats:
                apn, picked = choose_feature(feats, comps.get("raw", address))
                if apn:
                    method = "loose_where"
                    confidence = 0.85
                    if len(feats) > 1:
                        notes.append(f"MULTI_APN_CANDIDATES={len(feats)} pick={picked}")
                    if debug:
                        print(f"  ✓ SUCCESS (loose): {apn}", flush=True)
                elif debug:
                    print(f"    No valid APN in results", flush=True)

    # geocode → identify
    if not apn:
        if debug:
            print(f"  Trying geocode + identify...", flush=True)
        xy = geocode(address, rps, max_retries)
        if debug:
            print(f"    Geocoded: {xy if xy else 'FAILED'}", flush=True)

        if xy:
            attrs = identify(xy[0], xy[1], rps, max_retries)
            if debug:
                print(f"    Identified: {attrs if attrs else 'No parcel found'}", flush=True)

            if attrs:
                apn = attrs.get("APN_DASH") or attrs.get("APN")
                if apn:
                    apn = str(apn)
                    method = "geocode_identify"
                    confidence = 0.75
                    if debug:
                        print(f"  ✓ SUCCESS (geocode): {apn}", flush=True)

    # All methods failed
    if not apn and debug:
        print(f"  ✗ FAILED: All methods exhausted", flush=True)

    elapsed = int((time.time() - start) * 1000)
    notes_str = f"{'; '.join(notes)} | {elapsed}ms" if notes else f"{elapsed}ms"

    # Store in cache
    cache.put(address, apn, method, confidence)

    return apn, method, confidence, notes_str

def process_file(
    input_path: Path,
    sheet: Optional[str],
    output_path: Path,
    rps: float,
    max_retries: int,
    city_whitelist: Optional[List[str]] = None,
    debug: bool = False,
) -> Path:
    df = pd.read_excel(input_path, sheet_name=sheet if sheet is not None else 0, engine="openpyxl")

    # Initialize cache
    cache = APNCache()

    print(f"📁 Processing: {input_path.name}", flush=True)
    print(f"📊 Cache status: {len(cache.cache)} APNs cached, {len(cache.failed)} known failures", flush=True)
    print(f"⚡ Rate limit: {rps:.1f} requests/second", flush=True)
    print("-" * 60, flush=True)

    # Find address column (prefer header FULL_ADDRESS, case-insensitive); else first column
    addr_col = None
    for c in df.columns:
        if isinstance(c, str) and (c.strip().upper() == "FULL_ADDRESS" or c.strip().upper() == "FULL ADDRESS"):
            addr_col = c
            break
    if addr_col is None:
        addr_col = df.columns[0]

    # Initialize output columns
    apn_list, method_list, conf_list, notes_list = [], [], [], []

    whitelist = [w.strip().upper() for w in city_whitelist] if city_whitelist else None

    # Count statistics
    total_records = len(df)
    cache_hits = 0
    new_lookups = 0
    skipped = 0

    # Calculate time estimates
    start_time = time.time()

    for idx, val in enumerate(df[addr_col].astype(str).fillna("").tolist()):
        addr = val.strip()

        # Enhanced progress indicator every 50 records
        if idx % 50 == 0 and idx > 0:
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            remaining = (total_records - idx) / rate if rate > 0 else 0
            cache_rate = (cache_hits * 100 // idx) if idx > 0 else 0

            print(f"Progress: {idx}/{total_records} ({idx*100//total_records}%) | "
                  f"Cache hits: {cache_hits} ({cache_rate}%) | "
                  f"New lookups: {new_lookups} | "
                  f"Rate: {rate:.1f} rec/sec | "
                  f"ETA: {remaining/60:.1f} min", flush=True)

        if not addr:
            apn_list.append(None); method_list.append("not_found"); conf_list.append(0.0); notes_list.append("EMPTY_ADDRESS")
            continue

        if whitelist and not any(w in addr.upper() for w in whitelist):
            apn_list.append(None); method_list.append("skipped_non_maricopa"); conf_list.append(0.0); notes_list.append("CITY_FILTER")
            skipped += 1
            if debug:
                print(f"[{idx}] SKIP (city filter): {addr}")
            continue

        try:
            apn, method, conf, notes = lookup_one(addr, rps, max_retries, cache, debug)
            apn_list.append(apn)
            method_list.append(method)
            conf_list.append(conf)
            notes_list.append(notes)

            # Track statistics
            if "FROM_CACHE" in notes:
                cache_hits += 1
            elif method != "skipped":
                new_lookups += 1
            else:
                skipped += 1

            if debug:
                print(f"[{idx}] {method:17s} conf={conf:.2f} apn={apn} :: {addr}")
        except Exception as e:
            apn_list.append(None); method_list.append("error"); conf_list.append(0.0); notes_list.append(str(e))
            if debug:
                print(f"[{idx}] ERROR :: {addr} :: {e}")

    # Save cache after processing
    cache.save_cache()

    # Insert APN as column C (index 2). If DF has fewer than 2 columns, pad with empty columns.
    df_out = df.copy()
    insert_pos = 2 if df_out.shape[1] >= 2 else df_out.shape[1]
    df_out.insert(insert_pos, "APN", apn_list)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False)

    # Print final statistics
    elapsed_total = time.time() - start_time
    print(f"\n📊 Processing Complete:")
    print(f"   Total records: {total_records}")
    print(f"   Cache hits: {cache_hits} ({cache_hits*100//max(total_records, 1)}%)")
    print(f"   New lookups: {new_lookups} ({new_lookups*100//max(total_records, 1)}%)")
    print(f"   Skipped: {skipped} ({skipped*100//max(total_records, 1)}%)")
    print(f"   Total time: {elapsed_total/60:.1f} minutes")
    print(f"   Average rate: {total_records/elapsed_total:.1f} records/second")
    print(f"✅ Output saved: {output_path}")

    return output_path

def main() -> None:
    p = argparse.ArgumentParser(description="Maricopa APN lookup from Excel with caching")
    p.add_argument("-i", "--input", type=str, help="Path to input .xlsx (default: latest M.YY_APN_Upload file from APN/Upload/)")
    p.add_argument("-s", "--sheet", type=str, help="Sheet name/index (default: first)")
    p.add_argument("-o", "--output", type=str, help="Output .xlsx (default: M.YY_APN_Complete M.DD.HH-MM-SS.xlsx in APN/Complete/)")
    p.add_argument("--rate", type=float, default=5.0, help="Requests per second cap (default 5.0)")
    p.add_argument("--max-retries", type=int, default=3, help="Max HTTP retries per request (default 3)")
    p.add_argument("--city-whitelist", type=str, help="Comma list of city tokens; only process rows containing one")
    p.add_argument("--debug", action="store_true", help="Verbose progress logs")
    p.add_argument("--no-cache", action="store_true", help="Disable cache (force all lookups)")
    args = p.parse_args()

    if args.input:
        input_path = Path(args.input)
    else:
        latest = find_latest_upload()
        if not latest:
            print("ERROR: No input specified and no M.YY_APN_Upload files found in APN/Upload/", file=sys.stderr)
            sys.exit(1)
        input_path = latest

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # sheet can be name or index
    sheet = None
    if args.sheet is not None:
        try:
            sheet = int(args.sheet)
        except ValueError:
            sheet = args.sheet

    # Generate output path with new naming convention
    if args.output:
        output_path = Path(args.output)
    else:
        # Use standard timestamp from utils
        timestamp = get_standard_timestamp()

        # Extract M.YY prefix from input filename using utils
        input_name = input_path.stem
        extracted_timestamp = extract_timestamp_from_filename(input_name)

        if "_APN_Upload" in input_name:
            month_year = input_name.split("_APN_Upload")[0]
        else:
            month_year = "1.25"  # Default if pattern not found

        # If input file had timestamp, use it for consistency
        if extracted_timestamp:
            timestamp = extracted_timestamp

        # Create output path in APN/Complete directory
        complete_dir = Path("APN/Complete")
        complete_dir.mkdir(parents=True, exist_ok=True)

        # Use new naming convention with underscore (not space)
        new_filename = format_output_filename(month_year, "APN_Complete", timestamp)
        legacy_filename = get_legacy_filename(month_year, "APN_Complete", timestamp)

        output_path = complete_dir / new_filename
        legacy_path = complete_dir / legacy_filename

    whitelist = [s for s in args.city_whitelist.split(",")] if args.city_whitelist else None

    out = process_file(
        input_path=input_path,
        sheet=sheet,
        output_path=output_path,
        rps=max(0.1, float(args.rate)),
        max_retries=max(1, int(args.max_retries)),
        city_whitelist=whitelist,
        debug=bool(args.debug),
    )
    print(f"Wrote: {out}")

    # Create legacy copy if not using custom output path
    if not args.output:
        save_excel_with_legacy_copy(output_path, legacy_path)
        print(f"Legacy copy: {legacy_path}")

if __name__ == "__main__":
    main()
    