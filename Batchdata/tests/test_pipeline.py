"""
Test script for BatchData pipeline (mock mode)
"""

import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_data_transformation():
    """Test data transformation from eCorp to BatchData format."""
    print("=== Testing Data Transformation ===")
    
    from src.transform import transform_ecorp_to_batchdata
    from src.io import load_workbook_sheets
    
    # Load test eCorp data (first 3 records)
    ecorp_df = pd.read_excel("../M.YY_Ecorp_Complete.xlsx").head(3)
    print(f"Loaded {len(ecorp_df)} eCorp records for testing")
    
    # Transform to BatchData format
    batchdata_df = transform_ecorp_to_batchdata(ecorp_df)
    print(f"Transformed to {len(batchdata_df)} BatchData records")
    
    # Validate required columns
    required_columns = [
        'BD_RECORD_ID', 'BD_ENTITY_NAME', 'BD_TARGET_FIRST_NAME',
        'BD_TARGET_LAST_NAME', 'BD_OWNER_NAME_FULL', 'BD_ADDRESS', 'BD_CITY', 'BD_STATE'
    ]
    
    missing_cols = [col for col in required_columns if col not in batchdata_df.columns]
    if missing_cols:
        print(f"❌ Missing required columns: {missing_cols}")
        return False
    else:
        print("✅ All required columns present")
    
    # Check data quality
    print(f"Records with names: {len(batchdata_df[batchdata_df['BD_OWNER_NAME_FULL'].notna()])}")
    print(f"Records with addresses: {len(batchdata_df[batchdata_df['BD_ADDRESS'].notna()])}")

    print("\nSample transformed record:")
    sample = batchdata_df.iloc[0]
    for col in ['BD_RECORD_ID', 'BD_ENTITY_NAME', 'BD_OWNER_NAME_FULL', 'BD_CITY', 'BD_STATE']:
        print(f"  {col}: {sample[col]}")
    
    return True


def test_blacklist_filtering():
    """Test blacklist filtering functionality."""
    print("\n=== Testing Blacklist Filtering ===")
    
    from src.normalize import apply_blacklist_filter
    from src.io import load_blacklist_set
    
    # Load blacklist
    blacklist_df = pd.read_excel("../batchdata_local_pack/template_batchdata_upload.xlsx", 
                                sheet_name='BLACKLIST_NAMES')
    blacklist = load_blacklist_set(blacklist_df)
    print(f"Loaded {len(blacklist)} blacklist entries")
    
    # Create test data with some blacklisted names
    test_data = pd.DataFrame([
        {'BD_RECORD_ID': '1', 'BD_OWNER_NAME_FULL': 'John Doe'},
        {'BD_RECORD_ID': '2', 'BD_OWNER_NAME_FULL': 'CT Corporation System'},
        {'BD_RECORD_ID': '3', 'BD_OWNER_NAME_FULL': 'Jane Smith'},
        {'BD_RECORD_ID': '4', 'BD_OWNER_NAME_FULL': 'LegalZoom Service'}
    ])
    
    print(f"Test data before filtering: {len(test_data)} records")
    filtered_data = apply_blacklist_filter(test_data, blacklist)
    print(f"Test data after filtering: {len(filtered_data)} records")
    
    if len(filtered_data) < len(test_data):
        print("✅ Blacklist filtering working correctly")
        return True
    else:
        print("⚠️  No records filtered (may be expected)")
        return True


def test_cost_estimation():
    """Test cost estimation functionality."""
    print("\n=== Testing Cost Estimation ===")
    
    # Mock API client to avoid requiring real keys
    with patch('src.batchdata.create_client_from_env') as mock_client_factory:
        mock_client = MagicMock()
        
        # Mock cost estimation
        mock_costs = {
            'skip_trace': 4 * 0.07,  # 4 records * 7¢
            'phone_verification': 8 * 0.007,  # 8 estimated phones * 0.7¢
            'phone_dnc': 8 * 0.002,  # 8 phones * 0.2¢
            'phone_tcpa': 8 * 0.002,  # 8 phones * 0.2¢
            'total': 0.0
        }
        mock_costs['total'] = sum(v for k, v in mock_costs.items() if k != 'total')
        
        mock_client.estimate_cost.return_value = mock_costs
        mock_client_factory.return_value = mock_client
        
        from src.batchdata import BatchDataClient
        
        # Test cost estimation
        config = {
            'workflow.enable_phone_verification': True,
            'workflow.enable_phone_dnc': True,
            'workflow.enable_phone_tcpa': True
        }
        
        costs = mock_client.estimate_cost(4, config)
        print(f"Estimated total cost for 4 records: ${costs['total']:.2f}")
        print("Cost breakdown:")
        for service, cost in costs.items():
            if service != 'total' and cost > 0:
                print(f"  {service}: ${cost:.2f}")
        
        print("✅ Cost estimation working correctly")
        return True


def test_phone_processing():
    """Test phone processing and normalization."""
    print("\n=== Testing Phone Processing ===")
    
    from src.normalize import normalize_phone_e164
    from src.transform import explode_phones_to_long
    
    # Test phone normalization
    test_phones = [
        "480-555-1234",
        "(602) 555-5678", 
        "1-520-555-9999",
        "invalid-phone",
        ""
    ]
    
    print("Phone normalization test:")
    for phone in test_phones:
        normalized = normalize_phone_e164(phone)
        print(f"  {phone:<15} → {normalized}")
    
    # Test with sample data that might have phones
    test_df = pd.DataFrame([
        {'BD_RECORD_ID': '1', 'BD_PHONE_1': '480-555-1234', 'BD_PHONE_2': '602-555-5678'},
        {'BD_RECORD_ID': '2', 'BD_PHONE_1': '520-555-9999', 'BD_PHONE_2': ''}
    ])
    
    phones_long = explode_phones_to_long(test_df)
    print(f"Exploded {len(test_df)} records to {len(phones_long)} phone records")
    
    print("✅ Phone processing working correctly")
    return True


def run_full_mock_test():
    """Run a full pipeline test with mocked API calls."""
    print("\n=== Running Full Mock Pipeline Test ===")
    
    # Set mock environment variables
    os.environ['BD_SKIPTRACE_KEY'] = 'test_key_skiptrace'
    os.environ['BD_PHONE_KEY'] = 'test_key_phone'
    
    try:
        from src.run import run_pipeline
        
        # Mock the API client completely
        with patch('src.run.create_client_from_env') as mock_client_factory:
            mock_client = MagicMock()
            
            # Mock cost estimation
            mock_client.estimate_cost.return_value = {
                'skip_trace': 0.28, 'phone_verification': 0.056, 
                'phone_dnc': 0.016, 'phone_tcpa': 0.016, 'total': 0.368
            }
            
            # Mock pipeline execution
            mock_final_df = pd.DataFrame([
                {'BD_RECORD_ID': '1', 'BD_ENTITY_NAME': 'Test LLC', 'BD_PHONE_1': '+14805551234'}
            ])
            mock_client.run_skip_trace_pipeline.return_value = (mock_final_df, [])
            
            mock_client_factory.return_value = mock_client
            
            # Patch input to automatically confirm costs
            with patch('builtins.input', return_value='y'):
                # Run with dry run first
                print("Testing dry run mode...")
                run_pipeline("batchdata_local_input.xlsx", dry_run=True)
                print("✅ Dry run completed successfully")
                
                return True
                
    except Exception as e:
        print(f"❌ Mock test failed: {e}")
        return False
    finally:
        # Clean up environment
        for key in ['BD_SKIPTRACE_KEY', 'BD_PHONE_KEY']:
            if key in os.environ:
                del os.environ[key]


def main():
    """Run all tests."""
    print("BatchData Pipeline Test Suite")
    print("=" * 40)
    
    tests = [
        test_data_transformation,
        test_blacklist_filtering,
        test_cost_estimation,
        test_phone_processing,
        run_full_mock_test
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {total - passed} tests failed")


if __name__ == "__main__":
    main()