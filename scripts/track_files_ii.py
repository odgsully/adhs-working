import pandas as pd
import os
from datetime import datetime
import glob
import warnings
import difflib
warnings.filterwarnings('ignore')

# Define a mapping dictionary for each canonical field to its possible source names
FIELD_MAP = {
    "PROVIDER": [
        "FACILITY_NAME", "Account__r.Name", "Account Name", "External Facility Id", "ExternalFacilityID", "Name", "AccountName"
    ],
    "ADDRESS": [
        "Physical_Address__c", "Physical Street", "BillingStreet", "Street"
    ],
    "CITY": [
        "Physical_City__c", "City", "Physical City", "BillingCity"
    ],
    "ZIP": [
        "Physical_Zip_Code__c", "Zip", "Physical Zip Code", "BillingPostalCode", "Physical Zip/Postal Code"
    ],
    "CAPACITY": [
        "TotalCapacity__c", "TotalCapacity", "Total Capacity", "Capacity", "Capacity-Total Licensed", "CapacityTotalLicensed__c"
    ],
    "LONGITUDE": [
        "Account__r.BillingLongitude", "PhysicalLongitude", "Physical Longitude", "N_LON"
    ],
    "LATITUDE": [
        "Account__r.BillingLatitude", "PhysicalLatitude", "Physical Latitude", "N_LAT"
    ]
    # Add more as needed
}

for key, vals in FIELD_MAP.items():
    upper_vals = [v.upper() for v in vals if v.upper() not in vals]
    FIELD_MAP[key].extend(upper_vals)

def get_current_version():
    return datetime.now().strftime("%m.%y")

def read_excel_safely(file_path):
    try:
        return pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return None

def get_headers(file_path):
    df = read_excel_safely(file_path)
    if df is not None:
        return list(df.columns)
    return []

def find_column(df, canonical):
    for possible in FIELD_MAP.get(canonical, []):
        for col in df.columns:
            # Convert both to strings and handle datetime objects
            col_str = str(col).strip().lower()
            possible_str = str(possible).strip().lower()
            if col_str == possible_str:
                return col
    return None

def suggest_mapping(header, field_map):
    all_known = [item for sublist in field_map.values() for item in sublist]
    matches = difflib.get_close_matches(header, all_known, n=1, cutoff=0.8)
    if matches:
        return matches[0], difflib.SequenceMatcher(None, header, matches[0]).ratio()
    return None, 0

def create_tracking_data(raw_dir="Raw New Month"):
    files = glob.glob(os.path.join(raw_dir, "*.xlsx"))
    
    if not files:
        print(f"\n❌ ERROR: No Excel files found in '{raw_dir}' directory!")
        print(f"Please place your Excel files in the '{raw_dir}' folder and try again.")
        return None
    
    tracking_data = []
    for file in files:
        file_name = os.path.basename(file)
        headers = get_headers(file)
        if headers:
            # Convert all headers to strings to handle datetime objects
            headers_str = [str(header) for header in headers]
            tracking_data.append({
                'File Name': file_name,
                'File Format': 'xlsx',
                'Headers': ';;'.join(headers_str),
                'Necessary Columns': ';;'.join(['MONTH', 'YEAR', 'PROVIDER TYPE', 
                                              'PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 
                                              'CAPACITY', 'LONGITUDE', 'LATITUDE'])
            })
    
    return pd.DataFrame(tracking_data)

def convert_to_uppercase(df):
    """Convert all string values in DataFrame to uppercase."""
    for col in df.columns:
        if df[col].dtype == 'object':  # Only convert string/object columns
            df[col] = df[col].astype(str).str.upper()
    return df

def save_excel_with_formatting(df, output_path):
    """Save DataFrame to Excel with number formatting for MONTH and YEAR columns."""
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # Get the column indices for MONTH and YEAR
        month_col = df.columns.get_loc('MONTH')
        year_col = df.columns.get_loc('YEAR')
        
        # Set number format for MONTH and YEAR columns
        number_format = workbook.add_format({'num_format': '0'})
        worksheet.set_column(month_col, month_col, None, number_format)
        worksheet.set_column(year_col, year_col, None, number_format)

def create_all_to_date_file(month, year, combined_df):
    """Create or update the 'Reformat All to Date' file with all previous months plus new month."""
    summary_dir = "All-to-Date"
    os.makedirs(summary_dir, exist_ok=True)
    
    # Define the necessary columns for consistency
    necessary_cols = ['MONTH', 'YEAR', 'PROVIDER TYPE', 
                     'PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 
                     'CAPACITY', 'LONGITUDE', 'LATITUDE']
    
    # Look for existing "Reformat All to Date" files
    existing_files = glob.glob(os.path.join(summary_dir, "Reformat All to Date *.xlsx"))
    
    all_data = []
    
    if existing_files:
        # Read the most recent "All to Date" file
        latest_file = max(existing_files, key=os.path.getctime)
        print(f"Found existing cumulative file: {latest_file}")
        existing_df = read_excel_safely(latest_file)
        if existing_df is not None:
            # Remove existing records for the same MONTH/YEAR combination
            existing_df = existing_df[~((existing_df['MONTH'] == int(month)) & (existing_df['YEAR'] == int(year)))]
            print(f"Removed existing records for month {month}, year {year}")
            print(f"Loaded {len(existing_df)} existing records (after removal)")
            all_data.append(existing_df)
    else:
        print("No existing cumulative file found. Creating new one.")
    
    # Add the new month's data
    if combined_df is not None and len(combined_df) > 0:
        all_data.append(combined_df)
        print(f"Added {len(combined_df)} new records")
    
    # Create the combined file
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        print(f"Final combined file has {len(final_df)} total records")
    else:
        # Create empty DataFrame with headers only
        final_df = pd.DataFrame(columns=necessary_cols)
        print("Created empty file with headers only")
    
    # Save the cumulative file
    output_filename = f"Reformat All to Date {month}.{year}.xlsx"
    output_path = os.path.join(summary_dir, output_filename)
    save_excel_with_formatting(final_df, output_path)
    print(f"Saved cumulative file: {output_path}")

def remove_summary_rows(df):
    """Remove summary rows from the DataFrame that contain 'Total', 'Sum', or 'Count' patterns."""
    if df is None or len(df) == 0:
        return df
    
    # Convert first few columns to string for pattern matching
    df_clean = df.copy()
    
    # Get the first few column names for pattern checking
    first_col = df_clean.columns[0] if len(df_clean.columns) > 0 else None
    second_col = df_clean.columns[1] if len(df_clean.columns) > 1 else None
    
    # Convert to string for pattern matching
    if first_col:
        df_clean[first_col] = df_clean[first_col].astype(str)
    if second_col:
        df_clean[second_col] = df_clean[second_col].astype(str)
    
    # Find rows to remove based on patterns
    rows_to_remove = []
    
    for idx, row in df_clean.iterrows():
        # Pattern 1: "Total" in first column and "Sum" in second column
        if (first_col and second_col and 
            row[first_col].strip().upper() == 'TOTAL' and 
            row[second_col].strip().upper() == 'SUM'):
            rows_to_remove.append(idx)
            print(f"Removing summary row (Total/Sum): Row {idx}")
        
        # Pattern 2: "Count" in second column
        elif (second_col and row[second_col].strip().upper() == 'COUNT'):
            rows_to_remove.append(idx)
            print(f"Removing summary row (Count): Row {idx}")
        
        # Pattern 3: "Total" in first column (additional check)
        elif (first_col and row[first_col].strip().upper() == 'TOTAL'):
            rows_to_remove.append(idx)
            print(f"Removing summary row (Total): Row {idx}")
    
    # Remove the identified summary rows
    if rows_to_remove:
        df_clean = df_clean.drop(rows_to_remove)
        print(f"Removed {len(rows_to_remove)} summary rows")
    
    return df_clean

def process_files(tracking_df, month, year, raw_dir="Raw New Month"):
    current_version = get_current_version()
    output_dir = os.path.join("ALL MONTHS", f"Reformat {month}.{year}")
    os.makedirs(output_dir, exist_ok=True)
    
    combined_data = []
    unmapped_summary = {}
    
    for _, row in tracking_df.iterrows():
        file_path = os.path.join(raw_dir, row['File Name'])
        df = read_excel_safely(file_path)
        
        if df is not None:
            print(f"Processing {row['File Name']}...")
            
            # Remove summary rows before processing
            df = remove_summary_rows(df)
            
            # Add required columns with proper formatting
            df['MONTH'] = int(month)  # Convert to integer
            df['YEAR'] = int(year)  # Convert to integer
            # Remove .xlsx from PROVIDER TYPE
            sheet_name = row['File Name'].replace('.xlsx', '')
            df['PROVIDER TYPE'] = sheet_name
            # For each necessary col, fill from original if present, else blank
            necessary_cols = row['Necessary Columns'].split(';;')
            unmapped = []
            for col in necessary_cols:
                if col not in df.columns:
                    mapped = find_column(df, col)
                    if mapped:
                        print(f"Mapping {mapped} to {col}")
                        df[col] = df[mapped]
                    else:
                        # Auto-handle unmapped columns for batch processing
                        print(f"No match found for {col} - setting to blank")
                        df[col] = ''
                        unmapped.append(col)
            # Reorder columns
            df = df[necessary_cols]
            # Convert all string values to uppercase
            df = convert_to_uppercase(df)
            # Save formatted file with number formatting
            output_path = os.path.join(output_dir, row['File Name'].replace('.xlsx', '_Formatted.xlsx'))
            save_excel_with_formatting(df, output_path)
            # Add to combined data
            combined_data.append(df)
            if unmapped:
                unmapped_summary[row['File Name']] = unmapped
    
    # Create combined file
    combined_df = None
    if combined_data:
        combined_df = pd.concat(combined_data, ignore_index=True)
        combined_output_path = os.path.join("Reformat", f"{month}.{year} Reformat.xlsx")
        os.makedirs("Reformat", exist_ok=True)
        save_excel_with_formatting(combined_df, combined_output_path)
    
    # Create the cumulative "All to Date" file
    create_all_to_date_file(month, year, combined_df)
    
    # Print summary of unmapped fields
    if unmapped_summary:
        print(f"\n🔍 Unmapped Fields Summary for {month}.{year}:")
        for file, fields in unmapped_summary.items():
            print(f"📄 {file}: {', '.join(fields)}")
    
    return combined_df

def generate_month_list():
    """Generate chronological list of months from 9.24 to 7.25"""
    months = []
    
    # Start from September 2024 (9.24) to December 2024
    for month in range(9, 13):
        months.append((str(month), "24"))
    
    # January 2025 to July 2025
    for month in range(1, 8):
        months.append((str(month), "25"))
    
    return months

def batch_process_all_months():
    """Process all months from 9.24 to 7.25 in chronological order"""
    print("🚀 Starting batch processing for all months (9.24 to 7.25)...")
    months = generate_month_list()
    
    for i, (month, year) in enumerate(months, 1):
        print(f"\n{'='*60}")
        print(f"📅 Processing Month {i}/{len(months)}: {month}.{year}")
        print(f"{'='*60}")
        
        # Determine raw directory for this month
        raw_dir = f"ALL-MONTHS/Raw {month}.{year}"
        
        # Check if raw data exists for this month
        if not os.path.exists(raw_dir):
            print(f"❌ Skipping {month}.{year}: No raw data directory found at {raw_dir}")
            continue
        
        # Create tracking data for this month
        tracking_df = create_tracking_data(raw_dir)
        if tracking_df is None:
            print(f"❌ Skipping {month}.{year}: No Excel files found")
            continue
        
        # Process files for this month
        combined_df = process_files(tracking_df, month, year, raw_dir)
        
        print(f"✅ Completed processing for {month}.{year}")
    
    print(f"\n🎉 Batch processing complete! Processed all months from 9.24 to 7.25")

def main():
    print("Starting file processing...")
    print("Choose processing mode:")
    print("1. Single month (interactive)")
    print("2. Batch process all months (9.24 to 7.25)")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "2":
        batch_process_all_months()
        return
    
    # Single month processing (original functionality)
    month_input = input("What is this New Month?\n").strip()
    
    # Parse month and year from input
    try:
        if '.' in month_input:
            # Format like "9.24" for September 2024
            parts = month_input.split('.')
            month = str(int(parts[0]))
            year = str(int(parts[1]))
        elif month_input.isdigit():
            # Single digit or number - assume current year
            month = str(int(month_input))
            year = "25"  # Default to 2025
        else:
            # Try to parse month name - assume current year
            from datetime import datetime
            month = str(datetime.strptime(month_input, "%B").month)
            year = "25"  # Default to 2025
    except:
        print("Invalid month format. Using current month and year.")
        current_date = datetime.now()
        month = str(current_date.month)
        year = str(current_date.year)[-2:]  # Last 2 digits of year
    
    print(f"Processing for month {month}, year {year}")
    
    tracking_df = create_tracking_data()
    if tracking_df is not None:
        process_files(tracking_df, month, year)
        print("Processing complete!")

if __name__ == "__main__":
    main() 