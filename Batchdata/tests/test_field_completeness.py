"""
test_field_completeness.py - Testing framework for input field validation and API optimization
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.transform import (
    parse_address, validate_input_fields,
    transform_ecorp_to_batchdata
)
# NOTE: optimize_for_api removed (Nov 2025) - address-only API lookups
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
    """Test input field validation logic (address-only, Nov 2025)."""
    print("\n=== Testing Field Validation (Address-Only) ===")

    # Create test DataFrame - no name fields needed (removed Nov 2025)
    test_data = pd.DataFrame([
        {
            'BD_RECORD_ID': '1',
            'BD_ADDRESS': '123 Main St',
            'BD_CITY': 'Phoenix',
            'BD_STATE': 'AZ',
            'BD_ZIP': '85001'
        },
        {
            'BD_RECORD_ID': '2',
            'BD_ADDRESS': '456 Oak Ave',
            'BD_CITY': '',  # Missing city
            'BD_STATE': 'AZ',
            'BD_ZIP': '85251'
        },
        {
            'BD_RECORD_ID': '3',
            'BD_ADDRESS': '',  # Missing address
            'BD_CITY': 'Tucson',
            'BD_STATE': '',
            'BD_ZIP': ''
        }
    ])

    # Run validation
    validated_df = validate_input_fields(test_data)

    # Check validation flag (has_valid_name removed Nov 2025)
    assert 'has_valid_address' in validated_df.columns, "Missing has_valid_address column"

    tests_passed = 0
    tests_failed = 0

    # Record 1 should have valid address (all fields present)
    if validated_df.iloc[0]['has_valid_address']:
        print("✅ PASS: Record 1 correctly identified as having valid address")
        tests_passed += 1
    else:
        print("❌ FAIL: Record 1 should have valid address")
        tests_failed += 1

    # Record 2 should have invalid address (missing city)
    if not validated_df.iloc[1]['has_valid_address']:
        print("✅ PASS: Record 2 correctly identified as invalid (missing city)")
        tests_passed += 1
    else:
        print("❌ FAIL: Record 2 should be invalid (missing city)")
        tests_failed += 1

    # Record 3 should have invalid address (missing address line)
    if not validated_df.iloc[2]['has_valid_address']:
        print("✅ PASS: Record 3 correctly identified as invalid (missing address)")
        tests_passed += 1
    else:
        print("❌ FAIL: Record 3 should be invalid (missing address)")
        tests_failed += 1

    print(f"\nField Validation Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_field_optimization():
    """Test field validation (optimization removed Nov 2025 - address-only API)."""
    print("\n=== Testing Field Validation (optimization skipped) ===")
    print("NOTE: optimize_for_api removed - pipeline now uses address-only lookups")

    # With address-only lookups, we just verify fields are validated
    test_data = pd.DataFrame([
        {
            'BD_RECORD_ID': '1',
            'BD_ADDRESS': '123 Main St',
            'BD_CITY': 'Phoenix',
            'BD_STATE': 'AZ',
            'BD_ZIP': '85001'
        }
    ])

    validated_df = validate_input_fields(test_data)

    tests_passed = 0
    tests_failed = 0

    if 'has_valid_address' in validated_df.columns:
        print("✅ PASS: Validation adds has_valid_address column")
        tests_passed += 1
    else:
        print("❌ FAIL: Missing has_valid_address column")
        tests_failed += 1

    if validated_df.iloc[0].get('has_valid_address', False):
        print("✅ PASS: Record with complete address marked as valid")
        tests_passed += 1
    else:
        print("❌ FAIL: Valid address not detected")
        tests_failed += 1

    print(f"\nField Validation Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_ecorp_transformation():
    """Test eCorp to BatchData transformation (address-only, Nov 2025)."""
    print("\n=== Testing eCorp Transformation (Address-Only) ===")

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

    # Test 1: Should create records
    if len(batchdata_df) >= 1:
        print(f"✅ PASS: Created {len(batchdata_df)} records from eCorp data")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Expected at least 1 record, got {len(batchdata_df)}")
        tests_failed += 1

    # Test 2: Records should have BD_TITLE_ROLE (Nov 2025 - name fields removed)
    if len(batchdata_df) > 0:
        first_record = batchdata_df.iloc[0]
        if 'BD_TITLE_ROLE' in first_record.index and first_record['BD_TITLE_ROLE']:
            print("✅ PASS: BD_TITLE_ROLE populated")
            tests_passed += 1
        else:
            print("❌ FAIL: BD_TITLE_ROLE not populated")
            tests_failed += 1

    # Test 3: Records should have BD_ADDRESS
    if len(batchdata_df) > 0:
        first_record = batchdata_df.iloc[0]
        if 'BD_ADDRESS' in first_record.index and first_record['BD_ADDRESS']:
            print("✅ PASS: BD_ADDRESS populated")
            tests_passed += 1
        else:
            print("❌ FAIL: BD_ADDRESS not populated")
            tests_failed += 1

    # Test 4: Records should have BD_SOURCE_ENTITY_ID
    if len(batchdata_df) > 0:
        first_record = batchdata_df.iloc[0]
        if 'BD_SOURCE_ENTITY_ID' in first_record.index and first_record['BD_SOURCE_ENTITY_ID']:
            print("✅ PASS: BD_SOURCE_ENTITY_ID populated")
            tests_passed += 1
        else:
            print("❌ FAIL: BD_SOURCE_ENTITY_ID not populated")
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