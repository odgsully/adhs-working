# Immediate Fix Instructions

## Quick Solution: Enable Sync Permission

Based on your BatchData dashboard screenshot, the fix is simple:

### 1. Enable the Right Permission (30 seconds)

1. Go to your BatchData dashboard (where you took the screenshot)
2. Click on **"skiptrace bulk"** token (the one highlighted in red)
3. In the permissions dialog:
   - ✅ CHECK the box for **"property-skip-trace"**
   - Keep "property-skip-trace-async" checked as well
4. Click **UPDATE**
5. Done! Your API key now has the right permissions.

### 2. Fix the State Field Issue (2 minutes)

While we're fixing things, let's also fix the missing state field:

Edit `Batchdata/src/transform.py` (around line 140-150):

**Find this section:**
```python
if agent_address:
    address_parts = parse_address(agent_address)
    base_info.update({
        'address_line1': address_parts['line1'],
        'address_line2': address_parts['line2'],
        'city': address_parts['city'],
        'state': address_parts['state'],
        'zip': address_parts['zip'],
        'county': ecorp_row.get('County', '') or ecorp_row.get('COUNTY', '')
    })
```

**Replace with:**
```python
if agent_address:
    address_parts = parse_address(agent_address)

    # FIX: Use Domicile State if state not found in address
    if not address_parts.get('state') or address_parts['state'] == '':
        domicile_state = ecorp_row.get('Domicile State', '')
        if domicile_state and str(domicile_state).strip():
            address_parts['state'] = normalize_state(domicile_state)
        elif 'MARICOPA' in str(ecorp_row.get('County', '')).upper():
            address_parts['state'] = 'AZ'

    base_info.update({
        'address_line1': address_parts['line1'],
        'address_line2': address_parts['line2'],
        'city': address_parts['city'],
        'state': address_parts['state'],  # Now populated!
        'zip': address_parts['zip'],
        'county': ecorp_row.get('County', '') or ecorp_row.get('COUNTY', '')
    })
```

### 3. Test It Works (1 minute)

```bash
# Test the API directly
python3 Batchdata/test_api_directly.py

# If you see "200 OK" - it works!
# Then run the full pipeline:
python3 scripts/process_months_local.py
```

---

## Summary

You were SO close! Your API key just needs one checkbox enabled:
- ❌ Current: Only has `property-skip-trace-async` permission
- ✅ Needed: Enable `property-skip-trace` permission

Once you check that box and apply the state field fix, everything will work perfectly!