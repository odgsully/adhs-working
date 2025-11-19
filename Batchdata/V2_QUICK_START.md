# BatchData V2 Quick Start Guide

**Status**: Ready for V2 Implementation
**Date**: 2025-11-17

---

## ✅ What's Been Done

### 1. Base URLs Updated to V2
- ✅ `template_config.xlsx` → Now uses `/api/v2`
- ✅ `batchdata_local_input.xlsx` → Now uses `/api/v2`
- ✅ `batchdata.py` → Default changed to `/api/v2`
- ✅ Multiple Upload files updated

### 2. Implementation Plan Refactored
- Created `V2_IMPLEMENTATION_PLAN.md` with complete V2 approach
- Updated `SYNC_MIGRATION_IMPLEMENTATION.md` for V2
- Documented V2 flow (CSV upload → polling → download)

---

## 🔧 What You Need to Do Now

### Step 1: Fix State Field (5 minutes)

Edit `Batchdata/src/transform.py` around line 140:

```python
# Find this section in ecorp_to_batchdata_records function:
if agent_address:
    address_parts = parse_address(agent_address)

    # ADD THIS FIX:
    if not address_parts.get('state') or address_parts['state'] == '':
        domicile_state = ecorp_row.get('Domicile State', '')
        if domicile_state:
            address_parts['state'] = normalize_state(domicile_state)
        elif 'MARICOPA' in str(ecorp_row.get('County', '')).upper():
            address_parts['state'] = 'AZ'

    base_info.update({
        'address_line1': address_parts['line1'],
        'address_line2': address_parts['line2'],
        'city': address_parts['city'],
        'state': address_parts['state'],  # Now will be populated!
        'zip': address_parts['zip'],
        'county': ecorp_row.get('County', '') or ecorp_row.get('COUNTY', '')
    })
```

### Step 2: Test V2 API (2 minutes)

```bash
# Test with the CSV we created
export BD_SKIPTRACE_KEY="your-api-key"

# Quick test with curl
curl -X POST https://api.batchdata.com/api/v2/property/skip-trace/async \
  -H "Authorization: Bearer $BD_SKIPTRACE_KEY" \
  -F "file=@Batchdata/test_v2.csv"

# Should return a job_id if working
```

### Step 3: Run Full Pipeline (10 minutes)

```bash
# Run the existing async pipeline
cd /Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/"adhs-restore-28-Jul-2025 copy"
python3 scripts/process_months_local.py

# Select month 10.24
# Choose BatchData enrichment when prompted
```

---

## 📋 V2 API Flow Reminder

```
1. Create CSV file with data
2. Upload CSV to /api/v2/property/skip-trace/async
3. Get job_id from response
4. Poll /api/v2/jobs/{job_id} until status=complete
5. Download results from /api/v2/jobs/{job_id}/download
6. Parse CSV results back to Excel
```

Your existing `BatchDataClient` in `batchdata.py` already does all this!

---

## 🎯 Expected Results

### Before (V3 - Not Working)
- 403 Forbidden (no subscription)
- Wrong endpoint structure
- JSON requests not supported with wallet

### After (V2 - Should Work)
- 200 OK with job_id
- CSV upload works with wallet credits
- Proper async polling flow

---

## 💰 Cost with Wallet Credits

Check your dashboard for current balance. With V2:
- Skip-trace: $0.07 per record
- Deducts from wallet balance immediately
- No monthly subscription needed

---

## 🐛 Troubleshooting

### If you get 401/403 errors:
- Check API key is correct
- Verify you have wallet credits available
- Make sure using `/api/v2` not `/api/v3`

### If state field still empty:
- Apply the transform.py fix above
- Check Ecorp data has "Domicile State" column

### If job polling times out:
- Large batches take longer
- Increase timeout in polling logic
- Check job status manually with job_id

---

## ✅ Success Criteria

You'll know it's working when:
1. CSV upload returns job_id (not 403 error)
2. Job status shows "complete" after polling
3. Downloaded CSV has phone/email data
4. Complete Excel file has enriched data

---

## 📞 Next Steps After V2 Works

1. **Phase 2**: Implement smart indexing (30-40% cost savings)
2. **Phase 3**: Add interactive stage selection
3. **Phase 4**: Full testing and optimization

---

**Good luck!** The V2 implementation should work with your wallet credits. The main changes were:
- Base URL: `/api/v3` → `/api/v2`
- Fix state field using Domicile State
- Use existing async code (it was already built for V2 pattern!)