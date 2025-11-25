"""
Test script to verify address parsing and entity/individual logic fixes
"""

import os
import sys
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_address_parsing():
    """Test the improved address parsing function."""
    print("🏠 Testing Address Parsing Fixes")
    print("-" * 50)
    
    from src.transform import parse_address
    
    # Test cases from problematic CSV data
    test_addresses = [
        "3125 S. Gilbert Road,,85286,USA",
        "7955 S Priest Dr.,,AZ 85284,USA", 
        "3125 S GILBERT RD, CHANDLER, AZ 85286, USA",
        "14403 N 75TH AVE,,85381,USA",
        "2156 E LIBERTY LANE,,85048,USA",
        "3560 West Mesquite,,85142,USA"
    ]
    
    expected_results = [
        {"address": "3125 S. Gilbert Road,,85286,USA", "zip": "85286", "state": "", "city": ""},
        {"address": "7955 S Priest Dr.,,AZ 85284,USA", "zip": "85284", "state": "AZ", "city": ""},
        {"address": "3125 S GILBERT RD, CHANDLER, AZ 85286, USA", "zip": "85286", "state": "AZ", "city": "CHANDLER"},
        {"address": "14403 N 75TH AVE,,85381,USA", "zip": "85381", "state": "", "city": ""},
        {"address": "2156 E LIBERTY LANE,,85048,USA", "zip": "85048", "state": "", "city": ""},
        {"address": "3560 West Mesquite,,85142,USA", "zip": "85142", "state": "", "city": ""}
    ]
    
    passed = 0
    total = len(test_addresses)
    
    for i, test_addr in enumerate(test_addresses):
        result = parse_address(test_addr)
        expected = expected_results[i]
        
        print(f"\n📍 Test {i+1}: {test_addr}")
        print(f"   Result: City='{result['city']}', State='{result['state']}', ZIP='{result['zip']}'")
        
        # Check ZIP code (most important fix)
        zip_correct = result['zip'] == expected['zip']
        state_correct = result['state'] == expected['state'] or (result['state'] and expected['state'] == '')
        
        if zip_correct and (state_correct or result['state'] != 'USA'):
            print(f"   ✅ PASS - ZIP correct, State not 'USA'")
            passed += 1
        else:
            print(f"   ❌ FAIL - Expected ZIP: {expected['zip']}, Got: {result['zip']}")
            print(f"            Expected State: {expected['state']}, Got: {result['state']}")
    
    print(f"\n📊 Address Parsing Results: {passed}/{total} tests passed")
    return passed == total


def test_entity_individual_logic():
    """Test entity vs individual detection logic."""
    print("\n👥 Testing Entity vs Individual Logic")
    print("-" * 50)
    
    from src.transform import ecorp_to_batchdata_records
    
    # Create test eCorp records with problematic statutory agents
    test_records = [
        {
            'ECORP_NAME_S': 'CC/PDR SILVERSTONE LLC',
            'ECORP_ENTITY_ID_S': 'L12222688',
            'Statutory Agent': 'CC/PDR SILVERSTONE, L.L.C.',
            'Agent Address': '7955 S Priest Dr.,,AZ 85284,USA',
            'ECORP_COUNTY': 'Maricopa',
            'Title1': '', 'Name1': '', 'Address1': '',
            'Title2': '', 'Name2': '', 'Address2': '',
            'Title3': '', 'Name3': '', 'Address3': ''
        },
        {
            'ECORP_NAME_S': 'Test Individual Entity',
            'ECORP_ENTITY_ID_S': 'TEST001',
            'Statutory Agent': 'John Doe',
            'Agent Address': '123 Main St, Phoenix, AZ 85001, USA',
            'ECORP_COUNTY': 'Maricopa',
            'Title1': '', 'Name1': '', 'Address1': '',
            'Title2': '', 'Name2': '', 'Address2': '',
            'Title3': '', 'Name3': '', 'Address3': ''
        }
    ]
    
    passed = 0
    total = len(test_records)
    
    for i, test_record in enumerate(test_records):
        test_row = pd.Series(test_record)
        results = ecorp_to_batchdata_records(test_row)
        
        print(f"\n🏢 Test {i+1}: {test_record['Statutory Agent']}")
        
        if results:
            result = results[0]  # Should only be one record for these tests
            
            statutory_agent = test_record['Statutory Agent']
            first_name = result.get('BD_TARGET_FIRST_NAME', '')
            last_name = result.get('BD_TARGET_LAST_NAME', '')
            title_role = result.get('BD_TITLE_ROLE', '')
            
            print(f"   Statutory Agent: {statutory_agent}")
            print(f"   First Name: '{first_name}'")
            print(f"   Last Name: '{last_name}'")
            print(f"   Title Role: '{title_role}'")
            
            # Test entity agent (should have empty first/last names)
            if 'L.L.C.' in statutory_agent or 'LLC' in statutory_agent:
                if not first_name and not last_name and 'Entity' in title_role:
                    print(f"   ✅ PASS - Entity agent correctly identified")
                    passed += 1
                else:
                    print(f"   ❌ FAIL - Entity agent should have empty first/last names")
            
            # Test individual agent (should have first/last names)
            elif statutory_agent == 'John Doe':
                if first_name == 'John' and last_name == 'Doe':
                    print(f"   ✅ PASS - Individual agent correctly identified")
                    passed += 1
                else:
                    print(f"   ❌ FAIL - Individual agent should have proper first/last names")
        else:
            print(f"   ❌ FAIL - No records generated")
    
    print(f"\n📊 Entity/Individual Logic Results: {passed}/{total} tests passed")
    return passed == total


def test_with_real_data():
    """Test fixes with actual eCorp data transformation."""
    print("\n🧪 Testing with Real eCorp Data")
    print("-" * 50)
    
    try:
        from src.transform import transform_ecorp_to_batchdata
        
        # Load first 3 records from eCorp data for testing
        ecorp_df = pd.read_excel("../M.YY_Ecorp_Complete.xlsx").head(3)
        print(f"Loaded {len(ecorp_df)} eCorp records for testing")
        
        # Transform to BatchData format
        batchdata_df = transform_ecorp_to_batchdata(ecorp_df)
        print(f"Transformed to {len(batchdata_df)} BatchData records")
        
        # Check for common issues
        issues = []
        
        # Check for 'USA' in state column
        usa_states = batchdata_df[batchdata_df['BD_STATE'] == 'USA']
        if len(usa_states) > 0:
            issues.append(f"{len(usa_states)} records have 'USA' in state column")

        # Check for ZIP codes in city column
        zip_in_city = batchdata_df[batchdata_df['BD_CITY'].str.match(r'^\d{5}$', na=False)]
        if len(zip_in_city) > 0:
            issues.append(f"{len(zip_in_city)} records have ZIP codes in city column")

        # Check for empty ZIP codes where we should have them
        empty_zips = batchdata_df[batchdata_df['BD_ZIP'] == '']
        print(f"Records with empty ZIP codes: {len(empty_zips)}")

        # Check for entity names in individual fields
        entity_keywords = ['LLC', 'INC', 'CORP', 'COMPANY']
        entity_in_first_name = batchdata_df[
            batchdata_df['BD_TARGET_FIRST_NAME'].str.contains('|'.join(entity_keywords), case=False, na=False)
        ]
        if len(entity_in_first_name) > 0:
            issues.append(f"{len(entity_in_first_name)} records have entity names in first name field")

        print(f"\n📋 Sample transformed record:")
        sample = batchdata_df.iloc[0]
        for col in ['BD_RECORD_ID', 'BD_TARGET_FIRST_NAME', 'BD_TARGET_LAST_NAME', 'BD_CITY', 'BD_STATE', 'BD_ZIP']:
            print(f"   {col}: '{sample[col]}'")
        
        if issues:
            print(f"\n❌ Issues found:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print(f"\n✅ No major issues found in transformation")
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def main():
    """Run all fix verification tests."""
    print("🔧 Address Parsing and Entity Logic Fix Tests")
    print("=" * 60)
    
    tests = [
        test_address_parsing,
        test_entity_individual_logic,
        test_with_real_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
    
    print(f"\n=== Fix Verification Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All fixes working correctly!")
    else:
        print(f"⚠️  {total - passed} tests failed - additional fixes needed")


if __name__ == "__main__":
    main()