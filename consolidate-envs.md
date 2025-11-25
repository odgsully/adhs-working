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

---

# PHASE 1 STATUS: COMPLETED ✅

Phase 1 (File Consolidation) has been executed:
- ✅ `Batchdata/src/run.py:126` now loads from project root: `load_dotenv(Path(__file__).parent.parent.parent / '.env')`
- ✅ BatchData keys documented in `.env.sample`
- ⚠️ Redundant files may still exist (`.env.example`, subdirectory samples) - verify and clean up

---

# PHASE 2: Settings Class Centralization

**Goal**: Eliminate direct `os.getenv()` calls in business logic, centralize all config through Pydantic Settings.

## Problems Identified (8 Fragmentation Issues)

### Code-Level Violations

| # | File | Line(s) | Issue | Severity |
|---|------|---------|-------|----------|
| 1 | `src/adhs_etl/mcao_client.py` | 17, 21 | Module-level `load_dotenv()` - runs on every import | HIGH |
| 2 | `src/adhs_etl/mcao_client.py` | 39 | `os.getenv("MCAO_API_KEY")` bypasses Settings | HIGH |
| 3 | `src/adhs_etl/batchdata_bridge.py` | 284-287 | Direct `os.getenv()` for BD_* keys in business logic | MEDIUM |
| 4 | `Batchdata/src/batchdata.py` | 344-347 | `create_client_from_env()` uses `os.getenv()` directly | MEDIUM |
| 5 | `scripts/process_months_local.py` | - | Imports Settings but never instantiates it | LOW |
| 6 | `src/adhs_etl/cli_enhanced.py` | - | Imports Settings but never instantiates it | LOW |

### Configuration Mismatches

| # | Issue | Details |
|---|-------|---------|
| 7 | Prefix mismatch | Settings expects `ADHS_MCAO_API_KEY`, .env has `MCAO_API_KEY` |
| 8 | Missing fields | BatchData keys not in Settings class at all |

### Architectural Issues

- **3 separate `load_dotenv()` calls**: mcao_client.py, Batchdata/run.py, various scripts
- **Settings imported but unused**: Entry points import Settings but use hardcoded paths
- **No single source of truth**: Some config from Settings, some from os.getenv(), some from CONFIG sheet

---

## Implementation Steps

### Step 1: Enhance Settings Class

**File**: `src/adhs_etl/config.py`

**1.1 Add AliasChoices import and update mcao_api_key field:**

```python
from pydantic import Field, AliasChoices  # Add AliasChoices to import

# Change mcao_api_key field (around line 59-62) from:
mcao_api_key: Optional[str] = Field(default=None, description="MCAO API key")

# To:
mcao_api_key: Optional[str] = Field(
    default=None,
    description="MCAO API key for property data",
    validation_alias=AliasChoices("MCAO_API_KEY", "ADHS_MCAO_API_KEY"),
)
```

**1.2 Add BatchData API key fields (after mcao fields):**

```python
# BatchData API Keys (Stage 5 - Optional)
bd_skiptrace_key: Optional[str] = Field(
    default=None,
    description="BatchData skip-trace API key",
    validation_alias=AliasChoices("BD_SKIPTRACE_KEY"),
)
bd_address_key: Optional[str] = Field(
    default=None,
    description="BatchData address verification API key",
    validation_alias=AliasChoices("BD_ADDRESS_KEY"),
)
bd_property_key: Optional[str] = Field(
    default=None,
    description="BatchData property search API key",
    validation_alias=AliasChoices("BD_PROPERTY_KEY"),
)
bd_phone_key: Optional[str] = Field(
    default=None,
    description="BatchData phone verification/DNC/TCPA API key",
    validation_alias=AliasChoices("BD_PHONE_KEY"),
)
```

**1.3 Add convenience property for BatchData client initialization:**

```python
@property
def batchdata_api_keys(self) -> dict:
    """Get all BatchData API keys as dict for client initialization."""
    return {
        'BD_SKIPTRACE_KEY': self.bd_skiptrace_key,
        'BD_ADDRESS_KEY': self.bd_address_key,
        'BD_PROPERTY_KEY': self.bd_property_key,
        'BD_PHONE_KEY': self.bd_phone_key,
    }
```

**1.4 Add backward compatibility layer (populates os.environ):**

```python
def model_post_init(self, __context) -> None:
    """Populate os.environ for backward compatibility with legacy code."""
    import os
    env_mappings = {
        'MCAO_API_KEY': self.mcao_api_key,
        'BD_SKIPTRACE_KEY': self.bd_skiptrace_key,
        'BD_ADDRESS_KEY': self.bd_address_key,
        'BD_PROPERTY_KEY': self.bd_property_key,
        'BD_PHONE_KEY': self.bd_phone_key,
    }
    for key, value in env_mappings.items():
        if value is not None:
            os.environ[key] = str(value)
```

---

### Step 2: Fix mcao_client.py

**File**: `src/adhs_etl/mcao_client.py`

**2.1 Remove module-level load_dotenv (lines 17 and 21):**

```python
# DELETE these lines:
from dotenv import load_dotenv  # line 17
load_dotenv()                    # line 21
```

**2.2 Update constructor to use Settings (line 39):**

```python
# Change from:
self.api_key = api_key or os.getenv("MCAO_API_KEY")

# To:
if api_key is None:
    from .config import get_settings
    api_key = get_settings().mcao_api_key
self.api_key = api_key
```

**2.3 Remove unused os import if no longer needed**

---

### Step 3: Add load_dotenv to Primary Entry Point

**File**: `scripts/process_months_local.py`

**Add after shebang, before other imports (around line 8-10):**

```python
#!/usr/bin/env python3
"""
Enhanced Month Processing Script with Interactive Menu
...
"""

# Load environment variables ONCE at application entry
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

# Rest of imports...
import os
import shutil
```

---

### Step 4: Update batchdata_bridge.py (Optional but Recommended)

**File**: `src/adhs_etl/batchdata_bridge.py`

**4.1 Replace direct os.getenv loop (lines 284-287):**

```python
# Change from:
for key in ['BD_SKIPTRACE_KEY', 'BD_ADDRESS_KEY', 'BD_PROPERTY_KEY', 'BD_PHONE_KEY']:
    env_value = os.getenv(key)
    if env_value:
        api_keys[key] = env_value

# To:
from .config import get_settings
settings = get_settings()
settings_keys = settings.batchdata_api_keys
for key, value in settings_keys.items():
    if value:
        api_keys[key] = value
```

---

## What Stays Unchanged

| Component | Reason |
|-----------|--------|
| `Batchdata/` directory structure | Keep semi-independent, no subpackage migration |
| `Batchdata/src/run.py` load_dotenv | Required for standalone operation |
| `Batchdata/src/batchdata.py` create_client_from_env | Works with compat layer populating os.environ |
| Test files using os.environ | Standard mocking pattern, works with compat layer |
| Script files in Batchdata/ | No changes needed |

---

## Execution Order

| Step | File | Changes | Est. Time |
|------|------|---------|-----------|
| 1 | `src/adhs_etl/config.py` | Add AliasChoices, BD fields, compat layer | 15 min |
| 2 | `src/adhs_etl/mcao_client.py` | Remove load_dotenv, use Settings | 10 min |
| 3 | `scripts/process_months_local.py` | Add entry point load_dotenv | 5 min |
| 4 | `src/adhs_etl/batchdata_bridge.py` | Use Settings (optional) | 5 min |

**Total**: ~35 minutes

---

## Testing & Validation

### Test 1: Verify Settings loads all keys

```bash
poetry run python -c "
from adhs_etl.config import get_settings
s = get_settings(month='1.25')
print(f'MCAO key: {bool(s.mcao_api_key)}')
print(f'BD skip: {bool(s.bd_skiptrace_key)}')
print(f'BD phone: {bool(s.bd_phone_key)}')
print(f'API keys dict: {list(s.batchdata_api_keys.keys())}')
"
```

### Test 2: Verify backward compat layer populates os.environ

```bash
poetry run python -c "
import os
from adhs_etl.config import get_settings
s = get_settings(month='1.25')
print(f'os.environ MCAO: {bool(os.environ.get(\"MCAO_API_KEY\"))}')
print(f'os.environ BD_PHONE: {bool(os.environ.get(\"BD_PHONE_KEY\"))}')
"
```

### Test 3: MCAO client works without module-level load_dotenv

```bash
poetry run python -c "
from adhs_etl.mcao_client import MCAAOAPIClient
try:
    client = MCAAOAPIClient()
    print(f'Client OK, has key: {bool(client.api_key)}')
except ValueError as e:
    print(f'No key: {e}')
"
```

### Test 4: Full pipeline integration

```bash
poetry run python scripts/process_months_local.py
# Select test mode, single month, verify MCAO enrichment works
```

### Test 5: Batchdata standalone still works

```bash
cd Batchdata && python -m src.run --help && cd ..
```

### Test 6: Existing tests pass

```bash
poetry run pytest src/tests/ -v
cd Batchdata && python -m pytest tests/ -v && cd ..
```

---

## Backward Compatibility Matrix

| Change | Breaks Existing? | Notes |
|--------|------------------|-------|
| AliasChoices for MCAO key | No | Accepts both MCAO_API_KEY and ADHS_MCAO_API_KEY |
| Add BD fields to Settings | No | Additive, optional fields |
| Compat layer populating os.environ | No | Legacy code keeps working |
| Remove load_dotenv from mcao_client | No | Entry point loads it first |
| Entry point load_dotenv | No | Makes implicit explicit |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Script imports mcao_client before entry point runs | Low | MCAO key not found | Add load_dotenv to any direct script entry points |
| Test mocking breaks | Low | Test failures | Compat layer populates os.environ, mocking works |
| Batchdata standalone breaks | Very Low | BD pipeline fails | Batchdata/run.py unchanged, has own load_dotenv |

---

## Rollback Plan

```bash
# Before committing:
git checkout .

# After committing:
git revert HEAD

# Specific file rollback:
git checkout HEAD~1 -- src/adhs_etl/config.py
git checkout HEAD~1 -- src/adhs_etl/mcao_client.py
```

---

## Commit Message Template

```
feat: centralize environment config through Settings class

Phase 2 of environment consolidation - centralizes all config access
through Pydantic Settings class with backward compatibility.

Changes:
- Add AliasChoices to Settings for MCAO_API_KEY flexibility
- Add BatchData API keys (BD_*) to Settings class
- Add batchdata_api_keys property for client initialization
- Add compat layer that populates os.environ for legacy code
- Remove module-level load_dotenv from mcao_client.py
- Add explicit load_dotenv to process_months_local.py entry point

Benefits:
- Single source of truth for all configuration
- Type checking and validation via Pydantic
- Backward compatible (legacy os.getenv still works)
- Aligns with CLAUDE.md rule #2 (centralized config)

Breaking changes: None (compat layer ensures os.getenv works)

Refs: consolidate-envs.md Phase 2
```

---

## Summary

**Phase 1** (File Consolidation): ✅ COMPLETED
- Single .env at project root
- Batchdata/run.py uses explicit path

**Phase 2** (Settings Centralization): READY TO IMPLEMENT
- 4 files to modify
- ~35 minutes implementation
- Zero breaking changes via compat layer
- Gradual migration path (legacy code keeps working)

**Future Phase 3** (Deferred):
- Remove compat layer once all code migrated to Settings
- Consider making Batchdata a proper subpackage
- Remove all direct os.getenv from business logic
