#!/usr/bin/env python3
"""
Fix for missing state field in BatchData transformation.
This script shows the exact changes needed in transform.py
"""

# ADD THIS CODE to Batchdata/src/transform.py
# In the ecorp_to_batchdata_records function (around line 140-150)

# FIND THIS SECTION:
"""
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
"""

# REPLACE WITH:
"""
    if agent_address:
        address_parts = parse_address(agent_address)

        # FIX: Use Domicile State if state not found in address
        if not address_parts.get('state') or address_parts['state'] == '':
            # Try Domicile State column first
            domicile_state = ecorp_row.get('Domicile State', '')
            if domicile_state and str(domicile_state).strip():
                # normalize_state handles both full names and abbreviations
                address_parts['state'] = normalize_state(domicile_state)
            else:
                # Default to AZ if in Maricopa county
                county = ecorp_row.get('County', '') or ecorp_row.get('COUNTY', '')
                if 'MARICOPA' in str(county).upper():
                    address_parts['state'] = 'AZ'

        base_info.update({
            'address_line1': address_parts['line1'],
            'address_line2': address_parts['line2'],
            'city': address_parts['city'],
            'state': address_parts['state'],  # Now populated from Domicile State
            'zip': address_parts['zip'],
            'county': ecorp_row.get('County', '') or ecorp_row.get('COUNTY', '')
        })
"""

# ALSO UPDATE the section where individual principal addresses are processed (around line 173-182):

# FIND THIS:
"""
        # Parse address if provided, otherwise use base address
        if address and not pd.isna(address) and str(address).strip():
            addr_parts = parse_address(address)
        else:
            addr_parts = {
                'line1': base_info.get('address_line1', ''),
                'line2': base_info.get('address_line2', ''),
                'city': base_info.get('city', ''),
                'state': base_info.get('state', ''),
                'zip': base_info.get('zip', '')
            }
"""

# REPLACE WITH:
"""
        # Parse address if provided, otherwise use base address
        if address and not pd.isna(address) and str(address).strip():
            addr_parts = parse_address(address)

            # FIX: Use Domicile State if state not found in principal's address
            if not addr_parts.get('state') or addr_parts['state'] == '':
                # First try base_info state (which now has Domicile State)
                if base_info.get('state'):
                    addr_parts['state'] = base_info['state']
                else:
                    # Then try Domicile State directly
                    domicile_state = ecorp_row.get('Domicile State', '')
                    if domicile_state and str(domicile_state).strip():
                        addr_parts['state'] = normalize_state(domicile_state)
                    # Finally default to AZ for Maricopa
                    elif 'MARICOPA' in str(base_info.get('county', '')).upper():
                        addr_parts['state'] = 'AZ'
        else:
            addr_parts = {
                'line1': base_info.get('address_line1', ''),
                'line2': base_info.get('address_line2', ''),
                'city': base_info.get('city', ''),
                'state': base_info.get('state', ''),  # Will have state from base_info
                'zip': base_info.get('zip', '')
            }
"""

print("""
============================================================
State Field Fix Instructions
============================================================

1. Open: Batchdata/src/transform.py

2. Find the ecorp_to_batchdata_records function (around line 116)

3. Apply the changes shown above to:
   - Line ~140-150: Fix base address state extraction
   - Line ~173-182: Fix principal address state extraction

4. The key changes:
   - Check if state is empty after parse_address
   - Use 'Domicile State' column as fallback
   - Default to 'AZ' for Maricopa county records

5. After applying fix:
   - Re-run the ETL pipeline
   - State field should be populated
   - API calls should work (once API key is fixed)

============================================================
""")

# Test the logic
def test_state_fix():
    """Test that the state fix logic works correctly."""

    def normalize_state(state_input):
        """Simplified normalize_state for testing."""
        state_map = {
            'ARIZONA': 'AZ',
            'AZ': 'AZ',
            'CALIFORNIA': 'CA',
            'CA': 'CA',
            'TEXAS': 'TX',
            'TX': 'TX'
        }
        return state_map.get(str(state_input).upper().strip(), state_input)

    # Test cases
    test_cases = [
        {
            'name': 'Full state name',
            'domicile_state': 'Arizona',
            'expected': 'AZ'
        },
        {
            'name': 'State abbreviation',
            'domicile_state': 'AZ',
            'expected': 'AZ'
        },
        {
            'name': 'Empty state with Maricopa',
            'domicile_state': '',
            'county': 'MARICOPA',
            'expected': 'AZ'
        }
    ]

    print("\nTesting state fix logic:")
    print("-" * 40)

    for test in test_cases:
        domicile = test.get('domicile_state', '')
        county = test.get('county', '')

        # Apply fix logic
        state = ''
        if domicile and str(domicile).strip():
            state = normalize_state(domicile)
        elif 'MARICOPA' in str(county).upper():
            state = 'AZ'

        passed = state == test['expected']
        status = "✅ PASS" if passed else "❌ FAIL"

        print(f"{test['name']}: {status}")
        print(f"  Input: domicile='{domicile}', county='{county}'")
        print(f"  Output: '{state}' (expected: '{test['expected']}')")
        print()

if __name__ == "__main__":
    test_state_fix()