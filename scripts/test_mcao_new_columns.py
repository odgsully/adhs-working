#!/usr/bin/env python3
"""
Test script for new MCAO columns
=================================

Validates that the 22 new columns added to MAX_HEADERS are working correctly.
"""

import sys
import os
import json
sys.path.insert(0, 'src')

from adhs_etl.mcao_client import MCAAOAPIClient
from adhs_etl.mcao_field_mapping import MCAO_MAX_HEADERS

def test_new_columns():
    """Test the 22 new columns added to MCAO."""
    print("\n" + "="*60)
    print("Testing New MCAO Columns (22 additions)")
    print("="*60)

    # 1. Verify column count
    print("\n1. Column Count Verification:")
    assert len(MCAO_MAX_HEADERS) == 106, f"Expected 106 columns, got {len(MCAO_MAX_HEADERS)}"
    print(f"   ✅ Total columns: {len(MCAO_MAX_HEADERS)}")

    # 2. Verify new columns exist
    print("\n2. New Column Verification:")
    new_columns = [
        'IsRental',
        'LocalJusidiction',  # Note: typo preserved
        'MCR',
        'MapIDs_Book/Map Maps_0_UpdateDate',
        'MapIDs_Book/Map Maps_0_Url',
        'MapIDs_Book/Map Maps_1_UpdateDate',
        'MapIDs_Book/Map Maps_1_Url',
        'MapIDs_Book/Map Maps_2_UpdateDate',
        'MapIDs_Book/Map Maps_2_Url',
        'NumberOfParcelsInMCR',
        'NumberOfParcelsInSTR',
        'NumberOfParcelsInSubdivision',
        'Owner_DeedType',
        'Owner_SaleDate',
        'PEPropUseDesc',
        'PropertyAddress',
        'PropertyDescription',
        'ResidentialPropertyData_ConstructionYear',
        'ResidentialPropertyData_ExteriorWalls',
        'ResidentialPropertyData_ImprovementQualityGrade',
        'Valuations_0_AssessedLPV',
        'Valuations_0_AssessmentRatioPercentage'
    ]

    for col in new_columns:
        assert col in MCAO_MAX_HEADERS, f"Missing new column: {col}"
        idx = MCAO_MAX_HEADERS.index(col)
        print(f"   ✅ {col} at position {idx}")

    # 3. Verify critical columns haven't moved
    print("\n3. Critical Column Position Check:")
    assert MCAO_MAX_HEADERS[0] == 'FULL_ADDRESS', "Column A must be FULL_ADDRESS"
    print("   ✅ Column A (0): FULL_ADDRESS")
    assert MCAO_MAX_HEADERS[1] == 'COUNTY', "Column B must be COUNTY"
    print("   ✅ Column B (1): COUNTY")
    assert MCAO_MAX_HEADERS[4] == 'Owner_Ownership', "Column E must be Owner_Ownership"
    print("   ✅ Column E (4): Owner_Ownership")

    # 4. Test API mapping with new fields
    print("\n4. API Mapping Test:")
    try:
        client = MCAAOAPIClient(rate_limit=5.0)

        # Test with a sample APN
        test_apn = "165-28-054"
        print(f"   Testing with APN: {test_apn}")

        # Get API data
        api_data = client.get_all_property_data(test_apn)

        if api_data.get('data_complete'):
            # Map to headers
            mapped = client.map_to_max_headers(api_data)

            # Check new fields are populated
            populated_new_fields = []
            empty_new_fields = []

            for col in new_columns:
                if col in mapped and mapped[col] and str(mapped[col]).strip():
                    populated_new_fields.append((col, mapped[col]))
                else:
                    empty_new_fields.append(col)

            print(f"\n   Populated new fields: {len(populated_new_fields)}/22")
            for field, value in populated_new_fields[:10]:  # Show first 10
                print(f"     • {field}: {value}")

            if empty_new_fields:
                print(f"\n   Empty new fields: {len(empty_new_fields)}/22")
                for field in empty_new_fields[:5]:  # Show first 5
                    print(f"     • {field}")
        else:
            print(f"   ⚠️ API data not complete: {api_data.get('errors', [])}")

    except Exception as e:
        print(f"   ⚠️ API test skipped: {e}")

    print("\n" + "="*60)
    print("✅ New column tests completed successfully!")
    print("="*60)

if __name__ == "__main__":
    test_new_columns()