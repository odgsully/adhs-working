"""
Test script for entity family consolidation functionality
"""

import os
import sys
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_fuzzy_matching():
    """Test the fuzzy matching algorithm."""
    print("🔍 Testing Fuzzy Matching Algorithm")
    print("-" * 50)
    
    from src.transform import simple_fuzzy_ratio
    
    test_cases = [
        ("LEGACY TRADITIONAL SCHOOL-GILBERT", "LEGACY TRADITIONAL SCHOOL-PEORIA", "Expected: High"),
        ("ZION PROPERTY LLC", "ZION PROPERTY SERVICES LLC", "Expected: High"),
        ("METHODIST CHURCH", "UNITED METHODIST CHURCH", "Expected: Medium"),
        ("COMPLETELY DIFFERENT", "NOTHING IN COMMON", "Expected: Low"),
        ("EXACT MATCH", "EXACT MATCH", "Expected: Perfect"),
    ]
    
    for s1, s2, expected in test_cases:
        ratio = simple_fuzzy_ratio(s1, s2)
        print(f"'{s1}' vs '{s2}'")
        print(f"  Similarity: {ratio:.3f} - {expected}")
    
    return True


def test_entity_family_detection():
    """Test entity family detection."""
    print("\n🏢 Testing Entity Family Detection")
    print("-" * 50)
    
    from src.transform import detect_entity_families
    
    # Test with Legacy schools and other entity families
    test_entities = [
        "LEGACY TRADITIONAL SCHOOL-GILBERT",
        "LEGACY TRADITIONAL SCHOOL-PEORIA", 
        "LEGACY TRADITIONAL SCHOOL-GOODYEAR",
        "LEGACY TRADITIONAL SCHOOL-JEFFERSON",
        "ZION PROPERTY LLC",
        "ZION PROPERTY SERVICES LLC",
        "SPIRIT OF HOPE UNITED METHODIST CHURCH",
        "DESERT FOOTHILLS UNITED METHODIST CHURCH",
        "GLENDALE FIRST CHURCH OF THE NAZARENE",
        "STANDALONE ENTITY LLC"
    ]
    
    families = detect_entity_families(test_entities)
    
    print(f"Detected {len(families)} entity families:")
    for family_id, entities in families.items():
        print(f"\n{family_id}:")
        for entity in entities:
            print(f"  - {entity}")
    
    # Verify Legacy schools are grouped
    legacy_found = False
    for family_id, entities in families.items():
        if 'LEGACY' in family_id and len(entities) >= 3:
            legacy_found = True
            print(f"\n✅ Legacy Traditional Schools properly grouped in {family_id}")
            break
    
    if not legacy_found:
        print("❌ Legacy Traditional Schools not properly grouped")
        return False
    
    return True


def test_consolidation_function():
    """Test the consolidation function with sample data."""
    print("\n🔄 Testing Entity Family Consolidation Function")
    print("-" * 50)
    
    from src.transform import consolidate_entity_families
    
    # Create test data mimicking the Legacy school scenario
    # NOTE: Nov 2025 - consolidation now uses BD_TITLE_ROLE + BD_SOURCE_ENTITY_ID instead of names
    test_data = pd.DataFrame([
        {
            'BD_RECORD_ID': 'legacy_001',
            'BD_ENTITY_NAME': 'LEGACY TRADITIONAL SCHOOL-GILBERT',
            'BD_TITLE_ROLE': 'Manager',
            'BD_SOURCE_ENTITY_ID': 'L11111',
            'BD_ADDRESS': '3125 S GILBERT RD',
            'BD_CITY': '',
            'BD_STATE': '',
            'BD_ZIP': '85286',
            'BD_NOTES': 'Original record from Gilbert'
        },
        {
            'BD_RECORD_ID': 'legacy_002',
            'BD_ENTITY_NAME': 'LEGACY TRADITIONAL SCHOOL-PEORIA',
            'BD_TITLE_ROLE': 'Manager',
            'BD_SOURCE_ENTITY_ID': 'L22222',
            'BD_ADDRESS': '3125 S GILBERT RD',
            'BD_CITY': '',
            'BD_STATE': '',
            'BD_ZIP': '85286',
            'BD_NOTES': 'Original record from Peoria'
        },
        {
            'BD_RECORD_ID': 'legacy_003',
            'BD_ENTITY_NAME': 'LEGACY TRADITIONAL SCHOOL-GOODYEAR',
            'BD_TITLE_ROLE': 'Manager',
            'BD_SOURCE_ENTITY_ID': 'L33333',
            'BD_ADDRESS': '3125 S GILBERT RD',
            'BD_CITY': '',
            'BD_STATE': '',
            'BD_ZIP': '85286',
            'BD_NOTES': 'Original record from Goodyear'
        },
        {
            'BD_RECORD_ID': 'other_001',
            'BD_ENTITY_NAME': 'UNRELATED ENTITY LLC',
            'BD_TITLE_ROLE': 'Member',
            'BD_SOURCE_ENTITY_ID': 'C99999',
            'BD_ADDRESS': '456 Other St',
            'BD_CITY': 'Phoenix',
            'BD_STATE': 'AZ',
            'BD_ZIP': '85001',
            'BD_NOTES': 'Unrelated entity'
        }
    ])
    
    print(f"Input: {len(test_data)} records")
    print("Records:")
    for _, row in test_data.iterrows():
        print(f"  {row['BD_RECORD_ID']}: {row['BD_TITLE_ROLE']} @ {row['BD_ENTITY_NAME']}")

    # Apply consolidation
    consolidated = consolidate_entity_families(test_data)

    print(f"\nOutput: {len(consolidated)} records")
    print("Consolidated records:")
    for _, row in consolidated.iterrows():
        print(f"  {row['BD_RECORD_ID']}: {row['BD_TITLE_ROLE']} @ {row['BD_ADDRESS']}")
        if 'Consolidated' in str(row.get('BD_NOTES', '')):
            print(f"    Notes: {row['BD_NOTES'][:100]}...")
    
    # Verify consolidation worked
    # With address-only dedup, same address + role should consolidate: 3 Legacy records → 1 (but different entity IDs keep them separate)
    # Actually with distinct entity IDs, all 4 records stay distinct
    expected_records = 4
    if len(consolidated) == expected_records:
        print("✅ Entity family consolidation working correctly")
        return True
    else:
        print(f"❌ Expected {expected_records} records, got {len(consolidated)}")
        return False


def test_with_real_data():
    """Test with the actual deduplicated BatchData."""
    print("\n🧪 Testing with Real BatchData")
    print("-" * 50)
    
    try:
        # Load the deduplicated data
        dedupe_file = 'results/filtered_input_20250818_132817_20250818_132817_dedupe_test.csv'
        if not os.path.exists(dedupe_file):
            print("❌ Deduplicated test file not found")
            return False
        
        from src.transform import consolidate_entity_families
        
        df = pd.read_csv(dedupe_file)
        print(f"Input records after basic deduplication: {len(df)}")
        
        # Apply entity family consolidation
        consolidated = consolidate_entity_families(df)
        
        # Calculate savings
        original_count = len(df)
        final_count = len(consolidated)
        additional_savings = original_count - final_count
        additional_percent = (additional_savings / original_count) * 100 if original_count > 0 else 0
        
        print(f"\n💰 Real Data Results:")
        print(f"   After basic dedup: {original_count} records")
        print(f"   After family consolidation: {final_count} records")
        print(f"   Additional savings: {additional_savings} records ({additional_percent:.1f}%)")
        
        # Calculate total cost impact
        original_total = 103  # From before any deduplication
        total_reduction = original_total - final_count
        total_percent = (total_reduction / original_total) * 100
        
        original_cost = original_total * 0.07
        final_cost = final_count * 0.07
        total_savings = original_cost - final_cost
        
        print(f"   Total optimization: {original_total} → {final_count} records ({total_percent:.1f}% reduction)")
        print(f"   Total cost savings: ${total_savings:.2f} (${original_cost:.2f} → ${final_cost:.2f})")
        
        # Save consolidated results
        consolidated_file = dedupe_file.replace('_dedupe_test.csv', '_families_test.csv')
        consolidated.to_csv(consolidated_file, index=False)
        print(f"   Saved consolidated data: {consolidated_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Real data test failed: {e}")
        return False


def test_pipeline_integration():
    """Test the full pipeline with entity family consolidation."""
    print("\n🚀 Testing Full Pipeline Integration")
    print("-" * 50)
    
    try:
        # Set test environment
        os.environ['BD_SKIPTRACE_KEY'] = 'test_key'
        
        from src.run import run_pipeline
        from unittest.mock import patch, MagicMock
        
        # Mock the API client
        with patch('src.run.create_client_from_env') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.estimate_cost.return_value = {
                'skip_trace': 4.34, 'phone_verification': 0.87, 
                'phone_dnc': 0.25, 'phone_tcpa': 0.25, 'total': 5.71
            }
            mock_client_factory.return_value = mock_client
            
            with patch('builtins.input', return_value='y'):
                print("Testing full pipeline with all optimizations...")
                run_pipeline(
                    "../batchdata_local_pack/template_batchdata_upload.xlsx",
                    "../M.YY_Ecorp_Complete.xlsx",
                    dry_run=True,
                    dedupe=True,
                    consolidate_families=True
                )
                
        print("✅ Full pipeline integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        return False
    finally:
        if 'BD_SKIPTRACE_KEY' in os.environ:
            del os.environ['BD_SKIPTRACE_KEY']


def main():
    """Run all entity family consolidation tests."""
    print("🏢 Entity Family Consolidation Test Suite")
    print("=" * 60)
    
    tests = [
        test_fuzzy_matching,
        test_entity_family_detection,
        test_consolidation_function,
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
    
    print(f"\n=== Entity Family Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All entity family tests passed!")
    else:
        print(f"⚠️  {total - passed} tests failed")


if __name__ == "__main__":
    main()