# Continue: File Naming Standardization Implementation

## Quick Context

You are continuing a **file naming standardization project** for the ADHS ETL pipeline. The goal is to standardize ALL output file naming to: `M.YY_{Stage}_{timestamp}.xlsx` where timestamp = `MM.DD.HH-MM-SS` (12-hour format, no AM/PM).

**Branch**: `feature/standardize-file-naming`
**Checkpoint Tag**: `checkpoint-phase3-complete`
**Rollback Tag**: `pre-naming-standardization`

## What's Been Completed (Phases 0-3)

### ✅ Phase 0: Setup
- Feature branch created
- Baseline tests documented (`baseline_tests.log`)
- Rollback tag created

### ✅ Phase 1: Utils Module
**File**: `src/adhs_etl/utils.py` (NEW)

Functions created:
- `get_standard_timestamp()` - Returns `MM.DD.HH-MM-SS` format
- `format_output_filename(month_code, stage, timestamp)` - Returns `M.YY_{Stage}_{timestamp}.xlsx`
- `get_legacy_filename(month_code, stage, timestamp)` - Returns old format for compatibility
- `save_excel_with_legacy_copy(new_path, legacy_path)` - Creates both versions
- `extract_timestamp_from_filename(filename)` - Parses timestamp from filename
- `extract_month_code_from_filename(filename)` - Parses month code

### ✅ Phase 2: Test Expectations (TDD)
**Files Updated**:
- `Batchdata/tests/test_template_output.py`
- `Batchdata/tests/test_integration.py`

Tests now expect new naming format (will fail until implementation updated).

### ✅ Phase 3: Core ETL Modules
**Files Updated**:

1. **`src/adhs_etl/transform_enhanced.py`**
   - `create_reformat_output()` - New: `M.YY_Reformat_{timestamp}.xlsx`
   - `rebuild_all_to_date_from_monthly_files()` - New: `M.YY_Reformat_All_to_Date_{timestamp}.xlsx`
   - `create_all_to_date_output()` - New format + dual glob pattern support
   - All functions create legacy copies

2. **`src/adhs_etl/cli_enhanced.py`**
   - Analysis file creation - New: `M.YY_Analysis_{timestamp}.xlsx`
   - `get_all_historical_data()` - Dual glob pattern support
   - Legacy copy creation

3. **`src/adhs_etl/ecorp.py`**
   - `generate_ecorp_upload()` - New: `M.YY_Ecorp_Upload_{timestamp}.xlsx`
   - `generate_ecorp_complete()` - New: `M.YY_Ecorp_Complete_{timestamp}.xlsx`
   - Timestamp extraction using new utils
   - Legacy copies for both

**Key Changes**:
- All core modules import utils functions
- All accept optional `timestamp` parameter (for session consistency)
- All create BOTH new format and legacy format files
- Dual glob patterns support reading old and new formats

## What Remains (Phases 4-10 + Final)

### 🔄 Phase 4: Update Scripts (5 files)
**Critical for APN/MCAO file creation**

Files to update:
1. **`scripts/process_months_local.py`** ⭐ MOST IMPORTANT
   - Lines 551-555: APN Upload filename (change space to underscore)
   - Lines 620-624: MCAO Upload filename (change space to underscore)
   - Lines 758-761: MCAO Complete filename (change space to underscore)
   - Line 972: Update glob pattern for MCAO Complete
   - Lines 613-621: Update timestamp extraction logic
   - **CRITICAL**: Generate session timestamp once at start, pass to all stages
   - Add utils imports
   - Create legacy copies for all outputs

2. **`scripts/process_months_local 2.py`**
   - Same changes as #1 (it's a backup copy)

3. **`scripts/batch_process_months.py`**
   - Update file reference patterns
   - Add session timestamp if needed

4. **`scripts/process_months_menu.py`**
   - Lines 177, 223, 232, 375: Update filename patterns

5. **`scripts/generate_125_analysis.py`**
   - Update filename references to new format

**Strategy**: Can use subagent for files #2-5, but handle #1 directly (complex logic).

### 🔄 Phase 5: Update APN Module (1 file)
**File**: `APN/apn_lookup.py`
- Lines 645-646: Use `get_standard_timestamp()`
- Line 662: APN Complete filename (underscore, not space)
- Lines 650-653: Update timestamp extraction logic
- Accept timestamp parameter for session consistency
- Create legacy copies

### 🔄 Phase 6: Update Batchdata Pipeline (3 files)
**Files**:
1. `Batchdata/src/io.py`
   - Lines 22-23: Change `%Y%m%d_%H%M%S` → `%m.%d.%I-%M-%S`
   - Lines 229-230: Update template filename (underscores)

2. `Batchdata/src/run.py`
   - Line 129: Change timestamp format
   - Update output filenames for Upload/Complete

3. `Batchdata/src/batchdata.py`
   - Line 224: Change timestamp format for batch files

**Strategy**: Use subagent for coordinated updates.

### 🔄 Phase 7: BatchData Integration (NEW)
**Create**:
1. **`src/adhs_etl/batchdata_bridge.py`** (NEW)
   ```python
   def create_batchdata_upload(ecorp_complete_path, month_code, timestamp, config_template):
       # Transform Ecorp Complete → BatchData Upload
       # Save to /Batchdata/Upload/M.YY_BatchData_Upload_{timestamp}.xlsx

   def run_batchdata_enrichment(upload_path, month_code, config, dry_run=False):
       # Execute BatchData pipeline
       # Save to /Batchdata/Complete/M.YY_BatchData_Complete_{timestamp}.xlsx
   ```

2. **`Batchdata/template_config.xlsx`** (NEW)
   - Copy CONFIG from existing `batchdata_local_input.xlsx`
   - Copy BLACKLIST_NAMES from existing `batchdata_local_input.xlsx`
   - Empty INPUT_MASTER sheet

3. **Create directories**:
   - `Batchdata/Upload/` (with .gitkeep)
   - `Batchdata/Complete/` (with .gitkeep)

4. **Modify**: `scripts/process_months_local.py`
   - After Ecorp Complete step, add optional BatchData menu item
   - Import bridge functions
   - Pass session timestamp

### 🔄 Phase 8: Update Documentation (10+ files)
**Use subagent for systematic updates**

Files:
1. `README.md`
   - Lines 97-106: Update Output Files section
   - **ADD NEW SECTION**: "Individual Stage Commands & Testing"
     - Document ETL-integrated commands
     - Document standalone commands for each stage
     - Show `batchdata_local_input.xlsx` usage

2. `PIPELINE_FLOW.md` - Lines 18-143: All file patterns
3. `CLAUDE.md` - Lines 10-11: Output Files section
4. `Batchdata/README.md` - Lines 51-99: Usage examples
5. `Batchdata/docs/BATCHDATA.md` - All file patterns
6. `Ecorp/README.md` - Lines 13, 20, 26, 148
7. `MCAO/Want-to-edit-MCAO?.md` - Line 91
8. `v300Track_this.md` - Any filename references
9. `scripts/README.md` - Example commands
10. `Ecorp/FIELD_MAPPING.md` - If it has filename references

**Standard**: Use `{timestamp}` placeholder in examples (not real timestamps).

### 🔄 Phase 9: Update .gitignore (trivial)
Add:
```gitignore
# Generated outputs
Batchdata/Upload/*.xlsx
Batchdata/Complete/*.xlsx
!Batchdata/Upload/.gitkeep
!Batchdata/Complete/.gitkeep
```

### 🔄 Phase 10: Create Migration Guide (1 file)
**File**: `rename-prev-convention-howto.md` (NEW)

Content:
```markdown
# File Naming Convention Migration Guide

## Context
[Date], standardized to: M.YY_{Stage}_{timestamp}.xlsx

## Old vs New
[Table of all patterns]

## Backward Compatibility
Files created in BOTH formats during transition.

## Future Migration (Not Performed Yet)
[Prompt template for Claude Code to rename existing files]

## Timeline
- Phase 1: Dual format (current)
- Phase 2: Deprecate legacy (future)
- Phase 3: Remove legacy (future)
```

### 🔄 Final: Testing & Validation
1. Run full test suite: `poetry run pytest -v`
2. Integration test with month 1.25 (all stages)
3. Verify both file formats created correctly
4. Code review
5. Create PR: `feature/standardize-file-naming` → `main`

## Key Implementation Details

### Session Timestamp
**CRITICAL**: Generate timestamp ONCE per month processing session, pass to all stages.

In `scripts/process_months_local.py`:
```python
from adhs_etl.utils import get_standard_timestamp

# Generate session timestamp
session_timestamp = get_standard_timestamp()

# Pass to all stage functions
create_reformat_output(df, month, year, output_dir, timestamp=session_timestamp)
create_all_to_date_output(df, month, year, output_dir, timestamp=session_timestamp)
# ... etc for Analysis, APN, MCAO, Ecorp, BatchData
```

### Backward Compatibility Strategy
**Duplicate files** (not dual-pattern logic):
- Write new format: `1.25_Reformat_01.15.03-45-30.xlsx`
- Copy to legacy: `1.25 Reformat.xlsx`

All modules use `save_excel_with_legacy_copy()` from utils.

### Glob Pattern Updates
Where code reads files, support BOTH patterns:
```python
# Old: list(dir.glob("Reformat All to Date *.xlsx"))
# New:
new_files = list(dir.glob("*_Reformat_All_to_Date_*.xlsx"))
old_files = list(dir.glob("Reformat All to Date *.xlsx"))
all_files = new_files + old_files
```

## Validation Checklist

After each phase:
- [ ] Files import successfully
- [ ] Relevant tests pass (or expected to fail for TDD)
- [ ] Commit phase with clear message
- [ ] Update todo list

## Git Strategy

**Branch**: `feature/standardize-file-naming`
**Commits**: One per completed phase
**Final**: PR to `main` after all phases complete

Commit message template:
```
Phase N: [Description]

- [Change 1]
- [Change 2]
- [Change 3]

[Any important notes]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## How to Continue

### Step 1: Verify Current State
```bash
git checkout feature/standardize-file-naming
git status
git log --oneline -5
```

You should see:
- Branch: `feature/standardize-file-naming`
- Recent commits for Phases 0-2 and Phase 3
- Tag: `checkpoint-phase3-complete`

### Step 2: Start with Phase 4
Begin with **`scripts/process_months_local.py`** - the most critical script.

1. Read the file to understand current structure
2. Add utils imports at top
3. Generate session timestamp at start of processing
4. Update APN Upload filename creation (lines 551-555)
5. Update MCAO Upload filename creation (lines 620-624)
6. Update MCAO Complete filename creation (lines 758-761)
7. Update glob pattern (line 972)
8. Add legacy copy creation for each file
9. Pass session timestamp to all downstream functions

### Step 3: Use Subagents Strategically
- **Phase 4 scripts #2-5**: Use subagent (similar patterns)
- **Phase 6 Batchdata**: Use subagent (3 coordinated files)
- **Phase 8 Documentation**: Use subagent (10 files, systematic updates)

### Step 4: Progressive Testing
After Phase 4: Test process_months_local.py with month 1.25
After Phase 6: Test Batchdata standalone with dry-run
After Phase 10: Full integration test

### Step 5: Final Validation
- Run: `poetry run pytest -v`
- Verify both file formats created
- Code review
- Create PR

## Important Files Reference

**Core Utils**: `src/adhs_etl/utils.py`
**Already Updated**: `transform_enhanced.py`, `cli_enhanced.py`, `ecorp.py`
**Main Script**: `scripts/process_months_local.py` ⭐
**Test Config**: `batchdata_local_input.xlsx` (reference for template)

## Success Criteria

- [ ] All output files follow `M.YY_{Stage}_{timestamp}.xlsx` format
- [ ] Legacy copies created for all files
- [ ] Session timestamp consistent across all stages
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Integration test successful (month 1.25, all stages)
- [ ] Both file formats verified in output directories
- [ ] PR created to main

## Estimated Work

- **Phase 4**: 30-40 minutes (critical, complex)
- **Phase 5**: 10 minutes (similar to core modules)
- **Phase 6**: 15 minutes (3 files, subagent)
- **Phase 7**: 20 minutes (new integration)
- **Phase 8**: 20 minutes (docs, subagent)
- **Phase 9-10**: 5 minutes (trivial)
- **Final Testing**: 15-20 minutes

**Total**: ~2 hours of focused work

## Notes

- This is a **non-breaking change** (backward compatible)
- Existing files unchanged (new files get both formats)
- Can be deprecated later (Phase 2: remove legacy format generation)
- Session timestamp ensures consistency across all outputs
- Tests updated first (TDD) - they currently fail as expected

## Quick Start Command

```bash
# Verify you're on the right branch
git checkout feature/standardize-file-naming
git log --oneline -3

# Should show:
# 2817353 Phase 3: Update core ETL modules with new naming
# 7fd5d42 Phase 0-2: Setup, utilities, and test expectations
# ...

# Start with Phase 4
code scripts/process_months_local.py
```

Good luck! 🚀
