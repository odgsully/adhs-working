"""
io.py - Excel and CSV I/O operations with timestamped paths
"""

import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional


def get_timestamped_path(base_path: str, prefix: str, extension: str) -> str:
    """Generate timestamped filename.
    
    Args:
        base_path: Directory path
        prefix: Filename prefix
        extension: File extension (without dot)
        
    Returns:
        Full path with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{extension}"
    return os.path.join(base_path, filename)


def load_workbook_sheets(excel_path: str) -> Dict[str, pd.DataFrame]:
    """Load all sheets from Excel workbook.
    
    Args:
        excel_path: Path to Excel file
        
    Returns:
        Dictionary mapping sheet names to DataFrames
    """
    excel_file = pd.ExcelFile(excel_path)
    sheets = {}
    for sheet_name in excel_file.sheet_names:
        sheets[sheet_name] = pd.read_excel(excel_path, sheet_name=sheet_name)
    return sheets


def load_config_dict(config_df: pd.DataFrame) -> Dict[str, Any]:
    """Convert CONFIG sheet DataFrame to dictionary.
    
    Args:
        config_df: DataFrame with 'key' and 'value' columns
        
    Returns:
        Dictionary of configuration values
    """
    config = {}
    for _, row in config_df.iterrows():
        key = row['key']
        value = row['value']
        
        # Convert string booleans to actual booleans
        if str(value).upper() in ['TRUE', 'FALSE']:
            value = str(value).upper() == 'TRUE'
        # Convert numeric strings to integers
        elif str(value).isdigit():
            value = int(value)
        # Handle NaN values
        elif pd.isna(value):
            value = None
            
        config[key] = value
    
    return config


def write_csv_batch(df: pd.DataFrame, batch_path: str) -> str:
    """Write DataFrame to CSV for batch upload (legacy compatibility).
    
    Args:
        df: DataFrame to write
        batch_path: Output path for CSV
        
    Returns:
        Path to written CSV file
    """
    df.to_csv(batch_path, index=False)
    return batch_path


def write_xlsx_batch(df: pd.DataFrame, batch_path: str) -> str:
    """Write DataFrame to XLSX for batch upload.
    
    Args:
        df: DataFrame to write
        batch_path: Output path for XLSX
        
    Returns:
        Path to written XLSX file
    """
    df.to_excel(batch_path, index=False, engine='openpyxl')
    return batch_path


def write_final_excel(df: pd.DataFrame, output_path: str, sheet_name: str = 'Results') -> str:
    """Write DataFrame to Excel file.
    
    Args:
        df: DataFrame to write
        output_path: Output Excel path
        sheet_name: Name of sheet to create
        
    Returns:
        Path to written Excel file
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output_path


def ensure_results_dir(results_dir: str = "results") -> str:
    """Ensure results directory exists.
    
    Args:
        results_dir: Results directory path
        
    Returns:
        Absolute path to results directory
    """
    os.makedirs(results_dir, exist_ok=True)
    return os.path.abspath(results_dir)


def ensure_subfolder(base_dir: str, subfolder: str) -> str:
    """Create subfolder for organized API results output.
    
    Args:
        base_dir: Base results directory path
        subfolder: Name of subfolder (e.g., 'skiptrace', 'phoneverify')
        
    Returns:
        Absolute path to subfolder
    """
    subfolder_path = os.path.join(base_dir, subfolder)
    os.makedirs(subfolder_path, exist_ok=True)
    return os.path.abspath(subfolder_path)


def save_intermediate_csv(df: pd.DataFrame, results_dir: str, prefix: str) -> str:
    """Save intermediate results as timestamped CSV (legacy compatibility).
    
    Args:
        df: DataFrame to save
        results_dir: Results directory
        prefix: Filename prefix
        
    Returns:
        Path to saved CSV file
    """
    csv_path = get_timestamped_path(results_dir, prefix, 'csv')
    return write_csv_batch(df, csv_path)


def save_intermediate_xlsx(df: pd.DataFrame, results_dir: str, prefix: str) -> str:
    """Save intermediate results as timestamped XLSX.
    
    Args:
        df: DataFrame to save
        results_dir: Results directory
        prefix: Filename prefix
        
    Returns:
        Path to saved XLSX file
    """
    xlsx_path = get_timestamped_path(results_dir, prefix, 'xlsx')
    return write_xlsx_batch(df, xlsx_path)


def save_api_result(df: pd.DataFrame, results_dir: str, api_type: str, prefix: str, format_type: str = 'xlsx') -> str:
    """Save API results in appropriate subfolder with organized structure.
    
    Args:
        df: DataFrame containing API results
        results_dir: Base results directory
        api_type: Type of API ('skiptrace', 'phoneverify', 'dnc', 'tcpa', 'phone_scrub', 'input')
        prefix: Filename prefix
        format_type: Output format ('xlsx' or 'csv')
        
    Returns:
        Path to saved file in subfolder
    """
    # Create appropriate subfolder
    subfolder = ensure_subfolder(results_dir, api_type)
    
    # Save in the appropriate format
    if format_type.lower() == 'csv':
        file_path = get_timestamped_path(subfolder, prefix, 'csv')
        return write_csv_batch(df, file_path)
    else:
        file_path = get_timestamped_path(subfolder, prefix, 'xlsx')
        return write_xlsx_batch(df, file_path)


def load_blacklist_set(blacklist_df: pd.DataFrame, column_name: str = 'blacklist_name') -> set:
    """Load blacklist names into a set for fast lookup.
    
    Args:
        blacklist_df: DataFrame containing blacklist names
        column_name: Column containing blacklist entries
        
    Returns:
        Set of blacklist names (uppercase)
    """
    blacklist_names = set()
    for _, row in blacklist_df.iterrows():
        name = str(row[column_name]).strip().upper()
        if name and name != 'NAN':
            blacklist_names.add(name)
    return blacklist_names


# NEW TEMPLATE OUTPUT FUNCTIONS (additive - no modifications to existing functions)

def get_template_filename(base_path: str, month_year: str) -> str:
    """Generate template-style filename with M.YY format.
    
    Args:
        base_path: Directory path
        month_year: Month.Year format (e.g., "08.25")
        
    Returns:
        Full path with template naming format
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{month_year} batchdata_upload {timestamp}.xlsx"
    return os.path.join(base_path, filename)


def write_template_excel(df: pd.DataFrame, output_path: str, config_dict: Dict[str, Any], 
                        blacklist_set: set, template_path: str = None) -> str:
    """Write DataFrame to template-structured Excel file.
    
    Args:
        df: Processed DataFrame to write to INPUT_MASTER sheet
        output_path: Output Excel path
        config_dict: Configuration dictionary
        blacklist_set: Blacklist names set
        template_path: Path to template file (optional)
        
    Returns:
        Path to written Excel file
    """
    # Create README content
    readme_data = {
        'Info': [
            'BatchData Pipeline Processing Results',
            f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'Records Processed: {len(df)}',
            f'Output File: {os.path.basename(output_path)}',
            'Pipeline: eCorp → BatchData → API Processing'
        ]
    }
    readme_df = pd.DataFrame(readme_data)
    
    # Convert config dict back to DataFrame format
    config_df = pd.DataFrame([
        {'key': key, 'value': value, 'allowed': '', 'notes': ''}
        for key, value in config_dict.items()
    ])
    
    # Convert blacklist set back to DataFrame format
    blacklist_df = pd.DataFrame([
        {'blacklist_name': name} for name in sorted(blacklist_set)
    ])
    
    # Create expected fields reference (static for now)
    expected_fields_df = pd.DataFrame([
        {'endpoint': 'property-skip-trace-async', 'field': 'record_id', 'description': 'Echo of input row ID'},
        {'endpoint': 'property-skip-trace-async', 'field': 'phones[i].number', 'description': '+1E164 format'},
        {'endpoint': 'property-skip-trace-async', 'field': 'phones[i].type', 'description': 'mobile|landline|voip'},
        {'endpoint': 'phone-verification-async', 'field': 'is_active', 'description': 'Phone active status'},
        {'endpoint': 'phone-dnc-async', 'field': 'on_dnc', 'description': 'Do-Not-Call status'},
        {'endpoint': 'phone-tcpa-async', 'field': 'is_litigator', 'description': 'TCPA litigator status'}
    ])
    
    # Write multi-sheet Excel file
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        readme_df.to_excel(writer, sheet_name='README', index=False)
        config_df.to_excel(writer, sheet_name='CONFIG', index=False)
        df.to_excel(writer, sheet_name='INPUT_MASTER', index=False)
        blacklist_df.to_excel(writer, sheet_name='BLACKLIST_NAMES', index=False)
        expected_fields_df.to_excel(writer, sheet_name='EXPECTED_FIELDS', index=False)
    
    return output_path