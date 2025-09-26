"""
Test script to verify BatchData deduplication functionality
"""

import os
import sys
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_deduplication_function():
    """Test the deduplication function directly."""
    print("🔄 Testing Deduplication Function")
    print("-" * 50)
    
    from src.transform import deduplicate_batchdata_records
    
    # Create test data with known duplicates
    test_data = pd.DataFrame([
        {
            'record_id': 'test_001',
            'target_first_name': 'John',
            'target_last_name': 'Doe',
            'owner_name_full': 'John Doe',
            'address_line1': '123 Main St',
            'city': 'Phoenix',
            'state': 'AZ',
            'zip': '85001',
            'source_entity_name': 'Test LLC',
            'title_role': 'Member',
            'notes': 'Original record'
        },
        {
            'record_id': 'test_002',
            'target_first_name': 'John',
            'target_last_name': 'Doe',
            'owner_name_full': 'John Doe',
            'address_line1': '123 Main St',
            'city': 'Phoenix',
            'state': 'AZ',
            'zip': '85001',
            'source_entity_name': 'Test LLC',
            'title_role': 'Member',
            'notes': 'Duplicate record with phone data'
        },
        {
            'record_id': 'test_003',
            'target_first_name': 'Jane',
            'target_last_name': 'Smith',
            'owner_name_full': 'Jane Smith',
            'address_line1': '456 Oak Ave',
            'city': 'Tempe',
            'state': 'AZ',
            'zip': '85282',
            'source_entity_name': 'Another LLC',
            'title_role': 'Manager',
            'notes': 'Unique record'
        }
    ])
    
    print(f"Input records: {len(test_data)}")
    print("Records:")
    for _, row in test_data.iterrows():
        print(f"  {row['record_id']}: {row['target_first_name']} {row['target_last_name']} - {row['notes']}")
    
    # Apply deduplication
    deduplicated = deduplicate_batchdata_records(test_data)
    
    print(f"\nOutput records: {len(deduplicated)}")
    print("Kept records:")
    for _, row in deduplicated.iterrows():
        print(f"  {row['record_id']}: {row['target_first_name']} {row['target_last_name']} - {row['notes']}")
    
    # Verify results
    expected_records = 2  # John Doe (1 kept) + Jane Smith (1 kept)
    if len(deduplicated) == expected_records:
        print("✅ Deduplication working correctly")
        return True
    else:
        print(f"❌ Expected {expected_records} records, got {len(deduplicated)}")
        return False


def test_with_real_data():
    """Test deduplication with actual filtered input data."""
    print("\n🧪 Testing with Real BatchData")
    print("-" * 50)
    
    try:
        # Load the latest filtered input
        csv_file = 'results/filtered_input_20250818_132817_20250818_132817.csv'
        if not os.path.exists(csv_file):
            print("❌ Filtered input file not found")
            return False
        
        from src.transform import deduplicate_batchdata_records
        
        df = pd.read_csv(csv_file)
        print(f"Original records: {len(df)}")
        
        # Apply deduplication
        deduplicated = deduplicate_batchdata_records(df)
        
        # Calculate expected API cost reduction
        original_cost = len(df) * 0.07  # 7¢ per record
        new_cost = len(deduplicated) * 0.07
        savings = original_cost - new_cost
        savings_percent = (savings / original_cost) * 100 if original_cost > 0 else 0
        
        print(f"\n💰 Cost Impact Analysis:")
        print(f"   Original cost: ${original_cost:.2f}")
        print(f"   New cost: ${new_cost:.2f}")
        print(f"   Savings: ${savings:.2f} ({savings_percent:.1f}%)")
        
        # Save deduplicated version
        dedupe_file = csv_file.replace('.csv', '_dedupe_test.csv')
        deduplicated.to_csv(dedupe_file, index=False)
        print(f"\n📁 Saved deduplicated data: {dedupe_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_pipeline_integration():
    """Test deduplication integrated in the full pipeline."""
    print("\n🚀 Testing Pipeline Integration")
    print("-" * 50)
    
    try:
        # Test with deduplication enabled
        os.environ['BD_SKIPTRACE_KEY'] = 'test_key'
        
        # Import here to avoid issues if env vars not set earlier
        from src.run import run_pipeline
        from unittest.mock import patch, MagicMock
        
        # Mock the API client
        with patch('src.run.create_client_from_env') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.estimate_cost.return_value = {
                'skip_trace': 0.21, 'phone_verification': 0.042, 
                'phone_dnc': 0.012, 'phone_tcpa': 0.012, 'total': 0.276
            }
            mock_client_factory.return_value = mock_client
            
            with patch('builtins.input', return_value='y'):
                print("Testing with deduplication enabled...")
                run_pipeline(
                    "../batchdata_local_pack/template_batchdata_upload.xlsx",
                    "../M.YY_Ecorp_Complete.xlsx",
                    dry_run=True,
                    dedupe=True
                )
                
        print("✅ Pipeline integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        return False
    finally:
        if 'BD_SKIPTRACE_KEY' in os.environ:
            del os.environ['BD_SKIPTRACE_KEY']


def main():
    """Run all deduplication tests."""
    print("🔄 BatchData Deduplication Test Suite")
    print("=" * 60)
    
    tests = [
        test_deduplication_function,
        test_with_real_data,
        test_pipeline_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
    
    print(f"\n=== Deduplication Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All deduplication tests passed!")
    else:
        print(f"⚠️  {total - passed} tests failed")


if __name__ == "__main__":
    main()