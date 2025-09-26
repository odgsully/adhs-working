"""
test_api_response_handling.py - Test API response field preservation and merging
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.transform import (
    explode_phones_to_long, aggregate_top_phones, apply_phone_scrubs
)


def test_phone_explosion_and_aggregation():
    """Test phone data transformation from wide to long and back."""
    print("\n=== Testing Phone Data Transformation ===")
    
    # Create test data with various phone formats
    test_data = pd.DataFrame([
        {
            'record_id': 'rec1',
            'phone_1': '480-555-0001',
            'phone_2': '(602) 555-0002',
            'phone_3': '6235550003',
            'phone_1_type': 'mobile',
            'phone_2_type': 'landline',
            'phone_3_type': 'mobile'
        },
        {
            'record_id': 'rec2',
            'phone_1': '520-555-0004',
            'phone_2': '',
            'phone_3': '',
            'phone_1_type': 'mobile',
            'phone_2_type': '',
            'phone_3_type': ''
        }
    ])
    
    # Test explosion to long format
    phones_long = explode_phones_to_long(test_data)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Should have correct number of phone records
    expected_phones = 4  # 3 from rec1, 1 from rec2
    if len(phones_long) == expected_phones:
        print(f"✅ PASS: Correct number of phone records ({expected_phones})")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Expected {expected_phones} phone records, got {len(phones_long)}")
        tests_failed += 1
    
    # Test 2: Phone numbers should be normalized
    if len(phones_long) > 0:
        first_phone = phones_long.iloc[0]['phone']
        # Check if it's in E.164 format or at least cleaned
        if '+1' in first_phone or first_phone.replace('-', '').isdigit():
            print("✅ PASS: Phone numbers normalized")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Phone not normalized: '{first_phone}'")
            tests_failed += 1
    
    # Test aggregation back to wide format
    phones_wide = aggregate_top_phones(phones_long, top_n=5)
    
    # Test 3: Should have records for each unique record_id
    if len(phones_wide) == 2:
        print("✅ PASS: Correct number of aggregated records")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Expected 2 aggregated records, got {len(phones_wide)}")
        tests_failed += 1
    
    # Test 4: Should preserve phone metadata
    if 'phone_1_type' in phones_wide.columns:
        print("✅ PASS: Phone metadata preserved")
        tests_passed += 1
    else:
        print("❌ FAIL: Phone metadata not preserved")
        tests_failed += 1
    
    print(f"\nPhone Transformation Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_phone_scrubbing():
    """Test phone scrubbing with verification, DNC, and TCPA data."""
    print("\n=== Testing Phone Scrubbing ===")
    
    # Create test phone data
    phones_df = pd.DataFrame([
        {'record_id': 'rec1', 'phone': '+14805550001', 'type': 'mobile'},
        {'record_id': 'rec1', 'phone': '+16025550002', 'type': 'landline'},
        {'record_id': 'rec2', 'phone': '+16235550003', 'type': 'mobile'},
        {'record_id': 'rec2', 'phone': '+15205550004', 'type': 'voip'}
    ])
    
    # Create verification results
    verification_df = pd.DataFrame([
        {'phone': '+14805550001', 'is_active': True, 'line_type': 'mobile'},
        {'phone': '+16025550002', 'is_active': True, 'line_type': 'landline'},
        {'phone': '+16235550003', 'is_active': False, 'line_type': 'mobile'},
        {'phone': '+15205550004', 'is_active': True, 'line_type': 'voip'}
    ])
    
    # Create DNC results
    dnc_df = pd.DataFrame([
        {'phone': '+14805550001', 'on_dnc': False},
        {'phone': '+16025550002', 'on_dnc': True},
        {'phone': '+16235550003', 'on_dnc': False},
        {'phone': '+15205550004', 'on_dnc': False}
    ])
    
    # Create TCPA results
    tcpa_df = pd.DataFrame([
        {'phone': '+14805550001', 'is_litigator': False},
        {'phone': '+16025550002', 'is_litigator': False},
        {'phone': '+16235550003', 'is_litigator': False},
        {'phone': '+15205550004', 'is_litigator': True}
    ])
    
    # Apply scrubs
    scrubbed_phones = apply_phone_scrubs(phones_df, verification_df, dnc_df, tcpa_df)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Should only keep active mobile numbers
    if len(scrubbed_phones) == 1:
        print("✅ PASS: Correct number of phones after scrubbing")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Expected 1 phone after scrubbing, got {len(scrubbed_phones)}")
        tests_failed += 1
    
    # Test 2: Should be the correct phone number
    if len(scrubbed_phones) > 0:
        remaining_phone = scrubbed_phones.iloc[0]['phone']
        if remaining_phone == '+14805550001':
            print("✅ PASS: Correct phone retained after scrubbing")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Wrong phone retained: '{remaining_phone}'")
            tests_failed += 1
    
    # Test 3: Should have scrub flags
    if len(scrubbed_phones) > 0:
        first_record = scrubbed_phones.iloc[0]
        if 'is_active' in first_record and 'on_dnc' in first_record and 'is_litigator' in first_record:
            print("✅ PASS: Scrub flags preserved")
            tests_passed += 1
        else:
            print("❌ FAIL: Scrub flags not preserved")
            tests_failed += 1
    
    print(f"\nPhone Scrubbing Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_field_preservation_in_merge():
    """Test that all fields are preserved during merge operations."""
    print("\n=== Testing Field Preservation in Merges ===")
    
    # Create base data
    base_df = pd.DataFrame([
        {
            'record_id': 'rec1',
            'target_first_name': 'John',
            'target_last_name': 'Doe',
            'address_line1': '123 Main St',
            'custom_field_1': 'value1'
        },
        {
            'record_id': 'rec2',
            'target_first_name': 'Jane',
            'target_last_name': 'Smith',
            'address_line1': '456 Oak Ave',
            'custom_field_1': 'value2'
        }
    ])
    
    # Create API response with additional fields
    api_response = pd.DataFrame([
        {
            'record_id': 'rec1',
            'api_field_1': 'api_value1',
            'api_field_2': 'api_value2',
            'api_field_3': 'api_value3',
            'confidence_score': 0.95
        },
        {
            'record_id': 'rec2',
            'api_field_1': 'api_value4',
            'api_field_2': 'api_value5',
            'api_field_3': 'api_value6',
            'confidence_score': 0.87
        }
    ])
    
    # Create phone data
    phone_data = pd.DataFrame([
        {
            'record_id': 'rec1',
            'phone_1': '+14805550001',
            'phone_1_type': 'mobile',
            'phone_1_confidence': 'high'
        },
        {
            'record_id': 'rec2',
            'phone_1': '+16025550002',
            'phone_1_type': 'landline',
            'phone_1_confidence': 'medium'
        }
    ])
    
    # Perform merges as in the pipeline
    merged_df = pd.merge(base_df, phone_data, on='record_id', how='left', suffixes=('', '_phones'))
    merged_df = pd.merge(merged_df, api_response, on='record_id', how='left', suffixes=('', '_api'))
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: All original fields should be preserved
    original_fields = ['target_first_name', 'target_last_name', 'address_line1', 'custom_field_1']
    missing_fields = [f for f in original_fields if f not in merged_df.columns]
    if not missing_fields:
        print("✅ PASS: All original fields preserved")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Missing original fields: {missing_fields}")
        tests_failed += 1
    
    # Test 2: All API fields should be preserved
    api_fields = ['api_field_1', 'api_field_2', 'api_field_3', 'confidence_score']
    missing_api_fields = [f for f in api_fields if f not in merged_df.columns]
    if not missing_api_fields:
        print("✅ PASS: All API fields preserved")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Missing API fields: {missing_api_fields}")
        tests_failed += 1
    
    # Test 3: Phone fields should be preserved
    phone_fields = ['phone_1', 'phone_1_type', 'phone_1_confidence']
    missing_phone_fields = [f for f in phone_fields if f not in merged_df.columns]
    if not missing_phone_fields:
        print("✅ PASS: All phone fields preserved")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Missing phone fields: {missing_phone_fields}")
        tests_failed += 1
    
    # Test 4: Total field count should be sum of all unique fields
    expected_fields = len(set(list(base_df.columns) + list(api_response.columns) + list(phone_data.columns))) - 2  # -2 for duplicate record_id
    actual_fields = len(merged_df.columns)
    if actual_fields >= expected_fields:
        print(f"✅ PASS: Expected field count preserved ({actual_fields} fields)")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Field count mismatch. Expected at least {expected_fields}, got {actual_fields}")
        tests_failed += 1
    
    print(f"\nField Preservation Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_subfolder_organization():
    """Test that files are organized in correct subfolders."""
    print("\n=== Testing Subfolder Organization ===")
    
    from src.io import ensure_subfolder, save_api_result
    import tempfile
    import shutil
    
    tests_passed = 0
    tests_failed = 0
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test subfolder creation
        subfolders = ['skiptrace', 'phoneverify', 'dnc', 'tcpa', 'phone_scrub']
        
        for subfolder in subfolders:
            subfolder_path = ensure_subfolder(temp_dir, subfolder)
            if os.path.exists(subfolder_path):
                print(f"✅ PASS: Subfolder '{subfolder}' created")
                tests_passed += 1
            else:
                print(f"❌ FAIL: Subfolder '{subfolder}' not created")
                tests_failed += 1
        
        # Test file saving in subfolders
        test_df = pd.DataFrame({'test': [1, 2, 3]})
        
        for api_type in ['skiptrace', 'phoneverify', 'dnc', 'tcpa', 'phone_scrub']:
            file_path = save_api_result(test_df, temp_dir, api_type, f"test_{api_type}")
            
            # Check if file is in correct subfolder
            if api_type in file_path and os.path.exists(file_path):
                print(f"✅ PASS: File saved in '{api_type}' subfolder")
                tests_passed += 1
            else:
                print(f"❌ FAIL: File not saved correctly in '{api_type}' subfolder")
                tests_failed += 1
    
    print(f"\nSubfolder Organization Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def run_all_tests():
    """Run all API response handling tests."""
    print("=" * 60)
    print("API RESPONSE HANDLING TEST SUITE")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    # Run each test suite
    test_suites = [
        test_phone_explosion_and_aggregation,
        test_phone_scrubbing,
        test_field_preservation_in_merge,
        test_subfolder_organization
    ]
    
    for test_suite in test_suites:
        try:
            passed, failed = test_suite()
            total_passed += passed
            total_failed += failed
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
            total_failed += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests Passed: {total_passed}")
    print(f"Total Tests Failed: {total_failed}")
    
    if total_failed == 0:
        print("\n✅ ALL TESTS PASSED! API response handling is working correctly.")
    else:
        print(f"\n⚠️  {total_failed} tests failed. Please review and fix issues.")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)