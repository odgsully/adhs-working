# Batchdata Template Update Plan

Update script logic and documentation to match the updated `Batchdata_Template.xlsx` (173 columns).

## Summary of Changes

| Change | Status | Description |
|--------|--------|-------------|
| Remove BD_TITLE_ROLE | Template done, script needed | Remove from output generation |
| Add ECORP_TO_BATCH_MATCH_% | Template done, script needed | Calculate name matching percentage |
| Add MISSING_1-8_FULL_NAME | Template done, script needed | Store unmatched Ecorp names |
| Update documentation | Needed | Update Batchdata_template_fields_desc.md |

---

## CRITICAL: Ecorp Name Fields Not in Template

**Problem**: The Batchdata_Template.xlsx does NOT include the 22 Ecorp principal name fields (StatutoryAgent1-3_Name, Manager1-5_Name, etc.). These fields are in Ecorp_Complete but not passed through to Batchdata.

**Solution Options**:

1. **Option A - Pass Ecorp_Complete reference through pipeline** (Recommended)
   - Store original Ecorp_Complete DataFrame or file path during processing
   - Join back to get name fields when calculating match percentage
   - No template changes needed

2. **Option B - Add Ecorp name fields to template passthrough**
   - Add 22 new columns to template (StatutoryAgent1-3_Name, Manager1-5_Name, etc.)
   - Requires template update + documentation
   - Adds complexity to template (would be 195 columns)

**Decision**: Use Option A - join back to Ecorp_Complete during processing.

**Implementation**:
- `batchdata_bridge.py:run_batchdata_enrichment()` already loads `ecorp_file`
- Pass Ecorp_Complete DataFrame to name matching function
- Join on `FULL_ADDRESS` + `ECORP_INDEX_#` to match records

---

## Phase 1: Create Name Matching Module

### Create `Batchdata/src/name_matching.py`

```python
"""Name matching between Ecorp records and Batchdata API results."""

from typing import List, Tuple, Dict, Any
import pandas as pd
from rapidfuzz import fuzz

def fuzzy_name_match(name1: str, name2: str, threshold: float = 85.0) -> bool:
    """Check if two names match using token_sort_ratio (handles name order)."""
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
    """Extract all person names from Batchdata API response columns."""
    names = set()
    # Phone names (BD_PHONE_1-10_FIRST + BD_PHONE_1-10_LAST)
    for i in range(1, 11):
        first = str(row.get(f'BD_PHONE_{i}_FIRST', '') or '').strip()
        last = str(row.get(f'BD_PHONE_{i}_LAST', '') or '').strip()
        if first or last:
            names.add(f"{first} {last}".strip())
    # Email names (BD_EMAIL_1-10_FIRST + BD_EMAIL_1-10_LAST)
    for i in range(1, 11):
        first = str(row.get(f'BD_EMAIL_{i}_FIRST', '') or '').strip()
        last = str(row.get(f'BD_EMAIL_{i}_LAST', '') or '').strip()
        if first or last:
            names.add(f"{first} {last}".strip())
    return [n for n in names if n]

def calculate_match_percentage(
    ecorp_names: List[str],
    batch_names: List[str],
    threshold: float = 85.0
) -> Tuple[str, List[str]]:
    """Calculate percentage of Ecorp names matched in Batchdata.

    Formula: (Ecorp names matched at 85%+ confidence) / (Total Ecorp names) × 100

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

    for ecorp_name in ecorp_names_normalized:
        found = False
        for batch_name in batch_names:
            if fuzzy_name_match(ecorp_name, batch_name, threshold):
                matched.add(ecorp_name)
                found = True
                break
        if not found:
            # Store original (non-normalized) name for MISSING columns
            idx = ecorp_names_normalized.index(ecorp_name)
            missing.append(ecorp_names[idx])

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
    ecorp_complete_df: pd.DataFrame
) -> pd.DataFrame:
    """Add ECORP_TO_BATCH_MATCH_% and MISSING_1-8_FULL_NAME columns.

    Args:
        batchdata_df: Batchdata Complete DataFrame (after API enrichment)
        ecorp_complete_df: Original Ecorp_Complete DataFrame (has name fields)

    Join Key: FULL_ADDRESS + ECORP_INDEX_# (both present in Batchdata passthrough)
    """
    df = batchdata_df.copy()

    # Initialize columns
    df['ECORP_TO_BATCH_MATCH_%'] = ''
    for i in range(1, 9):
        df[f'MISSING_{i}_FULL_NAME'] = ''

    # Create lookup dict from Ecorp_Complete by FULL_ADDRESS
    ecorp_lookup = {}
    for idx, ecorp_row in ecorp_complete_df.iterrows():
        addr = str(ecorp_row.get('FULL_ADDRESS', '')).strip().upper()
        if addr:
            ecorp_lookup[addr] = ecorp_row

    for idx, row in df.iterrows():
        # Get matching Ecorp_Complete row
        addr = str(row.get('FULL_ADDRESS', '')).strip().upper()
        ecorp_row = ecorp_lookup.get(addr)

        if ecorp_row is not None:
            ecorp_names = extract_ecorp_names_from_complete(ecorp_row)
        else:
            # Fallback: use BD_OWNER_NAME_FULL from current row
            owner = str(row.get('BD_OWNER_NAME_FULL', '')).strip()
            ecorp_names = [owner] if owner else []

        batch_names = extract_batch_names(row)
        pct, missing = calculate_match_percentage(ecorp_names, batch_names)

        df.at[idx, 'ECORP_TO_BATCH_MATCH_%'] = pct
        for i, name in enumerate(missing[:8], 1):
            df.at[idx, f'MISSING_{i}_FULL_NAME'] = name

    return df
```

---

## Phase 2: Remove BD_TITLE_ROLE from Output

### File: `Batchdata/src/transform.py`

**Change 1** - Remove from record generation (~line 273):
```python
# REMOVE this line:
'BD_TITLE_ROLE': extract_title_role(title),
```

**Change 2** - Remove from entity fallback (~line 355):
```python
# REMOVE this line:
'BD_TITLE_ROLE': title_role,
```

**Change 3** - Remove import (~line 23-31):
```python
# Remove extract_title_role from imports
from .normalize import (
    split_full_name, normalize_state, clean_address_line,
    normalize_zip_code, normalize_phone_e164
    # REMOVED: extract_title_role
)
```

### File: `Batchdata/src/normalize.py`

**Add deprecation warning** to `extract_title_role()` (~line 186):
```python
import warnings

def extract_title_role(title: str) -> str:
    """[DEPRECATED] - BD_TITLE_ROLE removed from template."""
    warnings.warn(
        "extract_title_role() is deprecated",
        DeprecationWarning,
        stacklevel=2
    )
    # ... keep existing code for backward compat
```

---

## Phase 3: Integrate Name Matching into Pipeline

### File: `src/adhs_etl/batchdata_bridge.py`

The integration happens in `run_batchdata_enrichment()` which already has access to `ecorp_file`:

```python
def run_batchdata_enrichment(
    upload_path: str,
    month: str,
    ecorp_file: str = None,  # Already exists as parameter
    stage_config: Dict[str, bool] = None,
    ...
) -> str:
    # ... existing code ...

    # Load Ecorp_Complete for name matching
    if ecorp_file and Path(ecorp_file).exists():
        ecorp_complete_df = pd.read_excel(ecorp_file)
    else:
        ecorp_complete_df = None

    # After API enrichment, before saving:
    if ecorp_complete_df is not None:
        from Batchdata.src.name_matching import apply_name_matching
        logger.info("Computing Ecorp-to-Batchdata name matching...")
        result_df = apply_name_matching(result_df, ecorp_complete_df)
```

### Alternative: File `Batchdata/src/batchdata_sync.py`

If processing happens in sync client, modify `run_enrichment_pipeline()` to accept ecorp_df:

```python
def run_enrichment_pipeline(
    self,
    input_df: pd.DataFrame,
    stage_config: Dict[str, bool],
    ecorp_complete_df: pd.DataFrame = None,  # NEW parameter
    batch_size: int = 50
) -> pd.DataFrame:
    # ... existing stages ...

    # Stage 5: Name matching (after all API stages)
    if ecorp_complete_df is not None:
        from .name_matching import apply_name_matching
        logger.info("Computing Ecorp-to-Batchdata name matching...")
        current_df = apply_name_matching(current_df, ecorp_complete_df)

    return current_df
```

---

## Phase 4: Update Documentation

### File: `Batchdata/Batchdata_template_fields_desc.md`

**Changes needed:**
1. Line 3: Change "165 columns" to "173 columns"
2. Lines 99-104: Update column counts in section table
3. Lines 341-348: REMOVE BD_TITLE_ROLE section (column 22)
4. Renumber columns 23-37 to 22-36 throughout
5. Add new Section 6 after Metadata:

```markdown
## Section 6: Name Matching Columns (165-173)

### Column 165: ECORP_TO_BATCH_MATCH_%

**Where it comes from**: Calculated by `name_matching.py:calculate_match_percentage()`.

**What it contains**: Percentage of Ecorp names found in Batchdata results (85% fuzzy threshold).

**Values**:
- `0` to `100` - Percentage of Ecorp names matched
- `100+` - All Ecorp names matched AND Batchdata returned additional names

### Columns 166-173: MISSING_1-8_FULL_NAME

**Where it comes from**: Populated by `name_matching.py:apply_name_matching()`.

**What it contains**: Ecorp names NOT found in Batchdata results.

**When populated**: Whenever ECORP_TO_BATCH_MATCH_% < 100
```

---

## Phase 5: Update Tests

### Files to update (remove BD_TITLE_ROLE references):
- `Batchdata/tests/test_ecorp_alignment.py` - line ~175
- `Batchdata/tests/test_entity_families.py` - lines ~98, 111, 124, 137
- `Batchdata/tests/test_sync_client.py` - line ~45
- `Batchdata/tests/test_deduplication.py` - lines ~31, 44, 57

### New test file: `Batchdata/tests/test_name_matching.py`

Test cases:
- Empty Ecorp names → 100%
- Empty Batchdata names → 0%, all names missing
- Exact match → 100%
- Fuzzy match (85%+) → 100%
- Partial match → correct percentage
- >8 missing → only first 8 stored
- Case insensitive matching
- Name order invariant ("JOHN SMITH" = "SMITH JOHN")

---

## Implementation Order

1. **Phase 1**: Create `name_matching.py` + tests (additive, no risk)
2. **Phase 4**: Update documentation (defines expected output)
3. **Phase 3**: Integrate into pipeline (connects new module)
4. **Phase 2**: Remove BD_TITLE_ROLE (breaking change, do last)
5. **Phase 5**: Update existing tests

---

## Files to Modify

| File | Change Type | Risk |
|------|-------------|------|
| `Batchdata/src/name_matching.py` | **NEW FILE** | None |
| `Batchdata/tests/test_name_matching.py` | **NEW FILE** | None |
| `src/adhs_etl/batchdata_bridge.py` | Add import + call | Low |
| `Batchdata/src/transform.py` | Remove BD_TITLE_ROLE | Medium |
| `Batchdata/src/normalize.py` | Add deprecation | Low |
| `Batchdata/Batchdata_template_fields_desc.md` | Full update | Low |
| `Batchdata/tests/test_*.py` (4 files) | Remove BD_TITLE_ROLE | Low |

---

## Risks & Mitigations

**Risk 1**: BD_TITLE_ROLE removal breaks downstream consumers
- **Mitigation**: Column was purely informational, not used for filtering
- **Finding**: Analysis confirmed no business logic depends on it

**Risk 2**: Name matching accuracy
- **Mitigation**: Use `rapidfuzz.token_sort_ratio()` (proven in ecorp.py)
- **Threshold**: 85% is consistent with existing entity family detection

**Risk 3**: Column index shifts
- **Mitigation**: New columns added at END (165-173), minimal existing column shifts
