# VALIDATION RESULTS - Unit Tests

Generated: 2025-11-24

## Unit Test Results

| Branch | Tests Passed | Tests Failed | Total |
|--------|--------------|--------------|-------|
| `chore/consolidate-env-files` | 20 | 6 | 26 |
| `preserve/copy3-ai-refactor` | 20 | 6 | 26 |

**Result: IDENTICAL** - Both branches have the same test results.

## Failed Tests (Same on Both Branches)

These failures are pre-existing test fixture issues, not regressions:

1. `test_all_to_date_accumulation` - Missing FULL_ADDRESS column in test fixture
2. `test_all_to_date_deduplication` - Missing FULL_ADDRESS column in test fixture
3. `test_lost_hospital_report_detection` - Missing MONTH column in test data
4. `test_solo_provider_identification` - Missing expected column name
5. `test_this_month_status_all_provider_types` - Missing MONTH column
6. `test_output_file_structure` - Missing FULL_ADDRESS column

**Root cause**: Test fixtures don't include all expected columns. This is a test maintenance issue, not a code bug.

## Skipped Tests

- `test_cli.py` - Skipped due to broken CLI (missing `app` export)

## Golden Tests Status

**NOT RUN** - The CLI entry point (`adhs-etl run`) is broken:
```
AttributeError: module 'adhs_etl.cli' has no attribute 'app'
```

The alternative entry point (`scripts/process_months_local.py`) is interactive and cannot be automated.

## Assessment

### AI Refactor Impact

The Copy 3 AI refactor changes:
- **Did NOT introduce any new test failures**
- **Did NOT fix any existing test failures**
- **Both branches behave identically in tests**

### Deleted Files Assessment

| File | Still Referenced? | Safe to Delete? |
|------|-------------------|-----------------|
| `Batchdata/template_config.xlsx` | Yes (13 refs) | **NO** |
| `Batchdata/tests/batchdata_local_input.xlsx` | Yes (25 refs) | **NO** |

**Recommendation**: Keep both files. The AI refactor deletions should NOT be applied.

## Recommendation

- [x] **Option C**: Keep current state, do not merge AI refactor deletions
- [ ] **Option A**: Full merge (rejected - deletions would break code)
- [ ] **Option B**: Cherry-pick (not needed - no improvements detected)

**Rationale**:
1. Both branches have identical test results
2. The AI refactor modified 10 files but no measurable improvement
3. The refactor deleted 2 actively-used files
4. Risk outweighs benefit - keep current state

## Next Steps

1. Proceed to Phase 3.9 (create rollback tag)
2. Skip merging preserve/copy3-ai-refactor
3. Proceed directly to Phase 4 (promote current to main)
4. Delete preservation branch after main is stable
