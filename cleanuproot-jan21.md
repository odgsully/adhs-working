# Root Directory Cleanup Plan - January 21, 2026

## Executive Summary

This document outlines a comprehensive, risk-assessed plan for reorganizing the root directory of the `adhs-working` project. The analysis was conducted using six specialized agents examining different aspects of the codebase:

1. **File Inventory Agent** - Cataloged all 61 root-level files
2. **Path Dependency Agent** - Analyzed hardcoded paths and import references
3. **Directory Structure Agent** - Mapped existing subdirectory organization
4. **CI/CD Agent** - Examined gitignore, workflows, and automation
5. **Python Standards Agent** - Assessed PyPA compliance and best practices
6. **Redundancy Agent** - Identified duplicate/obsolete files

**Key Finding:** The original "must stay in root" assumptions were incorrect. Most config files CAN be relocated using existing environment variable support, but template files have hardcoded dependencies requiring code changes.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [File Inventory](#file-inventory)
3. [Dependency Analysis](#dependency-analysis)
4. [Redundancy and Cleanup Opportunities](#redundancy-and-cleanup-opportunities)
5. [Phased Reorganization Plan](#phased-reorganization-plan)
6. [Risk Assessment](#risk-assessment)
7. [Implementation Commands](#implementation-commands)
8. [Post-Cleanup Validation](#post-cleanup-validation)

---

## Current State Analysis

### Root Directory Statistics

| Metric | Count |
|--------|-------|
| Total Root Files | 61 |
| Standard Project Files | 4 |
| Configuration/Environment Files | 6 |
| Documentation (Markdown) | 23 |
| Data Templates/Test Data | 7 |
| Python Scripts (Tests/Utilities) | 6 |
| Build Artifacts | 3 |
| System/Temporary Files | 12 |

### Existing Directory Structure

```
adhs-working/
├── src/                          # Source code (PyPA src layout - EXCELLENT)
│   ├── adhs_etl/                 # Main package (16 modules)
│   └── tests/                    # Test suite with fixtures
├── scripts/                      # 35 utility scripts (NEEDS ORGANIZATION)
├── ALL-MONTHS/                   # Raw monthly data (12+ subdirs)
├── Reformat/                     # Standardized output (64 files)
├── All-to-Date/                  # Cumulative output (64 files)
├── Analysis/                     # Business analysis (57 files)
├── APN/                          # Stage 1: Assessor Parcel Numbers
│   ├── Upload/, Complete/, Cache/
├── MCAO/                         # Stage 2: Property enrichment
│   ├── Upload/, Complete/, API_Responses/, Logs/
├── Ecorp/                        # Stage 3: Entity lookup
│   ├── Upload/, Complete/, agent_ecorp/
├── Batchdata/                    # Stage 4: Contact discovery
│   ├── Upload/, Complete/, src/, tests/, docs/
├── docs/                         # Project docs (UNDERUTILIZED - 1 file)
├── ai_docs/                      # AI tool reference docs (9 files)
├── logs/                         # System logs
├── dnu/                          # "Do Not Use" archive
├── temp/, test-outputs/          # Temporary directories
└── [61 root-level files]         # TARGET FOR CLEANUP
```

---

## File Inventory

### Standard Project Files (KEEP AT ROOT)

| File | Size | Purpose | Status |
|------|------|---------|--------|
| `pyproject.toml` | 1.3K | Poetry project configuration | **REQUIRED** |
| `poetry.lock` | 178K | Locked dependency versions | **REQUIRED** |
| `README.md` | 7.2K | Primary project documentation | **REQUIRED** |
| `CLAUDE.md` | 5.8K | Claude Code operating rules | **REQUIRED** |
| `.gitignore` | 1.4K | Git ignore rules | **REQUIRED** |

### Environment & Configuration Files

| File | Size | Purpose | Can Relocate? |
|------|------|---------|---------------|
| `.env` | (secret) | Runtime environment variables | **YES** - with load_dotenv() |
| `.env.sample` | 2.3K | Environment template | Keep at root for visibility |
| `env.example` | 344B | Duplicate env template | **DELETE** |
| `.mcp.json.sample` | 198B | MCP configuration template | Keep at root |
| `field_map.yml` | 2.1K | Field mapping for ETL | **YES** - ADHS_FIELD_MAP_PATH |
| `field_map.TODO.yml` | 1.9K | Unknown column tracking | **YES** - ADHS_FIELD_MAP_TODO_PATH |

### Configuration Relocation Details

**field_map.yml and field_map.TODO.yml:**

The config.py already supports environment variable overrides:

```python
# src/adhs_etl/config.py lines 30-37
field_map_path: Path = Field(
    default=Path("./field_map.yml"),
    description="Path to field mapping YAML file",
)
field_map_todo_path: Path = Field(
    default=Path("./field_map.TODO.yml"),
    description="Path to TODO field mapping YAML file",
)
```

**To relocate:**
```bash
export ADHS_FIELD_MAP_PATH=./config/field_map.yml
export ADHS_FIELD_MAP_TODO_PATH=./config/field_map.TODO.yml
```

**.env file:**

Pydantic-settings has `env_file=".env"` hardcoded, but can be overridden with explicit load_dotenv():

```python
# Add to entry points before Settings instantiation:
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config/.env")
```

### Excel Templates

| File | Size | Hardcoded References | Can Relocate? |
|------|------|---------------------|---------------|
| `v300Track_this.xlsx` | 15K | 7+ code locations | **RISKY** - validation logic depends on it |
| `v300Dialer_template.xlsx` | 31K | Minimal | Yes, with doc updates |
| `Ecorp_Template_Complete.xlsx` | 10K | Minimal | Yes, with doc updates |
| `Batchdata_Template.xlsx` | 12K | `batchdata_bridge.py:34` | **RISKY** - hardcoded constant |
| `v200CRMtemplate.xlsx` | 15K | None (legacy) | **DELETE** |
| `test_small.xlsx` | 5.9K | Test data | Move to src/tests/fixtures/ |
| `dnu_Ecorp_Template_Complete.xlsx` | 13K | None (deprecated) | **DELETE** |

**Critical Hardcoded Reference:**
```python
# src/adhs_etl/batchdata_bridge.py line 34
BATCHDATA_COMPLETE_TEMPLATE = "Batchdata_Template.xlsx"
```

### Markdown Documentation Files (23 files)

#### Architecture & Reference (KEEP VISIBLE or move to docs/)

| File | Lines | Purpose | Recommendation |
|------|-------|---------|----------------|
| `PIPELINE_FLOW.md` | ~200 | ETL pipeline architecture | Move to `docs/architecture/` |
| `ADHS-ETL-INDEX.md` | ~100 | File/module index | Move to `docs/architecture/` |
| `v300Track_this.md` | 700 | v300 template specification | Move to `docs/templates/` |
| `v300_discrepancies.md` | ~80 | Known template issues | Move to `docs/templates/` |
| `INVENTORY.md` | ~60 | Project inventory | Move to `docs/` |
| `BRANCH_INVENTORY.md` | ~60 | Git branch tracking | Move to `docs/` |
| `VALIDATION_RESULTS.md` | ~50 | Test validation summary | Move to `docs/` |
| `GSREALTY_CLIENT_ALIGNMENT.md` | ~70 | Client alignment notes | Move to `docs/` |
| `setup_supabase_mcp.md` | ~40 | Supabase MCP setup | Move to `docs/` |
| `PROMPT_FOR_NEW_SESSION.md` | ~40 | Claude session instructions | Move to `docs/` |

#### Planning & Migration Docs (ARCHIVE)

| File | Lines | Purpose | Recommendation |
|------|-------|---------|----------------|
| `branching-strategy-conservative.md` | 1370 | Git branching strategy | Archive to `docs/archive/` |
| `consolidate-envs.md` | ~400 | Environment consolidation plan | Archive |
| `best-way-batch-plan.md` | ~300 | BatchData optimization plan | Archive |
| `last1percent-plan.md` | ~300 | Final data processing plan | Archive |
| `no-name-address-only-batch-plan.md` | ~250 | Address-only records plan | Archive |
| `11.24Batch-temp.md` | ~200 | Nov 2024 batch notes | Archive |
| `analysis-records-dup.md` | 1000 | Duplicate records analysis | Archive |
| `rename-prev-convention-howto.md` | ~200 | Naming convention migration | Archive |
| `CONTINUE_FILE_NAMING_STANDARDIZATION.md` | ~250 | Standardization continuation | Archive |
| `BD_PREFIX_MIGRATION_COMPLETE.md` | ~250 | BatchData prefix migration | Archive (COMPLETE) |
| `Batch-Up-Smart-Indexing.md` | ~250 | Smart indexing strategy | Archive |

### Python Test & Utility Scripts (Root Level)

| File | Size | Import Pattern | Can Relocate? |
|------|------|----------------|---------------|
| `test_checkpoint_validation.py` | 4.7K | Standard library only | Yes → `src/tests/` |
| `test_ecorp_grouping.py` | 7.1K | `from src.adhs_etl.ecorp` | Yes, update imports |
| `test_v300_migration.py` | 11K | `sys.path.insert(0, 'src')` | Yes, update imports |
| `test_fixes.py` | 7.8K | `sys.path.insert(0, 'src')` | Yes, update imports |
| `check_fixes.py` | 2.6K | Relative Excel paths | Yes, update paths |
| `setup_env.py` | 1.3K | Environment setup | Move to `scripts/` |

### Build Artifacts & Temporary Files

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `.coverage` | 53K | pytest coverage report | **KEEP** (regenerated) |
| `baseline_tests.log` | 3.1K | Old test log | **DELETE** |
| `git_test.txt` | 3B | Minimal test file | **DELETE** |
| `.DS_Store` | 14K | macOS system file | **DELETE** |
| `~$Batchdata_Template.xlsx` | 165B | Excel lock file | **DELETE** |
| `~$Ecorp_Template_Complete.xlsx` | 165B | Excel lock file | **DELETE** |
| `~$v300Dialer_template.xlsx` | 165B | Excel lock file | **DELETE** |

### CI/CD Configuration

| File | Location | Issue |
|------|----------|-------|
| `ci.yml` | Root | **SHOULD BE** `.github/workflows/ci.yml` |

---

## Dependency Analysis

### Hardcoded Path References

#### Critical (Will Break if Moved)

| File | Line | Reference | Impact |
|------|------|-----------|--------|
| `src/adhs_etl/config.py` | 31 | `Path("./field_map.yml")` | Default path, overridable via env |
| `src/adhs_etl/config.py` | 35 | `Path("./field_map.TODO.yml")` | Default path, overridable via env |
| `src/adhs_etl/batchdata_bridge.py` | 34 | `"Batchdata_Template.xlsx"` | **HARDCODED** - requires code change |
| `src/adhs_etl/config.py` | 14 | `env_file=".env"` | Pydantic settings default |

#### Directory Structure Dependencies

Multiple scripts assume these directories exist at project root:
- `ALL-MONTHS/` - Raw data storage
- `Raw-New-Month/` - Current month staging
- `Reformat/` - Output directory
- `All-to-Date/` - Cumulative output
- `Analysis/` - Business analysis output
- `APN/`, `MCAO/`, `Ecorp/`, `Batchdata/` - Enrichment stages

**Scripts with hardcoded paths:**
- `scripts/azdhs_monitor.py:112` - `PROJECT_ROOT / "ALL-MONTHS"`
- `scripts/batch_auto.py:39-40` - `Path("ALL-MONTHS")`, `Path("Raw-New-Month")`
- `scripts/process_months_local.py:95-96` - `Path("ALL-MONTHS")`
- `scripts/demo_pipeline.py:27` - `Path("Raw-New-Month")`

#### sys.path Modifications (Fragile Imports)

| Script | Pattern | Risk |
|--------|---------|------|
| `scripts/process_months_local.py` | `sys.path.insert(0, 'src')` | Breaks if CWD changes |
| `scripts/azdhs_monitor.py` | `PROJECT_ROOT = Path(__file__).parent.parent` | Breaks if script moves |
| `test_v300_migration.py` | `sys.path.insert(0, 'src')` | Breaks if file moves |
| `test_fixes.py` | `sys.path.insert(0, 'src')` | Breaks if file moves |

### Template File References

**v300Track_this.md/xlsx referenced in:**
- `CLAUDE.md` (lines 55, 61)
- `README.md` (lines 148, 150)
- `src/adhs_etl/analysis.py` (lines 3, 412, 745, 751, 1037, 1151)
- `scripts/process_months_*.py` (multiple files)
- `test_v300_migration.py` (line 19)
- `v300_discrepancies.md`
- `analysis-records-dup.md` (8 references)
- `CONTINUE_FILE_NAMING_STANDARDIZATION.md` (line 160)

**Total: 18+ references requiring update if moved**

---

## Redundancy and Cleanup Opportunities

### Duplicate Files (CONSOLIDATE)

| Duplicate | Keep | Delete | Reason |
|-----------|------|--------|--------|
| `.env.sample` (2.3K) | `.env.sample` | `env.example` (344B) | .env.sample is more comprehensive |
| `Ecorp_Template_Complete.xlsx` | Root version | `dnu_Ecorp_Template_Complete.xlsx` | dnu version is deprecated |

### Archived/Obsolete Files (DELETE)

| File | Size | Reason |
|------|------|--------|
| `env.example` | 344B | Duplicate of .env.sample |
| `dnu_Ecorp_Template_Complete.xlsx` | 13K | Deprecated, in dnu/ naming |
| `dnu/Batchdata_Template_ARCHIVED.xlsx` | 12K | Explicitly marked ARCHIVED |
| `v200CRMtemplate.xlsx` | 15K | Superseded by v300Dialer_template |
| `scripts/process_months_local.py.backup` | 12K | Backup of active file |
| `scripts/batch_process_temp_fix.py` | 7.3K | Temp fix script |
| `baseline_tests.log` | 3.1K | Old test log |
| `git_test.txt` | 3B | Minimal test artifact |

### Temporary Files (DELETE)

| Pattern | Count | Location |
|---------|-------|----------|
| `~$*.xlsx` | 3 | Root (Excel lock files) |
| `.DS_Store` | 11+ | Various directories |
| `temp/*` | 1 | Orphaned sample file |
| `test-outputs/*` | 1 | Nov 24 test artifact |
| `.corrupted_test_files/*` | 2 | Oct 2024 test files |

### Directory Cleanup Candidates

| Directory | Size | Status | Recommendation |
|-----------|------|--------|----------------|
| `dnu/` | 6.9MB | "Do Not Use" archive | Archive externally or delete |
| `dnu/Sep-progress/` | ~6MB | Sept 2024 test files | Delete (7 months old) |
| `git-nov/` | 1.4MB | Git snapshots from Nov | Archive or delete |
| `Ecorp/backup_20260112_113158/` | ~0 | Empty backup dirs | Delete if testing complete |
| `.corrupted_test_files/` | 1.8MB | Quarantined test data | Delete |

### Total Cleanup Potential

| Category | Size | Action |
|----------|------|--------|
| Safe deletions | ~3MB | Immediate |
| Archiveable | ~10MB | Move to external storage |
| Documentation consolidation | - | Organize, not delete |
| **Total** | ~13MB | Plus significant clutter reduction |

---

## Phased Reorganization Plan

### Phase 0: Safe Cleanup (ZERO RISK)

**Objective:** Delete obsolete, duplicate, and temporary files.

**Time:** 5 minutes

**Files to Delete:**
```
# Excel lock files (temporary)
~$Batchdata_Template.xlsx
~$Ecorp_Template_Complete.xlsx
~$v300Dialer_template.xlsx

# Duplicate environment file
env.example

# Archived/deprecated templates
dnu_Ecorp_Template_Complete.xlsx
v200CRMtemplate.xlsx

# Backup scripts
scripts/process_months_local.py.backup
scripts/batch_process_temp_fix.py

# Old logs and artifacts
baseline_tests.log
git_test.txt
.DS_Store

# Temp directory contents
temp/*
test-outputs/*
.corrupted_test_files/*
```

**Verification:** `git status` shows no tracked files affected.

---

### Phase 1: Documentation Consolidation (LOW RISK)

**Objective:** Organize 23 markdown files into structured docs/ directory.

**Time:** 15 minutes

**Target Structure:**
```
docs/
├── architecture/
│   ├── PIPELINE_FLOW.md
│   └── ADHS-ETL-INDEX.md
├── templates/
│   ├── v300Track_this.md
│   └── v300_discrepancies.md
├── reference/
│   ├── INVENTORY.md
│   ├── BRANCH_INVENTORY.md
│   ├── VALIDATION_RESULTS.md
│   ├── GSREALTY_CLIENT_ALIGNMENT.md
│   ├── setup_supabase_mcp.md
│   └── PROMPT_FOR_NEW_SESSION.md
├── archive/
│   ├── branching-strategy-conservative.md
│   ├── consolidate-envs.md
│   ├── best-way-batch-plan.md
│   ├── last1percent-plan.md
│   ├── no-name-address-only-batch-plan.md
│   ├── 11.24Batch-temp.md
│   ├── analysis-records-dup.md
│   ├── rename-prev-convention-howto.md
│   ├── CONTINUE_FILE_NAMING_STANDARDIZATION.md
│   ├── BD_PREFIX_MIGRATION_COMPLETE.md
│   └── Batch-Up-Smart-Indexing.md
└── ecorp-necessity-analysis-2026-01-12.md (existing)
```

**Note:** Keep `ai_docs/` separate - it contains external tool references (Anthropic, OpenAI, hooks) with different purpose and audience.

**Verification:** No code references markdown files by path (confirmed by agent analysis).

---

### Phase 2: Config Directory (MEDIUM RISK)

**Objective:** Consolidate configuration files into `config/` directory.

**Time:** 30 minutes

**Target Structure:**
```
config/
├── field_map.yml
├── field_map.TODO.yml
└── .env
```

**Required Changes:**

1. **Update .env.sample** with new paths:
```bash
# Add to .env.sample
ADHS_FIELD_MAP_PATH=config/field_map.yml
ADHS_FIELD_MAP_TODO_PATH=config/field_map.TODO.yml
```

2. **Update entry points** with explicit dotenv loading:
```python
# Add to scripts/process_months_local.py (before Settings import)
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / "config/.env")
```

**Files requiring dotenv update:**
- `scripts/process_months_local.py`
- `scripts/process_months_menu.py`
- `scripts/azdhs_monitor.py`
- `scripts/azdhs_supabase.py`
- `scripts/batch_auto.py`

3. **Update cli_enhanced.py** line 67 fallback:
```python
# Current
field_map_path=Path("field_map.yml")
# Change to
field_map_path=settings.field_map_path
```

**Verification:**
```bash
poetry run python -c "from adhs_etl.config import Settings; s = Settings(month='1.25'); print(s.field_map_path)"
poetry run adhs-etl run --month 1.25 --dry-run
```

---

### Phase 3: Templates Directory (MEDIUM-HIGH RISK)

**Objective:** Consolidate Excel templates into `templates/` directory.

**Time:** 1 hour

**Target Structure:**
```
templates/
├── v300Track_this.xlsx
├── v300Dialer_template.xlsx
├── Ecorp_Template_Complete.xlsx
└── Batchdata_Template.xlsx
```

**Required Code Changes:**

1. **Update batchdata_bridge.py** line 34:
```python
# Current
BATCHDATA_COMPLETE_TEMPLATE = "Batchdata_Template.xlsx"
# Change to
BATCHDATA_COMPLETE_TEMPLATE = "templates/Batchdata_Template.xlsx"
```

2. **Update documentation references:**
- `CLAUDE.md` lines 55, 61
- `README.md` lines 148, 150

3. **Update any validation logic** that references templates.

**Verification:**
```bash
poetry run pytest src/tests/ -v
poetry run adhs-etl run --month 1.25 --dry-run
```

---

### Phase 4: Scripts Reorganization (HIGH RISK - OPTIONAL)

**Objective:** Organize 35 scripts into logical subdirectories.

**Time:** 2+ hours

**Target Structure:**
```
scripts/
├── core/
│   ├── process_months_local.py
│   ├── process_months_menu.py
│   └── demo_pipeline.py
├── monitoring/
│   ├── azdhs_monitor.py
│   ├── azdhs_notify.py
│   └── azdhs_supabase.py
├── batch/
│   ├── fast_batch.py
│   ├── fast_batch_final.py
│   ├── fast_batch_remaining.py
│   ├── batch_auto.py
│   └── batch_process_all.py
├── testing/
│   ├── test_mcao_*.py (6 files)
│   ├── test_ecorp_*.py (2 files)
│   └── quick_test.py
├── analysis/
│   ├── generate_125_analysis.py
│   ├── generate_proper_analysis.py
│   └── compare_*.py
└── legacy/
    └── (deprecated scripts)
```

**Blockers:**

1. **Cross-script imports will break:**
```python
# scripts/azdhs_monitor.py imports from scripts/azdhs_notify.py
from scripts.azdhs_notify import send_notifications
```

2. **sys.path manipulation assumes script location:**
```python
PROJECT_ROOT = Path(__file__).parent.parent  # Assumes scripts/ is direct child
```

**Recommendation:** Defer this phase until import patterns can be standardized (e.g., using proper package imports instead of sys.path manipulation).

---

### Phase 5: Root Test Files (LOW-MEDIUM RISK)

**Objective:** Move root-level test files to `src/tests/`.

**Time:** 20 minutes

**Files to Move:**
```
test_checkpoint_validation.py → src/tests/
test_ecorp_grouping.py → src/tests/
test_v300_migration.py → src/tests/
test_fixes.py → src/tests/
check_fixes.py → scripts/analysis/
setup_env.py → scripts/
```

**Required Changes:**

Update import patterns from:
```python
sys.path.insert(0, 'src')
from adhs_etl.transform_enhanced import ProviderGrouper
```

To:
```python
from adhs_etl.transform_enhanced import ProviderGrouper  # No sys.path needed in src/tests/
```

**Verification:**
```bash
poetry run pytest src/tests/ -v
```

---

## Risk Assessment

### Risk Matrix

| Phase | Risk Level | Effort | Benefit | Dependencies |
|-------|------------|--------|---------|--------------|
| 0: Cleanup | **None** | 5 min | ~13MB freed, cleaner root | None |
| 1: Docs | **Low** | 15 min | 23 files organized | None |
| 2: Config | **Medium** | 30 min | 3 files organized | Entry point updates |
| 3: Templates | **Medium-High** | 1 hr | 4 files organized | Code changes required |
| 4: Scripts | **High** | 2+ hrs | 35 files organized | Import pattern overhaul |
| 5: Tests | **Low-Medium** | 20 min | 6 files organized | Import updates |

### Recommended Execution Order

1. **DO NOW:** Phase 0 (Safe Cleanup) + Phase 1 (Docs)
2. **CONSIDER:** Phase 2 (Config) - optional but clean
3. **DEFER:** Phase 3 (Templates) - until code changes can be tested
4. **FUTURE:** Phase 4 (Scripts) - requires import standardization
5. **AFTER PHASE 4:** Phase 5 (Tests) - easier after scripts are organized

---

## Implementation Commands

### Phase 0: Safe Cleanup

```bash
cd /Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-working

# Delete Excel lock files
rm -f "~\$Batchdata_Template.xlsx" "~\$Ecorp_Template_Complete.xlsx" "~\$v300Dialer_template.xlsx"

# Delete duplicate env file
rm -f env.example

# Delete archived templates
rm -f dnu_Ecorp_Template_Complete.xlsx
rm -f v200CRMtemplate.xlsx

# Delete backup scripts
rm -f scripts/process_months_local.py.backup
rm -f scripts/batch_process_temp_fix.py

# Delete old artifacts
rm -f baseline_tests.log git_test.txt .DS_Store

# Clear temp directories
rm -rf temp/* test-outputs/* .corrupted_test_files/*

# Verify no tracked files affected
git status
```

### Phase 1: Documentation Consolidation

```bash
cd /Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-working

# Create directory structure
mkdir -p docs/architecture docs/templates docs/reference docs/archive

# Move architecture docs
mv PIPELINE_FLOW.md docs/architecture/
mv ADHS-ETL-INDEX.md docs/architecture/

# Move template docs
mv v300Track_this.md docs/templates/
mv v300_discrepancies.md docs/templates/

# Move reference docs
mv INVENTORY.md docs/reference/
mv BRANCH_INVENTORY.md docs/reference/
mv VALIDATION_RESULTS.md docs/reference/
mv GSREALTY_CLIENT_ALIGNMENT.md docs/reference/
mv setup_supabase_mcp.md docs/reference/
mv PROMPT_FOR_NEW_SESSION.md docs/reference/

# Move archive docs (completed planning)
mv branching-strategy-conservative.md docs/archive/
mv consolidate-envs.md docs/archive/
mv best-way-batch-plan.md docs/archive/
mv last1percent-plan.md docs/archive/
mv no-name-address-only-batch-plan.md docs/archive/
mv 11.24Batch-temp.md docs/archive/
mv analysis-records-dup.md docs/archive/
mv rename-prev-convention-howto.md docs/archive/
mv CONTINUE_FILE_NAMING_STANDARDIZATION.md docs/archive/
mv BD_PREFIX_MIGRATION_COMPLETE.md docs/archive/
mv Batch-Up-Smart-Indexing.md docs/archive/

# Verify
ls -la docs/
git status
```

### Phase 2: Config Directory (If Proceeding)

```bash
# Create config directory
mkdir -p config

# Move config files
mv field_map.yml config/
mv field_map.TODO.yml config/
mv .env config/

# Update .env.sample with notes about new paths
echo "# Note: field_map files moved to config/" >> .env.sample
echo "ADHS_FIELD_MAP_PATH=config/field_map.yml" >> .env.sample
echo "ADHS_FIELD_MAP_TODO_PATH=config/field_map.TODO.yml" >> .env.sample
```

Then update entry points as documented in Phase 2 section.

---

## Post-Cleanup Validation

### After Phase 0

```bash
# Verify git status shows no tracked file changes
git status

# Verify project still runs
poetry run adhs-etl --help
```

### After Phase 1

```bash
# Verify docs structure
find docs -type f -name "*.md" | wc -l  # Should be ~23

# Verify no broken references (grep for old paths)
grep -r "PIPELINE_FLOW.md" --include="*.py" .  # Should find nothing in code
```

### After Phase 2

```bash
# Test config loading
poetry run python -c "
from adhs_etl.config import Settings
s = Settings(month='1.25')
print(f'Field map: {s.field_map_path}')
print(f'Field map TODO: {s.field_map_todo_path}')
print(f'Exists: {s.field_map_path.exists()}')
"

# Test CLI
poetry run adhs-etl run --month 1.25 --dry-run

# Run tests
poetry run pytest src/tests/ -v
```

### After Phase 3

```bash
# Test BatchData template loading
poetry run python -c "
from adhs_etl.batchdata_bridge import BATCHDATA_COMPLETE_TEMPLATE
from pathlib import Path
print(f'Template: {BATCHDATA_COMPLETE_TEMPLATE}')
print(f'Exists: {Path(BATCHDATA_COMPLETE_TEMPLATE).exists()}')
"

# Full test suite
poetry run pytest src/tests/ -v
```

---

## Final Target State

After completing Phases 0-3 (conservative approach):

```
adhs-working/
├── .env.sample               # Environment template (visible)
├── .gitignore
├── .mcp.json.sample
├── pyproject.toml
├── poetry.lock
├── README.md
├── CLAUDE.md
├── ci.yml                    # TODO: Move to .github/workflows/
├── config/                   # NEW: Configuration files
│   ├── field_map.yml
│   ├── field_map.TODO.yml
│   └── .env
├── templates/                # NEW: Excel templates
│   ├── v300Track_this.xlsx
│   ├── v300Dialer_template.xlsx
│   ├── Ecorp_Template_Complete.xlsx
│   └── Batchdata_Template.xlsx
├── docs/                     # EXPANDED: Organized documentation
│   ├── architecture/
│   ├── templates/
│   ├── reference/
│   └── archive/
├── ai_docs/                  # UNCHANGED: AI tool references
├── src/                      # UNCHANGED: Source code
├── scripts/                  # UNCHANGED (Phase 4 deferred)
├── ALL-MONTHS/               # Data directories (gitignored)
├── Reformat/
├── All-to-Date/
├── Analysis/
├── APN/
├── MCAO/
├── Ecorp/
└── Batchdata/
```

**Root files reduced: 61 → ~12 essential files**

---

## Appendix: Files Reference

### Complete Root File List (Pre-Cleanup)

```
.DS_Store
.coverage
.env
.env.sample
.gitignore
.mcp.json.sample
11.24Batch-temp.md
ADHS-ETL-INDEX.md
BD_PREFIX_MIGRATION_COMPLETE.md
BRANCH_INVENTORY.md
Batch-Up-Smart-Indexing.md
Batchdata_Template.xlsx
CLAUDE.md
CONTINUE_FILE_NAMING_STANDARDIZATION.md
Ecorp_Template_Complete.xlsx
GSREALTY_CLIENT_ALIGNMENT.md
INVENTORY.md
PIPELINE_FLOW.md
PROMPT_FOR_NEW_SESSION.md
README.md
VALIDATION_RESULTS.md
analysis-records-dup.md
baseline_tests.log
best-way-batch-plan.md
branching-strategy-conservative.md
check_fixes.py
ci.yml
consolidate-envs.md
dnu_Ecorp_Template_Complete.xlsx
env.example
field_map.TODO.yml
field_map.yml
git_test.txt
last1percent-plan.md
no-name-address-only-batch-plan.md
poetry.lock
pyproject.toml
rename-prev-convention-howto.md
setup_env.py
setup_supabase_mcp.md
test_checkpoint_validation.py
test_ecorp_grouping.py
test_fixes.py
test_small.xlsx
test_v300_migration.py
v200CRMtemplate.xlsx
v300Dialer_template.xlsx
v300Track_this.md
v300Track_this.xlsx
v300_discrepancies.md
~$Batchdata_Template.xlsx
~$Ecorp_Template_Complete.xlsx
~$v300Dialer_template.xlsx
```

### Gitignore Patterns (Relevant)

```gitignore
# Already excluded
Ecorp/backup_*/
field_map.TODO.yml
~$*.xls*
git-nov/
test-outputs/
.DS_Store

# Should add
dnu/
```

---

*Document generated: January 21, 2026*
*Analysis conducted by: 6 specialized exploration agents*
*Risk assessment: Conservative approach recommended*
