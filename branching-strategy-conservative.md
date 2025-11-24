# Conservative Branching Strategy for `adhs-working`

This document outlines a **conservative, no-data-loss** approach to consolidating the multiple Finder folder copies into proper git branches AND cleaning up the existing branch mess.

---

## Current State (as of 2025-11-24)

### Finder Copies

| Folder | Git Commit | Branch | Uncommitted Changes | Notes |
|--------|------------|--------|---------------------|-------|
| **Original** | `5f9b72a` | `Ensure-proper-through-analysis` | Unknown | Oldest state, different branch |
| **Copy 2** | `a9d6e56` | `chore/consolidate-env-files` | Unknown | 2 commits behind |
| **Copy (current)** | `048874f` | `chore/consolidate-env-files` | 5 files | Active working tree |
| **Copy 3** | `048874f` | `chore/consolidate-env-files` | 14 files | AI refactor - **DELETES 2 files** |
| **Copy 4** | `048874f` | `chore/consolidate-env-files` | 4 files | Nearly identical to current |

### Existing Branches

| Branch | Commit | Tracking | Notes |
|--------|--------|----------|-------|
| `main` | `3550ca2` | `origin/main: gone` | Orphaned - remote deleted |
| `chore/consolidate-env-files` | `048874f` | tracking | **Current working branch** |
| `feature/standardize-file-naming` | `a9d6e56` | tracking | Duplicate commit with batchdata-lockin |
| `batchdata-lockinlockinlockin-api` | `a9d6e56` | tracking | Duplicate commit with feature/standardize |
| `Ensure-proper-through-analysis` | `5f9b72a` | tracking | Checkpoint branch |
| `Ensure-Proper-Through-MCAO` | `5204301` | tracking | Checkpoint branch |
| `Ensure-Proper-Thorugh-Ecorp` | `9d90737` | tracking | Checkpoint branch (typo in name) |
| `Ensure-Proper-Through-Batchdata` | `d1d0e06` | tracking | Checkpoint - same commit as All-good-thru |
| `All-good-thru-Ecorp-MCAO-backtrack` | `d1d0e06` | tracking | Checkpoint - same commit as Batchdata |
| `2-Ensure-Proper-Through-Analysis` | `da7ea13` | tracking | Checkpoint branch |

### Known Issues

1. **Broken remote HEAD**: `fatal: bad object refs/remotes/origin/HEAD`
2. **Orphaned main**: `origin/main: gone` - remote tracking broken
3. **Duplicate branches**: Multiple branches at same commit (`d1d0e06` × 2, `a9d6e56` × 2)
4. **Typo branch**: `Ensure-Proper-Thorugh-Ecorp` ("Thorugh")
5. **Checkpoint branches as branches**: Should be tags, not branches

### Canonical Files

- **`Batchdata_Template.xlsx`**: The canonical version is at the repo root (`/Batchdata_Template.xlsx`), NOT `/Batchdata/Batchdata_Template.xlsx`

### Verify Current State

Run these commands to confirm the tables are accurate:

```bash
# Check commit SHA for each Finder folder
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE"
for dir in "adhs-restore-28-Jul-2025" "adhs-restore-28-Jul-2025 copy" \
           "adhs-restore-28-Jul-2025 copy 2" "adhs-restore-28-Jul-2025 copy 3" \
           "adhs-restore-28-Jul-2025 copy 4"; do
  echo "$dir: $(cd "$dir" 2>/dev/null && git rev-parse --short HEAD)"
done

# Check uncommitted file count for each
for dir in "adhs-restore-28-Jul-2025 copy" "adhs-restore-28-Jul-2025 copy 3" \
           "adhs-restore-28-Jul-2025 copy 4"; do
  echo "$dir: $(cd "$dir" && git status --short | wc -l) uncommitted"
done

# Check all branches
cd "adhs-restore-28-Jul-2025 copy"
git branch -vv
```

### Critical Warning: Copy 3

Copy 3 contains AI-assisted refactoring that:
- Modifies 7 Batchdata source files
- **DELETES** `Batchdata/template_config.xlsx`
- **DELETES** `Batchdata/tests/batchdata_local_input.xlsx`

These deletions may or may not be correct. Do not blindly sync from Copy 3.

---

## Phase 0: Fix Remote State

**Goal**: Fix the broken remote HEAD reference before any other operations.

### 0.1 Delete Broken Remote HEAD

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy"

# Remove the broken HEAD reference
git remote set-head origin -d
```

### 0.2 Verify Remote Connectivity

```bash
# Fetch latest from remote
git fetch origin

# Check remote state
git remote show origin

# List remote branches
git branch -r
```

### 0.3 Verify Fix

```bash
# This should no longer error
git log --oneline --graph --all --decorate -n 20
```

### 0.4 Prepare .gitignore for Test Outputs

Add test output directories to .gitignore early to prevent accidental commits:

```bash
# Add test-outputs directory (used in Phase 3)
echo "test-outputs/" >> .gitignore
git add .gitignore
git commit -m "chore: add test-outputs to gitignore"
```

**Do not proceed to Phase 1 until the fatal error is resolved.**

---

## Phase 1: Finder Copy Inventory (No Changes)

**Goal**: Understand exactly what's unique to each Finder copy before touching anything.

### 1.1 Diff Copy 3 vs Current

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE"

diff -rq "adhs-restore-28-Jul-2025 copy" "adhs-restore-28-Jul-2025 copy 3" \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='outputs' \
  --exclude='ALL-MONTHS' \
  --exclude='Reformat' \
  --exclude='All-to-Date' \
  --exclude='Raw-New-Month' \
  --exclude='Analysis' \
  --exclude='APN' \
  --exclude='MCAO' \
  --exclude='Ecorp' \
  --exclude='*.xlsx' \
  --exclude='*.xls'
```

Note: We exclude Excel files because .gitignore already handles them. Focus on code/config changes.

### 1.1.1 Check Tracked Excel Templates Separately

Some Excel templates ARE tracked in git (unlike output files). Check these via `git diff`:

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy"

# Compare tracked templates between Copy and Copy 3
git diff --no-index "../adhs-restore-28-Jul-2025 copy/Batchdata_Template.xlsx" \
                    "../adhs-restore-28-Jul-2025 copy 3/Batchdata_Template.xlsx" || true

git diff --no-index "../adhs-restore-28-Jul-2025 copy/v300Dialer_template.xlsx" \
                    "../adhs-restore-28-Jul-2025 copy 3/v300Dialer_template.xlsx" || true
```

Note: `git diff` on binary files will just show "Binary files differ" - that's enough to know they changed.

### 1.2 Diff Original vs Current

```bash
diff -rq "adhs-restore-28-Jul-2025 copy" "adhs-restore-28-Jul-2025" \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='outputs' \
  --exclude='ALL-MONTHS' \
  --exclude='Reformat' \
  --exclude='All-to-Date' \
  --exclude='Raw-New-Month' \
  --exclude='Analysis' \
  --exclude='APN' \
  --exclude='MCAO' \
  --exclude='Ecorp' \
  --exclude='*.xlsx' \
  --exclude='*.xls'
```

### 1.2.1 Diff Copy 2 vs Current

Copy 2 is 2 commits behind. Check if it has any uncommitted changes worth preserving:

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE"

# First check if Copy 2 has uncommitted changes
cd "adhs-restore-28-Jul-2025 copy 2"
git status --short
cd ..

# Then diff against current
diff -rq "adhs-restore-28-Jul-2025 copy" "adhs-restore-28-Jul-2025 copy 2" \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='outputs' \
  --exclude='ALL-MONTHS' \
  --exclude='Reformat' \
  --exclude='All-to-Date' \
  --exclude='Raw-New-Month' \
  --exclude='Analysis' \
  --exclude='APN' \
  --exclude='MCAO' \
  --exclude='Ecorp' \
  --exclude='*.xlsx' \
  --exclude='*.xls'
```

**Assessment**: Copy 2 is 2 commits behind current. If it has no uncommitted changes, it can be safely ignored (the commits exist in current). Only preserve if it has unique uncommitted work.

### 1.2.2 Diff Copy 4 vs Current

Copy 4 is documented as "nearly identical to current":

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE"

# Check uncommitted changes in Copy 4
cd "adhs-restore-28-Jul-2025 copy 4"
git status --short
cd ..

# Diff against current
diff -rq "adhs-restore-28-Jul-2025 copy" "adhs-restore-28-Jul-2025 copy 4" \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='outputs' \
  --exclude='ALL-MONTHS' \
  --exclude='Reformat' \
  --exclude='All-to-Date' \
  --exclude='Raw-New-Month' \
  --exclude='Analysis' \
  --exclude='APN' \
  --exclude='MCAO' \
  --exclude='Ecorp' \
  --exclude='*.xlsx' \
  --exclude='*.xls'
```

**Assessment**: Copy 4 has 4 uncommitted files vs current's 5. If the 4 files are a subset of current's changes, Copy 4 can be ignored.

### 1.3 Verify Deleted Files Still Exist in Current

```bash
ls -la "adhs-restore-28-Jul-2025 copy/Batchdata/template_config.xlsx"
ls -la "adhs-restore-28-Jul-2025 copy/Batchdata/tests/batchdata_local_input.xlsx"
```

### 1.4 Document Findings

Create `INVENTORY.md` using the template below.

**Do not proceed to Phase 1.5 until Finder copy inventory is complete.**

### INVENTORY.md Template

```markdown
# INVENTORY - `adhs-restore-28-Jul-2025` Copies

Generated: YYYY-MM-DD

## Summary

- Current canonical folder: `adhs-restore-28-Jul-2025 copy`
- Goal: Preserve unique code states as git branches, no data loss.

## Unique Files by Folder

### Copy 3 vs Copy (Current)

**Modified:**
- [ ] Batchdata/src/batchdata_sync.py
- [ ] Batchdata/src/io.py
- [ ] Batchdata/src/normalize.py
- [ ] Batchdata/src/run.py
- [ ] Batchdata/src/transform.py
- [ ] src/adhs_etl/batchdata_bridge.py
- [ ] Batchdata/PIPELINE_INTEGRATION_GUIDE.md
- [ ] Batchdata/README.md

**Added:**
- (list any new files in Copy 3)

**Deleted:**
- [ ] Batchdata/template_config.xlsx - Intentional? ___
- [ ] Batchdata/tests/batchdata_local_input.xlsx - Intentional? ___

### Original vs Copy (Current)

**Modified:**
- (list files)

**Added:**
- (list files)

**Deleted:**
- (list files)

### Copy 2 vs Copy (Current)

Copy 2 is at commit `a9d6e56` (2 commits behind `048874f`).

**Has uncommitted changes?** [ ] Yes / [ ] No

**If yes, modified files:**
- (list files)

**Verdict**: [ ] Preserve / [ ] Ignore (no unique content)

### Copy 4 vs Copy (Current)

Copy 4 is at commit `048874f` (same as current) with 4 uncommitted files.

**Has unique uncommitted changes?** [ ] Yes / [ ] No

**If yes, files not in current:**
- (list files)

**Verdict**: [ ] Preserve / [ ] Ignore (subset of current)

## Assessment

### Likely Intentional Changes
-

### Suspected Accidental Changes
-

### Open Questions
- Are `template_config.xlsx` and `batchdata_local_input.xlsx` still needed?
-

## Recommendation

Proceed to Phase 1.5: [ ] Yes / [ ] No

Reason:
```

---

## Phase 1.5: Branch Inventory

**Goal**: Understand all existing branches before creating new ones.

### 1.5.1 List All Branches with Merge Status

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy"

echo "=== Branches MERGED into chore/consolidate-env-files ==="
git branch --merged chore/consolidate-env-files

echo ""
echo "=== Branches NOT MERGED into chore/consolidate-env-files ==="
git branch --no-merged chore/consolidate-env-files
```

### 1.5.2 Identify Duplicate Branches

```bash
# Find branches pointing to the same commit
git branch -v | sort -k2 | awk '{
  if (prev_sha == $2) {
    print "DUPLICATE: " prev_branch " and " $1 " both at " $2
  }
  prev_sha = $2
  prev_branch = $1
}'
```

### 1.5.3 Visualize Branch History

```bash
# Full history graph
git log --oneline --graph --all --decorate -n 100

# Simplified: just branch tips
git show-branch --list
```

### 1.5.4 Check for Unique Content in Checkpoint Branches

For each "Ensure-Proper-Through-*" branch, check if it has unique commits:

```bash
# Example: check if Ensure-Proper-Through-MCAO has commits not in current
git log chore/consolidate-env-files..Ensure-Proper-Through-MCAO --oneline

# Repeat for each checkpoint branch
git log chore/consolidate-env-files..Ensure-Proper-Through-Batchdata --oneline
git log chore/consolidate-env-files..Ensure-Proper-Thorugh-Ecorp --oneline
git log chore/consolidate-env-files..Ensure-proper-through-analysis --oneline
```

### 1.5.5 Document Branch Inventory

Create `BRANCH_INVENTORY.md` using the template below.

**Do not proceed to Phase 2 until branch inventory is complete and reviewed.**

### BRANCH_INVENTORY.md Template

```markdown
# BRANCH INVENTORY - `adhs-working`

Generated: YYYY-MM-DD

## Summary

- Current working branch: `chore/consolidate-env-files` at `048874f`
- Total branches: 10
- Branches merged into current: ___
- Branches with unique commits: ___

## Branch Assessment

### Active Development

| Branch | Status | Action |
|--------|--------|--------|
| `chore/consolidate-env-files` | Current work | Promote to main |
| `main` | Orphaned (initial commit only) | Rename to main-initial-backup |

### Checkpoint Branches (Candidates for Tags)

| Branch | Commit | Unique Commits? | Recommendation |
|--------|--------|-----------------|----------------|
| `Ensure-proper-through-analysis` | `5f9b72a` | [ ] Yes / [ ] No | [ ] Tag / [ ] Delete |
| `Ensure-Proper-Through-MCAO` | `5204301` | [ ] Yes / [ ] No | [ ] Tag / [ ] Delete |
| `Ensure-Proper-Thorugh-Ecorp` | `9d90737` | [ ] Yes / [ ] No | [ ] Tag / [ ] Delete |
| `Ensure-Proper-Through-Batchdata` | `d1d0e06` | [ ] Yes / [ ] No | [ ] Tag / [ ] Delete |
| `All-good-thru-Ecorp-MCAO-backtrack` | `d1d0e06` | [ ] Yes / [ ] No | [ ] Tag / [ ] Delete |
| `2-Ensure-Proper-Through-Analysis` | `da7ea13` | [ ] Yes / [ ] No | [ ] Tag / [ ] Delete |

### Duplicate Branches (Same Commit)

| Branches | Commit | Keep Which? |
|----------|--------|-------------|
| `Ensure-Proper-Through-Batchdata`, `All-good-thru-Ecorp-MCAO-backtrack` | `d1d0e06` | __________ |
| `feature/standardize-file-naming`, `batchdata-lockinlockinlockin-api` | `a9d6e56` | __________ |

### Branches to Delete

| Branch | Reason |
|--------|--------|
| `Ensure-Proper-Thorugh-Ecorp` | Typo in name, content preserved in tag |
| (add others) | |

## Tag Naming Convention

Convert checkpoint branches to tags with format: `checkpoint/YYYY-MM-DD-description`

Example:
- `Ensure-Proper-Through-MCAO` → `checkpoint/2025-XX-XX-through-mcao`

## Recommendation

Proceed to Phase 2: [ ] Yes / [ ] No

Reason:
```

---

## Phase 2: Preserve (Additive Only)

**Goal**: Capture each state as a git branch without deleting anything.

### 2.1 Commit Current Working State

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy"
git add .
git commit -m "chore: snapshot current working state before branch consolidation"
```

### 2.2 Discover Modified Files in Copy 3

Before copying, generate a list of what actually changed:

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE"

# List modified/added files (excluding data directories)
diff -rq "adhs-restore-28-Jul-2025 copy" "adhs-restore-28-Jul-2025 copy 3" \
  --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' \
  --exclude='.DS_Store' --exclude='venv' --exclude='.venv' \
  --exclude='outputs' --exclude='ALL-MONTHS' --exclude='Reformat' \
  --exclude='All-to-Date' --exclude='Raw-New-Month' --exclude='Analysis' \
  | grep "Files .* differ" \
  | sed 's/Files .* and \(.*\) differ/\1/'
```

Review this list before proceeding. Only copy files you understand.

### 2.3 Create Preservation Branch for Copy 3

**Do NOT use `rsync --delete`.** Copy only the modified files identified above:

```bash
cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy"
git checkout -b preserve/copy3-ai-refactor

# Copy modified Batchdata source files
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata/src/batchdata_sync.py" Batchdata/src/
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata/src/io.py" Batchdata/src/
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata/src/normalize.py" Batchdata/src/
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata/src/run.py" Batchdata/src/
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata/src/transform.py" Batchdata/src/
cp "../adhs-restore-28-Jul-2025 copy 3/src/adhs_etl/batchdata_bridge.py" src/adhs_etl/

# Copy modified docs
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata/PIPELINE_INTEGRATION_GUIDE.md" Batchdata/
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata/README.md" Batchdata/

# Copy modified templates (these are tracked in git unlike output xlsx files)
cp "../adhs-restore-28-Jul-2025 copy 3/Batchdata_Template.xlsx" .
cp "../adhs-restore-28-Jul-2025 copy 3/v300Dialer_template.xlsx" .

# DO NOT delete template_config.xlsx or batchdata_local_input.xlsx
# Keep them until validation confirms they're obsolete

git add .
git commit -m "preserve: Copy 3 AI refactor changes (deletions deferred until validated)"
```

### 2.4 Create Preservation Branch for Original (if unique content exists)

```bash
git checkout chore/consolidate-env-files
git checkout -b preserve/original-state

# Copy any unique files from Original
# (only if inventory shows unique content worth preserving)

git add .
git commit -m "preserve: Original branch state from Ensure-proper-through-analysis"
```

### 2.5 Create Preservation Branch for Copy 2 (if unique content exists)

**Only if INVENTORY.md shows Copy 2 has unique uncommitted changes:**

```bash
git checkout chore/consolidate-env-files
git checkout -b preserve/copy2-state

# Copy only unique uncommitted files from Copy 2
# cp "../adhs-restore-28-Jul-2025 copy 2/path/to/unique/file" path/to/

git add .
git commit -m "preserve: Copy 2 uncommitted changes (2 commits behind)"
```

**If INVENTORY.md shows Copy 2 has NO unique content, skip this step.**

### 2.6 Create Preservation Branch for Copy 4 (if unique content exists)

**Only if INVENTORY.md shows Copy 4 has files not in current:**

```bash
git checkout chore/consolidate-env-files
git checkout -b preserve/copy4-state

# Copy only files that are in Copy 4 but not in current
# cp "../adhs-restore-28-Jul-2025 copy 4/path/to/unique/file" path/to/

git add .
git commit -m "preserve: Copy 4 unique uncommitted changes"
```

**If INVENTORY.md shows Copy 4 is a subset of current, skip this step.**

### 2.7 Push All Preservation Branches

```bash
git push origin preserve/copy3-ai-refactor
git push origin preserve/original-state
# Only if created:
git push origin preserve/copy2-state 2>/dev/null || true
git push origin preserve/copy4-state 2>/dev/null || true
```

---

## Phase 3: Validate (Test Before Merge)

**Goal**: Run golden tests on each branch before deciding what to keep.

### 3.1 Create Golden Test Script

**Note**: The `adhs-etl` CLI outputs to hardcoded directories (`Reformat/`, `All-to-Date/`, `Analysis/`).
The `--output-dir` parameter exists but is ignored. To compare branches, we run the pipeline
then copy outputs to a branch-specific archive folder.

Create `scripts/run_golden_tests.sh`:

```bash
#!/bin/bash
set -euo pipefail

BRANCH=$(git branch --show-current)
SHA=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_DIR="test-outputs/${BRANCH}_${SHA}_${TIMESTAMP}"

mkdir -p "$ARCHIVE_DIR"

# Log run metadata
{
  echo "Branch: $BRANCH"
  echo "Commit: $SHA"
  echo "Started: $(date -Iseconds)"
  echo "Working directory: $(pwd)"
} | tee "$ARCHIVE_DIR/run_info.txt"

echo ""
echo "Running golden tests for branch: $BRANCH"
echo "Archive directory: $ARCHIVE_DIR"
echo ""

# Run the 10.24 pipeline using the actual CLI
# Note: Outputs go to hardcoded dirs (Reformat/, All-to-Date/, Analysis/)
poetry run adhs-etl run --month 10.24 --raw-dir ./ALL-MONTHS/Raw\ 10.24

# Copy outputs to archive directory for comparison
echo "Archiving outputs..."
cp -r Reformat/ "$ARCHIVE_DIR/" 2>/dev/null || true
cp -r All-to-Date/ "$ARCHIVE_DIR/" 2>/dev/null || true
cp -r Analysis/ "$ARCHIVE_DIR/" 2>/dev/null || true

# Log completion
echo "Finished: $(date -Iseconds)" | tee -a "$ARCHIVE_DIR/run_info.txt"
echo ""
echo "Tests complete. Outputs archived to: $ARCHIVE_DIR"
```

Make it executable:

```bash
chmod +x scripts/run_golden_tests.sh
# Note: test-outputs/ was already added to .gitignore in Phase 0.4
```

### 3.2 Test Each Branch

**Important**: Clean the output directories between branch tests to avoid mixing results.

```bash
# Test current working state
git checkout chore/consolidate-env-files
rm -rf Reformat/ All-to-Date/ Analysis/  # Clean before run
./scripts/run_golden_tests.sh

# Test AI refactor
git checkout preserve/copy3-ai-refactor
rm -rf Reformat/ All-to-Date/ Analysis/  # Clean before run
./scripts/run_golden_tests.sh
```

### 3.3 Compare Outputs

Check for:
- Row counts match expected
- Headers are correct (especially Batchdata)
- No data loss in pipeline stages
- All expected output files generated

**⚠️ IMPORTANT: Excel files (.xlsx) are binary. Standard shell commands won't work:**
- `wc -l` does NOT count rows in Excel files
- `diff` does NOT meaningfully compare Excel files

**Use Python for Excel comparison.** Create `scripts/compare_excel_outputs.py`:

```python
#!/usr/bin/env python3
"""Compare Excel outputs between branches for golden test validation."""
import sys
from pathlib import Path
import pandas as pd

def compare_excel_files(file1: Path, file2: Path) -> dict:
    """Compare two Excel files and return comparison results."""
    results = {
        "file1": str(file1),
        "file2": str(file2),
        "file1_exists": file1.exists(),
        "file2_exists": file2.exists(),
    }

    if not file1.exists() or not file2.exists():
        results["match"] = False
        results["error"] = "One or both files missing"
        return results

    try:
        df1 = pd.read_excel(file1)
        df2 = pd.read_excel(file2)

        results["file1_rows"] = len(df1)
        results["file2_rows"] = len(df2)
        results["file1_cols"] = list(df1.columns)
        results["file2_cols"] = list(df2.columns)
        results["rows_match"] = len(df1) == len(df2)
        results["cols_match"] = list(df1.columns) == list(df2.columns)
        results["data_match"] = df1.equals(df2)
        results["match"] = results["rows_match"] and results["cols_match"] and results["data_match"]

        if not results["cols_match"]:
            results["cols_only_in_file1"] = set(df1.columns) - set(df2.columns)
            results["cols_only_in_file2"] = set(df2.columns) - set(df1.columns)

    except Exception as e:
        results["match"] = False
        results["error"] = str(e)

    return results

def compare_directories(dir1: Path, dir2: Path) -> None:
    """Compare all Excel files in two directories."""
    print(f"\n{'='*60}")
    print(f"Comparing: {dir1.name} vs {dir2.name}")
    print(f"{'='*60}")

    files1 = set(f.name for f in dir1.glob("*.xlsx"))
    files2 = set(f.name for f in dir2.glob("*.xlsx"))

    all_files = files1 | files2

    for filename in sorted(all_files):
        file1 = dir1 / filename
        file2 = dir2 / filename

        result = compare_excel_files(file1, file2)

        status = "✓ MATCH" if result.get("match") else "✗ DIFFER"
        print(f"\n{filename}: {status}")

        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Rows: {result.get('file1_rows', 'N/A')} vs {result.get('file2_rows', 'N/A')}")
            print(f"  Columns match: {result.get('cols_match', 'N/A')}")

            if not result.get("cols_match"):
                if result.get("cols_only_in_file1"):
                    print(f"  Only in file1: {result['cols_only_in_file1']}")
                if result.get("cols_only_in_file2"):
                    print(f"  Only in file2: {result['cols_only_in_file2']}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_excel_outputs.py <dir1> <dir2>")
        print("Example: python compare_excel_outputs.py test-outputs/branch1_abc/ test-outputs/branch2_def/")
        sys.exit(1)

    dir1 = Path(sys.argv[1])
    dir2 = Path(sys.argv[2])

    # Compare each output directory
    for subdir in ["Reformat", "All-to-Date", "Analysis"]:
        subdir1 = dir1 / subdir
        subdir2 = dir2 / subdir
        if subdir1.exists() or subdir2.exists():
            compare_directories(subdir1, subdir2)
```

Make it executable:

```bash
chmod +x scripts/compare_excel_outputs.py
```

**Run the comparison:**

```bash
# List archived test runs
ls -la test-outputs/

# Compare outputs between branches (adjust paths based on actual archive names)
poetry run python scripts/compare_excel_outputs.py \
    test-outputs/chore-consolidate-env-files_abc_123/ \
    test-outputs/preserve-copy3-ai-refactor_def_456/
```

**Quick row count check (alternative):**

```bash
# Use Python one-liner for row counts
poetry run python -c "
import pandas as pd
from pathlib import Path
for f in Path('test-outputs/').glob('**/Reformat/*.xlsx'):
    df = pd.read_excel(f)
    print(f'{f.parent.parent.name}: {len(df)} rows - {f.name}')
"
```

### 3.4 Document Test Results

Create `VALIDATION_RESULTS.md` using the template below.

**Do not proceed to Phase 3.5 until golden tests pass and documentation is drafted.**

---

## Phase 3.5: Unit Test Validation

**Goal**: Verify unit tests pass on each branch to catch function-level regressions.

Golden tests (Phase 3) verify pipeline outputs, but unit tests catch regressions in individual functions that might not surface in output files.

### 3.5.1 Run Unit Tests on Each Branch

```bash
# Test current working state
git checkout chore/consolidate-env-files
poetry run pytest -v --tb=short | tee test-outputs/pytest_current.txt
echo "Exit code: $?" >> test-outputs/pytest_current.txt

# Test AI refactor
git checkout preserve/copy3-ai-refactor
poetry run pytest -v --tb=short | tee test-outputs/pytest_copy3.txt
echo "Exit code: $?" >> test-outputs/pytest_copy3.txt
```

### 3.5.2 Run Coverage Check

```bash
# Check coverage meets threshold (≥80%)
poetry run pytest --cov=adhs_etl --cov-fail-under=80

# Generate coverage report
poetry run pytest --cov=adhs_etl --cov-report=html:test-outputs/coverage_report/
```

### 3.5.3 Compare Test Results

Both branches should:
- [ ] Pass all existing tests
- [ ] Meet coverage threshold (≥80%)
- [ ] Not introduce new test failures

If the AI refactor branch fails tests that current passes, investigate before merging.

**Do not proceed to Phase 4 until both golden tests AND unit tests pass.**

### VALIDATION_RESULTS.md Template

```markdown
# VALIDATION RESULTS - Golden Tests & Unit Tests

Generated: YYYY-MM-DD

## Unit Test Results

| Branch | Tests Passed | Coverage | Threshold Met? |
|--------|--------------|----------|----------------|
| `chore/consolidate-env-files` | ___/___  | ___% | [ ] Yes / [ ] No |
| `preserve/copy3-ai-refactor` | ___/___ | ___% | [ ] Yes / [ ] No |

**Notes on test failures (if any):**
-

## Branches Tested (Golden Tests)

| Branch | Commit | Archive Directory |
|--------|--------|-------------------|
| `chore/consolidate-env-files` | `______` | `test-outputs/chore-consolidate-env-files_______/` |
| `preserve/copy3-ai-refactor` | `______` | `test-outputs/preserve-copy3-ai-refactor_______/` |

## Test Dataset

- **Month**: 10.24
- **Input path**: ALL-MONTHS/Raw 10.24/
- **Expected outputs**:
  - [ ] Reformat file generated
  - [ ] All-to-Date file generated
  - [ ] Analysis file generated
  - [ ] BatchData Upload file generated (if applicable)

## Results by Branch

### `chore/consolidate-env-files` (Current)

- **Status**: [ ] Pass / [ ] Fail
- **Archive directory**: `test-outputs/chore-consolidate-env-files_______/`
- **Row counts**:
  - Reformat: _____ rows
  - Analysis: _____ rows
- **Header check**: [ ] Correct / [ ] Issues found
- **Notes**:

### `preserve/copy3-ai-refactor`

- **Status**: [ ] Pass / [ ] Fail
- **Archive directory**: `test-outputs/preserve-copy3-ai-refactor_______/`
- **Row counts**:
  - Reformat: _____ rows
  - Analysis: _____ rows
- **Header check**: [ ] Correct / [ ] Issues found
- **Regressions vs current**:
- **Notes**:

## Comparison Summary

| Metric | Current | Copy 3 Refactor | Match? |
|--------|---------|-----------------|--------|
| Reformat row count | | | |
| BatchData row count | | | |
| Headers correct | | | |
| All files generated | | | |

## Deleted Files Assessment

### `Batchdata/template_config.xlsx`
- Still referenced in code? [ ] Yes / [ ] No
- Used in pipeline? [ ] Yes / [ ] No
- **Verdict**: [ ] Keep / [ ] Safe to delete

### `Batchdata/tests/batchdata_local_input.xlsx`
- Still referenced in code? [ ] Yes / [ ] No
- Used in tests? [ ] Yes / [ ] No
- **Verdict**: [ ] Keep / [ ] Safe to delete

## Recommendation

- [ ] **Option A**: Merge entire `preserve/copy3-ai-refactor` into main
- [ ] **Option B**: Cherry-pick specific changes:
  - [ ] file1.py
  - [ ] file2.py
- [ ] **Option C**: Reject refactor, keep current state

**Rationale**:
```

---

## Phase 3.9: Create Rollback Point

**Goal**: Create a safety net before making integration changes.

### 3.9.1 Tag Current State

Before any integration, create a rollback tag:

```bash
git checkout chore/consolidate-env-files

# Create a rollback tag with today's date
git tag rollback/pre-integration-$(date +%Y%m%d)
git push origin rollback/pre-integration-$(date +%Y%m%d)

# Verify tag was created
git tag -l "rollback/*"
```

### 3.9.2 Document Rollback Procedure

If Phase 4 integration breaks anything, rollback with:

```bash
# Reset to pre-integration state
git checkout chore/consolidate-env-files
git reset --hard rollback/pre-integration-YYYYMMDD

# Or restore main to backup
git checkout main
git reset --hard main-initial-backup
```

**Do not proceed to Phase 4 without a rollback tag.**

---

## Phase 4: Integrate (Only After Validation)

**Goal**: Merge validated changes into main trunk.

### 4.0 Notify Collaborators (If Applicable)

⚠️ **If others have cloned this repository**, the branch restructuring will affect them.

Before proceeding:
1. Check if anyone else has active work on branches
2. Notify collaborators that `main` will be restructured
3. Advise them to push any uncommitted work before the change
4. After completion, they may need to run:
   ```bash
   git fetch origin
   git checkout main
   git reset --hard origin/main
   ```

**If you're the only contributor, skip this step.**

### 4.1 Decide on Integration Strategy

Based on validation results, choose one:

**Option A: AI Refactor is Fully Valid**
```bash
git checkout chore/consolidate-env-files
git merge preserve/copy3-ai-refactor
```

**If merge conflicts occur:**
```bash
# View conflicting files
git status

# For each conflicted file, resolve manually then:
git add <resolved-file>

# After all conflicts resolved:
git merge --continue

# If you need to abort and try again:
git merge --abort
```

**Option B: Cherry-Pick Specific Changes**
```bash
git checkout chore/consolidate-env-files
# Manually copy only the validated good changes
# Or use git cherry-pick for specific commits
```

**Option C: AI Refactor is Invalid**
```bash
# Keep current state, do not merge Copy 3 changes
# Document why the AI refactor was rejected
```

### 4.2 Handle Deleted Files

Only after validation confirms they're obsolete:

```bash
git rm Batchdata/template_config.xlsx
git rm Batchdata/tests/batchdata_local_input.xlsx
git commit -m "chore: remove obsolete template files (validated as unused)"
```

If validation shows they're still needed, document why and keep them.

### 4.3 Promote Working Branch to Main

```bash
# Rename current main to backup (don't delete)
git checkout main
git branch -m main-initial-backup

# Promote working branch
git checkout chore/consolidate-env-files
git branch -m main

# Push new main with upstream tracking
git push -u origin main

# Set remote HEAD to new main
git remote set-head origin main
```

### 4.3.1 Verify Remote Tracking

After renaming, verify the remote tracking is correct:

```bash
# Should show: main -> origin/main
git branch -vv

# Should show HEAD pointing to main
git remote show origin | head -10

# Verify you can push/pull
git fetch origin
git status
```

### 4.3.2 Update GitHub Default Branch

In the GitHub web UI:
1. Go to repository Settings → Branches
2. Change "Default branch" from whatever it was to `main`
3. Confirm the change

This ensures new clones and PRs target the correct branch.

---

## Phase 4.5: Branch Cleanup

**Goal**: Convert checkpoint branches to tags and delete redundant branches.

### 4.5.1 Convert Checkpoint Branches to Tags

For each checkpoint branch worth preserving:

```bash
# Example: Convert Ensure-Proper-Through-MCAO to a tag
git tag checkpoint/through-mcao Ensure-Proper-Through-MCAO
git push origin checkpoint/through-mcao

# Repeat for other checkpoint branches (adjust names as documented in BRANCH_INVENTORY.md)
git tag checkpoint/through-analysis Ensure-proper-through-analysis
git push origin checkpoint/through-analysis

git tag checkpoint/through-ecorp Ensure-Proper-Thorugh-Ecorp
git push origin checkpoint/through-ecorp

git tag checkpoint/through-batchdata Ensure-Proper-Through-Batchdata
git push origin checkpoint/through-batchdata
```

### 4.5.2 Delete Duplicate Branches

For branches at the same commit, keep one and delete the rest:

```bash
# Example: d1d0e06 has two branches - keep one
# If keeping Ensure-Proper-Through-Batchdata (now a tag), delete the duplicate:
git branch -d All-good-thru-Ecorp-MCAO-backtrack
git push origin --delete All-good-thru-Ecorp-MCAO-backtrack

# Same for a9d6e56 branches
git branch -d batchdata-lockinlockinlockin-api
git push origin --delete batchdata-lockinlockinlockin-api
```

### 4.5.3 Delete Checkpoint Branches (Now Tags)

After converting to tags, **verify each tag points to the expected commit** before deleting:

```bash
# Sanity check: confirm tags point where expected
git show --quiet checkpoint/through-mcao
git show --quiet checkpoint/through-analysis
git show --quiet checkpoint/through-ecorp
git show --quiet checkpoint/through-batchdata
```

Only proceed with deletion if tags show the correct commits.

```bash
# Local deletes
git branch -d Ensure-proper-through-analysis
git branch -d Ensure-Proper-Through-MCAO
git branch -d Ensure-Proper-Thorugh-Ecorp
git branch -d Ensure-Proper-Through-Batchdata
git branch -d 2-Ensure-Proper-Through-Analysis
git branch -d feature/standardize-file-naming

# Remote deletes
git push origin --delete Ensure-proper-through-analysis
git push origin --delete Ensure-Proper-Through-MCAO
git push origin --delete Ensure-Proper-Thorugh-Ecorp
git push origin --delete Ensure-Proper-Through-Batchdata
git push origin --delete 2-Ensure-Proper-Through-Analysis
git push origin --delete feature/standardize-file-naming
```

### 4.5.4 Verify Branch Cleanup

```bash
# Should show only: main, main-initial-backup, and any preserve/* branches
git branch -a

# Tags should now contain the checkpoint history
git tag -l "checkpoint/*"
```

---

## Phase 5: Cleanup (Only After Everything Works)

**Goal**: Remove redundant branches and archive Finder copies.

### 5.1 Verify Remote State

```bash
git fetch origin
git branch -a  # Confirm main is correct
git remote show origin  # Confirm HEAD points to main
```

### 5.2 Archive Finder Copies

**Do not delete. Move to archive location:**

```bash
ARCHIVE_DIR=~/Archives/adhs-copies-$(date +%Y-%m-%d)
mkdir -p "$ARCHIVE_DIR"

mv "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy 2" "$ARCHIVE_DIR/"
mv "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy 3" "$ARCHIVE_DIR/"
mv "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy 4" "$ARCHIVE_DIR/"
```

### 5.3 Delete Preservation Branches (Optional)

Only after confirming main contains everything:

```bash
git branch -d preserve/copy3-ai-refactor
git branch -d preserve/original-state
git push origin --delete preserve/copy3-ai-refactor
git push origin --delete preserve/original-state
```

### 5.4 Final Verification

```bash
# Branch list should be clean
git branch -a
# Expected:
#   main
#   main-initial-backup
#   remotes/origin/main

# Tags should preserve checkpoint history
git tag -l
# Expected:
#   checkpoint/through-analysis
#   checkpoint/through-mcao
#   checkpoint/through-ecorp
#   checkpoint/through-batchdata
```

---

## Branch Naming Conventions (Going Forward)

Once consolidation is complete, use these conventions:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New functionality | `feature/add-pinal-county` |
| `bugfix/` | Fixes to existing behavior | `bugfix/batchdata-header-mismatch` |
| `chore/` | Non-functional changes | `chore/update-dependencies` |
| `experiment/` | AI-assisted or risky refactors | `experiment/ai-refactor-2025-11-25` |
| `preserve/` | Historical snapshots (temporary) | `preserve/copy3-ai-refactor` |

### Tag Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `checkpoint/` | Historical pipeline states | `checkpoint/through-mcao` |
| `release/` | Production releases | `release/v1.0.0` |

---

## Rules for AI-Assisted Changes

1. **Never run AI refactors directly on main**
2. **Always create an experiment branch first**
   ```bash
   git checkout main
   git checkout -b experiment/ai-something-YYYY-MM-DD
   ```
3. **Commit current state before AI modifies files**
4. **Run golden tests after AI changes**
5. **Review diffs before merging** - AI may delete files that are still needed

---

## Summary Checklist

- [ ] **Phase 0**: Fix remote state
  - [ ] Broken HEAD reference removed
  - [ ] Remote connectivity verified
  - [ ] `git log --graph --all` works without errors
  - [ ] `.gitignore` updated with `test-outputs/`
- [ ] **Phase 1**: Finder copy inventory complete
  - [ ] Copy 3 vs Current diff reviewed
  - [ ] Original vs Current diff reviewed
  - [ ] **Copy 2 vs Current** assessed (unique changes?)
  - [ ] **Copy 4 vs Current** assessed (unique changes?)
  - [ ] INVENTORY.md created with verdicts for each copy
  - [ ] Deleted files assessed
- [ ] **Phase 1.5**: Branch inventory complete
  - [ ] BRANCH_INVENTORY.md created
  - [ ] Merged vs unmerged branches identified
  - [ ] Duplicate branches identified
  - [ ] Checkpoint branches marked for tag conversion
- [ ] **Phase 2**: All preservation branches created and pushed
  - [ ] Current state committed
  - [ ] `preserve/copy3-ai-refactor` created
  - [ ] `preserve/original-state` created (if needed)
  - [ ] `preserve/copy2-state` created (if unique content)
  - [ ] `preserve/copy4-state` created (if unique content)
- [ ] **Phase 3**: Golden tests run on all branches
  - [ ] `run_golden_tests.sh` created and executable
  - [ ] **`compare_excel_outputs.py`** created (Python, not shell!)
  - [ ] Tests run on `chore/consolidate-env-files`
  - [ ] Tests run on `preserve/copy3-ai-refactor`
  - [ ] Excel outputs compared using Python script
- [ ] **Phase 3.5**: Unit tests validated
  - [ ] `pytest` passes on current branch
  - [ ] `pytest` passes on AI refactor branch
  - [ ] Coverage meets threshold (≥80%)
  - [ ] VALIDATION_RESULTS.md created with both golden + unit test results
- [ ] **Phase 3.9**: Rollback point created
  - [ ] `rollback/pre-integration-YYYYMMDD` tag created
  - [ ] Tag pushed to remote
- [ ] **Phase 4**: Integration complete
  - [ ] Collaborators notified (if applicable)
  - [ ] Option A/B/C selected with rationale
  - [ ] Merge conflicts resolved (if any)
  - [ ] Deleted files validated as obsolete (or kept)
  - [ ] Main branch promoted
  - [ ] Remote tracking verified (`git branch -vv`)
- [ ] **Phase 4.5**: Branch cleanup complete
  - [ ] Checkpoint branches converted to tags
  - [ ] Duplicate branches deleted
  - [ ] Typo branches deleted
  - [ ] Only main + backup branches remain
- [ ] **Phase 5**: Final cleanup
  - [ ] Finder copies archived (not deleted)
  - [ ] Preservation branches deleted (optional)
  - [ ] Final verification passed

---

## Estimated Time

| Phase | Estimated Duration | Notes |
|-------|-------------------|-------|
| Phase 0 | 5-10 min | Quick git commands |
| Phase 1 | 30-60 min | Careful review of diffs |
| Phase 1.5 | 15-30 min | Branch analysis |
| Phase 2 | 20-40 min | Creating preservation branches |
| Phase 3 | 30-60 min | Running pipeline tests |
| Phase 3.5 | 10-20 min | Unit tests |
| Phase 3.9 | 5 min | Creating rollback tag |
| Phase 4 | 15-30 min | Integration + verification |
| Phase 4.5 | 20-30 min | Branch cleanup |
| Phase 5 | 10-15 min | Final cleanup |
| **Total** | **2.5-5 hours** | Varies based on findings |

⚠️ **Do not rush.** This is a conservative strategy intentionally. Taking time now prevents data loss later.
