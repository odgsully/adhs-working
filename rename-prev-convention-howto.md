# File Naming Convention Migration Guide

## Context

**Date**: November 15, 2024
**Branch**: `feature/standardize-file-naming`
**Status**: Implementation complete, backward compatible transition period active

The ADHS ETL pipeline has been standardized to use consistent file naming across all output stages:

**New Convention**: `M.YY_{Stage}_{timestamp}.xlsx`

Where:
- `M.YY` = Month code (e.g., `1.25` for January 2025)
- `{Stage}` = Processing stage (Reformat, Analysis, APN_Upload, etc.)
- `{timestamp}` = Timestamp in `MM.DD.HH-MM-SS` format (12-hour, no AM/PM)

**Example**: `1.25_Reformat_01.15.03-45-30.xlsx`

## Old vs New Naming Patterns

| Stage | Old Format | New Format | Notes |
|-------|------------|------------|-------|
| **Core Pipeline** |
| Reformat | `M.YY Reformat.xlsx` | `M.YY_Reformat_{timestamp}.xlsx` | Spaces → underscores, added timestamp |
| All-to-Date | `Reformat All to Date M.YY.xlsx` | `M.YY_Reformat_All_to_Date_{timestamp}.xlsx` | Reorganized order, underscores |
| Analysis | `M.YY Analysis.xlsx` | `M.YY_Analysis_{timestamp}.xlsx` | Spaces → underscores, added timestamp |
| **APN Processing** |
| APN Upload | `M.YY_APN_Upload.xlsx` | `M.YY_APN_Upload_{timestamp}.xlsx` | Added timestamp |
| APN Complete | `M.YY_APN_Complete.xlsx` | `M.YY_APN_Complete_{timestamp}.xlsx` | Added timestamp |
| **MCAO Processing** |
| MCAO Upload | `M.YY_MCAO_Upload.xlsx` | `M.YY_MCAO_Upload_{timestamp}.xlsx` | Added timestamp |
| MCAO Complete | `M.YY_MCAO_Complete.xlsx` | `M.YY_MCAO_Complete_{timestamp}.xlsx` | Added timestamp |
| **Ecorp Processing** |
| Ecorp Upload | `M.YY Ecorp Upload.xlsx` | `M.YY_Ecorp_Upload_{timestamp}.xlsx` | Spaces → underscores, added timestamp |
| Ecorp Complete | `M.YY Ecorp Complete.xlsx` | `M.YY_Ecorp_Complete_{timestamp}.xlsx` | Spaces → underscores, added timestamp |
| **BatchData Processing** |
| BatchData Upload | *(new)* | `M.YY_BatchData_Upload_{timestamp}.xlsx` | New stage added in Phase 7 |
| BatchData Complete | *(new)* | `M.YY_BatchData_Complete_{timestamp}.xlsx` | New stage added in Phase 7 |

## Timestamp Format Details

**Format**: `MM.DD.HH-MM-SS` (12-hour format, no AM/PM indicator)

**Examples**:
- `01.15.03-45-30` = January 15, 3:45:30 (AM)
- `12.25.11-30-15` = December 25, 11:30:15 (AM or PM)

**Why 12-hour format?**
- Compact (always 2 digits for hour)
- Sortable lexicographically
- Human-readable
- Avoids AM/PM confusion in filenames

## Backward Compatibility

### Current Implementation (Phases 1-8)

**Dual-File Strategy**: The pipeline creates BOTH formats during the transition period.

For every output, two files are created:
1. **New format** (primary): `1.25_Reformat_01.15.03-45-30.xlsx`
2. **Legacy format** (compatibility): `1.25 Reformat.xlsx`

**Implementation**: All core modules use `save_excel_with_legacy_copy()` from `src/adhs_etl/utils.py`

```python
from adhs_etl.utils import save_excel_with_legacy_copy

# Creates both new and legacy files automatically
save_excel_with_legacy_copy(new_path, legacy_path)
```

### Reading Files (Dual Pattern Support)

Code that reads files supports BOTH patterns via glob:

```python
# Old code (single pattern)
files = list(dir.glob("Reformat All to Date *.xlsx"))

# New code (dual pattern support)
new_files = list(dir.glob("*_Reformat_All_to_Date_*.xlsx"))
old_files = list(dir.glob("Reformat All to Date *.xlsx"))
all_files = new_files + old_files
```

**Why this approach?**
- Zero breaking changes to existing workflows
- Gradual migration without data loss
- Legacy files can be deprecated later

## Session Timestamp Consistency

**Critical Feature**: All outputs from a single month processing session share the same timestamp.

**Implementation** in `scripts/process_months_local.py`:

```python
# Generate session timestamp ONCE
session_timestamp = get_standard_timestamp()

# Pass to all stages
create_reformat_output(df, month, year, output_dir, timestamp=session_timestamp)
create_all_to_date_output(df, month, year, output_dir, timestamp=session_timestamp)
create_analysis_output(df, month, year, output_dir, timestamp=session_timestamp)
# ... APN, MCAO, Ecorp, BatchData all use same timestamp
```

**Benefits**:
- Easy to identify related files from same processing run
- Simplifies troubleshooting
- Enables batch operations on session outputs

## Future Migration (Not Performed Yet)

### Phase 2: Deprecate Legacy Format (Future)

**When**: After confirming all downstream systems support new format (estimated 3-6 months)

**Actions**:
1. Remove `save_excel_with_legacy_copy()` calls
2. Update code to write only new format
3. Keep dual-pattern glob support for reading old files
4. Add deprecation warnings when old files are encountered

### Phase 3: Remove Legacy Support (Future)

**When**: After all existing old-format files are no longer in active use (estimated 6-12 months)

**Actions**:
1. Remove dual-pattern glob support
2. Remove `get_legacy_filename()` function
3. Clean up old format files from output directories

### Migration Prompt Template for Claude Code

When ready to migrate existing files, use this prompt:

```markdown
I need to rename existing files in the ADHS ETL output directories to the new naming convention.

**Context**:
- Old format: `M.YY Reformat.xlsx` (spaces, no timestamp)
- New format: `M.YY_Reformat_{timestamp}.xlsx` (underscores, with timestamp)

**Directories to migrate**:
- Reformat/
- All-to-Date/
- Analysis/
- APN/Upload/
- APN/Complete/
- MCAO/Upload/
- MCAO/Complete/
- Ecorp/Upload/
- Ecorp/Complete/

**Requirements**:
1. Scan each directory for old-format files
2. For each file, generate timestamp from file modification time
3. Rename to new format: replace spaces with underscores, add timestamp
4. Preserve file modification times
5. Create backup of original files before renaming
6. Generate migration log with old → new mappings

**Safety**:
- Dry-run mode first to show what would be renamed
- Confirm before executing
- Keep backups until verified

Please create a Python script to perform this migration safely.
```

## Implementation Summary

### Files Modified (Phases 0-8)

**Phase 1: Utils Module**
- `src/adhs_etl/utils.py` (NEW) - Core timestamp and filename functions

**Phase 3: Core ETL**
- `src/adhs_etl/transform_enhanced.py` - Reformat and All-to-Date outputs
- `src/adhs_etl/cli_enhanced.py` - Analysis output
- `src/adhs_etl/ecorp.py` - Ecorp Upload and Complete

**Phase 4: Scripts**
- `scripts/process_months_local.py` - Main processing script
- `scripts/process_months_local 2.py` - Backup copy
- `scripts/batch_process_months.py` - Batch processor
- `scripts/process_months_menu.py` - Menu interface
- `scripts/generate_125_analysis.py` - Analysis generator

**Phase 5: APN Module**
- `APN/apn_lookup.py` - APN lookup service

**Phase 6: Batchdata Pipeline**
- `Batchdata/src/io.py` - I/O operations
- `Batchdata/src/run.py` - Pipeline runner
- `Batchdata/src/batchdata.py` - Core logic

**Phase 7: BatchData Integration**
- `src/adhs_etl/batchdata_bridge.py` (NEW) - Bridge module
- `Batchdata/template_config.xlsx` (NEW) - Template configuration
- `scripts/process_months_local.py` - Added BatchData menu integration
- `.gitignore` - Added BatchData directories

**Phase 8: Documentation**
- `README.md` - Updated with new naming and standalone commands
- `PIPELINE_FLOW.md` - Updated flowchart and stage descriptions
- `claude.md` - Updated folder structure and output files
- `Batchdata/README.md` - Updated examples
- `Batchdata/docs/BATCHDATA.md` - Updated file patterns
- `Ecorp/README.md` - Updated file references
- `Ecorp/FIELD_MAPPING.md` - Updated examples
- `MCAO/Want-to-edit-MCAO?.md` - Cleanup
- `scripts/README.md` - Updated batch processing examples

### Test Files Updated (Phase 2)
- `Batchdata/tests/test_template_output.py`
- `Batchdata/tests/test_integration.py`

## Timeline

### Completed
- ✅ **Phase 0** (Nov 2024): Setup, baseline tests, rollback tag
- ✅ **Phase 1** (Nov 2024): Utils module created
- ✅ **Phase 2** (Nov 2024): Test expectations updated
- ✅ **Phase 3** (Nov 2024): Core ETL modules updated
- ✅ **Phase 4** (Nov 2024): Scripts updated (4.1 + 4.2)
- ✅ **Phase 5** (Nov 2024): APN module updated
- ✅ **Phase 6** (Nov 2024): Batchdata pipeline updated
- ✅ **Phase 7** (Nov 2024): BatchData integration added
- ✅ **Phase 8** (Nov 2024): Documentation updated
- ✅ **Phase 9** (Nov 2024): .gitignore updated (completed in Phase 7)
- ✅ **Phase 10** (Nov 2024): Migration guide created (this document)

### Next Steps
- 🔄 **Final Testing**: Full integration test with month 1.25
- 🔄 **Code Review**: Review all changes before PR
- 🔄 **PR Creation**: `feature/standardize-file-naming` → `main`

### Future (Not Scheduled)
- ⏳ **Phase 2.1**: Deprecate legacy format creation (3-6 months)
- ⏳ **Phase 2.2**: Migrate existing old-format files (6-12 months)
- ⏳ **Phase 3**: Remove legacy support entirely (12+ months)

## Rollback Instructions

If issues are discovered and rollback is needed:

```bash
# Checkout the rollback tag
git checkout pre-naming-standardization

# Or, if on feature branch, revert to main
git checkout main
git branch -D feature/standardize-file-naming
```

**Rollback tag**: `pre-naming-standardization` (created before Phase 0)

## Testing Checklist

Before merging to main:

- [ ] All tests pass: `poetry run pytest -v`
- [ ] Full integration test with month 1.25 (all 5 stages)
- [ ] Verify both file formats created correctly
- [ ] Verify session timestamp consistency across all outputs
- [ ] Verify backward compatibility (old files still readable)
- [ ] Verify imports work: `python3 -c "from src.adhs_etl.utils import *"`
- [ ] Code review completed
- [ ] Documentation reviewed and accurate

## Support and Questions

For questions or issues:
1. Review this migration guide
2. Check `CONTINUE_FILE_NAMING_STANDARDIZATION.md` for implementation details
3. Review commit messages for specific changes
4. Check git log: `git log --oneline feature/standardize-file-naming`

## Key Benefits

✅ **Consistency**: All outputs follow same naming pattern
✅ **Traceability**: Timestamp enables session tracking
✅ **Sortability**: Lexicographic sort works correctly
✅ **Compatibility**: Backward compatible during transition
✅ **Automation-friendly**: Predictable patterns for scripting
✅ **Human-readable**: Clear stage identification

---

**Document Version**: 1.0
**Last Updated**: November 15, 2024
**Status**: Active - Transition Period
