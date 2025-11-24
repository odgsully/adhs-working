# BRANCH INVENTORY - `adhs-working`

Generated: 2025-11-24

## Summary

- Current working branch: `chore/consolidate-env-files` at `1eac4f4` (ahead 2 from `048874f`)
- Total branches: 10
- Branches merged into current: **ALL 10**
- Branches with unique commits: **NONE**

## Branch Assessment

### Active Development

| Branch | Status | Action |
|--------|--------|--------|
| `chore/consolidate-env-files` | Current work | Promote to main |
| `main` | Initial commit only (`3550ca2`) | Rename to main-initial-backup |

### Checkpoint Branches (Candidates for Tags)

All checkpoint branches have **NO unique commits** - they are just markers in the history.

| Branch | Commit | Unique Commits? | Recommendation |
|--------|--------|-----------------|----------------|
| `Ensure-proper-through-analysis` | `5f9b72a` | No | Convert to tag |
| `Ensure-Proper-Through-MCAO` | `5204301` | No | Convert to tag |
| `Ensure-Proper-Thorugh-Ecorp` | `9d90737` | No | Convert to tag (fix typo) |
| `Ensure-Proper-Through-Batchdata` | `d1d0e06` | No | Convert to tag |
| `All-good-thru-Ecorp-MCAO-backtrack` | `d1d0e06` | No | Delete (duplicate) |
| `2-Ensure-Proper-Through-Analysis` | `da7ea13` | No | Convert to tag |

### Duplicate Branches (Same Commit)

| Branches | Commit | Keep Which? |
|----------|--------|-------------|
| `Ensure-Proper-Through-Batchdata`, `All-good-thru-Ecorp-MCAO-backtrack` | `d1d0e06` | Keep Batchdata as tag, delete backtrack |
| `feature/standardize-file-naming`, `batchdata-lockinlockinlockin-api` | `a9d6e56` | Keep feature/standardize as tag, delete batchdata-lockin |

### Feature Branches

| Branch | Commit | Action |
|--------|--------|--------|
| `feature/standardize-file-naming` | `a9d6e56` | Delete (merged, duplicate) |
| `batchdata-lockinlockinlockin-api` | `a9d6e56` | Delete (merged, duplicate) |

### Branches to Delete

| Branch | Reason |
|--------|--------|
| `Ensure-Proper-Thorugh-Ecorp` | Typo in name, content preserved in tag |
| `All-good-thru-Ecorp-MCAO-backtrack` | Duplicate of Batchdata checkpoint |
| `batchdata-lockinlockinlockin-api` | Duplicate of feature/standardize |
| `feature/standardize-file-naming` | Merged, no longer needed |

## Tag Naming Convention

Convert checkpoint branches to tags with format: `checkpoint/{description}`

Planned tags:
- `checkpoint/through-analysis` ← `Ensure-proper-through-analysis`
- `checkpoint/through-mcao` ← `Ensure-Proper-Through-MCAO`
- `checkpoint/through-ecorp` ← `Ensure-Proper-Thorugh-Ecorp`
- `checkpoint/through-batchdata` ← `Ensure-Proper-Through-Batchdata`
- `checkpoint/analysis-v2` ← `2-Ensure-Proper-Through-Analysis`

## Recommendation

Proceed to Phase 2: [x] Yes

**Key insight**: All branches are already merged into current. The checkpoint branches serve as historical markers only. Converting them to tags is safe and will clean up the branch list significantly.

**Expected final state:**
- Branches: `main`, `main-initial-backup`
- Tags: 5 checkpoint tags + any existing tags
