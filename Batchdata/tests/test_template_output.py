"""
Test template output functionality without API calls
"""

import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_template_output():
    """Test template output creation with mock data."""
    print("🧪 Testing Template Output Creation")
    print("-" * 50)
    
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
            
            # Mock pipeline execution with sample results
            mock_final_df = pd.DataFrame([
                {
                    'record_id': 'test_001', 
                    'source_entity_name': 'Test LLC', 
                    'target_first_name': 'John',
                    'target_last_name': 'Doe',
                    'owner_name_full': 'John Doe',
                    'city': 'Phoenix',
                    'state': 'AZ',
                    'phone_1': '+14805551234'
                }
            ])
            mock_client.run_skip_trace_pipeline.return_value = (mock_final_df, [])
            
            mock_client_factory.return_value = mock_client
            
            # Patch input to automatically confirm costs
            with patch('builtins.input', return_value='y'):
                print("🚀 Running template output test...")
                
                # Test template output with small dataset
                run_pipeline(
                    "batchdata_local_input.xlsx", 
                    dry_run=False, 
                    template_output=True
                )
                
                # Check if template output file was created
                # Expected format: M.YY_batchdata_upload_MM.DD.HH-MM-SS.xlsx
                results_files = [f for f in os.listdir("results") if f.endswith(".xlsx") and "_batchdata_upload_" in f]

                if results_files:
                    latest_file = max(results_files, key=lambda f: os.path.getctime(os.path.join("results", f)))
                    file_path = os.path.join("results", latest_file)
                    
                    print(f"✅ Template file created: {latest_file}")
                    
                    # Verify file structure
                    excel_file = pd.ExcelFile(file_path)
                    expected_sheets = ['README', 'CONFIG', 'INPUT_MASTER', 'BLACKLIST_NAMES', 'EXPECTED_FIELDS']
                    
                    print(f"📊 Sheets found: {excel_file.sheet_names}")
                    
                    missing_sheets = [sheet for sheet in expected_sheets if sheet not in excel_file.sheet_names]
                    if missing_sheets:
                        print(f"❌ Missing sheets: {missing_sheets}")
                        return False
                    else:
                        print("✅ All required sheets present")
                    
                    # Check INPUT_MASTER content
                    input_master = pd.read_excel(file_path, sheet_name='INPUT_MASTER')
                    print(f"📋 INPUT_MASTER records: {len(input_master)}")
                    
                    # Check README content
                    readme = pd.read_excel(file_path, sheet_name='README')
                    print(f"📄 README entries: {len(readme)}")
                    
                    print("✅ Template output test successful!")
                    return True
                else:
                    print("❌ No template output file found")
                    return False
                
    except Exception as e:
        print(f"❌ Template output test failed: {e}")
        return False
    finally:
        # Clean up environment
        for key in ['BD_SKIPTRACE_KEY', 'BD_PHONE_KEY']:
            if key in os.environ:
                del os.environ[key]


def test_naming_convention():
    """Test the M.YY naming convention."""
    print("\n📅 Testing Naming Convention")
    print("-" * 50)
    
    from src.io import get_template_filename
    from datetime import datetime
    
    # Test current month.year format
    month_year = datetime.now().strftime("%m.%y")
    test_path = get_template_filename("results", month_year)
    
    print(f"Month.Year format: {month_year}")
    print(f"Generated filename: {os.path.basename(test_path)}")
    
    # Verify naming pattern: M.YY_batchdata_upload_MM.DD.HH-MM-SS.xlsx
    filename = os.path.basename(test_path)
    if "_batchdata_upload_" in filename and month_year in filename and "_" in filename:
        print("✅ Naming convention correct")
        return True
    else:
        print("❌ Naming convention incorrect")
        return False


def main():
    """Run template output tests."""
    print("🔬 Template Output Test Suite")
    print("=" * 50)
    
    tests = [
        test_naming_convention,
        test_template_output
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
    
    print(f"\n=== Template Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All template tests passed!")
    else:
        print(f"⚠️  {total - passed} tests failed")


if __name__ == "__main__":
    main()