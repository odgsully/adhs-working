# INVENTORY - `adhs-restore-28-Jul-2025` Copies

Generated: 2025-11-24

## Summary

- Current canonical folder: `adhs-restore-28-Jul-2025 copy`
- Goal: Preserve unique code states as git branches, no data loss.

## Unique Files by Folder

### Copy 3 vs Copy (Current)

Copy 3 is at same commit (`048874f`) but has AI refactor changes in working tree.

**Modified (9 files):**
- [x] Batchdata/src/batchdata_sync.py
- [x] Batchdata/src/io.py
- [x] Batchdata/src/normalize.py
- [x] Batchdata/src/run.py
- [x] Batchdata/src/transform.py
- [x] src/adhs_etl/batchdata_bridge.py
- [x] Batchdata/PIPELINE_INTEGRATION_GUIDE.md
- [x] Batchdata/README.md
- [x] Batchdata_Template.xlsx (tracked template)
- [x] v300Dialer_template.xlsx (tracked template)

**Added:**
- BD_PREFIX_MIGRATION_COMPLETE.md (also in current)
- Batchdata/BD_PREFIX_MIGRATION.md (also in current)

**DELETED (CRITICAL):**
- [x] Batchdata/template_config.xlsx - **Has 13 code references - KEEP**
- [x] Batchdata/tests/batchdata_local_input.xlsx - **Has 25 code references - KEEP**

**Verdict**: Preserve as `preserve/copy3-ai-refactor` but DO NOT apply deletions

---

### Copy 2 vs Copy (Current)

Copy 2 is at commit `a9d6e56` (2 commits behind `048874f`).

**Has uncommitted changes?** [x] Yes

**Unique content in Copy 2:**
- `.claude/hooks/*.py` files (8 hook scripts + utils directory)
- These hooks exist in Copy 2 but NOT in Current

**Changed files (mostly logs/session data):**
- Various `.env` file modifications
- Log file differences
- Documentation differences

**Verdict**: [x] Ignore - hooks can be recreated if needed, no unique code

---

### Copy 4 vs Copy (Current)

Copy 4 is at commit `048874f` (same as current).

**Has unique uncommitted changes?** [ ] No

**Differences:**
- Only `.gitignore` and `.claude/settings.local.json` differ
- No code differences

**Verdict**: [x] Ignore (subset of current, no unique content)

---

### Original vs Copy (Current)

Original is at commit `5f9b72a` on branch `Ensure-proper-through-analysis`.

**Status:** Vastly different - much older state

**Missing from Original:**
- Entire Batchdata/ directory structure
- Many newer scripts and modules
- MCAO, Ecorp integration files

**Unique to Original:**
- `.claude/hooks/*.py` files (same as Copy 2)
- `docs/ADHS_PRD_v1.0_cli.md`
- `ecorp/` directory (different structure)

**Verdict**: [x] Ignore - represents old checkpoint, all commits merged into current

---

## Assessment

### Likely Intentional Changes (Copy 3)
- Batchdata source file refactoring
- Updated pipeline integration docs
- Updated templates

### Suspected Accidental/Risky Changes (Copy 3)
- **Deletion of `template_config.xlsx`** - Still referenced in code
- **Deletion of `batchdata_local_input.xlsx`** - Still referenced in 25 files

### Open Questions
- Q: Are `template_config.xlsx` and `batchdata_local_input.xlsx` still needed?
- A: **YES** - Both have active code references. Keep until validated.

## Recommendation

Proceed to Phase 1.5: [x] Yes

Folders to preserve:
- **Copy 3**: Create `preserve/copy3-ai-refactor` (code changes only, no deletions)
- **Copy 2**: Skip (no unique code)
- **Copy 4**: Skip (subset of current)
- **Original**: Skip (all commits merged)
