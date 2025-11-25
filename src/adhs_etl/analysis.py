"""Analysis module for ADHS ETL pipeline - identifies lost licenses and generates lead reports."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ProviderAnalyzer:
    """Analyzes provider data to identify lost licenses and generate leads."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.status_to_lead_type = {
            'NEW PROVIDER TYPE, NEW ADDRESS': 'SURVEY LEAD',
            'NEW PROVIDER TYPE, EXISTING ADDRESS': 'SURVEY LEAD',
            'EXISTING PROVIDER TYPE, NEW ADDRESS': 'SURVEY LEAD',
            'EXISTING PROVIDER TYPE, EXISTING ADDRESS': 'SURVEY LEAD',
            'LOST PROVIDER TYPE, EXISTING ADDRESS': 'SELLER/SURVEY LEAD',
            'LOST PROVIDER TYPE, LOST ADDRESS (0 REMAIN)': 'SELLER LEAD',
            'LOST PROVIDER TYPE, LOST ADDRESS (1+ REMAIN)': 'SELLER LEAD'
        }
    
    def analyze_month_changes(
        self,
        current_month_df: pd.DataFrame,
        previous_month_df: pd.DataFrame,
        all_historical_df: pd.DataFrame,
        skip_lost_licenses: bool = False
    ) -> pd.DataFrame:
        """Analyze changes between months to identify lost licenses and opportunities.

        Args:
            current_month_df: Current month's data
            previous_month_df: Previous month's data
            all_historical_df: All historical data for comparison
            skip_lost_licenses: If True, skip lost license processing (useful for test mode)
        """
        
        # Create unique identifiers
        current_month_df = current_month_df.copy()
        previous_month_df = previous_month_df.copy()
        
        # Debug logging
        current_provider_types = current_month_df['PROVIDER TYPE'].unique() if not current_month_df.empty else []
        logger.info(f"Current month provider types: {list(current_provider_types)}")
        
        previous_provider_types = previous_month_df['PROVIDER TYPE'].unique() if not previous_month_df.empty else []
        logger.info(f"Previous month provider types: {list(previous_provider_types)}")
        
        # Key is (PROVIDER TYPE, PROVIDER, ADDRESS)
        current_month_df['KEY'] = (
            current_month_df['PROVIDER TYPE'].astype(str) + '|' +
            current_month_df['PROVIDER'].astype(str) + '|' +
            current_month_df['ADDRESS'].astype(str)
        )
        
        if not previous_month_df.empty:
            previous_month_df['KEY'] = (
                previous_month_df['PROVIDER TYPE'].astype(str) + '|' +
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
                    record['THIS MONTH STATUS'] = 'EXISTING PROVIDER TYPE, NEW ADDRESS'
                else:
                    record['THIS MONTH STATUS'] = 'EXISTING PROVIDER TYPE, EXISTING ADDRESS'
            else:
                # New provider type at this address
                if address not in all_historical_addresses:
                    record['THIS MONTH STATUS'] = 'NEW PROVIDER TYPE, NEW ADDRESS'
                else:
                    record['THIS MONTH STATUS'] = 'NEW PROVIDER TYPE, EXISTING ADDRESS'
            
            # Assign lead type
            record['LEAD TYPE'] = self.status_to_lead_type.get(record['THIS MONTH STATUS'], '')
            
            # Remove the KEY field
            del record['KEY']
            
            analysis_records.append(record)

        # Now check for lost licenses (in previous but not current)
        if not previous_month_df.empty and not skip_lost_licenses:
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
                        lost_record['THIS MONTH STATUS'] = 'LOST PROVIDER TYPE, LOST ADDRESS (0 REMAIN)'
                    else:
                        lost_record['THIS MONTH STATUS'] = 'LOST PROVIDER TYPE, LOST ADDRESS (1+ REMAIN)'
                else:
                    lost_record['THIS MONTH STATUS'] = 'LOST PROVIDER TYPE, EXISTING ADDRESS'
                
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
            'SOLO PROVIDER TYPE PROVIDER [Y, #]',
            'PROVIDER GROUP (DBA CONCAT)',
            'PROVIDER GROUP, ADDRESS COUNT'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = 'N/A'
        
        # Get group information
        group_info = {}
        
        for group_id in df['PROVIDER GROUP INDEX #'].unique():
            group_df = df[df['PROVIDER GROUP INDEX #'] == group_id]
            
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
            group_id = row['PROVIDER GROUP INDEX #']
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
                df.at[idx, 'SOLO PROVIDER TYPE PROVIDER [Y, #]'] = 'Y'
            else:
                df.at[idx, 'SOLO PROVIDER TYPE PROVIDER [Y, #]'] = str(len(providers_at_address))
        
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
            counts = month_df.groupby(['PROVIDER', 'PROVIDER TYPE'])['ADDRESS'].count()
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
                key = (row['PROVIDER'], row['PROVIDER TYPE'])
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
    
    def calculate_enhanced_tracking_fields(self, df: pd.DataFrame, previous_month_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate enhanced tracking fields (columns EH-EY) per v300Track_this.md.

        These fields include:
        - EH: PREVIOUS_MONTH_STATUS
        - EI: STATUS_CONFIDENCE
        - EJ: PROVIDER_TYPES_GAINED
        - EK: PROVIDER_TYPES_LOST
        - EL: NET_TYPE_CHANGE
        - EM: MONTHS_SINCE_LOST
        - EN: REINSTATED_FLAG
        - EO: REINSTATED_DATE
        - EP: DATA_QUALITY_SCORE
        - EQ: MANUAL_REVIEW_FLAG
        - ER: REVIEW_NOTES
        - ES: LAST_ACTIVE_MONTH
        - ET: REGIONAL_MARKET
        - EU: HISTORICAL_STABILITY_SCORE
        - EV: EXPANSION_VELOCITY
        - EW: CONTRACTION_RISK
        - EX: MULTI_CITY_OPERATOR
        - EY: RELOCATION_FLAG
        """
        df = df.copy()

        # Check if previous month data is available
        has_prev = not previous_month_df.empty if isinstance(previous_month_df, pd.DataFrame) else False

        # EH: PREVIOUS_MONTH_STATUS - lookup from previous month
        if has_prev and 'THIS MONTH STATUS' in previous_month_df.columns:
            # Create a lookup key
            prev_lookup = {}
            for _, row in previous_month_df.iterrows():
                key = f"{row.get('PROVIDER', '')}|{row.get('PROVIDER TYPE', '')}|{row.get('FULL_ADDRESS', row.get('ADDRESS', ''))}"
                prev_lookup[key] = row.get('THIS MONTH STATUS', '')

            def get_prev_status(row):
                key = f"{row.get('PROVIDER', '')}|{row.get('PROVIDER TYPE', '')}|{row.get('FULL_ADDRESS', row.get('ADDRESS', ''))}"
                return prev_lookup.get(key, 'No Prev Month Found')

            df['PREVIOUS_MONTH_STATUS'] = df.apply(get_prev_status, axis=1)
        else:
            df['PREVIOUS_MONTH_STATUS'] = 'No Prev Month Found'

        # EI: STATUS_CONFIDENCE - based on data completeness
        def calc_confidence(row):
            score = 100
            if pd.isna(row.get('PROVIDER', '')) or row.get('PROVIDER', '') == '':
                score -= 30
            if pd.isna(row.get('FULL_ADDRESS', row.get('ADDRESS', ''))) or row.get('FULL_ADDRESS', row.get('ADDRESS', '')) == '':
                score -= 25
            if pd.isna(row.get('COUNTY', '')) or row.get('COUNTY', '') == '':
                score -= 5
            if pd.isna(row.get('PROVIDER GROUP INDEX #', '')) or row.get('PROVIDER GROUP INDEX #', '') == '':
                score -= 10
            if row.get('PREVIOUS_MONTH_STATUS', '') == 'No Prev Month Found':
                score -= 20

            if score >= 80:
                return 'High'
            elif score >= 50:
                return 'Medium'
            else:
                return 'Low'

        df['STATUS_CONFIDENCE'] = df.apply(calc_confidence, axis=1)

        # EJ-EL: Provider type changes (simplified for now)
        df['PROVIDER_TYPES_GAINED'] = 'No Prev Month Found' if not has_prev else ''
        df['PROVIDER_TYPES_LOST'] = 'No Prev Month Found' if not has_prev else ''
        df['NET_TYPE_CHANGE'] = 'No Prev Month Found' if not has_prev else '0'

        # EM: MONTHS_SINCE_LOST
        df['MONTHS_SINCE_LOST'] = ''

        # EN: REINSTATED_FLAG
        df['REINSTATED_FLAG'] = 'N'

        # EO: REINSTATED_DATE
        df['REINSTATED_DATE'] = ''

        # EP: DATA_QUALITY_SCORE
        def calc_quality_score(row):
            required_fields = ['PROVIDER', 'PROVIDER TYPE', 'FULL_ADDRESS', 'COUNTY', 'ZIP', 'PROVIDER GROUP INDEX #']
            optional_fields = ['CAPACITY', 'LONGITUDE', 'LATITUDE']

            score = 0
            for field in required_fields:
                alt_field = 'ADDRESS' if field == 'FULL_ADDRESS' else field
                val = row.get(field, row.get(alt_field, ''))
                if not pd.isna(val) and val != '':
                    score += 15

            for field in optional_fields:
                val = row.get(field, '')
                if not pd.isna(val) and val != '':
                    score += 3.33

            return round(score)

        df['DATA_QUALITY_SCORE'] = df.apply(calc_quality_score, axis=1)

        # EQ: MANUAL_REVIEW_FLAG
        def calc_review_flag(row):
            if row.get('STATUS_CONFIDENCE', '') == 'Low':
                return 'Y'
            if row.get('DATA_QUALITY_SCORE', 100) < 70:
                return 'Y'
            return 'N'

        df['MANUAL_REVIEW_FLAG'] = df.apply(calc_review_flag, axis=1)

        # ER: REVIEW_NOTES
        df['REVIEW_NOTES'] = ''

        # ES: LAST_ACTIVE_MONTH
        df['LAST_ACTIVE_MONTH'] = ''

        # ET: REGIONAL_MARKET
        def calc_regional_market(row):
            county = str(row.get('COUNTY', '')).upper()
            if county in ('MARICOPA', 'PINAL'):
                return 'Phoenix Metro'
            elif county == 'PIMA':
                return 'Tucson Metro'
            elif county in ('COCONINO', 'YAVAPAI'):
                return 'Northern AZ'
            else:
                return 'Rural/Other'

        df['REGIONAL_MARKET'] = df.apply(calc_regional_market, axis=1)

        # EU: HISTORICAL_STABILITY_SCORE (placeholder - requires historical data)
        df['HISTORICAL_STABILITY_SCORE'] = ''

        # EV: EXPANSION_VELOCITY (placeholder - requires 6-month historical data)
        df['EXPANSION_VELOCITY'] = ''

        # EW: CONTRACTION_RISK
        df['CONTRACTION_RISK'] = 'Low'

        # EX: MULTI_CITY_OPERATOR
        if 'PROVIDER GROUP INDEX #' in df.columns and 'CITY' in df.columns:
            # Group by provider group and count unique cities
            city_counts = df.groupby('PROVIDER GROUP INDEX #')['CITY'].nunique()
            df['MULTI_CITY_OPERATOR'] = df['PROVIDER GROUP INDEX #'].map(
                lambda x: 'Y' if city_counts.get(x, 1) > 1 else 'N'
            )
        else:
            df['MULTI_CITY_OPERATOR'] = 'N'

        # EY: RELOCATION_FLAG
        df['RELOCATION_FLAG'] = 'No Prev Month Found' if not has_prev else 'N'

        return df

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
                   'PROVIDER GROUP INDEX #' in df.columns:
                    # Create summary concatenation
                    df[summary_col] = df.apply(
                        lambda row: f"{row['PROVIDER GROUP, ADDRESS COUNT']}, "
                                   f"{row['PROVIDER GROUP (DBA CONCAT)']}, "
                                   f"{row['PROVIDER GROUP INDEX #']}",
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
        """Ensure all 155 columns from v300Track_this.xlsx are present in the analysis output.

        Column structure (155 total):
        - A-P: Core identification fields (16 columns)
        - Q-BD: Monthly COUNT fields (40 columns: 9.24 through 12.27)
        - BE-CQ: Monthly TO PREV fields (39 columns: 10.24 through 12.27)
        - CR-EE: Monthly SUMMARY fields (40 columns: 9.24 through 12.27)
        - EF-EG: MONTH, YEAR (2 columns)
        - EH-EY: Enhanced tracking fields (18 columns)
        """
        df = df.copy()

        # Use processing month/year for reference
        reference_month = processing_month if processing_month is not None else 9
        reference_year = processing_year if processing_year is not None else 2024

        # Generate month list from 9.24 through 12.27 (40 months)
        def generate_month_codes():
            months = []
            year = 24
            month = 9
            while year < 28:  # Stop before 2028
                months.append(f"{month}.{year}")
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            return months

        month_codes = generate_month_codes()

        # Build expected columns list (155 columns total)
        expected_columns = [
            # A-P: Core identification fields (16 columns)
            'SOLO PROVIDER TYPE PROVIDER [Y, #]',  # A
            'PROVIDER TYPE',  # B
            'PROVIDER',  # C
            'ADDRESS',  # D
            'CITY',  # E
            'ZIP',  # F
            'FULL_ADDRESS',  # G
            'CAPACITY',  # H
            'LONGITUDE',  # I
            'LATITUDE',  # J
            'COUNTY',  # K
            'PROVIDER GROUP INDEX #',  # L
            'PROVIDER GROUP (DBA CONCAT)',  # M
            'PROVIDER GROUP, ADDRESS COUNT',  # N
            'THIS MONTH STATUS',  # O
            'LEAD TYPE',  # P
        ]

        # Q-BD: Monthly COUNT columns (40 columns)
        for mc in month_codes:
            expected_columns.append(f'{mc} COUNT')

        # BE-CQ: Monthly TO PREV columns (39 columns - starts from 10.24)
        for mc in month_codes[1:]:  # Skip first month (9.24)
            expected_columns.append(f'{mc} TO PREV')

        # CR-EE: Monthly SUMMARY columns (40 columns)
        for mc in month_codes:
            expected_columns.append(f'{mc} SUMMARY')

        # EF-EG: Metadata (2 columns)
        expected_columns.extend(['MONTH', 'YEAR'])

        # EH-EY: Enhanced tracking fields (18 columns)
        enhanced_tracking_cols = [
            'PREVIOUS_MONTH_STATUS',  # EH
            'STATUS_CONFIDENCE',  # EI
            'PROVIDER_TYPES_GAINED',  # EJ
            'PROVIDER_TYPES_LOST',  # EK
            'NET_TYPE_CHANGE',  # EL
            'MONTHS_SINCE_LOST',  # EM
            'REINSTATED_FLAG',  # EN
            'REINSTATED_DATE',  # EO
            'DATA_QUALITY_SCORE',  # EP
            'MANUAL_REVIEW_FLAG',  # EQ
            'REVIEW_NOTES',  # ER
            'LAST_ACTIVE_MONTH',  # ES
            'REGIONAL_MARKET',  # ET
            'HISTORICAL_STABILITY_SCORE',  # EU
            'EXPANSION_VELOCITY',  # EV
            'CONTRACTION_RISK',  # EW
            'MULTI_CITY_OPERATOR',  # EX
            'RELOCATION_FLAG',  # EY
        ]
        expected_columns.extend(enhanced_tracking_cols)

        # Construct FULL_ADDRESS from ADDRESS + CITY + ZIP if not present or empty
        if 'FULL_ADDRESS' not in df.columns or df['FULL_ADDRESS'].isna().all() or (df['FULL_ADDRESS'] == '').all():
            if all(col in df.columns for col in ['ADDRESS', 'CITY', 'ZIP']):
                def build_full_address(row):
                    parts = []
                    addr = str(row.get('ADDRESS', '')).strip()
                    city = str(row.get('CITY', '')).strip()

                    # FIX: Convert ZIP from float to int to remove .0 suffix
                    zip_raw = row.get('ZIP', '')
                    try:
                        zip_code = str(int(float(zip_raw))).strip()
                    except (ValueError, TypeError):
                        zip_code = str(zip_raw).strip()

                    if addr and addr.upper() not in ('NAN', 'NONE', ''):
                        parts.append(addr)
                    if city and city.upper() not in ('NAN', 'NONE', ''):
                        parts.append(city)

                    # Add "AZ ZIP" as a single part (no comma between state and ZIP)
                    if zip_code and zip_code.upper() not in ('NAN', 'NONE', ''):
                        if city or addr:  # Only add AZ+ZIP if we have address components
                            parts.append(f'AZ {zip_code}')
                        else:
                            parts.append(zip_code)

                    return ', '.join(parts) if parts else ''

                df['FULL_ADDRESS'] = df.apply(build_full_address, axis=1)

        # Add any missing columns with appropriate default values
        for col in expected_columns:
            if col not in df.columns:
                # Determine appropriate default value based on column type
                if col.endswith(' COUNT'):
                    try:
                        month_year = col.replace(' COUNT', '')
                        m, y = month_year.split('.')
                        m = int(m)
                        y = 2000 + int(y)

                        if (y < reference_year) or (y == reference_year and m <= reference_month):
                            df[col] = 0
                        else:
                            df[col] = ''
                    except:
                        df[col] = ''

                elif col.endswith(' TO PREV'):
                    try:
                        month_year = col.replace(' TO PREV', '')
                        m, y = month_year.split('.')
                        m = int(m)
                        y = 2000 + int(y)

                        if (y < reference_year) or (y == reference_year and m <= reference_month):
                            df[col] = ''
                        else:
                            df[col] = ''
                    except:
                        df[col] = ''

                elif col.endswith(' SUMMARY'):
                    df[col] = ''

                elif col in enhanced_tracking_cols:
                    # Enhanced tracking fields - use appropriate defaults
                    if col in ('REINSTATED_FLAG', 'MULTI_CITY_OPERATOR'):
                        df[col] = 'N'
                    elif col == 'CONTRACTION_RISK':
                        df[col] = 'Low'
                    elif col == 'STATUS_CONFIDENCE':
                        df[col] = 'Medium'
                    elif col == 'DATA_QUALITY_SCORE':
                        df[col] = 0
                    else:
                        df[col] = ''

                else:
                    df[col] = ''

        # Reorder columns to match expected order
        final_columns = [col for col in expected_columns if col in df.columns]

        # Add any extra columns that weren't in expected list at the end
        extra_cols = [col for col in df.columns if col not in expected_columns]
        final_columns.extend(extra_cols)

        return df[final_columns]


def create_analysis_summary_sheet(analysis_df: pd.DataFrame, current_month_df: pd.DataFrame = None) -> pd.DataFrame:
    """Create the summary sheet with counts.

    Args:
        analysis_df: The analysis DataFrame
        current_month_df: Optional current month Reformat data (for v300 compliance)
    """
    summary_data = []

    # Use current_month_df for counts if provided, otherwise use analysis_df
    count_df = current_month_df if current_month_df is not None else analysis_df

    # Count basic metrics
    total_addresses = count_df['ADDRESS'].nunique() if 'ADDRESS' in count_df.columns else analysis_df['ADDRESS'].nunique()
    total_providers = analysis_df['PROVIDER'].nunique()
    total_provider_groups = analysis_df['PROVIDER GROUP INDEX #'].nunique() if 'PROVIDER GROUP INDEX #' in analysis_df else 0
    total_blanks = analysis_df.isnull().sum().sum()
    total_solo_providers = len(analysis_df[analysis_df.get('SOLO PROVIDER TYPE PROVIDER [Y, #]', '') == 'Y'])
    
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
    provider_type_counts = analysis_df['PROVIDER TYPE'].value_counts() if 'PROVIDER TYPE' in analysis_df else {}
    total_record_count = len(analysis_df)
    
    # Create the exact template structure
    summary_data = [
        ['Total ADDRESS', total_addresses],
        ['Total PROVIDER', total_providers],
        ['Total PROVIDER GROUP', total_provider_groups],
        ['Total Blanks', total_blanks],
        ['Total SOLO PROVIDER TYPE PROVIDER', total_solo_providers],
        ['', ''],  # Empty row
        ['New PROVIDER TYPE, New ADDRESS', new_provider_new_address],
        ['New PROVIDER TYPE, Existing ADDRESS', new_provider_existing_address],
        ['Existing PROVIDER TYPE, New ADDRESS', existing_provider_new_address],
        ['Existing PROVIDER TYPE, Existing ADDRESS', existing_provider_existing_address],
        ['Lost PROVIDER TYPE, Existing ADDRESS', lost_provider_existing_address],
        ['Lost PROVIDER TYPE, Lost ADDRESS (0 remain)', lost_provider_lost_address_0],
        ['Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)', lost_provider_lost_address_1],
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


def create_blanks_count_sheet(current_month_df: pd.DataFrame, month_num: int = None, year_num: int = None) -> pd.DataFrame:
    """Create the blanks count sheet by provider type.

    Args:
        current_month_df: Current month's Reformat data
        month_num: Optional month number (for v300 compliance)
        year_num: Optional year number (for v300 compliance)
    """
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
        type_df = current_month_df[current_month_df['PROVIDER TYPE'] == provider_type]
        
        if type_df.empty:
            # No data for this provider type
            blanks_data.append({
                'PROVIDER TYPE': provider_type,
                'MONTH': 0,
                'YEAR': 0,
                'PROVIDER': 0,
                'ADDRESS': 0,
                'CITY': 0,
                'ZIP': 0,
                'CAPACITY': 0,
                'LONGITUDE': 0,
                'LATITUDE': 0,
                'PROVIDER GROUP INDEX #': 0
            })
        else:
            # Count blanks in each field
            row_data = {'PROVIDER TYPE': provider_type}
            
            fields = ['MONTH', 'YEAR', 'PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 
                     'CAPACITY', 'LONGITUDE', 'LATITUDE', 'PROVIDER GROUP INDEX #']
            
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