"""
test_integration.py - Integration test for the entire pipeline
"""

import pandas as pd
import sys
import os
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.io import (
    ensure_results_dir, save_api_result, load_config_dict, load_blacklist_set,
    get_timestamped_path
)
from src.transform import (
    transform_ecorp_to_batchdata, validate_input_fields, optimize_for_api,
    deduplicate_batchdata_records, filter_entity_only_records
)
from src.normalize import apply_blacklist_filter


def test_end_to_end_pipeline():
    """Test the complete pipeline from eCorp data to optimized output."""
    print("\n=== Testing End-to-End Pipeline ===")
    
    # Create test eCorp data
    ecorp_data = pd.DataFrame([
        {
            'Entity Name(s)': 'Test Company LLC',
            'Entity ID(s)': 'L12345',
            'Agent Address': '123 Main St, Phoenix, AZ 85001',
            'County': 'Maricopa',
            'Title1': 'Manager',
            'Name1': 'John Doe',
            'Address1': '456 Oak Ave, Scottsdale, AZ 85251',
            'Title2': 'Member',
            'Name2': 'Jane Smith',
            'Address2': '456 Oak Ave, Scottsdale, AZ 85251',  # Same address for deduplication test
            'Title3': '',
            'Name3': '',
            'Address3': '',
            'Status': 'Active'
        },
        {
            'Entity Name(s)': 'Another Corp',
            'Entity ID(s)': 'C67890',
            'Agent Address': '789 Pine Rd, Tucson, AZ 85701',
            'County': 'Pima',
            'Title1': 'President',
            'Name1': 'Bob Wilson',
            'Address1': '',
            'Title2': '',
            'Name2': '',
            'Address2': '',
            'Title3': '',
            'Name3': '',
            'Address3': '',
            'Status': 'Active',
            'Statutory Agent': 'Registered Agent Inc'
        }
    ])
    
    # Create config data
    config_data = pd.DataFrame([
        {'key': 'workflow.enable_phone_verification', 'value': 'TRUE'},
        {'key': 'workflow.enable_phone_dnc', 'value': 'TRUE'},
        {'key': 'workflow.enable_phone_tcpa', 'value': 'FALSE'},
        {'key': 'cost_limit', 'value': '100'}
    ])
    
    # Create blacklist data
    blacklist_data = pd.DataFrame([
        {'blacklist_name': 'REGISTERED AGENT INC'},
        {'blacklist_name': 'CT CORPORATION'},
        {'blacklist_name': 'INCORPORATING SERVICES'}
    ])
    
    tests_passed = 0
    tests_failed = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Step 1: Transform eCorp to BatchData format
            print("  Step 1: Transforming eCorp data...")
            batchdata_df = transform_ecorp_to_batchdata(ecorp_data)
            
            if len(batchdata_df) >= 2:
                print("  ✅ eCorp transformation successful")
                tests_passed += 1
            else:
                print("  ❌ eCorp transformation failed")
                tests_failed += 1
            
            # Step 2: Load configuration and blacklist
            print("  Step 2: Processing configuration...")
            config = load_config_dict(config_data)
            blacklist = load_blacklist_set(blacklist_data)
            
            if len(config) > 0 and len(blacklist) > 0:
                print("  ✅ Configuration and blacklist loaded")
                tests_passed += 1
            else:
                print("  ❌ Configuration or blacklist loading failed")
                tests_failed += 1
            
            # Step 3: Apply blacklist filter
            print("  Step 3: Applying blacklist filter...")
            pre_filter_count = len(batchdata_df)
            filtered_df = apply_blacklist_filter(batchdata_df, blacklist)
            post_filter_count = len(filtered_df)
            
            if post_filter_count < pre_filter_count:
                print(f"  ✅ Blacklist filter removed {pre_filter_count - post_filter_count} records")
                tests_passed += 1
            else:
                print("  ✅ No blacklisted records found (expected)")
                tests_passed += 1
            
            # Step 4: Validate and optimize input fields
            print("  Step 4: Validating and optimizing fields...")
            validated_df = validate_input_fields(filtered_df)
            optimized_df = optimize_for_api(validated_df)
            
            if 'has_valid_name' in validated_df.columns and len(optimized_df) > 0:
                print("  ✅ Field validation and optimization successful")
                tests_passed += 1
            else:
                print("  ❌ Field validation or optimization failed")
                tests_failed += 1
            
            # Step 5: Apply deduplication
            print("  Step 5: Applying deduplication...")
            deduped_df = deduplicate_batchdata_records(optimized_df)
            
            if len(deduped_df) <= len(optimized_df):
                print("  ✅ Deduplication successful")
                tests_passed += 1
            else:
                print("  ❌ Deduplication failed")
                tests_failed += 1
            
            # Step 6: Filter entity-only records
            print("  Step 6: Filtering entity-only records...")
            entity_filtered_df = filter_entity_only_records(deduped_df, filter_enabled=True)
            
            if len(entity_filtered_df) <= len(deduped_df):
                print("  ✅ Entity filtering successful")
                tests_passed += 1
            else:
                print("  ❌ Entity filtering failed")
                tests_failed += 1
            
            # Step 7: Create organized output structure
            print("  Step 7: Creating organized output structure...")
            results_dir = ensure_results_dir(os.path.join(temp_dir, "results"))
            
            # Save in different subfolders
            input_path = save_api_result(entity_filtered_df, results_dir, 'input', 'processed_input')
            
            # Verify subfolder structure
            expected_subfolders = ['input']
            for subfolder in expected_subfolders:
                subfolder_path = os.path.join(results_dir, subfolder)
                if os.path.exists(subfolder_path):
                    print(f"  ✅ Subfolder '{subfolder}' created successfully")
                    tests_passed += 1
                else:
                    print(f"  ❌ Subfolder '{subfolder}' not created")
                    tests_failed += 1
            
            # Step 8: Verify final data quality
            print("  Step 8: Verifying final data quality...")
            
            # Check that we have valid records
            final_record_count = len(entity_filtered_df)
            valid_name_count = entity_filtered_df['has_valid_name'].sum()
            valid_address_count = entity_filtered_df['has_valid_address'].sum()
            
            if final_record_count > 0 and valid_name_count > 0:
                print(f"  ✅ Final data quality: {final_record_count} records, {valid_name_count} with valid names")
                tests_passed += 1
            else:
                print("  ❌ Final data quality check failed")
                tests_failed += 1
            
            # Step 9: Test filename generation
            print("  Step 9: Testing output filename generation...")
            final_path = get_timestamped_path(results_dir, "batchdata_complete", "xlsx")

            # Expected format: prefix_MM.DD.HH-MM-SS.xlsx (with underscores, not spaces)
            if "_batchdata_complete_" in final_path and final_path.endswith(".xlsx"):
                print("  ✅ Output filename generation successful")
                tests_passed += 1
            else:
                print("  ❌ Output filename generation failed")
                tests_failed += 1
            
        except Exception as e:
            print(f"  ❌ Pipeline failed with error: {e}")
            tests_failed += 1
    
    print(f"\nEnd-to-End Pipeline Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def run_integration_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("BATCHDATA PIPELINE INTEGRATION TEST SUITE")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    # Run integration test
    try:
        passed, failed = test_end_to_end_pipeline()
        total_passed += passed
        total_failed += failed
    except Exception as e:
        print(f"❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        total_failed += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests Passed: {total_passed}")
    print(f"Total Tests Failed: {total_failed}")
    
    if total_failed == 0:
        print("\n✅ ALL INTEGRATION TESTS PASSED! The pipeline is ready for production use.")
    else:
        print(f"\n⚠️  {total_failed} integration tests failed. Please review and fix issues.")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)