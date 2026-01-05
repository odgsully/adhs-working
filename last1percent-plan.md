# Last 1% Plan: Conservative Grouping & Address Normalization

> Improving PROVIDER_GROUP_INDEX_# accuracy while preserving 99.4% of existing behavior

## Executive Summary

This plan addresses systematic gaps in the ADHS-ETL provider grouping logic that affect approximately **0.6% of records**. The approach is conservative, reversible, and includes comprehensive safety nets.

**Problem**: Address formatting variations (WEST vs W, STREET vs ST, whitespace) cause false splits in provider grouping.

**Solution**: Address normalization + enhanced grouping algorithm running in parallel with full validation before adoption.

**Risk**: Low — 99.4% of records unchanged; all changes flagged for review.

---

## Current State Analysis

### Grouping Algorithm (V1)

| Aspect | Current Implementation |
|--------|------------------------|
| **Primary matching** | ADDRESS first 20 characters (exact match) |
| **Secondary matching** | PROVIDER name fuzzy match (85% Levenshtein) |
| **Comparison limit** | First 20 unmatched providers only |
| **Field used** | ADDRESS (street only, not FULL_ADDRESS) |

### Known Issues

1. **Address prefix too short** — 20 chars doesn't capture city/ZIP
2. **No address normalization** — "W" vs "WEST" creates false splits
3. **Processing order dependent** — Results vary based on data order
4. **Comparison limit** — May miss matches beyond position 20

### Impact Metrics (from 11.24 Analysis)

| Metric | Value |
|--------|-------|
| Total records | 10,280 |
| Unique groups | 8,165 |
| Single-provider groups | 84.2% (6,874) |
| Multi-provider groups | 15.8% (1,291) |
| Addresses in 2+ groups | 37 (0.4%) |
| Records with address variations | ~300 (1.5%) |

---

## Critical Dependencies Identified

### PROVIDER_GROUP_INDEX_# (67+ references)

| Component | Impact | Risk if Changed |
|-----------|--------|-----------------|
| analysis.py (12 refs) | Drives DBA_Concat, ADDRESS_COUNT, SOLO, MULTI_CITY | CRITICAL |
| transform_enhanced.py | Generates column via ProviderGrouper | CRITICAL |
| field_map.yml | Maps 4 input variations | HIGH |
| Summary sheet | Aggregates group metrics | HIGH |
| 6 Python scripts | Report unique group counts | MEDIUM |

### ADDRESS Field Dependencies

| Stage | Usage | Format Expected |
|-------|-------|-----------------|
| Provider Grouping | 20-char prefix matching | Street only, exact |
| Status Classification | NEW/EXISTING ADDRESS detection | Exact match |
| FULL_ADDRESS Construction | Concatenation with CITY/ZIP | Separated components |
| BatchData API | Skip-trace lookup | Street only (separated) |

### 155-Column Hard Limit

```python
# process_months_local.py line 544
expected_columns = 155  # BLOCKS output if not exactly 155
```

**Implication**: Cannot add columns to Analysis output without updating validation.

---

## ADDRESS vs FULL_ADDRESS Analysis

### Comparison

| Aspect | ADDRESS | FULL_ADDRESS |
|--------|---------|--------------|
| Format | `123 MAIN ST` | `123 MAIN ST, PHOENIX, AZ 85001` |
| Length | ~15-30 chars | ~40-60 chars |
| 20-char captures | Street number + partial name | Same (doesn't reach city) |
| Geographic uniqueness | None | City/ZIP disambiguation |
| Variation sources | Street abbreviations | Street + City + ZIP formats |

### Recommendation

**Use FULL_ADDRESS with 35-char prefix** for grouping:

1. Geographic disambiguation — prevents false matches across cities
2. Downstream alignment — already standard for APN/MCAO/Ecorp/BatchData
3. More unique — ZIP code adds strong signal

Apply normalization to ADDRESS component within FULL_ADDRESS:
```
FULL_ADDRESS = normalize(ADDRESS) + ", " + CITY + ", AZ " + ZIP
```

---

## Implementation Plan

### Phase 0: Safety Net (Week 1)

**Purpose**: Create regression protection before any changes.

#### 0A. Golden Test Baseline

| Task | Details |
|------|---------|
| Export golden files | 9.24, 10.24, 11.24 Analysis outputs |
| Document expected groups | 50 known provider groupings |
| Create comparison script | Detect differences from baseline |
| Commit to git | Version-controlled baseline |

**Records impacted**: 0%

#### 0B. Add Missing Critical Tests

| Test File | Coverage |
|-----------|----------|
| `test_provider_grouping.py` | PROVIDER_GROUP_INDEX_# assignment |
| `test_full_address_construction.py` | ADDRESS + CITY + ZIP concatenation |
| `test_address_normalization.py` | Normalization rules validation |
| `test_grouping_regression.py` | Golden file comparison |

**Records impacted**: 0%

---

### Phase 1: Infrastructure Fixes (Week 2)

**Purpose**: Fix underlying code issues without changing behavior.

#### 1A. Fix 155-Column Validation

```python
# Current (RIGID):
expected_columns = 155
if len(df.columns) != 155: BLOCK

# New (FLEXIBLE):
MINIMUM_COLUMNS = 155
if len(df.columns) < MINIMUM_COLUMNS: BLOCK
```

**Records impacted**: 0%
**Code lines changed**: 1-2
**Rollback**: Revert 1 line

#### 1B. Replace Hardcoded Indices in Ecorp

```python
# Current (FRAGILE):
df.iloc[:, 4]  # Owner_Ownership

# New (ROBUST):
df['Owner_Ownership']  # Named column access
```

**Records impacted**: 0%
**Code lines changed**: ~5-10
**Rollback**: Revert to indices

#### 1C. Add Internal Normalized Column

```python
# Internal column (dropped before output)
df['_ADDRESS_NORMALIZED'] = normalize_address(df['ADDRESS'])
# Grouper uses _ADDRESS_NORMALIZED
# Output uses original ADDRESS
```

**Records impacted**: 0% (internal only)
**Output change**: None
**Rollback**: Remove column creation

---

### Phase 2: Address Normalization (Week 3)

**Purpose**: Standardize address formats for improved matching.

#### 2A. Normalization Rules

| Priority | Rule | Before | After |
|----------|------|--------|-------|
| 1 | Collapse whitespace | `123  MAIN` | `123 MAIN` |
| 2 | Expand directionals | `123 W MAIN` | `123 WEST MAIN` |
| 3 | Expand street types | `123 MAIN ST` | `123 MAIN STREET` |
| 4 | Standardize suite | `STE 5` | `SUITE 5` |

#### 2B. Normalization Map

```python
NORMALIZATION_MAP = {
    # Directionals (word boundary required)
    r'\bW\b': 'WEST',
    r'\bE\b': 'EAST',
    r'\bN\b': 'NORTH',
    r'\bS\b': 'SOUTH',

    # Street types
    r'\bST\b': 'STREET',
    r'\bAVE\b': 'AVENUE',
    r'\bRD\b': 'ROAD',
    r'\bDR\b': 'DRIVE',
    r'\bBLVD\b': 'BOULEVARD',
    r'\bLN\b': 'LANE',

    # Suite formatting
    r'\bSTE\b': 'SUITE',
}
```

#### 2C. Injection Point

```
transform_enhanced.py line 442:
  ↓
  df['_ADDRESS_NORMALIZED'] = normalize(df['ADDRESS'])  ← NEW
  ↓
  grouper.group_providers(df, address_col='_ADDRESS_NORMALIZED')  ← MODIFIED
  ↓
  df.drop('_ADDRESS_NORMALIZED')  ← REMOVE BEFORE OUTPUT
```

#### 2D. Expected Impact

| Metric | Value |
|--------|-------|
| Records with address variations | ~300 (1.5%) |
| Addresses with multiple formats | 74 |
| Records benefiting from directional normalization | ~8,800 |
| Records benefiting from street type normalization | ~10,400 |
| **Expected grouping changes** | **~60-80 records (0.6%)** |
| Risk of false merges | <10 records |

---

### Phase 3: Parallel V2 Grouping (Week 4)

**Purpose**: Run improved algorithm alongside V1 for comparison.

#### 3A. Internal-Only Columns

```python
# Internal columns (prefixed with underscore, dropped before output)
'_PROVIDER_GROUP_INDEX_V2'      # New grouping result
'_GROUP_CONFIDENCE_SCORE'       # 0-100 confidence
'_GROUP_DIFF_FLAG'              # Y/N vs V1
```

**Why internal?** Preserves 155-column structure; comparison data goes to separate report.

#### 3B. V2 Algorithm Enhancements

| Enhancement | V1 | V2 |
|-------------|-----|-----|
| Address prefix length | 20 chars | 35 chars |
| Field used | ADDRESS | FULL_ADDRESS (normalized) |
| Processing order | Data-dependent | Deterministic (sorted) |
| Comparison limit | First 20 | All providers |
| Confidence scoring | None | 0-100 score |

#### 3C. Comparison Report (Separate File)

```
M.YY_Grouping_Comparison_{timestamp}.xlsx
├── Sheet 1: Summary
│   ├── V1 Groups: 8,165
│   ├── V2 Groups: 8,102
│   ├── Differences: 63 records
│   ├── Merges: 41 (V1 too narrow)
│   └── Splits: 22 (V1 too broad)
├── Sheet 2: Differences Only
│   └── PROVIDER | ADDRESS | V1_GROUP | V2_GROUP | CHANGE | CONFIDENCE
└── Sheet 3: Validation Checklist
```

#### 3D. Feature Flag

```python
# config.py
ENABLE_V2_GROUPING_COMPARISON = False  # Default off

# When enabled:
# - Runs both V1 and V2
# - Generates comparison report
# - Output uses V1 (unchanged)
```

#### 3E. Expected Impact

| Metric | Value |
|--------|-------|
| Single-provider groups (unchanged) | 84.2% |
| Multi-provider groups (potentially affected) | 15.8% |
| Addresses in 2+ groups (merge candidates) | 37 (0.4%) |
| **Expected V1 vs V2 differences** | **~63 records (0.6%)** |
| Confidence: High (no change) | ~95% |
| Confidence: Medium (review needed) | ~4% |
| Confidence: Low (manual review) | ~1% |

---

### Phase 4: Validation & Adoption (Week 5+)

**Purpose**: Validate improvements before committing.

#### 4A. Validation Process

1. Process 9.24, 10.24, 11.24 with V2 enabled
2. Review comparison reports
3. Validate V2 improvements vs V1
4. Check for regressions against golden baseline
5. Manual review of flagged records

#### 4B. Manual Review Checklist

- [ ] No false merges (unrelated providers grouped)
- [ ] No false splits (related providers separated)
- [ ] Address normalization catches known issues
- [ ] Historical comparison still works
- [ ] All regression tests pass
- [ ] Downstream stages unaffected (APN, MCAO, Ecorp, BatchData)

#### 4C. Adoption Decision

```
IF validation passes:
  - Update grouper to use V2 by default
  - Keep V1 available via config flag
  - Monitor for issues

IF validation fails:
  - Disable V2
  - Adjust normalization rules
  - Re-run validation
```

#### 4D. Expected Impact

| Metric | Value |
|--------|-------|
| Records impacted during validation | 0% |
| Records impacted after adoption | ~0.6% |
| Rollback capability | 100% (feature flag) |

---

## Total Expected Impact Summary

| Phase | Records Changed | Records Reviewed | Risk Level |
|-------|-----------------|------------------|------------|
| 0 (Tests) | 0 | 0 | None |
| 1A-C (Infrastructure) | 0 | 0 | None |
| 2 (Normalization) | ~60-80 (0.6%) | ~300 (3%) | Low |
| 3 (V2 Grouping) | ~63 (0.6%) | ~400 (4%) | Low |
| 4 (Adoption) | 0 new | 0 new | None |
| **TOTAL** | **~100-140 records** | **~500 records** | **Low** |

**99.4% of records will be UNCHANGED** by this entire plan.

---

## Safety Guarantees

| Guarantee | How Achieved |
|-----------|--------------|
| Output format unchanged | V2 columns are internal-only, dropped before output |
| 155 columns preserved | Comparison data goes to separate report file |
| Historical comparison works | Status KEY uses original ADDRESS |
| Downstream stages unaffected | Original ADDRESS/FULL_ADDRESS columns unchanged |
| Instant rollback | Feature flags for V2, normalization |
| Regression detection | Golden tests compare to known-good baseline |

---

## Remaining Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Normalization changes grouping unexpectedly | Low | Golden test catches differences |
| V2 grouping creates false merges | Low | Comparison report flags all changes |
| Performance impact from dual processing | Low | Only when flag enabled; disable after validation |
| Historical months have different normalization | Medium | Apply normalization consistently to all months |

---

## File Changes Required

### New Files

| File | Purpose |
|------|---------|
| `src/tests/test_provider_grouping.py` | Grouping assignment tests |
| `src/tests/test_full_address_construction.py` | FULL_ADDRESS tests |
| `src/tests/test_address_normalization.py` | Normalization tests |
| `src/tests/test_grouping_regression.py` | Golden file comparison |
| `src/tests/fixtures/grouping/` | Golden test data |
| `src/adhs_etl/address_normalizer.py` | Normalization functions |
| `src/adhs_etl/grouping_v2.py` | Enhanced grouping algorithm |

### Modified Files

| File | Changes |
|------|---------|
| `src/adhs_etl/transform_enhanced.py` | Add normalization call, V2 grouping |
| `src/adhs_etl/config.py` | Add feature flags |
| `src/adhs_etl/ecorp.py` | Replace hardcoded indices |
| `scripts/process_months_local.py` | Fix 155-column validation |

---

## Success Criteria

1. All regression tests pass
2. V2 grouping produces ≥95% identical results to V1
3. Address normalization catches known variations (74 addresses)
4. No downstream stage failures
5. Comparison report accurately flags all differences
6. Manual review approves changes
7. Rollback tested and working

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | 0 (Safety Net) | Golden baseline, regression tests |
| 2 | 1 (Infrastructure) | Validation fix, index fix, internal column |
| 3 | 2 (Normalization) | Address normalizer, integration |
| 4 | 3 (V2 Grouping) | Parallel algorithm, comparison report |
| 5+ | 4 (Validation) | Review, adoption decision |

---

## Appendix A: Address Variation Patterns Found

| Pattern | Records Affected | Example |
|---------|------------------|---------|
| W → WEST | 857 | `123 W MAIN` → `123 WEST MAIN` |
| E → EAST | 836 | `456 E OAK` → `456 EAST OAK` |
| N → NORTH | 710 | `789 N PINE` → `789 NORTH PINE` |
| S → SOUTH | 433 | `321 S ELM` → `321 SOUTH ELM` |
| ST → STREET | 1,640 | `MAIN ST` → `MAIN STREET` |
| AVE → AVENUE | 2,004 | `OAK AVE` → `OAK AVENUE` |
| RD → ROAD | 2,229 | `PINE RD` → `PINE ROAD` |
| DR → DRIVE | 1,664 | `ELM DR` → `ELM DRIVE` |
| BLVD → BOULEVARD | 431 | `CENTRAL BLVD` → `CENTRAL BOULEVARD` |
| STE → SUITE | 1,741 | `STE 100` → `SUITE 100` |
| Double spaces | 206 | `123  MAIN` → `123 MAIN` |

---

## Appendix B: Test Coverage Gaps (Current State)

| Area | Current Coverage | Gap |
|------|------------------|-----|
| PROVIDER_GROUP_INDEX_# assignment | None | CRITICAL |
| Address normalization | None | CRITICAL |
| FULL_ADDRESS construction | None | CRITICAL |
| Grouping regression | None | CRITICAL |
| Fuzzy name matching | Isolated tests only | MEDIUM |
| End-to-end pipeline | Partial | MEDIUM |

---

## Appendix C: Downstream Stage Dependencies

```
Reformat (16 cols)
    ↓
Analysis (155 cols) ← PROVIDER_GROUP_INDEX_# created here
    ↓
APN Upload (2 cols: FULL_ADDRESS, COUNTY)
    ↓
APN Complete (3 cols: + APN)
    ↓
MCAO Upload (3 cols)
    ↓
MCAO Complete (87 cols)
    ↓
Ecorp Upload (4 cols: FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE)
    ↓
Ecorp Complete (93 cols)
    ↓
BatchData Upload (16 cols)
    ↓
BatchData Complete
```

**Key finding**: PROVIDER_GROUP_INDEX_# is NOT used by downstream stages (Ecorp has its own ECORP_INDEX_#). Changes to grouping affect Analysis only.

---

*Document created: 2025-12-02*
*Last updated: 2025-12-02*
*Status: PLANNING*
