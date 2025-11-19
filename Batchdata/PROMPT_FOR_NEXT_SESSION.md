# Prompt for Next Claude Code Session

Copy and paste this prompt into a new Claude Code instance to continue:

---

## Prompt to Continue BatchData V2 Implementation

```
I'm working on BatchData integration using V2 API (wallet credits, not V3 subscription).

Current situation:
- Location: /Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy
- API: Using V2 (CSV upload + polling) with wallet credits
- Base URLs: Already updated to https://api.batchdata.com/api/v2
- Documentation: Read Batchdata/V2_QUICK_START.md for current status

Issues to fix:
1. State field is empty in all records - need to use "Domicile State" column from Ecorp data
2. Need to test V2 async flow with wallet credits

Please help me:
1. Apply the state field fix in Batchdata/src/transform.py (use Domicile State as fallback)
2. Test the V2 async pipeline with CSV upload/polling
3. Verify the Complete file has enriched phone/email data

The existing async code should work - it just needs the state field fix and testing with V2 endpoints.
```

---

## Alternative Detailed Prompt (if more context needed)

```
I need help completing BatchData V2 API integration for the ADHS ETL pipeline.

Project: /Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy

Background:
- Started with V3 implementation but discovered it requires subscription (I only have wallet credits)
- Refactored to V2 which works with wallet credits
- V2 uses CSV upload + job polling (async pattern)
- Base URLs already changed from /api/v3 to /api/v2

Current Status (read these files for details):
- Batchdata/SYNC_MIGRATION_IMPLEMENTATION.md - See "CURRENT STATUS CHECKPOINT" section
- Batchdata/V2_QUICK_START.md - Action items
- Batchdata/V2_IMPLEMENTATION_PLAN.md - Complete V2 approach

Immediate Tasks:
1. Fix missing state field issue:
   - Problem: State is empty in all records
   - Solution: Use "Domicile State" column from Ecorp data
   - File: Batchdata/src/transform.py (around line 140)
   - Code fix is provided in V2_QUICK_START.md

2. Test V2 API with wallet credits:
   - Upload test CSV to /api/v2/property/skip-trace/async
   - Poll job status
   - Download results

3. Run full pipeline:
   - Execute: python3 scripts/process_months_local.py
   - Select month 10.24
   - Enable BatchData enrichment

Expected outcome: The existing async code should work once the state field is fixed.
```

---

## Quick Context Files to Check

When starting the new session, have Claude read these files first:

1. `Batchdata/V2_QUICK_START.md` - Current action items
2. `Batchdata/src/transform.py` - Where to apply state field fix (line ~140)
3. `Batchdata/src/batchdata.py` - The async client (should work as-is)

---

## Test Commands

After applying fixes, test with:

```bash
# Set API key
export BD_SKIPTRACE_KEY="your-api-key"

# Test V2 endpoint
curl -X POST https://api.batchdata.com/api/v2/property/skip-trace/async \
  -H "Authorization: Bearer $BD_SKIPTRACE_KEY" \
  -F "file=@Batchdata/test_v2.csv"

# Run pipeline
python3 scripts/process_months_local.py
```

---

## Success Criteria

You'll know it's working when:
1. CSV upload returns a job_id (not 403 error)
2. Job status polling shows "complete"
3. Downloaded CSV has phone/email data
4. Complete Excel file shows enriched records

---

**Note**: The V3 sync client we built (`batchdata_sync.py`) is not needed for V2, but it's complete and tested if you ever upgrade to a subscription plan.