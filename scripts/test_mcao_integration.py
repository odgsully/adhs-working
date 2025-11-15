#!/usr/bin/env python3
"""
Test script for MCAO integration
=================================

Tests the MCAO API client and field mapping functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from adhs_etl.mcao_client import MCAAOAPIClient
from adhs_etl.mcao_field_mapping import (
    MCAO_MAX_HEADERS,
    get_empty_mcao_record,
    validate_mcao_record
)

def test_field_mapping():
    """Test the field mapping configuration."""
    print("\n" + "="*60)
    print("Testing MCAO Field Mapping")
    print("="*60)

    # Check we have 106 columns (84 original + 22 new)
    assert len(MCAO_MAX_HEADERS) == 106, f"Expected 106 columns, got {len(MCAO_MAX_HEADERS)}"
    print(f"✅ Confirmed {len(MCAO_MAX_HEADERS)} columns in MAX_HEADERS")

    # Check first and last columns
    assert MCAO_MAX_HEADERS[0] == 'FULL_ADDRESS', f"First column should be FULL_ADDRESS, got {MCAO_MAX_HEADERS[0]}"
    assert MCAO_MAX_HEADERS[1] == 'COUNTY', f"Second column should be COUNTY, got {MCAO_MAX_HEADERS[1]}"
    assert MCAO_MAX_HEADERS[2] == 'APN', f"Third column should be APN, got {MCAO_MAX_HEADERS[2]}"
    print("✅ First 3 columns correct: FULL_ADDRESS, COUNTY, APN")

    # Test empty record generation
    empty_record = get_empty_mcao_record()
    assert len(empty_record) == 106, f"Empty record should have 106 fields, got {len(empty_record)}"
    assert all(v == '' for v in empty_record.values()), "All values should be empty strings"
    print("✅ Empty record generation works correctly")

    # Test record validation
    test_record = {
        'FULL_ADDRESS': '123 Main St',
        'COUNTY': 'MARICOPA',
        'APN': '123-45-678',
        'Owner_OwnerName': 'Test Owner',
        'INVALID_COLUMN': 'Should be ignored'
    }
    validated = validate_mcao_record(test_record)
    assert len(validated) == 106, f"Validated record should have 106 fields, got {len(validated)}"
    assert validated['FULL_ADDRESS'] == '123 Main St'
    assert validated['Owner_OwnerName'] == 'Test Owner'
    assert 'INVALID_COLUMN' not in validated
    print("✅ Record validation works correctly")

def test_mcao_api_client():
    """Test the MCAO API client initialization."""
    print("\n" + "="*60)
    print("Testing MCAO API Client")
    print("="*60)

    try:
        # Try to initialize client
        client = MCAAOAPIClient(rate_limit=5.0)
        print("✅ MCAO API client initialized successfully")
        print(f"   API Key configured: {client.api_key[:8]}...")

        # Test with a known APN (if you have one for testing)
        # test_apn = "123-45-678"  # Replace with a real APN for testing
        # print(f"\nTesting API with APN: {test_apn}")
        # data = client.get_parcel_details(test_apn)
        # if data:
        #     print(f"✅ API call successful, got data: {list(data.keys())[:5]}...")
        # else:
        #     print("⚠️  No data returned (APN may not exist)")

    except ValueError as e:
        print(f"❌ Failed to initialize MCAO API client: {e}")
        print("   Please ensure MCAO_API_KEY is set in .env file")
        return False

    return True

def test_env_setup():
    """Test that environment is properly configured."""
    print("\n" + "="*60)
    print("Testing Environment Setup")
    print("="*60)

    # Check .env file exists
    env_path = Path(".env")
    if env_path.exists():
        print(f"✅ .env file exists at {env_path.absolute()}")
    else:
        print(f"❌ .env file not found at {env_path.absolute()}")
        return False

    # Check MCAO_API_KEY is set
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("MCAO_API_KEY")
    if api_key:
        print(f"✅ MCAO_API_KEY is configured: {api_key[:8]}...")
    else:
        print("❌ MCAO_API_KEY not found in environment")
        return False

    return True

def main():
    """Run all tests."""
    print("🧪 MCAO Integration Test Suite")
    print("="*60)

    all_passed = True

    # Test environment
    if not test_env_setup():
        all_passed = False

    # Test field mapping
    try:
        test_field_mapping()
    except Exception as e:
        print(f"❌ Field mapping test failed: {e}")
        all_passed = False

    # Test API client
    if not test_mcao_api_client():
        all_passed = False

    # Final result
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Please review the output above.")
    print("="*60)

if __name__ == "__main__":
    main()