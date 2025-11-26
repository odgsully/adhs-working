"""Name matching between Ecorp records and Batchdata API results.

This module calculates ECORP_TO_BATCH_MATCH_% and populates MISSING_1-8_FULL_NAME
columns by comparing names from Ecorp_Complete against names returned by the
Batchdata skip-trace API.
"""

from typing import List, Tuple
import pandas as pd
from rapidfuzz import fuzz


def fuzzy_name_match(name1: str, name2: str, threshold: float = 85.0) -> bool:
    """Check if two names match using token_sort_ratio (handles name order).

    Args:
        name1: First name to compare
        name2: Second name to compare
        threshold: Minimum similarity score (0-100) to consider a match

    Returns:
        True if names match at or above threshold, False otherwise
    """
    if not name1 or not name2:
        return False
    score = fuzz.token_sort_ratio(name1.upper().strip(), name2.upper().strip())
    return score >= threshold


def extract_ecorp_names_from_complete(ecorp_row: pd.Series) -> List[str]:
    """Extract ALL 22 principal names from Ecorp_Complete row.

    Sources (22 fields total):
    - StatutoryAgent1-3_Name (3)
    - Manager1-5_Name (5)
    - Member1-5_Name (5)
    - Manager/Member1-5_Name (5)
    - IndividualName1-4 (4)

    Args:
        ecorp_row: A row from Ecorp_Complete DataFrame

    Returns:
        List of unique names (preserving original case, deduplicated by uppercase)
    """
    names = []
    seen = set()

    # Statutory Agents (3)
    for i in range(1, 4):
        name = ecorp_row.get(f'StatutoryAgent{i}_Name', '')
        if name and str(name).strip() and str(name).strip().upper() not in seen:
            names.append(str(name).strip())
            seen.add(str(name).strip().upper())

    # Managers (5)
    for i in range(1, 6):
        name = ecorp_row.get(f'Manager{i}_Name', '')
        if name and str(name).strip() and str(name).strip().upper() not in seen:
            names.append(str(name).strip())
            seen.add(str(name).strip().upper())

    # Members (5)
    for i in range(1, 6):
        name = ecorp_row.get(f'Member{i}_Name', '')
        if name and str(name).strip() and str(name).strip().upper() not in seen:
            names.append(str(name).strip())
            seen.add(str(name).strip().upper())

    # Manager/Members (5)
    for i in range(1, 6):
        name = ecorp_row.get(f'Manager/Member{i}_Name', '')
        if name and str(name).strip() and str(name).strip().upper() not in seen:
            names.append(str(name).strip())
            seen.add(str(name).strip().upper())

    # Individual Names (4)
    for i in range(1, 5):
        name = ecorp_row.get(f'IndividualName{i}', '')
        if name and str(name).strip() and str(name).strip().upper() not in seen:
            names.append(str(name).strip())
            seen.add(str(name).strip().upper())

    return names


def extract_batch_names(row: pd.Series) -> List[str]:
    """Extract all person names from Batchdata API response columns.

    Extracts names from:
    - BD_PHONE_1-10_FIRST + BD_PHONE_1-10_LAST (10 phone name pairs)
    - BD_EMAIL_1-10_FIRST + BD_EMAIL_1-10_LAST (10 email name pairs)

    Args:
        row: A row from Batchdata Complete DataFrame

    Returns:
        List of unique full names (FIRST + LAST concatenated)
    """
    names = set()

    # Phone names (BD_PHONE_1-10_FIRST + BD_PHONE_1-10_LAST)
    for i in range(1, 11):
        first = str(row.get(f'BD_PHONE_{i}_FIRST', '') or '').strip()
        last = str(row.get(f'BD_PHONE_{i}_LAST', '') or '').strip()
        if first or last:
            full_name = f"{first} {last}".strip()
            if full_name:
                names.add(full_name)

    # Email names (BD_EMAIL_1-10_FIRST + BD_EMAIL_1-10_LAST)
    for i in range(1, 11):
        first = str(row.get(f'BD_EMAIL_{i}_FIRST', '') or '').strip()
        last = str(row.get(f'BD_EMAIL_{i}_LAST', '') or '').strip()
        if first or last:
            full_name = f"{first} {last}".strip()
            if full_name:
                names.add(full_name)

    return list(names)


def calculate_match_percentage(
    ecorp_names: List[str],
    batch_names: List[str],
    threshold: float = 85.0
) -> Tuple[str, List[str]]:
    """Calculate percentage of Ecorp names matched in Batchdata.

    Formula: (Ecorp names matched at 85%+ confidence) / (Total Ecorp names) × 100

    Args:
        ecorp_names: List of names from Ecorp_Complete record
        batch_names: List of names from Batchdata API response
        threshold: Fuzzy match threshold (default 85%)

    Returns:
        Tuple of (match_percentage_string, list_of_missing_names)
        - "0"-"100": Percentage of Ecorp names found in Batchdata
        - "100+": ALL Ecorp names matched AND Batchdata returned additional names
        - Missing names: Ecorp names not found (empty when 100 or 100+)
    """
    if not ecorp_names:
        return "100", []

    matched = set()
    missing = []
    ecorp_names_normalized = [n.upper().strip() for n in ecorp_names]

    for i, ecorp_name in enumerate(ecorp_names_normalized):
        found = False
        for batch_name in batch_names:
            if fuzzy_name_match(ecorp_name, batch_name, threshold):
                matched.add(ecorp_name)
                found = True
                break
        if not found:
            # Store original (non-normalized) name for MISSING columns
            missing.append(ecorp_names[i])

    match_count = len(matched)
    total = len(ecorp_names_normalized)
    pct = (match_count / total) * 100

    # 100+: ALL Ecorp names matched AND Batchdata has MORE names
    # When 100+, MISSING columns stay EMPTY (nothing missing from Ecorp)
    if match_count == total and len(batch_names) > total:
        return "100+", []

    # 100: ALL matched, no extras from Batchdata
    if match_count == total:
        return "100", []

    # <100: Some Ecorp names not found, store in MISSING (up to 8)
    return str(int(round(pct))), missing[:8]


def apply_name_matching(
    batchdata_df: pd.DataFrame,
    ecorp_complete_df: pd.DataFrame = None
) -> pd.DataFrame:
    """Add ECORP_TO_BATCH_MATCH_% and MISSING_1-8_FULL_NAME columns.

    Compares names from Ecorp_Complete against names returned by Batchdata API
    to calculate match percentage and identify missing names.

    Args:
        batchdata_df: Batchdata Complete DataFrame (after API enrichment).
                      Should have ECORP passthrough columns (FULL_ADDRESS, BD_OWNER_NAME_FULL, etc.)
        ecorp_complete_df: Original Ecorp_Complete DataFrame (has all 22 principal name fields).
                          If None, uses BD_OWNER_NAME_FULL from passthrough as fallback.

    Returns:
        DataFrame with 9 new columns added:
        - ECORP_TO_BATCH_MATCH_%
        - MISSING_1_FULL_NAME through MISSING_8_FULL_NAME

    Join Key: ECORP_ENTITY_ID_S (Ecorp) ↔ BD_SOURCE_ENTITY_ID (BatchData)

    Note: ecorp_complete_df is REQUIRED for proper name matching.
          If not provided or lookup fails, match is set to "N/A".
          BD_OWNER_NAME_FULL fallback has been removed.
    """
    df = batchdata_df.copy()

    # Initialize columns
    df['ECORP_TO_BATCH_MATCH_%'] = ''
    for i in range(1, 9):
        df[f'MISSING_{i}_FULL_NAME'] = ''

    # Create lookup dict from Ecorp_Complete by ECORP_ENTITY_ID_S (unique key)
    # NOTE: Changed from FULL_ADDRESS to avoid collision when multiple entities share same address
    ecorp_lookup = {}
    if ecorp_complete_df is not None:
        for _, ecorp_row in ecorp_complete_df.iterrows():
            entity_id = str(ecorp_row.get('ECORP_ENTITY_ID_S', '')).strip()
            if entity_id:
                ecorp_lookup[entity_id] = ecorp_row

    for idx, row in df.iterrows():
        ecorp_names = []

        if ecorp_lookup:
            # Get matching Ecorp_Complete row using BD_SOURCE_ENTITY_ID
            entity_id = str(row.get('BD_SOURCE_ENTITY_ID', '')).strip()
            ecorp_row = ecorp_lookup.get(entity_id)

            if ecorp_row is not None:
                ecorp_names = extract_ecorp_names_from_complete(ecorp_row)

        # No fallback - if lookup fails, set to "N/A"
        if not ecorp_names:
            df.at[idx, 'ECORP_TO_BATCH_MATCH_%'] = 'N/A'
            continue  # Skip to next row

        batch_names = extract_batch_names(row)
        pct, missing = calculate_match_percentage(ecorp_names, batch_names)

        df.at[idx, 'ECORP_TO_BATCH_MATCH_%'] = pct
        for i, name in enumerate(missing[:8], 1):
            df.at[idx, f'MISSING_{i}_FULL_NAME'] = name

    return df
