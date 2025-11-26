# Plan: Remove Name Input Fields from BatchData Pipeline

## Summary

Update documentation and code after removal of 4 columns from Batchdata_Template.xlsx:
- **Removed**: BD_TARGET_FIRST_NAME (V), BD_TARGET_LAST_NAME (W), BD_OWNER_NAME_FULL (X), BD_ADDRESS_2 (Z)
- **INPUT_MASTER**: Now 16 columns (was 20)
- **Key Change**: BatchData API now uses ADDRESS ONLY for skip-trace lookups

## User Requirements

1. **API Request**: Address fields only - no name fields in API payload
2. **ECORP_TO_BATCH_MATCH_%**: Compare ECORP principal names (from Ecorp_Complete file) against BatchData API RESULTS (BD_PHONE_X_FIRST/LAST, BD_EMAIL_X_FIRST/LAST)
3. **Documentation**: Update all references to removed columns

---

## CRITICAL ISSUES IDENTIFIED (Must Address)

### Issue 1: Deduplication Will Break
**Current code** (`transform.py:700-703`):
```python
comparison_fields = [
    'BD_TARGET_FIRST_NAME', 'BD_TARGET_LAST_NAME', 'BD_OWNER_NAME_FULL',
    'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP'
]
```

**Problem**: With address-only comparison, multiple principals at the same address will be incorrectly deduplicated (e.g., John Smith and Jane Smith at 123 Main St → ONE record).

**Solution**: Update to include distinguishing fields:
```python
comparison_fields = [
    'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP',
    'BD_TITLE_ROLE', 'BD_SOURCE_ENTITY_ID'  # Keep these to distinguish principals
]
```

### Issue 2: Name Matching Lookup Uses Wrong Key
**Current code** (`name_matching.py:215-217`):
```python
addr = str(ecorp_row.get('FULL_ADDRESS', '')).strip().upper()
ecorp_lookup[addr] = ecorp_row  # LAST ONE WINS!
```

**Problem**: Multiple Ecorp records can have same FULL_ADDRESS. Last one overwrites previous ones.

**Solution**: Use `BD_SOURCE_ENTITY_ID` as join key instead:
```python
entity_id = str(ecorp_row.get('ECORP_ENTITY_ID_S', '')).strip()
ecorp_lookup[entity_id] = ecorp_row
```

### Issue 3: No Fallback for Name Matching
**Current code** (`name_matching.py:230-233`):
```python
if not ecorp_names:
    owner = str(row.get('BD_OWNER_NAME_FULL', '')).strip()  # REMOVED!
    ecorp_names = [owner] if owner else []
```

**Problem**: BD_OWNER_NAME_FULL is removed, so fallback fails silently.

**Solution**: Make `ecorp_complete_df` REQUIRED, or set match to "N/A" with warning when unavailable.

### Issue 4: Keep BD_TITLE_ROLE
**Rationale**: BD_TITLE_ROLE (Manager, Member, Statutory Agent) is still valuable:
- Distinguishes principals at same address
- No API cost (not sent to API)
- Useful for contact prioritization

**Action**: DO NOT REMOVE BD_TITLE_ROLE from the pipeline

---

## Phase 1: Documentation Updates

### Files to Update

| File | Changes |
|------|---------|
| `Batchdata/Batchdata_template_fields_desc.md` | Remove columns 23-25, 27 descriptions; update INPUT_MASTER from 20→16 cols; update total from 173→169 cols |
| `Batchdata/README.md` | Remove BD_TARGET_*, BD_OWNER_NAME_FULL, BD_ADDRESS_2 from INPUT_MASTER requirements |
| `Batchdata/PIPELINE_INTEGRATION_GUIDE.md` | Remove name fields from Input Requirements section; update examples |
| `Batchdata/SYNC_MIGRATION_IMPLEMENTATION.md` | Update Schema Requirements section |
| `Batchdata/BD_PREFIX_MIGRATION.md` | Mark columns as REMOVED in migration table |
| `Batchdata/V2_QUICK_START.md` | Remove BD_ADDRESS_2 from examples |
| `Batchdata/PHASE_1_TEST_RESULTS.md` | Update schema compatibility section |
| `Batchdata/docs/examples/PRD_BatchData_Bulk_Pipeline.md` | Remove name columns from input spec |
| `Batchdata/TEMPLATE_CONSOLIDATION_PLAN.md` | Update to reflect new column structure |

### Key Documentation Changes

**Batchdata_template_fields_desc.md** - Major rewrite:
- Section 2 (BD Input Columns): Change from 18-37 → 18-33 (16 columns)
- Remove detailed descriptions for columns 23-25, 27
- Update column numbering for BD_ADDRESS (was 26, now 22), BD_CITY (was 28, now 23), etc.
- Update Section totals: Phone blocks start at col 34 (was 38), Email blocks adjust accordingly
- Final total: 169 columns (was 173)

---

## Phase 2: Code Updates

### 2.1 Transform Logic (`Batchdata/src/transform.py`)

**Function: `ecorp_to_batchdata_records()` (~lines 155-410)**

Remove these field assignments:
```python
# REMOVE these lines:
'BD_TARGET_FIRST_NAME': first_name,
'BD_TARGET_LAST_NAME': last_name,
'BD_OWNER_NAME_FULL': str(name).strip(),
'BD_ADDRESS_2': addr_parts['line2'],
```

**Function: `deduplicate_batchdata_records()` (~lines 682-783)**

Update comparison_fields - **CRITICAL: Must include distinguishing fields to avoid data loss**:
```python
# CHANGE FROM:
comparison_fields = [
    'BD_TARGET_FIRST_NAME', 'BD_TARGET_LAST_NAME', 'BD_OWNER_NAME_FULL',
    'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP'
]
# CHANGE TO:
comparison_fields = [
    'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP',
    'BD_TITLE_ROLE', 'BD_SOURCE_ENTITY_ID'  # KEEP these to distinguish principals!
]
```

**Why**: Without distinguishing fields, multiple principals at same address collapse into one record.

**Function: `filter_entity_only_records()` (~lines 880-920)**

**REMOVE ENTIRELY** - This function's sole purpose is checking for empty BD_TARGET_FIRST/LAST_NAME fields. Without name fields, it has no purpose. Any callers should be updated to remove the call.

**Function: `validate_input_fields()` (~lines 923-976)**

**SIMPLIFY** - Remove name field validation, keep address validation:
```python
# REMOVE has_valid_name check using BD_TARGET_* fields
# KEEP address validation: BD_ADDRESS, BD_CITY, BD_STATE, BD_ZIP
```

**Function: `optimize_for_api()` (~lines 979-1049)**

**REMOVE ENTIRELY** - This function's purpose is to fall back from full name to first/last parsing. Without name fields in API requests, optimization is unnecessary. Any callers should be updated to remove the call.

**Function: `consolidate_entity_families()` (~lines 1052-1181)**

Update consolidation_fields to remove name fields.

### 2.2 API Request Logic (`Batchdata/src/batchdata_sync.py`)

**Function: `_df_to_sync_request()` (~lines 140-189)**

Remove ALL name-related code from API payload:
```python
# REMOVE these lines (~164-186):
first_name = row.get('BD_TARGET_FIRST_NAME', '')
last_name = row.get('BD_TARGET_LAST_NAME', '')
full_name = row.get('BD_OWNER_NAME_FULL', '')

if first_name or last_name:
    request_item["name"] = {...}
elif full_name:
    # Parse full name...
```

Keep ONLY address fields in request:
```python
request_item = {
    "address": {
        "street": str(row.get('BD_ADDRESS', '')),
        "city": str(row.get('BD_CITY', '')),
        "state": str(row.get('BD_STATE', '')),
        "zip": str(row.get('BD_ZIP', ''))
    }
}
```

### 2.3 Name Matching Logic (`Batchdata/src/name_matching.py`)

**Needs multiple fixes**:

**Fix 1: Change lookup key from FULL_ADDRESS to ECORP_ENTITY_ID_S** (~lines 211-217)
```python
# CHANGE FROM:
for idx, ecorp_row in ecorp_complete_df.iterrows():
    addr = str(ecorp_row.get('FULL_ADDRESS', '')).strip().upper()
    if addr:
        ecorp_lookup[addr] = ecorp_row  # PROBLEM: Last one wins!

# CHANGE TO:
for idx, ecorp_row in ecorp_complete_df.iterrows():
    entity_id = str(ecorp_row.get('ECORP_ENTITY_ID_S', '')).strip()
    if entity_id:
        ecorp_lookup[entity_id] = ecorp_row
```

**Why**: Multiple Ecorp records can share same FULL_ADDRESS; using entity ID is unique.

**Fix 2: Update lookup usage** (~line 224-225)
```python
# CHANGE FROM:
addr = str(row.get('FULL_ADDRESS', '')).strip().upper()
ecorp_row = ecorp_lookup.get(addr)

# CHANGE TO:
entity_id = str(row.get('BD_SOURCE_ENTITY_ID', '')).strip()
ecorp_row = ecorp_lookup.get(entity_id)
```

**Fix 3: Remove BD_OWNER_NAME_FULL fallback** (~lines 230-233)
```python
# REMOVE this fallback logic entirely:
if not ecorp_names:
    owner = str(row.get('BD_OWNER_NAME_FULL', '')).strip()
    ecorp_names = [owner] if owner else []

# REPLACE WITH:
if not ecorp_names:
    # No Ecorp data available - cannot compute match
    df.at[idx, 'ECORP_TO_BATCH_MATCH_%'] = 'N/A'
    continue  # Skip to next row
```

**New behavior**: If `ecorp_complete_df` is None or lookup fails, set match to "N/A" instead of silent 0%.

### 2.4 Bridge Integration (`src/adhs_etl/batchdata_bridge.py`)

Ensure `ecorp_file` parameter is REQUIRED (not optional) for name matching:

```python
# In _run_sync_enrichment() - make ecorp_file mandatory for name matching
if not ecorp_file or not Path(ecorp_file).exists():
    print("WARNING: No Ecorp_Complete file provided - name matching will be skipped")
    # Set ECORP_TO_BATCH_MATCH_% to empty or N/A
```

---

## Phase 3: Test Updates

### Files to Update

| File | Changes |
|------|---------|
| `Batchdata/tests/test_name_matching.py` | Remove BD_OWNER_NAME_FULL fallback tests |
| `Batchdata/tests/test_integration.py` | Update test data to not include removed columns |
| `Batchdata/tests/test_pipeline.py` | Update expected column counts |
| `Batchdata/tests/test_template_output.py` | Update template validation |

---

## New INPUT_MASTER Column Structure (16 columns)

| Col | Field | Description |
|-----|-------|-------------|
| A | BD_RECORD_ID | Unique record identifier |
| B | BD_SOURCE_TYPE | Always "Entity" |
| C | BD_ENTITY_NAME | Registered entity name |
| D | BD_SOURCE_ENTITY_ID | ACC file number |
| E | BD_TITLE_ROLE | Principal's role |
| F | BD_ADDRESS | Street address line 1 |
| G | BD_CITY | City name |
| H | BD_STATE | 2-letter state |
| I | BD_ZIP | 5-digit ZIP |
| J | BD_COUNTY | County name |
| K | BD_APN | Assessor Parcel Number |
| L | BD_MAILING_LINE1 | Mailing address line 1 |
| M | BD_MAILING_CITY | Mailing city |
| N | BD_MAILING_STATE | Mailing state |
| O | BD_MAILING_ZIP | Mailing ZIP |
| P | BD_NOTES | Processing notes |

**Removed columns**: BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL, BD_ADDRESS_2

---

## New OUTPUT_MASTER Column Count

- ECORP Passthrough: 17 columns (unchanged)
- BD Input: 16 columns (was 20)
- BD Phone Blocks: 80 columns (unchanged)
- BD Email Blocks: 40 columns (unchanged)
- BD Metadata: 8 columns (unchanged)
- Name Matching: 8 columns (unchanged)

**Total: 169 columns** (was 173)

---

## ECORP_TO_BATCH_MATCH_% Logic (Unchanged Core)

1. **Source ECORP names from**: Ecorp_Complete file (22 principal fields)
2. **Compare against**: BatchData API RESULTS (BD_PHONE_X_FIRST/LAST, BD_EMAIL_X_FIRST/LAST)
3. **Matching**: 85% fuzzy threshold using token_sort_ratio
4. **Output**: 0-100 percentage + MISSING_1-8_FULL_NAME columns

The logic remains the same - we're just removing the BD_OWNER_NAME_FULL fallback.

---

## Execution Order

1. Update `Batchdata/src/transform.py` - remove field population
2. Update `Batchdata/src/batchdata_sync.py` - address-only API requests
3. Update `Batchdata/src/name_matching.py` - remove BD_OWNER_NAME_FULL fallback
4. Update `src/adhs_etl/batchdata_bridge.py` - handle missing ecorp_file gracefully
5. Update all documentation files
6. Update test files
7. Run tests to verify

---

## Critical Files

- `Batchdata/src/transform.py` - Lines 155-410, 682-783, 880-920, 923-976, 979-1049, 1052-1181
- `Batchdata/src/batchdata_sync.py` - Lines 140-189
- `Batchdata/src/name_matching.py` - Lines 189-232 (+ fix lookup key bug)
- `src/adhs_etl/batchdata_bridge.py` - Lines 394-408
- `Batchdata/Batchdata_template_fields_desc.md` - Full rewrite needed

---

## Additional Improvements (Beyond Original Plan)

### 1. Keep `split_full_name()` in normalize.py
**Rationale**: While we're removing name fields from INPUT_MASTER, the function is still used:
- Entity-level fallback records (transform.py:348)
- Potentially useful for other parts of pipeline

**Action**: Keep the function, remove only the calls in transform.py that populate removed fields.

### 2. `consolidate_entity_families()` Fix (transform.py:1096-1098)
Same issue as deduplication - update consolidation_fields:
```python
# CHANGE FROM:
consolidation_fields = [
    'BD_TARGET_FIRST_NAME', 'BD_TARGET_LAST_NAME', 'BD_OWNER_NAME_FULL',
    'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP', '_entity_family'
]
# CHANGE TO:
consolidation_fields = [
    'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP',
    'BD_TITLE_ROLE', 'BD_SOURCE_ENTITY_ID', '_entity_family'
]
```

### 3. Testing Strategy
After implementation, verify:
1. **Deduplication preserves distinct principals** - Run with 2 principals at same address, confirm both survive
2. **API requests contain NO name fields** - Add debug logging to verify payload
3. **Name matching uses entity ID join** - Test with multiple records sharing FULL_ADDRESS
4. **Column counts correct** - INPUT_MASTER=16, OUTPUT_MASTER=169

### 4. Backward Compatibility
- Existing BatchData Complete files (with old 173 columns) should still be readable
- New files will have 169 columns
- Consider adding version marker to CONFIG sheet

---

## Summary of Plan Improvements

| Original Plan | Improved Plan |
|---------------|---------------|
| Address-only deduplication | Include BD_TITLE_ROLE + BD_SOURCE_ENTITY_ID in comparison |
| FULL_ADDRESS lookup key | Use ECORP_ENTITY_ID_S for reliable join |
| Silent fallback failure | Explicit "N/A" when Ecorp lookup unavailable |
| Remove 4 columns only | Also fix consolidate_entity_families() |
| No testing strategy | Added verification checklist |
