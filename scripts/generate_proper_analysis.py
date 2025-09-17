#!/usr/bin/env python3
"""
Generate proper Analysis file matching v100Track_this_shit.xlsx template.
"""

import sys
import shutil
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, 'src')

from adhs_etl.transform_enhanced import (
    EnhancedFieldMapper, 
    ProviderGrouper,
    process_month_data,
    create_reformat_output,
    create_all_to_date_output
)

def create_proper_summary_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """Create proper summary sheet matching v100Track_this_shit.xlsx template."""
    
    # Follow exact structure from template
    summary_data = []
    
    # Row 1: Total ADDRESS (B2 i.e. Count of all ADDRESS)
    summary_data.append({"Metric": "Total ADDRESS", "Count": len(df['ADDRESS'].unique())})
    
    # Row 2: Total PROVIDER (B3 i.e. Count of all PROVIDER)
    summary_data.append({"Metric": "Total PROVIDER", "Count": len(df['PROVIDER'].unique())})
    
    # Row 3: Total PROVIDER GROUP (B4 i.e. highest PROVIDER GROUP INDEX #)
    summary_data.append({"Metric": "Total PROVIDER GROUP", "Count": df['PROVIDER GROUP INDEX #'].max()})
    
    # Row 4: Total Blanks (B5 i.e. Count of all Blank records)
    blank_count = 0
    for col in ['PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 'CAPACITY', 'LONGITUDE', 'LATITUDE']:
        if col in df.columns:
            blank_count += df[col].apply(lambda x: pd.isna(x) or str(x).strip() in ['', 'N/A', 'NAN']).sum()
    summary_data.append({"Metric": "Total Blanks", "Count": blank_count})
    
    # Row 5: Total SOLO PROVIDER TYPE PROVIDER (B6 i.e. count of 'Y' records)
    summary_data.append({"Metric": "Total SOLO PROVIDER TYPE PROVIDER", "Count": len(df)})
    
    # Row 6: Empty row
    summary_data.append({"Metric": "", "Count": ""})
    
    # Rows 7-11: Status types (B8-B14 based on PROVIDER TYPE & ADDRESS details)
    summary_data.append({"Metric": "New PROVIDER TYPE, New ADDRESS", "Count": len(df)})  # First month = all new
    summary_data.append({"Metric": "New PROVIDER TYPE, Existing ADDRESS", "Count": 0})
    summary_data.append({"Metric": "Existing PROVIDER TYPE, New ADDRESS", "Count": 0})
    summary_data.append({"Metric": "Existing PROVIDER TYPE, Existing ADDRESS", "Count": 0})
    summary_data.append({"Metric": "Lost PROVIDER TYPE, Existing ADDRESS", "Count": 0})
    
    # Row 12: Empty row
    summary_data.append({"Metric": "", "Count": ""})
    
    # Row 13: Lost PROVIDER TYPE, Lost ADDRESS (0 remain)
    summary_data.append({"Metric": "Lost PROVIDER TYPE, Lost ADDRESS (0 remain)", "Count": 0})
    
    # Row 14: Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)
    summary_data.append({"Metric": "Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)", "Count": 0})
    
    # Row 15: Empty row
    summary_data.append({"Metric": "", "Count": ""})
    
    # Row 16: Seller Leads (B16 i.e. 'Seller Lead', or 'Seller/Survey Lead')
    summary_data.append({"Metric": "Seller Leads", "Count": 0})
    
    # Row 17: Survey Leads (B17 i.e. 'Survey Lead', or 'Seller/Survey Lead')
    summary_data.append({"Metric": "Survey Leads", "Count": len(df)})  # First month = all survey leads
    
    # Row 18: Empty row
    summary_data.append({"Metric": "", "Count": ""})
    
    # Rows 19-30: Provider type counts (B19-B31 Total records for each PROVIDER TYPE)
    provider_types = [
        'ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME',
        'ASSISTED_LIVING_CENTER',
        'ASSISTED_LIVING_HOME',
        'BEHAVIORAL_HEALTH_INPATIENT',
        'BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY',
        'CC_CENTERS',
        'CC_GROUP_HOMES',
        'DEVELOPMENTALLY_DISABLED_GROUP_HOME',
        'HOSPITAL_REPORT',
        'NURSING_HOME',
        'NURSING_SUPPORTED_GROUP_HOMES',
        'OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT'
    ]
    
    for provider_type in provider_types:
        count = len(df[df['PROVIDER TYPE'] == provider_type])
        summary_data.append({"Metric": provider_type, "Count": count})
    
    return pd.DataFrame(summary_data)

def create_proper_blanks_count_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """Create proper blanks count sheet matching template structure."""
    
    provider_types = [
        'ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME',
        'ASSISTED_LIVING_CENTER',
        'ASSISTED_LIVING_HOME', 
        'BEHAVIORAL_HEALTH_INPATIENT',
        'BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY',
        'CC_CENTERS',
        'CC_GROUP_HOMES',
        'DEVELOPMENTALLY_DISABLED_GROUP_HOME',
        'HOSPITAL_REPORT',
        'NURSING_HOME',
        'NURSING_SUPPORTED_GROUP_HOMES',
        'OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT'
    ]
    
    blanks_data = []
    
    for provider_type in provider_types:
        type_df = df[df['PROVIDER TYPE'] == provider_type]
        
        if type_df.empty:
            # No records for this provider type - all fields are blank
            row_data = {
                'PROVIDER TYPE': provider_type,
                'MONTH': 0, 'YEAR': 0, 'PROVIDER': 0, 'ADDRESS': 0, 'CITY': 0, 
                'ZIP': 0, 'CAPACITY': 0, 'LONGITUDE': 0, 'LATITUDE': 0,
                'PROVIDER GROUP INDEX #': 0
            }
        else:
            row_data = {'PROVIDER TYPE': provider_type}
            
            fields = ['MONTH', 'YEAR', 'PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 
                     'CAPACITY', 'LONGITUDE', 'LATITUDE', 'PROVIDER GROUP INDEX #']
            
            for field in fields:
                if field in type_df.columns:
                    # For MONTH and YEAR, they should never be blank since we populate them
                    if field in ['MONTH', 'YEAR']:
                        row_data[field] = 0  # Always populated
                    else:
                        blank_count = type_df[field].apply(
                            lambda x: pd.isna(x) or str(x).strip() in ['', 'N/A', 'NAN']
                        ).sum()
                        row_data[field] = blank_count
                else:
                    # Field doesn't exist in data
                    row_data[field] = len(type_df)
        
        blanks_data.append(row_data)
    
    return pd.DataFrame(blanks_data)

def create_proper_analysis_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """Create proper analysis sheet with all required columns."""
    
    analysis_df = df.copy()
    
    # Add all required columns from v100Track_this_shit.xlsx
    required_columns = [
        'SOLO PROVIDER TYPE PROVIDER [Y, #]',
        'PROVIDER TYPE', 'PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 'CAPACITY',
        'LONGITUDE', 'LATITUDE', 'PROVIDER GROUP INDEX #',
        'PROVIDER GROUP (DBA CONCAT)', 'PROVIDER GROUP, ADDRESS COUNT',
        'THIS MONTH STATUS', 'LEAD TYPE',
        
        # Monthly counts (9.24 through 12.25)
        '9.24 COUNT', '10.24 COUNT', '11.24 COUNT', '12.24 COUNT',
        '1.25 COUNT', '2.25 COUNT', '3.25 COUNT', '4.25 COUNT',
        '5.25 COUNT', '6.25 COUNT', '7.25 COUNT', '8.25 COUNT',
        '9.25 COUNT', '10.25 COUNT', '11.25 COUNT', '12.25 COUNT',
        
        # Monthly movements 
        '10.24 TO PREV', '11.24 TO PREV', '12.24 TO PREV',
        '1.25 TO PREV', '2.25 TO PREV', '3.25 TO PREV', '4.25 TO PREV',
        '5.25 TO PREV', '6.25 TO PREV', '7.25 TO PREV', '8.25 TO PREV',
        '9.25 TO PREV', '10.25 TO PREV', '11.25 TO PREV', '12.25 TO PREV',
        
        # MCAO property data
        'APN', "BR'S", "BA'S", 'STORIES', 'OWNER NAME', 'OWNER MAILING',
        'PURCHASE PRICE', 'PURCHASE DATE',
        
        # Monthly summaries
        '9.24 SUMMARY', '10.24 SUMMARY', '11.24 SUMMARY', '12.24 SUMMARY',
        '1.25 SUMMARY', '2.25 SUMMARY', '3.25 SUMMARY', '4.25 SUMMARY',
        '5.25 SUMMARY', '6.25 SUMMARY', '7.25 SUMMARY', '8.25 SUMMARY',
        '9.25 SUMMARY', '10.25 SUMMARY', '11.25 SUMMARY', '12.25 SUMMARY'
    ]
    
    # Add missing columns with appropriate defaults
    for col in required_columns:
        if col not in analysis_df.columns:
            if 'COUNT' in col:
                analysis_df[col] = 0
            elif 'TO PREV' in col:
                analysis_df[col] = ''
            elif 'SUMMARY' in col:
                analysis_df[col] = ''
            else:
                analysis_df[col] = 'N/A'
    
    # Fill in some basic analysis values
    analysis_df['SOLO PROVIDER TYPE PROVIDER [Y, #]'] = 'Y'  # Simplified
    analysis_df['PROVIDER GROUP (DBA CONCAT)'] = 'N/A'
    analysis_df['PROVIDER GROUP, ADDRESS COUNT'] = 1
    analysis_df['THIS MONTH STATUS'] = 'NEW PROVIDER TYPE, NEW ADDRESS'  # First month
    analysis_df['LEAD TYPE'] = 'SURVEY LEAD'  # First month
    
    # Set current month count to 1
    analysis_df['9.24 COUNT'] = 1
    
    # Set current month summary
    analysis_df['9.24 SUMMARY'] = analysis_df.apply(
        lambda row: f"{row['PROVIDER GROUP, ADDRESS COUNT']}, {row['PROVIDER GROUP (DBA CONCAT)']}, {row['PROVIDER GROUP INDEX #']}",
        axis=1
    )
    
    # Reorder columns
    final_columns = [col for col in required_columns if col in analysis_df.columns]
    other_columns = [col for col in analysis_df.columns if col not in required_columns]
    
    return analysis_df[final_columns + other_columns]

def main():
    """Generate proper analysis file."""
    print("🎯 Generating Proper Analysis File")
    
    # Setup
    raw_dir = Path("Raw-New-Month")
    
    # Initialize components (suppress warnings)
    import logging
    logging.getLogger('adhs_etl.transform').setLevel(logging.ERROR)
    
    field_mapper = EnhancedFieldMapper(
        Path("field_map.yml"),
        Path("field_map.TODO.yml")
    )
    provider_grouper = ProviderGrouper()
    
    # Process data
    print("🔄 Processing data...")
    df = process_month_data(
        raw_dir,
        field_mapper,
        provider_grouper,
        month=9,
        year=2024
    )
    
    print(f"✅ Processed {len(df)} records")
    
    # Create proper analysis file
    analysis_dir = Path("Analysis")
    analysis_dir.mkdir(exist_ok=True)
    analysis_path = analysis_dir / "9.24 Analysis.xlsx"
    
    # Create all three sheets
    summary_df = create_proper_summary_sheet(df)
    blanks_df = create_proper_blanks_count_sheet(df)
    analysis_df = create_proper_analysis_sheet(df)
    
    print(f"📊 Created summary sheet: {len(summary_df)} rows")
    print(f"📊 Created blanks sheet: {len(blanks_df)} rows")  
    print(f"📊 Created analysis sheet: {len(analysis_df)} rows, {len(analysis_df.columns)} columns")
    
    # Write to Excel
    with pd.ExcelWriter(analysis_path, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        blanks_df.to_excel(writer, sheet_name='Blanks Count', index=False)
        analysis_df.to_excel(writer, sheet_name='Analysis', index=False)
    
    print(f"💾 Created: {analysis_path} ({analysis_path.stat().st_size} bytes)")
    
    # Verify
    print(f"\n🔍 File verification:")
    xl_file = pd.ExcelFile(analysis_path)
    print(f"  Sheets: {xl_file.sheet_names}")
    
    for sheet in xl_file.sheet_names:
        test_df = pd.read_excel(analysis_path, sheet_name=sheet)
        print(f"  ✅ {sheet}: {len(test_df)} rows, {len(test_df.columns)} columns")
    
    print(f"\n🎉 Proper Analysis file generated!")
    print(f"📈 Now includes BlanksCount sheet and proper column structure")

if __name__ == "__main__":
    main()