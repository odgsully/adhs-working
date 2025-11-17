# Environment File Consolidation Plan

**Goal**: SIMPLE, CONSERVATIVE, CLEAN - One `.env.sample`, one `.env`, BatchData points to root.

---

## Current State → Target State

```
BEFORE (5 files):                    AFTER (2 files):
├── .env ✅                           ├── .env ✅ (enhanced)
├── .env.sample                       ├── .env.sample (consolidated)
├── .env.example ❌
├── Batchdata/.env.sample ❌
└── Ecorp/agent_ecorp/.env.sample ❌
```

**Problem**:
- Batchdata violates CLAUDE.md rule #2 (should use centralized config)
- 4 redundant template files
- BD_* keys not in root config

---

## Prerequisites Verification

**Run before starting**:

```bash
# 1. Verify current state matches assumptions
ls -la .env .env.sample .env.example Batchdata/.env.sample Ecorp/agent_ecorp/.env.sample

# 2. Verify NO local Batchdata/.env exists (should fail)
ls -la Batchdata/.env  # Should error: No such file

# 3. Compare sample files for conflicts
diff .env.sample .env.example
# Note any conflicts (same key, different values)

# 4. Verify .gitignore coverage
grep "^\.env$" .gitignore  # Should exist

# 5. Create feature branch
git checkout -b chore/consolidate-env-files
```

**Conflict Resolution Strategy**:
- If `.env.sample` and `.env.example` have **same key, different values**: Keep `.env.sample` value (it's the Python standard)
- Document any conflicts in commit message

---

## Changes At-a-Glance

### Files to Delete (3)
| File | Reason |
|------|--------|
| `.env.example` | Redundant - merged into .env.sample |
| `Batchdata/.env.sample` | Redundant - keys in root .env.sample |
| `Ecorp/agent_ecorp/.env.sample` | Redundant - Ecorp uses no API keys |

### Files to Modify (8)

| File | Lines | Change | Type |
|------|-------|--------|------|
| `.env.sample` | Add section | Add BatchData keys + merge .env.example | Config |
| `Batchdata/src/run.py` | 1-10, 125 | Add `Path` import, explicit .env path | Code |
| `README.md` | 69-79 | Add BatchData keys to env vars | Docs |
| `Batchdata/README.md` | 20-38 | Reference root .env | Docs |
| `Batchdata/docs/BATCHDATA.md` | 26-38 | Update config instructions | Docs |
| `Batchdata/docs/examples/PRD_BatchData_Bulk_Pipeline.md` | Throughout | Reference root .env | Docs |
| `Batchdata/docs/examples/claude_code_prompt.md` | Throughout | Update env var instructions | Docs |
| `PIPELINE_FLOW.md` | 180-185 | Include BatchData keys | Docs |
| `ADHS-ETL-INDEX.md` | 10 | Note BatchData keys available | Docs |

---

## Execution Steps

### Step 1: Consolidate Sample Files

```bash
# 1.1 Review differences
diff .env.sample .env.example > /tmp/env-diff.txt
cat /tmp/env-diff.txt
# Manually review and note any unique variables

# 1.2 Add BatchData section to .env.sample
# (See code block below)

# 1.3 Delete redundant files
rm .env.example
rm Batchdata/.env.sample
rm Ecorp/agent_ecorp/.env.sample
```

**Add to `.env.sample`** (after existing MCAO keys):

```bash
# ======================
# BatchData API Keys (Optional - Stage 5)
# ======================
# Required for contact discovery enrichment pipeline
# See: Batchdata/README.md for API details and costs

# Skip-trace API: $0.07 per record
BD_SKIPTRACE_KEY=your-batchdata-skiptrace-key

# Address verification API (optional)
BD_ADDRESS_KEY=your-batchdata-address-key

# Property search API (optional)
BD_PROPERTY_KEY=your-batchdata-property-key

# Phone verification/DNC/TCPA API: $0.007-0.002 per phone
BD_PHONE_KEY=your-batchdata-phone-key
```

### Step 2: Fix BatchData Code

**File**: `Batchdata/src/run.py`

**Line 1-10** - Add import (Path not currently imported):
```python
"""
run.py - CLI entrypoint for BatchData pipeline
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path  # ADD THIS LINE
from dotenv import load_dotenv
import pandas as pd
```

**Line 125** - Change from:
```python
    # Load environment variables
    load_dotenv()
```

**To**:
```python
    # Load environment variables from project root
    load_dotenv(Path(__file__).parent.parent.parent / '.env')
```

### Step 3: Update Documentation (Batch)

**Use multi-file search/replace** for efficiency:

```bash
# Update all docs to reference "root .env" instead of "Batchdata/.env"
# Update all docs to remove "cp .env.example .env" instructions
# Update all docs to add BatchData keys section
```

**Specific updates** (see detailed changes in Appendix A):
1. `README.md` - Add BatchData keys to env vars section
2. `Batchdata/README.md` - Remove "cp .env.example" step, reference root
3. `Batchdata/docs/BATCHDATA.md` - Update configuration section
4. `Batchdata/docs/examples/PRD_BatchData_Bulk_Pipeline.md` - Reference root .env
5. `Batchdata/docs/examples/claude_code_prompt.md` - Update env instructions
6. `PIPELINE_FLOW.md` - Add BatchData keys to config section
7. `ADHS-ETL-INDEX.md` - Note BatchData keys available in .env

---

## Critical User Action

⚠️ **IMPORTANT**: After deployment, users must MANUALLY add BatchData keys to their working `.env` file:

```bash
# Users with existing .env:
# 1. Open your .env file
# 2. Add the BD_* keys (copy from .env.sample)
# 3. Fill in your actual API keys

# New users:
cp .env.sample .env
# Edit .env with your keys
```

**The `.env.sample` is just a template - it doesn't automatically update your `.env`**

---

## Validation Checklist

### Pre-Deployment
- [ ] Prerequisites completed (branch created, files verified)
- [ ] Conflicts in .env.sample vs .env.example resolved
- [ ] `.env.sample` has BatchData keys section added
- [ ] `Path` import added to `Batchdata/src/run.py`
- [ ] `load_dotenv()` path fixed in `Batchdata/src/run.py:125`
- [ ] All 7 docs updated to reference root .env
- [ ] 3 files deleted (.env.example, 2x .env.sample)

### Post-Deployment Tests

```bash
# 1. File structure verification
test -f .env && test -f .env.sample && echo "✓ Core files exist"
test ! -f .env.example && test ! -f Batchdata/.env.sample && echo "✓ Deleted files gone"

# 2. Import test
cd Batchdata
python3 -c "from src.run import load_dotenv; print('✓ Import successful')"

# 3. BatchData dry-run (requires test input file)
python3 src/run.py --input tests/batchdata_local_input.xlsx --dry-run
# Should output: "Dry run complete - no processing performed"

# 4. Main ETL test
cd ..
poetry run pytest src/tests/test_transform.py -v
# Should pass

# 5. Documentation grep
grep -r "Batchdata/\.env" . --include="*.md" | grep -v consolidate-envs.md
# Should return empty (no docs reference Batchdata/.env)

# 6. Verify all docs updated
for doc in README.md Batchdata/README.md Batchdata/docs/BATCHDATA.md \
  Batchdata/docs/examples/PRD_BatchData_Bulk_Pipeline.md \
  Batchdata/docs/examples/claude_code_prompt.md \
  PIPELINE_FLOW.md ADHS-ETL-INDEX.md; do
  echo "Checking $doc..."
  grep -q "root.*\.env\|project.*\.env\|BD_SKIPTRACE_KEY" "$doc" && echo "  ✓" || echo "  ✗ MISSING"
done
```

---

## Rollback Plan

**If something breaks**:

```bash
# Before committing (if testing fails):
git checkout .
git clean -fd

# After committing (if issues in production):
git revert HEAD
# Or
git reset --hard HEAD~1
git push --force  # Only if not shared with team yet

# Restore deleted files from git history:
git checkout HEAD~1 -- .env.example Batchdata/.env.sample Ecorp/agent_ecorp/.env.sample
```

---

## Risk Assessment

### What Could Break

| Scenario | Risk | Impact | Mitigation |
|----------|------|--------|------------|
| User has local `Batchdata/.env` | Low | Ignored after change | Document in commit msg, CHANGELOG |
| `.env.example` has unique keys | Low | Keys not merged | Step 1.1 manual review |
| `Path` import conflict | Minimal | Runtime error | Verified not imported, will work |
| Doc references missed | Medium | Confusion | Comprehensive grep in validation |

### What Won't Break

✅ **Existing `.env` file** - Unchanged, continues working
✅ **Main ETL pipeline** - No changes to core code
✅ **MCAO processing** - No changes
✅ **Ecorp processing** - No changes
✅ **CI/CD** - No env vars in `.github/workflows/ci.yml`
✅ **Users without BatchData** - Optional Stage 5, no impact

---

## Commit & PR

### Commit Message

```
chore: consolidate environment files to root .env

Consolidates all environment configuration to single .env file at project root.

Changes:
- Merge .env.example into .env.sample, add BatchData keys
- Delete 3 redundant files (.env.example, 2x module .env.sample)
- Fix Batchdata/src/run.py to use explicit root .env path
- Update 7 docs to reference centralized .env

Benefits:
- Single source of truth for environment configuration
- Eliminates confusion from multiple sample files
- Aligns with CLAUDE.md rule #2 (centralized config)
- Simplifies setup for new developers

Breaking changes: None (existing .env continues working)

IMPORTANT: Users must manually add BD_* keys to their .env file
(see consolidate-envs.md for details)

Conflicts resolved:
- [List any .env.sample vs .env.example conflicts and resolutions]

Closes #[issue-number]
```

### PR Checklist

- [ ] All validation tests pass
- [ ] Documentation updated (7 files)
- [ ] Code changes minimal (1 file, 2 lines)
- [ ] Rollback plan tested
- [ ] User migration notes in PR description
- [ ] No breaking changes to existing deployments

---

## Appendix A: Detailed Documentation Changes

### A.1 README.md

**Lines 69-79** - Update environment variables section:

**Change from**:
```markdown
Copy `.env.example` to `.env` and configure:

```bash
MCAO_API_KEY=your-api-key
FUZZY_THRESHOLD=80.0
LOG_LEVEL=INFO
```
```

**To**:
```markdown
Copy `.env.sample` to `.env` and configure:

```bash
# Main ETL Configuration
MCAO_API_KEY=your-api-key
FUZZY_THRESHOLD=80.0
LOG_LEVEL=INFO

# BatchData API Keys (Optional - Stage 5 enrichment)
BD_SKIPTRACE_KEY=your-batchdata-key
BD_ADDRESS_KEY=your-batchdata-key
BD_PROPERTY_KEY=your-batchdata-key
BD_PHONE_KEY=your-batchdata-key
```
```

### A.2 Batchdata/README.md

**Lines 20-38** - Update installation section:

**Change from**:
```markdown
2. Copy environment template:
```bash
cp .env.example .env
```

3. Configure your BatchData API keys in `.env`:
```bash
BD_SKIPTRACE_KEY=your_skiptrace_api_key_here
...
```
```

**To**:
```markdown
2. Configure BatchData API keys in project root `.env`:
```bash
# See root .env.sample for complete configuration template
# Add these keys to your root .env file:

BD_SKIPTRACE_KEY=your_skiptrace_api_key_here
BD_ADDRESS_KEY=your_address_verify_api_key_here
BD_PROPERTY_KEY=your_property_api_key_here
BD_PHONE_KEY=your_phone_verification_api_key_here
```

**Note**: BatchData uses the centralized `.env` file at the project root, not a local Batchdata/.env file.
```

### A.3-A.7 Other Documentation

Similar pattern: Replace references to "Batchdata/.env" or "local .env" with "project root .env" and note that BatchData keys should be added to the main `.env.sample`.

---

## Future Phase: Settings Class Integration (Deferred)

**Not included in this plan** to keep it simple. Future work:

```python
# src/adhs_etl/config.py - Add BatchData fields
class Settings(BaseSettings):
    # ... existing ...
    bd_skiptrace_key: Optional[str] = Field(default=None)
    bd_address_key: Optional[str] = Field(default=None)
    bd_property_key: Optional[str] = Field(default=None)
    bd_phone_key: Optional[str] = Field(default=None)

# Batchdata/src/batchdata.py - Use Settings
from adhs_etl.config import Settings
settings = Settings()
api_keys = {'BD_SKIPTRACE_KEY': settings.bd_skiptrace_key, ...}
```

**Benefits**: Type checking, validation, better IDE support
**Complexity**: Higher - separate PR recommended

---

## Summary

**Simple**: 3 deletes, 8 updates, 2 line code change
**Conservative**: Existing .env unchanged, no Settings refactor
**Clean**: One .env.sample, explicit paths, zero redundancy

**Time estimate**: 30 minutes execution + testing
