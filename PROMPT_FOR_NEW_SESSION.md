# Prompt for New Claude Code Session

Copy and paste this into a new Claude Code session to continue the file naming standardization work:

---

I need you to continue a **file naming standardization project** for the ADHS ETL pipeline.

**Current branch**: `feature/standardize-file-naming`
**Checkpoint**: `checkpoint-phase3-complete` tag

## What's Been Completed (Phases 0-3)
✅ Utils module created (`src/adhs_etl/utils.py`) with timestamp standardization
✅ Test expectations updated (TDD approach)
✅ Core ETL modules updated: `transform_enhanced.py`, `cli_enhanced.py`, `ecorp.py`

All core modules now generate files in **both** new format (`M.YY_{Stage}_{timestamp}.xlsx`) and legacy format for backward compatibility.

## What You Need to Do (Phases 4-10)

**Read this file FIRST**: `CONTINUE_FILE_NAMING_STANDARDIZATION.md` - it has comprehensive details on:
- What's been done
- Exactly what needs to be done
- Implementation strategies
- Code examples
- Validation steps

## Start Here

**Phase 4** is next - update scripts for APN/MCAO file creation:

1. Start with `scripts/process_months_local.py` (most critical)
   - Add utils imports
   - Generate session timestamp at start
   - Update APN/MCAO filename creation (change space to underscore)
   - Add legacy copy creation
   - Pass session timestamp to all downstream functions

2. Then update 4 remaining scripts (can use subagent)

3. Test with month 1.25

**Then proceed through Phases 5-10** as detailed in `CONTINUE_FILE_NAMING_STANDARDIZATION.md`.

## Key Constraints

- ✅ Create BOTH new and legacy format files (backward compatibility)
- ✅ Session timestamp must be consistent across all stages
- ✅ Use utils functions from `src/adhs_etl/utils.py`
- ✅ Commit each phase incrementally
- ✅ Follow the git commit message template in continuation guide

## Success =
All output files follow `M.YY_{Stage}_{timestamp}.xlsx` format + legacy copies, all tests pass, documentation updated, PR created.

**Let's continue!**
