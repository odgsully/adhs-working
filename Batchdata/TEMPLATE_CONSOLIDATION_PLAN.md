# Batchdata Template Consolidation Plan

## Problem Statement

The root `Batchdata_Template.xlsx` (173 columns) should be the canonical template for BatchData Upload and Complete outputs, but it is not currently used. Instead:

1. **Root template is ignored** - Code uses `Batchdata/template_config.xlsx` for CONFIG/BLACKLIST only
2. **ECORP passthrough columns are dropped** - Transform discards 17 context columns
3. **Orphaned template exists** - `Batchdata/Batchdata_Template.xlsx` has wrong column naming
4. **Output schema is hardcoded** - `batchdata_sync.py` hardcodes columns instead of reading from template
5. **Root template defect** - Missing `BD_TITLE_ROLE` column (position 22)

## Current vs Expected Data Flow

### Current (Broken):
```
Ecorp_Complete (93 cols)
    → transform [DROPS 17 ECORP cols]
    → Upload INPUT_MASTER (20 BD cols)
    → API enrichment
    → Complete OUTPUT_MASTER (~162 cols) ← MISSING 11 COLS
```

### Expected:
```
Ecorp_Complete (93 cols)
    → transform [PRESERVES 17 ECORP cols]
    → Upload INPUT_MASTER (37 cols: 17 ECORP + 20 BD)
    → API enrichment
    → Complete OUTPUT_MASTER (173 cols) ← MATCHES TEMPLATE
```

## Recommended Approach

### Phase 1: Template Update (Completed November 2025)
**File:** `Batchdata_Template.xlsx`
- BD_TITLE_ROLE column at position 22 ✓
- **REMOVED**: BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL, BD_ADDRESS_2
- Total column count: **169** (was 173)
- API uses address-only for skip-trace lookups
- This becomes the single source of truth

### Phase 2: Modify Transform to Preserve ECORP Context
**File:** `Batchdata/src/transform.py`

Modify `transform_ecorp_to_batchdata()` to:
1. Accept `preserve_ecorp_context=True` parameter (backward compat)
2. Copy 17 ECORP passthrough columns to each exploded principal record
3. Ensure `BD_TITLE_ROLE` is populated from principal role

ECORP passthrough columns to preserve:
- FULL_ADDRESS, COUNTY, Owner_Ownership, ECORP_INDEX_#, OWNER_TYPE
- ECORP_SEARCH_NAME, ECORP_TYPE, ECORP_NAME_S, ECORP_ENTITY_ID_S
- ECORP_ENTITY_TYPE, ECORP_STATUS, ECORP_FORMATION_DATE
- ECORP_BUSINESS_TYPE, ECORP_STATE, ECORP_COUNTY, ECORP_COMMENTS, ECORP_URL

### Phase 3: Update Bridge to Use Root Template
**File:** `src/adhs_etl/batchdata_bridge.py`

Modify `create_batchdata_upload()`:
1. Change `config_template_path` default to point to root template or new upload template
2. Ensure Upload INPUT_MASTER includes 37 columns (17 ECORP + 20 BD)
3. Read column order from template for consistency

Modify `_run_sync_enrichment()`:
1. Remove ecorp_file re-read for name matching (use passthrough cols instead)
2. Validate output schema against root template before writing

### Phase 4: Make Sync Client Template-Aware
**File:** `Batchdata/src/batchdata_sync.py`

Modify `_parse_sync_response_to_schema()`:
1. Preserve ECORP passthrough columns from input (don't overwrite)
2. Ensure enrichment columns match template order
3. Add schema validation against template

### Phase 5: Update Name Matching to Use Passthrough
**File:** `Batchdata/src/name_matching.py`

Modify `apply_name_matching()`:
1. Extract ECORP principal names from passthrough columns already in DataFrame
2. Remove dependency on external ecorp_file parameter
3. More efficient and less fragile

### Phase 6: Cleanup
- Archive `Batchdata/Batchdata_Template.xlsx` to `dnu/` folder (wrong column names, causes confusion)
- Update `Batchdata/template_config.xlsx` INPUT_MASTER to include 37 columns (17 ECORP + 20 BD)
- Update `Batchdata/Batchdata_template_fields_desc.md` if column positions change

### Phase 7: Add Strict Validation
**File:** `src/adhs_etl/batchdata_bridge.py`

Add validation function before writing Complete output:
```python
def validate_output_against_template(df: pd.DataFrame, template_path: str) -> None:
    """Fail if output columns don't match template exactly."""
    template_cols = list(pd.read_excel(template_path, nrows=0).columns)
    output_cols = list(df.columns)
    if output_cols != template_cols:
        raise ValueError(f"Output schema mismatch: expected {len(template_cols)} cols, got {len(output_cols)}")
```

## Critical Files to Modify

| File | Changes |
|------|---------|
| `Batchdata_Template.xlsx` | Add BD_TITLE_ROLE column |
| `Batchdata/src/transform.py` | Preserve ECORP passthrough in transform |
| `src/adhs_etl/batchdata_bridge.py` | Use root template, remove ecorp re-read |
| `Batchdata/src/batchdata_sync.py` | Preserve passthrough, template-aware output |
| `Batchdata/src/name_matching.py` | Use passthrough cols instead of re-reading |
| `Batchdata/template_config.xlsx` | Update INPUT_MASTER to 37 columns |

## User Decisions

1. **Upload Schema**: Full 37 columns (17 ECORP passthrough + 20 BD input)
2. **Orphan File**: Archive `Batchdata/Batchdata_Template.xlsx` to `dnu/` folder
3. **Validation**: Strict validation - fail if output doesn't match 173-column template

## Backward Compatibility

- `preserve_ecorp_context=True` flag in transform (default ON for ETL, OFF for standalone)
- Standalone mode (`Batchdata/src/run.py`) continues to work without ECORP context
- Multi-sheet structure (CONFIG, INPUT_MASTER/OUTPUT_MASTER, BLACKLIST_NAMES) maintained

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Breaking standalone mode | Low | Backward compat flag |
| Column order mismatch | Medium | Template validation before write |
| Transform explosion complexity | Medium | Unit tests for 1-to-many scenarios |
| Downstream system breakage | Medium | Schema validation, test with real data |

## Testing Strategy

1. Unit test transform with ECORP passthrough
2. Integration test full pipeline (Ecorp → Upload → Complete)
3. Validate Complete output matches 173-column template exactly
4. Test standalone mode still works without ECORP context
