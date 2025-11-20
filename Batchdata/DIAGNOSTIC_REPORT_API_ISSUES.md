# BatchData API Diagnostic Report

**Date**: 2025-11-17 15:20:00
**Status**: Two Critical Issues Identified

---

## Executive Summary

The BatchData integration is failing due to **two separate issues**:

1. **API Permission Issue (Primary)**: The API key doesn't have permission for the skip-trace endpoint
2. **Data Quality Issue (Secondary)**: State field is missing from all records

Both issues need to be resolved for the integration to work.

---

## Issue #1: API Key Permission Error

### Problem
All API calls are returning **403 Forbidden** with the message:
```json
{
  "status": {
    "code": 403,
    "text": "Forbidden",
    "message": "Provided token does not have permission to access this API."
  }
}
```

### Evidence
- API Key exists: `3U0uXDGxnD...` (confirmed loaded)
- Endpoint should be v1: `https://api.batchdata.com/api/v1/property/skip-trace`
- Request format is valid (tested with proper JSON structure)
- Error is consistent: 403 on all requests

### Root Cause - UPDATED 2025-11-18
The API key has **async** permission but not **sync** permission:

**Testing Results:**
- `/api/v1/property/skip-trace` (sync) → **403 Forbidden** (no permission)
- `/api/v1/property/skip-trace/async` → **400 Bad Request** (needs webhook - but permission OK!)
- `/api/v2/*` endpoints → **404 Not Found** (don't exist)

### Solutions

**OPTION 1: Contact BatchData (Recommended)**
1. Log into BatchData dashboard
2. Go to API Keys section
3. Request "property-skip-trace" (sync) permission be added
4. This allows the simpler JSON request/response flow

**OPTION 2: Use Async with Webhook**
1. Set up a webhook receiver (e.g., https://webhook.site for testing)
2. Pass webhook URL in request options
3. Modify batchdata_bridge.py to set `use_sync=False`
4. Implement webhook handler to receive and process results

**OPTION 3: Use BatchData CSV File Upload (Manual)**
1. Export data to CSV format
2. Upload CSV manually via BatchData dashboard
3. Download results when processing completes
4. Import results back into pipeline

### Current Code Default
The pipeline in `batchdata_bridge.py` defaults to `use_sync=True` which causes the 403 error.
To use async, set `use_sync=False` but you'll need a webhook URL configured.

---

## Issue #2: Missing State Field in Data

### Problem
All records have empty state fields, which will cause API failures even after fixing permissions.

### Evidence
From data analysis:
```
Missing Critical Fields:
- state: 4/4 records missing (100%)
- address_line1: 1/4 records missing (25%)
- city: 1/4 records missing (25%)
```

Sample request being sent:
```json
{
  "propertyAddress": {
    "street": "8888 E Raintree Drive",
    "city": "SCOTTSDALE",
    "state": "",  // ← EMPTY
    "zip": "85260"
  }
}
```

### Root Cause
The Ecorp data has state in a separate "ECORP_STATE" column, but the transformation is looking for state within the address string.

**Data Flow Issue**:
1. Ecorp Complete has: `ECORP_STATE: Arizona`
2. Ecorp Complete has: `Address: 8888 E Raintree Drive` (no state)
3. Transform tries to parse state from address string
4. No state found → empty state field
5. API receives invalid request

### Solution: Fix Transform to Use ECORP_STATE

**File to modify**: `Batchdata/src/transform.py`

**Add this fix to the `ecorp_to_batchdata_records` function** (around line 140):

```python
def ecorp_to_batchdata_records(ecorp_row: pd.Series) -> List[Dict[str, Any]]:
    # ... existing code ...

    # Extract address information
    agent_address = ecorp_row.get('Agent Address', '')
    if not agent_address:
        agent_address = ecorp_row.get('StatutoryAgent1_Address', '')

    if agent_address:
        address_parts = parse_address(agent_address)

        # FIX: Use ECORP_STATE if state not found in address
        if not address_parts['state'] or address_parts['state'] == '':
            domicile_state = ecorp_row.get('ECORP_STATE', '')
            if domicile_state:
                # Convert full state name to abbreviation
                address_parts['state'] = normalize_state(domicile_state)

        base_info.update({
            'address_line1': address_parts['line1'],
            'address_line2': address_parts['line2'],
            'city': address_parts['city'],
            'state': address_parts['state'],  # Now will have state from ECORP_STATE
            'zip': address_parts['zip'],
            'county': ecorp_row.get('ECORP_COUNTY', '') or ecorp_row.get('COUNTY', '')
        })
```

---

## Testing After Fixes

### Step 1: Test API Key
```bash
# Set correct API key
export BD_SKIPTRACE_KEY="your-correct-skip-trace-key"

# Test directly
python3 Batchdata/test_api_directly.py
```

Expected: 200 OK response with data

### Step 2: Apply Transform Fix
1. Edit `Batchdata/src/transform.py` as shown above
2. Re-run the transformation to create new Upload file
3. Verify state field is populated

### Step 3: Full Pipeline Test
```bash
# Run with small batch
python3 scripts/process_months_local.py
# Select month 10.24
# Choose BatchData enrichment
```

---

## Current Data Sample

Here's what's actually being processed:

| Record | Name | Address | City | State | Issue |
|--------|------|---------|------|-------|-------|
| 1 | ERIC MAUGHAN | [empty] | [empty] | [empty] | No address data |
| 2 | BRUCE GRIMM | 8888 E Raintree Dr | SCOTTSDALE | [empty] | Missing state |
| 3 | KATHLEEN O'NEIL | 8888 E Raintree Dr | SCOTTSDALE | [empty] | Missing state |
| 4 | BRUCE GRIMM | 8888 E Raintree Dr | SCOTTSDALE | [empty] | Missing state |

**Note**: Even record 1 with no address will fail, but records 2-4 would work if state was populated.

---

## Action Items

### Immediate Actions
1. ✅ **Check API Key Permissions**
   - Log into BatchData dashboard
   - Verify skip-trace service is enabled
   - Get correct API key if needed

2. ✅ **Fix State Field**
   - Apply the transform.py modification
   - Use ECORP_STATE column as fallback

3. ✅ **Test with Fixed Data**
   - Re-run with corrected API key
   - Verify state field populated
   - Check for successful enrichment

### Follow-up Actions
1. Consider implementing data validation before API calls
2. Add better error handling for specific API errors
3. Log API responses for debugging
4. Add state validation/defaulting logic

---

## Summary

**Two fixes needed**:
1. **API Key**: Get skip-trace enabled API key from BatchData
2. **State Field**: Modify transform.py to use ECORP_STATE column

Once both are fixed, the integration should work correctly. The code itself is functioning properly - it's an authentication and data quality issue.

---

**Next Steps After Fixes**:
- Phase 2: Smart Indexing (30-40% cost savings)
- Phase 3: Interactive stage selection
- Phase 4: Full integration testing