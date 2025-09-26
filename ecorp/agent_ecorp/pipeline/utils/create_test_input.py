"""
Helper script to create test input file from eCorp data and template
"""

import pandas as pd
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.transform import transform_ecorp_to_batchdata

def create_test_input():
    """Create test input file from eCorp data and template."""
    
    # Load eCorp data
    ecorp_path = "../M.YY_Ecorp_Complete.xlsx"
    template_path = "../batchdata_local_pack/template_batchdata_upload.xlsx"
    
    print(f"Loading eCorp data from: {ecorp_path}")
    ecorp_df = pd.read_excel(ecorp_path)
    print(f"Loaded {len(ecorp_df)} eCorp records")
    
    # Transform to BatchData format - take first 3 records for testing
    print("Transforming to BatchData format...")
    test_ecorp = ecorp_df.head(3).copy()
    batchdata_df = transform_ecorp_to_batchdata(test_ecorp)
    print(f"Transformed to {len(batchdata_df)} BatchData records")
    
    # Load template sheets
    print(f"Loading template from: {template_path}")
    config_df = pd.read_excel(template_path, sheet_name='CONFIG')
    blacklist_df = pd.read_excel(template_path, sheet_name='BLACKLIST_NAMES')
    
    # Create output file
    output_path = "batchdata_local_input.xlsx"
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Write README sheet
        readme_data = {
            'Info': [
                'BatchData Bulk Pipeline Test Input',
                'Created from eCorp data transformation',
                f'Source: {ecorp_path}',
                f'Records: {len(batchdata_df)}',
                'Usage: python -m src.run --input batchdata_local_input.xlsx'
            ]
        }
        pd.DataFrame(readme_data).to_excel(writer, sheet_name='README', index=False)
        
        # Write configuration
        config_df.to_excel(writer, sheet_name='CONFIG', index=False)
        
        # Write transformed input data
        batchdata_df.to_excel(writer, sheet_name='INPUT_MASTER', index=False)
        
        # Write blacklist
        blacklist_df.to_excel(writer, sheet_name='BLACKLIST_NAMES', index=False)
        
        # Create expected fields sheet (for reference)
        expected_df = pd.read_excel(template_path, sheet_name='EXPECTED_FIELDS')
        expected_df.to_excel(writer, sheet_name='EXPECTED_FIELDS', index=False)
    
    print(f"Created test input file: {output_path}")
    print(f"Test records: {len(batchdata_df)}")
    print("\nSample records:")
    print(batchdata_df[['record_id', 'source_entity_name', 'target_first_name', 'target_last_name', 'city', 'state']].head())

if __name__ == "__main__":
    create_test_input()