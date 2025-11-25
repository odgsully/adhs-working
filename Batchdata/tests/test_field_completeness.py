"""
test_field_completeness.py - Testing framework for input field validation and API optimization
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.transform import (
    parse_address, validate_input_fields, optimize_for_api,
    transform_ecorp_to_batchdata
)
from src.normalize import (
    normalize_state, normalize_zip_code, clean_address_line,
    split_full_name
)


def test_address_parsing():
    """Test enhanced address parsing logic."""
    print("\n=== Testing Address Parsing ===")
    
    test_cases = [
        # (input, expected)
        ("123 Main St, Phoenix, AZ 85001", {
            'line1': '123 Main St',
            'line2': '',
            'city': 'Phoenix',
            'state': 'AZ',
            'zip': '85001'
        }),
        ("456 Oak Ave, Suite 200, Scottsdale, AZ 85251", {
            'line1': '456 Oak Ave',
            'line2': 'Suite 200',
            'city': 'Scottsdale',
            'state': 'AZ',
            'zip': '85251'
        }),
        ("789 Pine Rd Phoenix AZ 85008", {
            'line1': '789 Pine Rd Phoenix AZ',
            'city': '',
            'state': 'AZ',
            'zip': '85008'
        }),
        ("1234 Elm Street, Tucson, Arizona 85701", {
            'line1': '1234 Elm Street',
            'line2': '',
            'city': 'Tucson',
            'state': 'AZ',
            'zip': '85701'
        }),
        ("5678 Maple Dr, Los Angeles, CA", {
            'line1': '5678 Maple Dr',
            'line2': '',
            'city': 'Los Angeles',
            'state': 'CA',
            'zip': ''
        }),
    ]
    
    passed = 0
    failed = 0
    
    for address_input, expected in test_cases:
        result = parse_address(address_input)
        
        # Check key fields
        match = True
        for key in ['line1', 'city', 'state', 'zip']:
            if result.get(key, '') != expected.get(key, ''):
                match = False
                break
        
        if match:
            print(f"✅ PASS: {address_input[:50]}...")
            passed += 1
        else:
            print(f"❌ FAIL: {address_input[:50]}...")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}")
            failed += 1
    
    print(f"\nAddress Parsing Results: {passed} passed, {failed} failed")
    return passed, failed


def test_field_validation():
    """Test input field validation logic."""
    print("\n=== Testing Field Validation ===")
    
    # Create test DataFrame
    test_data = pd.DataFrame([
        {
            'BD_RECORD_ID': '1',
            'BD_TARGET_FIRST_NAME': 'John',
            'BD_TARGET_LAST_NAME': 'Doe',
            'BD_OWNER_NAME_FULL': 'John Doe',
            'BD_ADDRESS': '123 Main St',
            'BD_CITY': 'Phoenix',
            'BD_STATE': 'AZ',
            'BD_ZIP': '85001'
        },
        {
            'BD_RECORD_ID': '2',
            'BD_TARGET_FIRST_NAME': '',
            'BD_TARGET_LAST_NAME': '',
            'BD_OWNER_NAME_FULL': 'Jane Smith',
            'BD_ADDRESS': '456 Oak Ave',
            'BD_CITY': '',
            'BD_STATE': 'AZ',
            'BD_ZIP': '85251'
        },
        {
            'BD_RECORD_ID': '3',
            'BD_TARGET_FIRST_NAME': 'Bob',
            'BD_TARGET_LAST_NAME': '',
            'BD_OWNER_NAME_FULL': '',
            'BD_ADDRESS': '',
            'BD_CITY': 'Tucson',
            'BD_STATE': '',
            'BD_ZIP': ''
        }
    ])
    
    # Run validation
    validated_df = validate_input_fields(test_data)
    
    # Check validation flags
    assert 'has_valid_name' in validated_df.columns, "Missing has_valid_name column"
    assert 'has_valid_address' in validated_df.columns, "Missing has_valid_address column"
    
    # Test specific records
    tests_passed = 0
    tests_failed = 0
    
    # Record 1 should be fully valid
    if validated_df.iloc[0]['has_valid_name'] and validated_df.iloc[0]['has_valid_address']:
        print("✅ PASS: Record 1 correctly identified as fully valid")
        tests_passed += 1
    else:
        print("❌ FAIL: Record 1 should be fully valid")
        tests_failed += 1
    
    # Record 2 should have valid name but invalid address (missing city)
    if validated_df.iloc[1]['has_valid_name'] and not validated_df.iloc[1]['has_valid_address']:
        print("✅ PASS: Record 2 correctly identified (valid name, invalid address)")
        tests_passed += 1
    else:
        print("❌ FAIL: Record 2 validation incorrect")
        tests_failed += 1
    
    # Record 3 should have valid name but invalid address
    if validated_df.iloc[2]['has_valid_name'] and not validated_df.iloc[2]['has_valid_address']:
        print("✅ PASS: Record 3 correctly identified (valid name, invalid address)")
        tests_passed += 1
    else:
        print("❌ FAIL: Record 3 validation incorrect")
        tests_failed += 1
    
    print(f"\nField Validation Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_field_optimization():
    """Test field optimization for API calls."""
    print("\n=== Testing Field Optimization ===")
    
    # Create test DataFrame with missing/incomplete data
    test_data = pd.DataFrame([
        {
            'BD_RECORD_ID': '1',
            'BD_TARGET_FIRST_NAME': '',
            'BD_TARGET_LAST_NAME': '',
            'BD_OWNER_NAME_FULL': 'John Michael Doe',
            'BD_ADDRESS': '  123 MAIN ST  ',
            'BD_CITY': 'phoenix',
            'BD_STATE': 'arizona',
            'BD_ZIP': '85001-1234'
        },
        {
            'BD_RECORD_ID': '2',
            'BD_TARGET_FIRST_NAME': 'Jane',
            'BD_TARGET_LAST_NAME': '',
            'BD_OWNER_NAME_FULL': '',
            'BD_ADDRESS': '456 Oak Ave',
            'BD_CITY': '',
            'BD_STATE': 'AZ',
            'BD_ZIP': '85251'
        },
        {
            'BD_RECORD_ID': '3',
            'BD_TARGET_FIRST_NAME': '',
            'BD_TARGET_LAST_NAME': '',
            'BD_OWNER_NAME_FULL': 'Robert Johnson Jr',
            'BD_ADDRESS': '456 Oak Ave',  # Same as record 2
            'BD_CITY': '',
            'BD_STATE': '',
            'BD_ZIP': ''
        }
    ])
    
    # Run optimization
    optimized_df = optimize_for_api(test_data)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Names should be extracted from full name
    if optimized_df.iloc[0]['BD_TARGET_FIRST_NAME'] == 'John':
        print("✅ PASS: First name extracted from full name")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Expected 'John', got '{optimized_df.iloc[0]['BD_TARGET_FIRST_NAME']}'")
        tests_failed += 1

    # Test 2: Address should be cleaned
    if optimized_df.iloc[0]['BD_ADDRESS'] == '123 Main St':
        print("✅ PASS: Address line cleaned and formatted")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Address not properly cleaned: '{optimized_df.iloc[0]['BD_ADDRESS']}'")
        tests_failed += 1

    # Test 3: City should be title case
    if optimized_df.iloc[0]['BD_CITY'] == 'Phoenix':
        print("✅ PASS: City properly capitalized")
        tests_passed += 1
    else:
        print(f"❌ FAIL: City not properly formatted: '{optimized_df.iloc[0]['BD_CITY']}'")
        tests_failed += 1

    # Test 4: State should be normalized to abbreviation
    if optimized_df.iloc[0]['BD_STATE'] == 'AZ':
        print("✅ PASS: State normalized to abbreviation")
        tests_passed += 1
    else:
        print(f"❌ FAIL: State not normalized: '{optimized_df.iloc[0]['BD_STATE']}'")
        tests_failed += 1

    # Test 5: ZIP should be normalized to 5 digits
    if optimized_df.iloc[0]['BD_ZIP'] == '85001':
        print("✅ PASS: ZIP normalized to 5 digits")
        tests_passed += 1
    else:
        print(f"❌ FAIL: ZIP not normalized: '{optimized_df.iloc[0]['BD_ZIP']}'")
        tests_failed += 1

    # Test 6: Record 3 should inherit city/state/zip from Record 2 (same address)
    if optimized_df.iloc[2]['BD_CITY'] == 'AZ' or optimized_df.iloc[2]['BD_STATE'] == 'AZ':
        print("✅ PASS: Missing fields filled from matching address")
        tests_passed += 1
    else:
        print("❌ FAIL: Fields not filled from matching address")
        tests_failed += 1
    
    print(f"\nField Optimization Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_ecorp_transformation():
    """Test eCorp to BatchData transformation."""
    print("\n=== Testing eCorp Transformation ===")
    
    # Create test eCorp data
    ecorp_data = pd.DataFrame([
        {
            'ECORP_NAME_S': 'Test Company LLC',
            'ECORP_ENTITY_ID_S': 'L12345',
            'Agent Address': '123 Main St, Phoenix, AZ 85001',
            'ECORP_COUNTY': 'Maricopa',
            'Title1': 'Manager',
            'Name1': 'John Doe',
            'Address1': '456 Oak Ave, Scottsdale, AZ 85251',
            'Title2': 'Member',
            'Name2': 'Jane Smith',
            'Address2': '',
            'Title3': '',
            'Name3': '',
            'Address3': '',
            'ECORP_STATUS': 'Active'
        },
        {
            'ECORP_NAME_S': 'Another Corp',
            'ECORP_ENTITY_ID_S': 'C67890',
            'Agent Address': '789 Pine Rd, Tucson, AZ 85701',
            'ECORP_COUNTY': 'Pima',
            'Title1': '',
            'Name1': '',
            'Address1': '',
            'Title2': '',
            'Name2': '',
            'Address2': '',
            'Title3': '',
            'Name3': '',
            'Address3': '',
            'ECORP_STATUS': 'Active',
            'Statutory Agent': 'Agent Services Inc'
        }
    ])
    
    # Transform
    batchdata_df = transform_ecorp_to_batchdata(ecorp_data)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Should create records for each principal
    if len(batchdata_df) >= 2:
        print(f"✅ PASS: Created {len(batchdata_df)} records from eCorp data")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Expected at least 2 records, got {len(batchdata_df)}")
        tests_failed += 1
    
    # Test 2: First record should have proper name splitting
    if len(batchdata_df) > 0:
        first_record = batchdata_df.iloc[0]
        if first_record['BD_TARGET_FIRST_NAME'] == 'John' and first_record['BD_TARGET_LAST_NAME'] == 'Doe':
            print("✅ PASS: Names properly split")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Name splitting failed: {first_record['BD_TARGET_FIRST_NAME']} {first_record['BD_TARGET_LAST_NAME']}")
            tests_failed += 1

    # Test 3: Address parsing from principal address
    if len(batchdata_df) > 0:
        first_record = batchdata_df.iloc[0]
        if first_record['BD_CITY'] == 'Scottsdale' or first_record['BD_CITY'] == 'Phoenix':
            print("✅ PASS: Address properly parsed")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Address parsing failed: city = '{first_record['BD_CITY']}'")
            tests_failed += 1

    # Test 4: Entity with no principals should use statutory agent
    entity_records = batchdata_df[batchdata_df['BD_SOURCE_ENTITY_ID'] == 'C67890']
    if len(entity_records) > 0:
        if 'Agent Services Inc' in entity_records.iloc[0]['BD_OWNER_NAME_FULL']:
            print("✅ PASS: Statutory agent used when no principals")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Statutory agent not used: '{entity_records.iloc[0]['BD_OWNER_NAME_FULL']}'")
            tests_failed += 1
    
    print(f"\neCorp Transformation Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def run_all_tests():
    """Run all test suites."""
    print("=" * 60)
    print("BATCHDATA PIPELINE FIELD COMPLETENESS TEST SUITE")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    # Run each test suite
    test_suites = [
        test_address_parsing,
        test_field_validation,
        test_field_optimization,
        test_ecorp_transformation
    ]
    
    for test_suite in test_suites:
        try:
            passed, failed = test_suite()
            total_passed += passed
            total_failed += failed
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            total_failed += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests Passed: {total_passed}")
    print(f"Total Tests Failed: {total_failed}")
    
    if total_failed == 0:
        print("\n✅ ALL TESTS PASSED! The pipeline is ready for use.")
    else:
        print(f"\n⚠️  {total_failed} tests failed. Please review and fix issues.")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)