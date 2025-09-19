"""Analysis module for ADHS ETL pipeline - identifies lost licenses and generates lead reports."""

import logging
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


class ProviderAnalyzer:
    """Analyzes provider data to identify lost licenses and generate leads."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.status_to_lead_type = {
            'NEW PROVIDER_TYPE, NEW ADDRESS': 'SURVEY LEAD',
            'NEW PROVIDER_TYPE, EXISTING ADDRESS': 'SURVEY LEAD',
            'EXISTING PROVIDER_TYPE, NEW ADDRESS': 'SURVEY LEAD',
            'EXISTING PROVIDER_TYPE, EXISTING ADDRESS': 'SURVEY LEAD',
            'LOST PROVIDER_TYPE, EXISTING ADDRESS': 'SELLER/SURVEY LEAD',
            'LOST PROVIDER_TYPE, LOST ADDRESS (0 REMAIN)': 'SELLER LEAD',
            'LOST PROVIDER_TYPE, LOST ADDRESS (1+ REMAIN)': 'SELLER LEAD'
        }
    
    def analyze_month_changes(
        self,
        current_month_df: pd.DataFrame,
        previous_month_df: pd.DataFrame,
        all_historical_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Analyze changes between months to identify lost licenses and opportunities."""
        
        # Create unique identifiers
        current_month_df = current_month_df.copy()
        previous_month_df = previous_month_df.copy()
        
        # Debug logging
        current_provider_types = current_month_df['PROVIDER_TYPE'].unique() if not current_month_df.empty else []
        logger.info(f"Current month provider types: {list(current_provider_types)}")
        
        previous_provider_types = previous_month_df['PROVIDER_TYPE'].unique() if not previous_month_df.empty else []
        logger.info(f"Previous month provider types: {list(previous_provider_types)}")
        
        # Key is (PROVIDER TYPE, PROVIDER, ADDRESS)
        current_month_df['KEY'] = (
            current_month_df['PROVIDER_TYPE'].astype(str) + '|' +
            current_month_df['PROVIDER'].astype(str) + '|' +
            current_month_df['ADDRESS'].astype(str)
        )
        
        if not previous_month_df.empty:
            previous_month_df['KEY'] = (
                previous_month_df['PROVIDER_TYPE'].astype(str) + '|' +
                previous_month_df['PROVIDER'].astype(str) + '|' +
                previous_month_df['ADDRESS'].astype(str)
            )
            prev_keys = set(previous_month_df['KEY'])
        else:
            prev_keys = set()
        
        current_keys = set(current_month_df['KEY'])
        
        # Get all historical addresses
        all_historical_addresses = set()
        if not all_historical_df.empty:
            all_historical_addresses = set(all_historical_df['ADDRESS'].unique())
        
        # Analyze each record
        analysis_records = []
        
        for idx, row in current_month_df.iterrows():
            record = row.to_dict()
            key = row['KEY']
            address = row['ADDRESS']
            
            # Check if this exact combination existed before
            if key in prev_keys:
                # Check if address is new to system
                if address not in all_historical_addresses:
                    record['THIS MONTH STATUS'] = 'EXISTING PROVIDER_TYPE, NEW ADDRESS'
                else:
                    record['THIS MONTH STATUS'] = 'EXISTING PROVIDER_TYPE, EXISTING ADDRESS'
            else:
                # New provider type at this address
                if address not in all_historical_addresses:
                    record['THIS MONTH STATUS'] = 'NEW PROVIDER_TYPE, NEW ADDRESS'
                else:
                    record['THIS MONTH STATUS'] = 'NEW PROVIDER_TYPE, EXISTING ADDRESS'
            
            # Assign lead type
            record['LEAD TYPE'] = self.status_to_lead_type.get(record['THIS MONTH STATUS'], '')
            
            # Remove the KEY field
            del record['KEY']
            
            analysis_records.append(record)
        
        # Now check for lost licenses (in previous but not current)
        if not previous_month_df.empty:
            lost_keys = prev_keys - current_keys
            
            for lost_key in lost_keys:
                # Get the lost record
                lost_record = previous_month_df[previous_month_df['KEY'] == lost_key].iloc[0].to_dict()
                address = lost_record['ADDRESS']
                
                # Check if any providers remain at this address
                remaining_at_address = len(current_month_df[current_month_df['ADDRESS'] == address])
                
                if remaining_at_address == 0:
                    # Check if address still has any providers in current month
                    any_at_address = len(current_month_df[current_month_df['ADDRESS'] == address])
                    if any_at_address == 0:
                        lost_record['THIS MONTH STATUS'] = 'LOST PROVIDER_TYPE, LOST ADDRESS (0 REMAIN)'
                    else:
                        lost_record['THIS MONTH STATUS'] = 'LOST PROVIDER_TYPE, LOST ADDRESS (1+ REMAIN)'
                else:
                    lost_record['THIS MONTH STATUS'] = 'LOST PROVIDER_TYPE, EXISTING ADDRESS'
                
                # Assign lead type
                lost_record['LEAD TYPE'] = self.status_to_lead_type.get(lost_record['THIS MONTH STATUS'], '')
                
                # Remove the KEY field
                del lost_record['KEY']
                
                analysis_records.append(lost_record)
        
        return pd.DataFrame(analysis_records)
    
    def calculate_provider_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate provider group information."""
        df = df.copy()
        
        # Ensure all required columns exist
        required_columns = [
            'SOLO PROVIDER_TYPE PROVIDER [Y, #]',
            'PROVIDER GROUP (DBA CONCAT)',
            'PROVIDER GROUP, ADDRESS COUNT'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = 'N/A'
        
        # Get group information
        group_info = {}
        
        for group_id in df['PROVIDER_GROUP_INDEX_#'].unique():
            group_df = df[df['PROVIDER_GROUP_INDEX_#'] == group_id]
            
            # Get all providers in group
            providers = []
            for _, row in group_df.iterrows():
                provider_address = f"{row['PROVIDER']} ({row['ADDRESS']})"
                if provider_address not in providers:
                    providers.append(provider_address)
            
            # Remove self from concat list
            group_info[group_id] = {
                'all_providers': providers,
                'address_count': len(group_df['ADDRESS'].unique())
            }
        
        # Add group information to each record
        for idx, row in df.iterrows():
            group_id = row['PROVIDER_GROUP_INDEX_#']
            info = group_info[group_id]
            
            # Create concat excluding self
            self_key = f"{row['PROVIDER']} ({row['ADDRESS']})"
            other_providers = [p for p in info['all_providers'] if p != self_key]
            
            if other_providers:
                df.at[idx, 'PROVIDER GROUP (DBA CONCAT)'] = ', '.join(other_providers)
            else:
                df.at[idx, 'PROVIDER GROUP (DBA CONCAT)'] = 'N/A'
            
            df.at[idx, 'PROVIDER GROUP, ADDRESS COUNT'] = info['address_count']
            
            # Check if solo provider - a provider is solo if it's the only provider at that address
            providers_at_address = df[df['ADDRESS'] == row['ADDRESS']]['PROVIDER'].unique()
            
            if len(providers_at_address) == 1:
                df.at[idx, 'SOLO PROVIDER_TYPE PROVIDER [Y, #]'] = 'Y'
            else:
                df.at[idx, 'SOLO PROVIDER_TYPE PROVIDER [Y, #]'] = str(len(providers_at_address))
        
        return df
    
    def create_monthly_counts(
        self,
        all_historical_df: pd.DataFrame,
        current_month: int,
        current_year: int
    ) -> Dict[str, pd.Series]:
        """Create monthly count columns for the analysis."""
        # Get unique months in data
        if all_historical_df.empty:
            return {}
        
        months_data = {}
        
        # Group by month/year and count addresses per provider
        for (month, year), month_df in all_historical_df.groupby(['MONTH', 'YEAR']):
            # Format column name
            if month >= 10:
                col_name = f"{month}.{year % 100} COUNT"
            else:
                col_name = f"{month}.{year % 100} COUNT"
            
            # Count addresses per provider
            counts = month_df.groupby(['PROVIDER', 'PROVIDER_TYPE'])['ADDRESS'].count()
            months_data[col_name] = counts
        
        return months_data
    
    def create_movement_columns(
        self,
        df: pd.DataFrame,
        months_data: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """Add movement comparison columns."""
        df = df.copy()
        
        # Sort months chronologically
        sorted_months = sorted(months_data.keys(), key=lambda x: (
            int(x.split('.')[1].split()[0]),  # year (remove " COUNT" suffix)
            int(x.split('.')[0])  # month
        ))
        
        # Add count columns
        for month_col in sorted_months:
            df[month_col] = 0
            
            # Fill in counts
            for idx, row in df.iterrows():
                key = (row['PROVIDER'], row['PROVIDER_TYPE'])
                if key in months_data[month_col].index:
                    df.at[idx, month_col] = months_data[month_col][key]
        
        # Add movement columns
        for i in range(1, len(sorted_months)):
            prev_month = sorted_months[i-1]
            curr_month = sorted_months[i]
            
            # Extract month number for column name
            month_num = curr_month.split('.')[0]
            year_num = curr_month.split('.')[1].split()[0]  # Remove " COUNT" suffix
            
            if int(month_num) >= 10:
                movement_col = f"{month_num}.{year_num} TO PREV"
            else:
                movement_col = f"{month_num}.{year_num} TO PREV"
            
            df[movement_col] = df.apply(
                lambda row: self._calculate_movement(row[prev_month], row[curr_month]),
                axis=1
            )
        
        return df
    
    def _calculate_movement(self, prev_count: int, curr_count: int) -> str:
        """Calculate movement between two counts."""
        if pd.isna(prev_count) or pd.isna(curr_count):
            return ''
        
        if curr_count > prev_count:
            return 'INCREASED'
        elif curr_count < prev_count:
            return 'DECREASED'
        else:
            return 'NO MOVEMENT'
    
    def create_summary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add summary columns for each month."""
        df = df.copy()
        
        # Find all count columns
        count_cols = [col for col in df.columns if col.endswith(' COUNT')]
        
        for count_col in count_cols:
            try:
                # Extract month/year for summary column name
                parts = count_col.replace(' COUNT', '').split('.')
                if len(parts) < 2:
                    continue
                    
                month = parts[0]
                year = parts[1]
                
                if int(month) >= 10:
                    summary_col = f"{month}.{year} SUMMARY"
                else:
                    summary_col = f"{month}.{year} SUMMARY"
                
                # Check if required columns exist
                if 'PROVIDER GROUP, ADDRESS COUNT' in df.columns and \
                   'PROVIDER GROUP (DBA CONCAT)' in df.columns and \
                   'PROVIDER_GROUP_INDEX_#' in df.columns:
                    # Create summary concatenation
                    df[summary_col] = df.apply(
                        lambda row: f"{row['PROVIDER GROUP, ADDRESS COUNT']}, "
                                   f"{row['PROVIDER GROUP (DBA CONCAT)']}, "
                                   f"{row['PROVIDER_GROUP_INDEX_#']}",
                        axis=1
                    )
                else:
                    # If columns don't exist, use default
                    df[summary_col] = "N/A, N/A, N/A"
            except Exception as e:
                logger.warning(f"Error creating summary column for {count_col}: {e}")
                continue
        
        return df
    
    def ensure_all_analysis_columns(self, df: pd.DataFrame, processing_month: int = None, processing_year: int = None) -> pd.DataFrame:
        """Ensure all 63 columns from v100Track_this_shit.xlsx are present in the analysis output."""
        df = df.copy()
        
        # Define the complete set of columns expected in analysis output (exactly 63 columns to match v100Track_this_shit.xlsx)
        expected_columns = [
            # Core provider data
            'SOLO PROVIDER_TYPE PROVIDER [Y, #]',
            'PROVIDER_TYPE',
            'PROVIDER',
            'ADDRESS',
            'CITY',
            'ZIP',
            'FULL_ADDRESS',
            'CAPACITY',
            'LONGITUDE',
            'LATITUDE',
            'COUNTY',
            'PROVIDER_GROUP_INDEX_#',
            
            # Provider grouping
            'PROVIDER GROUP (DBA CONCAT)',
            'PROVIDER GROUP, ADDRESS COUNT',
            'THIS MONTH STATUS',
            'LEAD TYPE',
            
            # Monthly counts (9.24 through 12.25)
            '9.24 COUNT', '10.24 COUNT', '11.24 COUNT', '12.24 COUNT',
            '1.25 COUNT', '2.25 COUNT', '3.25 COUNT', '4.25 COUNT',
            '5.25 COUNT', '6.25 COUNT', '7.25 COUNT', '8.25 COUNT',
            '9.25 COUNT', '10.25 COUNT', '11.25 COUNT', '12.25 COUNT',
            
            # Monthly movements (10.24 through 12.25)
            '10.24 TO PREV', '11.24 TO PREV', '12.24 TO PREV',
            '1.25 TO PREV', '2.25 TO PREV', '3.25 TO PREV', '4.25 TO PREV',
            '5.25 TO PREV', '6.25 TO PREV', '7.25 TO PREV', '8.25 TO PREV',
            '9.25 TO PREV', '10.25 TO PREV', '11.25 TO PREV', '12.25 TO PREV',
            
            # Monthly summaries (9.24 through 12.25)
            '9.24 SUMMARY', '10.24 SUMMARY', '11.24 SUMMARY', '12.24 SUMMARY',
            '1.25 SUMMARY', '2.25 SUMMARY', '3.25 SUMMARY', '4.25 SUMMARY',
            '5.25 SUMMARY', '6.25 SUMMARY', '7.25 SUMMARY', '8.25 SUMMARY',
            '9.25 SUMMARY', '10.25 SUMMARY', '11.25 SUMMARY', '12.25 SUMMARY',
            
            # Metadata
            'MONTH',
            'YEAR'
        ]
        
        # Add any missing columns with appropriate default values
        # Use processing month/year for reference, not current system date
        reference_month = processing_month if processing_month is not None else 7
        reference_year = processing_year if processing_year is not None else 2025
        
        for col in expected_columns:
            if col not in df.columns:
                # Determine appropriate default value based on column type
                if col.endswith(' COUNT'):
                    # For monthly count columns, use 0 for past/current months, N/A for future months
                    try:
                        # Extract month and year from column name like "9.24 COUNT"
                        month_year = col.replace(' COUNT', '')
                        month, year = month_year.split('.')
                        month = int(month)
                        year = 2000 + int(year)
                        
                        # If it's a past month or current month, use 0; if future, use N/A
                        if (year < reference_year) or (year == reference_year and month <= reference_month):
                            df[col] = 0
                        else:
                            df[col] = 'N/A'
                    except Exception:
                        df[col] = 'N/A'
                        
                elif col.endswith(' TO PREV'):
                    # For monthly movement columns, use empty string for past/current months, N/A for future months
                    try:
                        # Extract month and year from column name like "9.24 TO PREV"
                        month_year = col.replace(' TO PREV', '')
                        month, year = month_year.split('.')
                        month = int(month)
                        year = 2000 + int(year)
                        
                        # If it's a past month or current month, use empty string; if future, use N/A
                        if (year < reference_year) or (year == reference_year and month <= reference_month):
                            df[col] = ''
                        else:
                            df[col] = 'N/A'
                    except Exception:
                        df[col] = 'N/A'
                        
                elif col.endswith(' SUMMARY'):
                    # For monthly summary columns, use empty string for past/current months, N/A for future months
                    try:
                        # Extract month and year from column name like "9.24 SUMMARY"
                        month_year = col.replace(' SUMMARY', '')
                        month, year = month_year.split('.')
                        month = int(month)
                        year = 2000 + int(year)
                        
                        # If it's a past month or current month, use empty string; if future, use N/A
                        if (year < reference_year) or (year == reference_year and month <= reference_month):
                            df[col] = ''
                        else:
                            df[col] = 'N/A'
                    except Exception:
                        df[col] = 'N/A'
                        
                else:
                    # For all other columns, use N/A
                    df[col] = 'N/A'
        
        # Reorder columns to match expected order
        existing_cols = [col for col in expected_columns if col in df.columns]
        other_cols = [col for col in df.columns if col not in expected_columns]
        
        # Create final column order
        final_columns = existing_cols + other_cols
        
        return df[final_columns]


def create_analysis_summary_sheet(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Create the summary sheet with counts."""
    summary_data = []
    
    # Count basic metrics
    total_addresses = analysis_df['ADDRESS'].nunique()
    total_providers = analysis_df['PROVIDER'].nunique()
    total_provider_groups = analysis_df['PROVIDER_GROUP_INDEX_#'].nunique() if 'PROVIDER_GROUP_INDEX_#' in analysis_df else 0
    total_blanks = analysis_df.isnull().sum().sum()
    total_solo_providers = len(analysis_df[analysis_df.get('SOLO PROVIDER_TYPE PROVIDER [Y, #]', '') == 'Y'])
    
    # Count status types
    status_counts = analysis_df['THIS MONTH STATUS'].value_counts() if 'THIS MONTH STATUS' in analysis_df else {}
    
    new_provider_new_address = status_counts.get('NEW PROVIDER TYPE, NEW ADDRESS', 0)
    new_provider_existing_address = status_counts.get('NEW PROVIDER TYPE, EXISTING ADDRESS', 0)
    existing_provider_new_address = status_counts.get('EXISTING PROVIDER TYPE, NEW ADDRESS', 0)
    existing_provider_existing_address = status_counts.get('EXISTING PROVIDER TYPE, EXISTING ADDRESS', 0)
    lost_provider_existing_address = status_counts.get('LOST PROVIDER TYPE, EXISTING ADDRESS', 0)
    lost_provider_lost_address_0 = status_counts.get('LOST PROVIDER TYPE, LOST ADDRESS (0 remain)', 0)
    lost_provider_lost_address_1 = status_counts.get('LOST PROVIDER TYPE, LOST ADDRESS (1+ remain)', 0)
    
    # Count leads
    seller_leads = len(analysis_df[analysis_df.get('LEAD TYPE', '').isin(['SELLER LEAD', 'SELLER/SURVEY LEAD'])])
    survey_leads = len(analysis_df[analysis_df.get('LEAD TYPE', '').isin(['SURVEY LEAD', 'SELLER/SURVEY LEAD'])])
    
    # Count by provider type
    provider_type_counts = analysis_df['PROVIDER_TYPE'].value_counts() if 'PROVIDER_TYPE' in analysis_df else {}
    total_record_count = len(analysis_df)
    
    # Create the exact template structure
    summary_data = [
        ['Total ADDRESS', total_addresses],
        ['Total PROVIDER', total_providers],
        ['Total PROVIDER GROUP', total_provider_groups],
        ['Total Blanks', total_blanks],
        ['Total SOLO PROVIDER_TYPE PROVIDER', total_solo_providers],
        ['', ''],  # Empty row
        ['New PROVIDER_TYPE, New ADDRESS', new_provider_new_address],
        ['New PROVIDER_TYPE, Existing ADDRESS', new_provider_existing_address],
        ['Existing PROVIDER_TYPE, New ADDRESS', existing_provider_new_address],
        ['Existing PROVIDER_TYPE, Existing ADDRESS', existing_provider_existing_address],
        ['Lost PROVIDER_TYPE, Existing ADDRESS', lost_provider_existing_address],
        ['Lost PROVIDER_TYPE, Lost ADDRESS (0 remain)', lost_provider_lost_address_0],
        ['Lost PROVIDER_TYPE, Lost ADDRESS (1+ remain)', lost_provider_lost_address_1],
        ['', ''],  # Empty row
        ['Seller Leads', seller_leads],
        ['Survey Leads', survey_leads],
        ['', ''],  # Empty row
        ['Total Record Count (TRC)', total_record_count],
        ['ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME (TRC)', provider_type_counts.get('ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME', 0)],
        ['ASSISTED_LIVING_CENTER (TRC)', provider_type_counts.get('ASSISTED_LIVING_CENTER', 0)],
        ['ASSISTED_LIVING_HOME (TRC)', provider_type_counts.get('ASSISTED_LIVING_HOME', 0)],
        ['BEHAVIORAL_HEALTH_INPATIENT (TRC)', provider_type_counts.get('BEHAVIORAL_HEALTH_INPATIENT', 0)],
        ['BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY (TRC)', provider_type_counts.get('BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY', 0)],
        ['CC_CENTERS (TRC)', provider_type_counts.get('CC_CENTERS', 0)],
        ['CC_GROUP_HOMES (TRC)', provider_type_counts.get('CC_GROUP_HOMES', 0)],
        ['DEVELOPMENTALLY_DISABLED_GROUP_HOME (TRC)', provider_type_counts.get('DEVELOPMENTALLY_DISABLED_GROUP_HOME', 0)],
        ['HOSPITAL_REPORT (TRC)', provider_type_counts.get('HOSPITAL_REPORT', 0)],
        ['NURSING_HOME (TRC)', provider_type_counts.get('NURSING_HOME', 0)],
        ['NURSING_SUPPORTED_GROUP_HOMES (TRC)', provider_type_counts.get('NURSING_SUPPORTED_GROUP_HOMES', 0)],
        ['OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT (TRC)', provider_type_counts.get('OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT', 0)]
    ]
    
    # Create DataFrame with exact template column names
    summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Count'])
    
    return summary_df


def create_blanks_count_sheet(current_month_df: pd.DataFrame) -> pd.DataFrame:
    """Create the blanks count sheet by provider type."""
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
        # Filter to this provider type
        type_df = current_month_df[current_month_df['PROVIDER_TYPE'] == provider_type]
        
        if type_df.empty:
            # No data for this provider type
            blanks_data.append({
                'PROVIDER_TYPE': provider_type,
                'MONTH': 0,
                'YEAR': 0,
                'PROVIDER': 0,
                'ADDRESS': 0,
                'CITY': 0,
                'ZIP': 0,
                'CAPACITY': 0,
                'LONGITUDE': 0,
                'LATITUDE': 0,
                'PROVIDER_GROUP_INDEX_#': 0
            })
        else:
            # Count blanks in each field
            row_data = {'PROVIDER_TYPE': provider_type}
            
            fields = ['MONTH', 'YEAR', 'PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 'FULL_ADDRESS',
                     'CAPACITY', 'LONGITUDE', 'LATITUDE', 'COUNTY', 'PROVIDER_GROUP_INDEX_#']
            
            for field in fields:
                if field in type_df.columns:
                    # Count empty, NaN, or 'NAN' values
                    blank_count = type_df[field].apply(
                        lambda x: pd.isna(x) or str(x).strip() in ['', 'NAN', 'N/A']
                    ).sum()
                    row_data[field] = blank_count
                else:
                    row_data[field] = len(type_df)  # All blank if column doesn't exist
            
            blanks_data.append(row_data)
    
    return pd.DataFrame(blanks_data)