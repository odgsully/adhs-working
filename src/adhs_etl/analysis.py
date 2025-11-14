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
            'NEW PROVIDER TYPE, NEW ADDRESS': 'Survey Lead',
            'NEW PROVIDER TYPE, EXISTING ADDRESS': 'Survey Lead',
            'EXISTING PROVIDER TYPE, NEW ADDRESS': 'Survey Lead',
            'EXISTING PROVIDER TYPE, EXISTING ADDRESS': 'Survey Lead',  # Changed from '' to 'Survey Lead'
            'LOST PROVIDER TYPE, EXISTING ADDRESS': 'Seller/Survey Lead',
            'LOST PROVIDER TYPE, LOST ADDRESS (0 remain)': 'Seller Lead',
            'LOST PROVIDER TYPE, LOST ADDRESS (1+ remain)': 'Seller Lead',
            'REINSTATED PROVIDER TYPE, EXISTING ADDRESS': 'Survey Lead'
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
            current_month_df: Current month data
            previous_month_df: Previous month data
            all_historical_df: All historical data
            skip_lost_licenses: If True, skip lost license detection (useful for test mode)
        """
        
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
                    record['THIS_MONTH_STATUS'] = 'EXISTING PROVIDER TYPE, NEW ADDRESS'
                else:
                    record['THIS_MONTH_STATUS'] = 'EXISTING PROVIDER TYPE, EXISTING ADDRESS'
            else:
                # Check if this is a reinstated provider (existed historically but not in previous month)
                # This requires checking all historical data for this key
                is_reinstated = False
                if not all_historical_df.empty and key not in prev_keys:
                    # Only create KEY column if it doesn't exist
                    if 'KEY' not in all_historical_df.columns:
                        all_historical_df['KEY'] = (
                            all_historical_df['PROVIDER_TYPE'].astype(str) + '|' +
                            all_historical_df['PROVIDER'].astype(str) + '|' +
                            all_historical_df['ADDRESS'].astype(str)
                        )
                    historical_keys = set(all_historical_df['KEY'])

                    if key in historical_keys:
                        # This combo existed historically but was lost, now reinstated
                        is_reinstated = True
                        record['THIS_MONTH_STATUS'] = 'REINSTATED PROVIDER TYPE, EXISTING ADDRESS'

                if not is_reinstated:
                    # New provider type at this address
                    if address not in all_historical_addresses:
                        record['THIS_MONTH_STATUS'] = 'NEW PROVIDER TYPE, NEW ADDRESS'
                    else:
                        record['THIS_MONTH_STATUS'] = 'NEW PROVIDER TYPE, EXISTING ADDRESS'
            
            # Assign lead type
            record['LEAD_TYPE'] = self.status_to_lead_type.get(record['THIS_MONTH_STATUS'], '')
            
            # Remove the KEY field
            del record['KEY']
            
            analysis_records.append(record)
        
        # Now check for lost licenses (in previous but not current)
        # Skip this in test mode to avoid bloating the dataset
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
                        lost_record['THIS_MONTH_STATUS'] = 'LOST PROVIDER TYPE, LOST ADDRESS (0 remain)'
                    else:
                        lost_record['THIS_MONTH_STATUS'] = 'LOST PROVIDER TYPE, LOST ADDRESS (1+ remain)'
                else:
                    lost_record['THIS_MONTH_STATUS'] = 'LOST PROVIDER TYPE, EXISTING ADDRESS'
                
                # Assign lead type
                lost_record['LEAD_TYPE'] = self.status_to_lead_type.get(lost_record['THIS_MONTH_STATUS'], '')
                
                # Remove the KEY field
                del lost_record['KEY']

                analysis_records.append(lost_record)

        # Create the base analysis DataFrame
        analysis_df = pd.DataFrame(analysis_records)

        # Add monthly counts and movement columns
        # Combine historical and current month data for complete counts
        if not current_month_df.empty:
            current_month = current_month_df.iloc[0]['MONTH'] if 'MONTH' in current_month_df.columns else None
            current_year = current_month_df.iloc[0]['YEAR'] if 'YEAR' in current_month_df.columns else None

            # Combine historical with current month for complete tracking
            if not all_historical_df.empty:
                combined_for_counts = pd.concat([all_historical_df, current_month_df], ignore_index=True)
            else:
                combined_for_counts = current_month_df

            # Create monthly counts from combined data
            months_data = self.create_monthly_counts(combined_for_counts, current_month, current_year)

            # Add count and movement columns
            if months_data:
                analysis_df = self.create_movement_columns(analysis_df, months_data)
                # Note: create_summary_columns() must be called AFTER calculate_provider_groups()
                # because it needs PROVIDER_GROUP,_ADDRESS_COUNT and PROVIDER_GROUP_(DBA_Concat) columns

        return analysis_df
    
    def calculate_provider_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate provider group information."""
        df = df.copy()
        
        # Ensure all required columns exist (v300 exact names)
        required_columns = [
            'SOLO_PROVIDER_TYPE_PROVIDER_[Y,#]',
            'PROVIDER_GROUP_(DBA_CONCAT)',
            'PROVIDER_GROUP,_ADDRESS_COUNT'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''  # FIXED: Use empty string instead of pd.NA to prevent column dropping
        
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
                df.at[idx, 'PROVIDER_GROUP_(DBA_CONCAT)'] = ', '.join(other_providers)
            else:
                df.at[idx, 'PROVIDER_GROUP_(DBA_CONCAT)'] = ''  # FIXED: Use empty string instead of pd.NA to prevent column dropping

            df.at[idx, 'PROVIDER_GROUP,_ADDRESS_COUNT'] = info['address_count']
            
            # Check if solo provider - a provider is solo if it's the only provider at that address
            providers_at_address = df[df['ADDRESS'] == row['ADDRESS']]['PROVIDER'].unique()
            
            if len(providers_at_address) == 1:
                df.at[idx, 'SOLO_PROVIDER_TYPE_PROVIDER_[Y,#]'] = 'Y'
            else:
                df.at[idx, 'SOLO_PROVIDER_TYPE_PROVIDER_[Y,#]'] = str(len(providers_at_address))
        
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
            # Format column name with underscore for v300 compliance
            if month >= 10:
                col_name = f"{month}.{year % 100}_COUNT"
            else:
                col_name = f"{month}.{year % 100}_COUNT"
            
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
            int(x.split('.')[1].split('_')[0]),  # year (remove "_COUNT" suffix)
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
            
            # Extract month number for column name with underscore for v300 compliance
            month_num = curr_month.split('.')[0]
            year_num = curr_month.split('.')[1].split('_')[0]  # Remove "_COUNT" suffix

            if int(month_num) >= 10:
                movement_col = f"{month_num}.{year_num}_TO_PREV"
            else:
                movement_col = f"{month_num}.{year_num}_TO_PREV"
            
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
        count_cols = [col for col in df.columns if col.endswith('_COUNT')]

        for count_col in count_cols:
            try:
                # Extract month/year for summary column name
                parts = count_col.replace('_COUNT', '').split('.')
                if len(parts) < 2:
                    continue
                    
                month = parts[0]
                year = parts[1]
                
                if int(month) >= 10:
                    summary_col = f"{month}.{year}_SUMMARY"
                else:
                    summary_col = f"{month}.{year}_SUMMARY"
                
                # Check if required columns exist (using v300 exact names)
                if 'PROVIDER_GROUP,_ADDRESS_COUNT' in df.columns and \
                   'PROVIDER_GROUP_(DBA_CONCAT)' in df.columns:
                    # Create summary concatenation (just Column N and M, per user requirement)
                    df[summary_col] = df.apply(
                        lambda row: f"{row['PROVIDER_GROUP,_ADDRESS_COUNT']}, {row['PROVIDER_GROUP_(DBA_CONCAT)']}",
                        axis=1
                    )
                else:
                    # If columns don't exist, use default
                    df[summary_col] = "N/A, N/A"
            except Exception as e:
                logger.warning(f"Error creating summary column for {count_col}: {e}")
                continue
        
        return df

    def calculate_enhanced_tracking_fields(self, df: pd.DataFrame, previous_month_df: pd.DataFrame = None) -> pd.DataFrame:
        """Calculate all enhanced tracking fields (Columns EH-EY) for v300."""
        df = df.copy()

        # EH: PREVIOUS_MONTH_STATUS
        if previous_month_df is not None and not previous_month_df.empty and 'THIS_MONTH_STATUS' in previous_month_df.columns:
            # Create lookup based on provider+address
            prev_status_map = {}
            for _, row in previous_month_df.iterrows():
                key = f"{row.get('PROVIDER', '')}|{row.get('ADDRESS', '')}"
                prev_status_map[key] = row.get('THIS_MONTH_STATUS', '')

            df['PREVIOUS_MONTH_STATUS'] = df.apply(
                lambda row: prev_status_map.get(f"{row.get('PROVIDER', '')}|{row.get('ADDRESS', '')}", ''),
                axis=1
            )
        else:
            df['PREVIOUS_MONTH_STATUS'] = ''

        # EI: STATUS_CONFIDENCE
        def calculate_confidence(row):
            score = 100
            if pd.isna(row.get('PROVIDER', '')) or row.get('PROVIDER', '') == '':
                score -= 30
            if pd.isna(row.get('FULL_ADDRESS', '')) or row.get('FULL_ADDRESS', '') == '':
                score -= 25
            if pd.isna(row.get('COUNTY', '')) or row.get('COUNTY', '') == '':
                score -= 5
            if pd.isna(row.get('PROVIDER_GROUP_INDEX_#', '')):
                score -= 10
            if row.get('PREVIOUS_MONTH_STATUS', '') == '':
                score -= 20

            if score >= 80:
                return 'High'
            elif score >= 50:
                return 'Medium'
            else:
                return 'Low'

        df['STATUS_CONFIDENCE'] = df.apply(calculate_confidence, axis=1)

        # Prepare provider type sets for comparison (used by both GAINED and LOST)
        if previous_month_df is not None and not previous_month_df.empty:
            # Get unique provider types for each provider in both months
            current_provider_types = df.groupby('PROVIDER')['PROVIDER_TYPE'].apply(set).to_dict()
            prev_provider_types = previous_month_df.groupby('PROVIDER')['PROVIDER_TYPE'].apply(set).to_dict()
        else:
            current_provider_types = {}
            prev_provider_types = {}

        # EJ: PROVIDER_TYPES_GAINED
        # Compare provider types between current and previous month
        if previous_month_df is not None and not previous_month_df.empty:
            def get_types_gained(row):
                provider = row['PROVIDER']
                if provider in prev_provider_types:
                    current_types = current_provider_types.get(provider, set())
                    prev_types = prev_provider_types.get(provider, set())
                    gained = current_types - prev_types
                    if gained:
                        return ', '.join(sorted(gained))
                return ''

            df['PROVIDER_TYPES_GAINED'] = df.apply(get_types_gained, axis=1)
        else:
            df['PROVIDER_TYPES_GAINED'] = ''

        # EK: PROVIDER_TYPES_LOST
        # For PROVIDER_TYPES_LOST, we need to check the previous month data for providers that had types
        if previous_month_df is not None and not previous_month_df.empty:
            # Create a mapping of providers to their lost types
            lost_types_map = {}

            # Check each provider in the previous month
            for provider, prev_types in prev_provider_types.items():
                current_types = current_provider_types.get(provider, set())
                lost = prev_types - current_types
                if lost:
                    lost_types_map[provider] = ', '.join(sorted(lost))

            # Apply to dataframe
            df['PROVIDER_TYPES_LOST'] = df['PROVIDER'].map(lost_types_map).fillna('')
        else:
            df['PROVIDER_TYPES_LOST'] = ''

        # EL: NET_TYPE_CHANGE
        df['NET_TYPE_CHANGE'] = 0

        # EM: MONTHS_SINCE_LOST
        df['MONTHS_SINCE_LOST'] = df.apply(
            lambda row: 1 if 'LOST' in str(row.get('THIS_MONTH_STATUS', '')) else 0,
            axis=1
        )

        # EN: REINSTATED_FLAG
        df['REINSTATED_FLAG'] = df.apply(
            lambda row: 'Y' if 'REINSTATED' in str(row.get('THIS_MONTH_STATUS', '')) else 'N',
            axis=1
        )

        # EO: REINSTATED_DATE
        df['REINSTATED_DATE'] = ''

        # EP: DATA_QUALITY_SCORE
        def calculate_quality_score(row):
            score = 0
            # Required fields (60 points)
            if not pd.isna(row.get('PROVIDER', '')) and row.get('PROVIDER', '') != '':
                score += 10
            if not pd.isna(row.get('PROVIDER_TYPE', '')) and row.get('PROVIDER_TYPE', '') != '':
                score += 10
            if not pd.isna(row.get('FULL_ADDRESS', '')) and row.get('FULL_ADDRESS', '') != '':
                score += 10
            if not pd.isna(row.get('COUNTY', '')) and row.get('COUNTY', '') != '':
                score += 10
            if not pd.isna(row.get('ZIP', '')) and row.get('ZIP', '') != '':
                score += 10
            if not pd.isna(row.get('PROVIDER_GROUP_INDEX_#', '')):
                score += 10

            # Optional fields (40 points)
            if not pd.isna(row.get('CAPACITY', '')):
                score += 13
            if not pd.isna(row.get('LONGITUDE', '')):
                score += 13
            if not pd.isna(row.get('LATITUDE', '')):
                score += 14

            return score

        df['DATA_QUALITY_SCORE'] = df.apply(calculate_quality_score, axis=1)

        # EQ: MANUAL_REVIEW_FLAG
        df['MANUAL_REVIEW_FLAG'] = df.apply(
            lambda row: 'Y' if (
                row.get('STATUS_CONFIDENCE', '') == 'Low' or
                row.get('DATA_QUALITY_SCORE', 0) < 70 or
                (row.get('REINSTATED_FLAG', '') == 'Y' and row.get('MONTHS_SINCE_LOST', 0) > 12)
            ) else 'N',
            axis=1
        )

        # ER: REVIEW_NOTES
        df['REVIEW_NOTES'] = ''

        # ES: LAST_ACTIVE_MONTH
        df['LAST_ACTIVE_MONTH'] = ''

        # ET: REGIONAL_MARKET
        def get_regional_market(county):
            if pd.isna(county):
                return ''
            county_upper = str(county).upper()
            if county_upper in ['MARICOPA', 'PINAL']:
                return 'Phoenix Metro'
            elif county_upper == 'PIMA':
                return 'Tucson Metro'
            elif county_upper in ['COCONINO', 'YAVAPAI']:
                return 'Northern Arizona'
            elif county_upper in ['MOHAVE', 'LA PAZ', 'YUMA']:
                return 'Western Arizona'
            elif county_upper in ['COCHISE', 'SANTA CRUZ']:
                return 'Southern Border'
            elif county_upper in ['APACHE', 'NAVAJO']:
                return 'Native Regions'
            elif county_upper in ['GILA', 'GRAHAM', 'GREENLEE']:
                return 'Eastern Arizona'
            else:
                return 'Other'

        df['REGIONAL_MARKET'] = df['COUNTY'].apply(get_regional_market)

        # EU: HISTORICAL_STABILITY_SCORE (simplified - count non-zero months)
        count_cols = [col for col in df.columns if col.endswith('_COUNT') and not 'ADDRESS' in col]
        if count_cols:
            df['HISTORICAL_STABILITY_SCORE'] = df[count_cols].apply(
                lambda row: (row > 0).sum() / len(count_cols) * 100 if len(count_cols) > 0 else 0,
                axis=1
            )
        else:
            df['HISTORICAL_STABILITY_SCORE'] = 0

        # EV: EXPANSION_VELOCITY
        df['EXPANSION_VELOCITY'] = 0  # Would need trend analysis

        # EW: CONTRACTION_RISK
        df['CONTRACTION_RISK'] = 0  # Would need trend analysis

        # EX: MULTI_CITY_OPERATOR
        # Check if provider group operates in multiple cities
        city_counts = df.groupby('PROVIDER_GROUP_INDEX_#')['CITY'].nunique()
        multi_city_map = (city_counts > 1).to_dict()
        df['MULTI_CITY_OPERATOR'] = df['PROVIDER_GROUP_INDEX_#'].map(multi_city_map).fillna(False)
        df['MULTI_CITY_OPERATOR'] = df['MULTI_CITY_OPERATOR'].apply(lambda x: 'Y' if x else 'N')

        # EY: RELOCATION_FLAG
        df['RELOCATION_FLAG'] = df.apply(
            lambda row: 'Y' if (
                'NEW ADDRESS' in str(row.get('THIS_MONTH_STATUS', '')) and
                'EXISTING PROVIDER' in str(row.get('THIS_MONTH_STATUS', ''))
            ) else 'N',
            axis=1
        )

        return df

    def ensure_all_analysis_columns(self, df: pd.DataFrame, processing_month: int = None, processing_year: int = None) -> pd.DataFrame:
        """
        Ensure all columns from v300Track_this.xlsx as defined in v300Track_this.md are present in the analysis output.
        Optimized to use pd.concat for better performance and avoid DataFrame fragmentation.
        """
        df = df.copy()

        # Keep internal column names (with underscores) as they match v300Track_this.xlsx exactly

        # Define the complete set of columns expected in analysis output (150+ columns to match v300Track_this.xlsx)
        # Use internal names here, will rename at the end
        # Columns A-P according to v300Track_this.md
        expected_columns_internal = [
            # Core provider data (Columns A-P) - EXACT v300 order
            'SOLO_PROVIDER_TYPE_PROVIDER_[Y,#]',  # Column A - EXACT v300 match
            'PROVIDER_TYPE',                        # Column B - Internal name with underscore
            'PROVIDER',                             # Column C
            'ADDRESS',                              # Column D
            'CITY',                                 # Column E
            'ZIP',                                  # Column F
            'FULL_ADDRESS',                         # Column G - Internal name with underscore
            'CAPACITY',                             # Column H
            'LONGITUDE',                            # Column I
            'LATITUDE',                             # Column J
            'COUNTY',                               # Column K
            'PROVIDER_GROUP_INDEX_#',               # Column L - Internal name with underscore
            'PROVIDER_GROUP_(DBA_CONCAT)',          # Column M - EXACT v300 match
            'PROVIDER_GROUP,_ADDRESS_COUNT',        # Column N - EXACT v300 match
            'THIS_MONTH_STATUS',                    # Column O - EXACT v300 match
            'LEAD_TYPE',                            # Column P - EXACT v300 match

            # Extended Monthly counts (Columns Q-BD) - exactly 40 columns starting from actual data (9.24)
            '9.24_COUNT', '10.24_COUNT', '11.24_COUNT', '12.24_COUNT',
            '1.25_COUNT', '2.25_COUNT', '3.25_COUNT', '4.25_COUNT',
            '5.25_COUNT', '6.25_COUNT', '7.25_COUNT', '8.25_COUNT',
            '9.25_COUNT', '10.25_COUNT', '11.25_COUNT', '12.25_COUNT',
            '1.26_COUNT', '2.26_COUNT', '3.26_COUNT', '4.26_COUNT',
            '5.26_COUNT', '6.26_COUNT', '7.26_COUNT', '8.26_COUNT',
            '9.26_COUNT', '10.26_COUNT', '11.26_COUNT', '12.26_COUNT',
            '1.27_COUNT', '2.27_COUNT', '3.27_COUNT', '4.27_COUNT',
            '5.27_COUNT', '6.27_COUNT', '7.27_COUNT', '8.27_COUNT',
            '9.27_COUNT', '10.27_COUNT', '11.27_COUNT', '12.27_COUNT',

            # Extended Monthly movements (Columns BE-CQ) - exactly 39 TO PREV columns starting from 10.24
            '10.24_TO_PREV', '11.24_TO_PREV', '12.24_TO_PREV',
            '1.25_TO_PREV', '2.25_TO_PREV', '3.25_TO_PREV', '4.25_TO_PREV',
            '5.25_TO_PREV', '6.25_TO_PREV', '7.25_TO_PREV', '8.25_TO_PREV',
            '9.25_TO_PREV', '10.25_TO_PREV', '11.25_TO_PREV', '12.25_TO_PREV',
            '1.26_TO_PREV', '2.26_TO_PREV', '3.26_TO_PREV', '4.26_TO_PREV',
            '5.26_TO_PREV', '6.26_TO_PREV', '7.26_TO_PREV', '8.26_TO_PREV',
            '9.26_TO_PREV', '10.26_TO_PREV', '11.26_TO_PREV', '12.26_TO_PREV',
            '1.27_TO_PREV', '2.27_TO_PREV', '3.27_TO_PREV', '4.27_TO_PREV',
            '5.27_TO_PREV', '6.27_TO_PREV', '7.27_TO_PREV', '8.27_TO_PREV',
            '9.27_TO_PREV', '10.27_TO_PREV', '11.27_TO_PREV', '12.27_TO_PREV',

            # Extended Monthly summaries (Columns CR-EE) - exactly 40 SUMMARY columns starting from 9.24
            '9.24_SUMMARY', '10.24_SUMMARY', '11.24_SUMMARY', '12.24_SUMMARY',
            '1.25_SUMMARY', '2.25_SUMMARY', '3.25_SUMMARY', '4.25_SUMMARY',
            '5.25_SUMMARY', '6.25_SUMMARY', '7.25_SUMMARY', '8.25_SUMMARY',
            '9.25_SUMMARY', '10.25_SUMMARY', '11.25_SUMMARY', '12.25_SUMMARY',
            '1.26_SUMMARY', '2.26_SUMMARY', '3.26_SUMMARY', '4.26_SUMMARY',
            '5.26_SUMMARY', '6.26_SUMMARY', '7.26_SUMMARY', '8.26_SUMMARY',
            '9.26_SUMMARY', '10.26_SUMMARY', '11.26_SUMMARY', '12.26_SUMMARY',
            '1.27_SUMMARY', '2.27_SUMMARY', '3.27_SUMMARY', '4.27_SUMMARY',
            '5.27_SUMMARY', '6.27_SUMMARY', '7.27_SUMMARY', '8.27_SUMMARY',
            '9.27_SUMMARY', '10.27_SUMMARY', '11.27_SUMMARY', '12.27_SUMMARY',

            # Metadata (Columns EF-EG) - repositioned after extended historical columns
            'MONTH',
            'YEAR',

            # Enhanced Tracking Fields (Columns EH-EY) - 18 new v300 fields
            'PREVIOUS_MONTH_STATUS',
            'STATUS_CONFIDENCE',
            'PROVIDER_TYPES_GAINED',
            'PROVIDER_TYPES_LOST',
            'NET_TYPE_CHANGE',
            'MONTHS_SINCE_LOST',
            'REINSTATED_FLAG',
            'REINSTATED_DATE',
            'DATA_QUALITY_SCORE',
            'MANUAL_REVIEW_FLAG',
            'REVIEW_NOTES',
            'LAST_ACTIVE_MONTH',
            'REGIONAL_MARKET',
            'HISTORICAL_STABILITY_SCORE',
            'EXPANSION_VELOCITY',
            'CONTRACTION_RISK',
            'MULTI_CITY_OPERATOR',
            'RELOCATION_FLAG'
        ]

        # Use processing month/year for reference, not current system date
        reference_month = processing_month if processing_month is not None else 7
        reference_year = processing_year if processing_year is not None else 2025

        # Collect all missing columns and their default values
        missing_columns = {}

        for col in expected_columns_internal:
            if col not in df.columns:
                # Determine appropriate default value based on column type
                if col.endswith('_COUNT'):
                    # For monthly count columns, use 0 for past/current months, pd.NA for future months
                    try:
                        # Extract month and year from column name like "9.24 COUNT"
                        month_year = col.replace('_COUNT', '')
                        month, year = month_year.split('.')
                        month = int(month)
                        year = 2000 + int(year)

                        # If it's a past month or current month, use 0; if future, use None for blank cells
                        if (year < reference_year) or (year == reference_year and month <= reference_month):
                            missing_columns[col] = 0
                        else:
                            missing_columns[col] = None  # Use None for future months to show blank in Excel
                    except Exception:
                        missing_columns[col] = pd.NA  # Use pd.NA instead of 'N/A' string

                elif col.endswith('_TO_PREV'):
                    # For monthly movement columns, use empty string for past/current months, None for future months
                    try:
                        # Extract month and year from column name like "9.24 TO PREV"
                        month_year = col.replace('_TO_PREV', '')
                        month, year = month_year.split('.')
                        month = int(month)
                        year = 2000 + int(year)

                        # If it's a past month or current month, use empty string; if future, use None for blank cells
                        if (year < reference_year) or (year == reference_year and month <= reference_month):
                            missing_columns[col] = ''
                        else:
                            missing_columns[col] = None  # Use None for future months to show blank in Excel
                    except Exception:
                        missing_columns[col] = pd.NA  # Use pd.NA instead of 'N/A' string

                elif col.endswith('_SUMMARY'):
                    # For monthly summary columns, use empty string for past/current months, None for future months
                    try:
                        # Extract month and year from column name like "9.24 SUMMARY"
                        month_year = col.replace('_SUMMARY', '')
                        month, year = month_year.split('.')
                        month = int(month)
                        year = 2000 + int(year)

                        # If it's a past month or current month, use empty string; if future, use None for blank cells
                        if (year < reference_year) or (year == reference_year and month <= reference_month):
                            missing_columns[col] = ''
                        else:
                            missing_columns[col] = None  # Use None for future months to show blank in Excel
                    except Exception:
                        missing_columns[col] = ''  # FIXED: Use empty string instead of pd.NA to prevent column dropping

                else:
                    # For all other columns, use empty string to preserve columns for v300
                    missing_columns[col] = ''  # FIXED: Use empty string instead of pd.NA to prevent column dropping

        # If there are missing columns, add them all at once using pd.concat
        if missing_columns:
            # Create a DataFrame with the missing columns
            new_cols_df = pd.DataFrame(
                {col: [val] * len(df) if len(df) > 0 else [val]
                 for col, val in missing_columns.items()},
                index=df.index if len(df) > 0 else [0]
            )

            # Concatenate the new columns to the existing dataframe
            df = pd.concat([df, new_cols_df], axis=1)

            # If df was empty, remove the dummy row
            if len(df) == 1 and df.index[0] == 0 and len(df.columns) == len(missing_columns):
                df = df.iloc[0:0]  # Empty dataframe with columns

        # Reorder columns to match expected order (using internal names)
        existing_cols = [col for col in expected_columns_internal if col in df.columns]
        other_cols = [col for col in df.columns if col not in expected_columns_internal]

        # Create final column order
        final_columns = existing_cols + other_cols
        df = df[final_columns].copy()  # Use copy() to de-fragment

        # Column names already match v300Track_this.xlsx exactly (keep underscores)

        # Return properly formatted DataFrame
        return df


def create_analysis_summary_sheet(analysis_df: pd.DataFrame, reformat_df: pd.DataFrame = None) -> pd.DataFrame:
    """Create the summary sheet with counts matching v300Track_this.xlsx template."""
    summary_data = []

    # Count basic metrics from Analysis data
    total_addresses = analysis_df['ADDRESS'].nunique()
    total_providers = analysis_df['PROVIDER'].nunique()
    # Use v300 exact column name
    provider_group_col = 'PROVIDER_GROUP_INDEX_#'
    total_provider_groups = analysis_df[provider_group_col].nunique() if provider_group_col in analysis_df.columns else 0

    # Count blanks from Reformat data (critical fields only)
    if reformat_df is not None:
        # Count blanks in critical fields from Reformat
        critical_fields = ['PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 'PROVIDER_TYPE']
        total_blanks = 0
        for field in critical_fields:
            if field in reformat_df.columns:
                total_blanks += reformat_df[field].isna().sum()
    else:
        # Fallback to counting blanks in Analysis if Reformat not provided
        # But only count critical fields, not all columns
        critical_fields = ['PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 'PROVIDER_TYPE']
        total_blanks = 0
        for field in critical_fields:
            if field in analysis_df.columns:
                total_blanks += analysis_df[field].isna().sum()

    # Use v300 exact column name
    solo_provider_col = 'SOLO_PROVIDER_TYPE_PROVIDER_[Y,#]'
    total_solo_providers = len(analysis_df[analysis_df[solo_provider_col] == 'Y']) if solo_provider_col in analysis_df.columns else 0

    # Count status types
    status_counts = analysis_df['THIS_MONTH_STATUS'].value_counts() if 'THIS_MONTH_STATUS' in analysis_df else {}

    new_provider_new_address = status_counts.get('NEW PROVIDER TYPE, NEW ADDRESS', 0)
    new_provider_existing_address = status_counts.get('NEW PROVIDER TYPE, EXISTING ADDRESS', 0)
    existing_provider_new_address = status_counts.get('EXISTING PROVIDER TYPE, NEW ADDRESS', 0)
    existing_provider_existing_address = status_counts.get('EXISTING PROVIDER TYPE, EXISTING ADDRESS', 0)
    lost_provider_existing_address = status_counts.get('LOST PROVIDER TYPE, EXISTING ADDRESS', 0)
    lost_provider_lost_address_0 = status_counts.get('LOST PROVIDER TYPE, LOST ADDRESS (0 remain)', 0)
    lost_provider_lost_address_1 = status_counts.get('LOST PROVIDER TYPE, LOST ADDRESS (1+ remain)', 0)
    reinstated_provider_existing_address = status_counts.get('REINSTATED PROVIDER TYPE, EXISTING ADDRESS', 0)

    # Count leads - updated for v300 with proper case sensitivity
    total_seller_survey_leads = len(analysis_df[~analysis_df['LEAD_TYPE'].isin(['', pd.NA])]) if 'LEAD_TYPE' in analysis_df.columns else 0
    seller_leads = len(analysis_df[analysis_df['LEAD_TYPE'].isin(['Seller Lead', 'Seller/Survey Lead'])]) if 'LEAD_TYPE' in analysis_df.columns else 0
    survey_leads = len(analysis_df[analysis_df['LEAD_TYPE'].isin(['Survey Lead', 'Seller/Survey Lead'])]) if 'LEAD_TYPE' in analysis_df.columns else 0

    # Count by provider type - use v300 exact column name
    provider_type_col = 'PROVIDER_TYPE'
    provider_type_counts = analysis_df[provider_type_col].value_counts() if provider_type_col in analysis_df.columns else {}
    total_record_count = len(analysis_df)

    # Create the exact template structure matching v300Track_this.xlsx
    # Row 1 is headers, data starts at row 2
    summary_data = [
        ['Total ADDRESS', total_addresses],                                     # Row 2
        ['Total PROVIDER', total_providers],                                    # Row 3
        ['Total PROVIDER GROUP', total_provider_groups],                        # Row 4
        ['Total Blanks', total_blanks],                                         # Row 5
        ['Total SOLO PROVIDER TYPE PROVIDER', total_solo_providers],            # Row 6
        ['', ''],                                                                # Row 7 - Empty row
        ['New PROVIDER TYPE, New ADDRESS', new_provider_new_address],           # Row 8
        ['New PROVIDER TYPE, Existing ADDRESS', new_provider_existing_address], # Row 9
        ['Existing PROVIDER TYPE, New ADDRESS', existing_provider_new_address], # Row 10
        ['Existing PROVIDER TYPE, Existing ADDRESS', existing_provider_existing_address], # Row 11
        ['Lost PROVIDER TYPE, Existing ADDRESS', lost_provider_existing_address],        # Row 12
        ['Lost PROVIDER TYPE, Lost ADDRESS (0 remain)', lost_provider_lost_address_0],   # Row 13
        ['Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)', lost_provider_lost_address_1],  # Row 14
        ['Reinstated PROVIDER TYPE, Existing ADDRESS', reinstated_provider_existing_address], # Row 15
        ['', ''],                                                                # Row 16 - Empty row
        ['Total Seller/Survey Lead', total_seller_survey_leads],                # Row 17 - NEW v300 row
        ['Total Seller Lead', seller_leads],                                    # Row 18 (was 17)
        ['Total Survey Lead', survey_leads],                                    # Row 19 (was 18)
        ['', ''],                                                                # Row 20 - Empty row (was 19)
        ['Total Record Count (TRC)', total_record_count],                       # Row 21 (was 20)
        ['ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME (TRC)', provider_type_counts.get('ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME', 0)],  # Row 22
        ['ASSISTED_LIVING_CENTER (TRC)', provider_type_counts.get('ASSISTED_LIVING_CENTER', 0)],  # Row 23
        ['ASSISTED_LIVING_HOME (TRC)', provider_type_counts.get('ASSISTED_LIVING_HOME', 0)],  # Row 24
        ['BEHAVIORAL_HEALTH_INPATIENT (TRC)', provider_type_counts.get('BEHAVIORAL_HEALTH_INPATIENT', 0)],  # Row 25
        ['BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY (TRC)', provider_type_counts.get('BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY', 0)],  # Row 26
        ['CC_CENTERS (TRC)', provider_type_counts.get('CC_CENTERS', 0)],  # Row 27
        ['CC_GROUP_HOMES (TRC)', provider_type_counts.get('CC_GROUP_HOMES', 0)],  # Row 28
        ['DEVELOPMENTALLY_DISABLED_GROUP_HOME (TRC)', provider_type_counts.get('DEVELOPMENTALLY_DISABLED_GROUP_HOME', 0)],  # Row 29
        ['HOSPITAL_REPORT (TRC)', provider_type_counts.get('HOSPITAL_REPORT', 0)],  # Row 30
        ['NURSING_HOME (TRC)', provider_type_counts.get('NURSING_HOME', 0)],  # Row 31
        ['NURSING_SUPPORTED_GROUP_HOMES (TRC)', provider_type_counts.get('NURSING_SUPPORTED_GROUP_HOMES', 0)],  # Row 32
        ['OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT (TRC)', provider_type_counts.get('OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT', 0)]  # Row 33
    ]
    
    # Create DataFrame with exact template column names
    summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Count'])
    
    return summary_df


def create_blanks_count_sheet(current_month_df: pd.DataFrame, processing_month: int = None, processing_year: int = None) -> pd.DataFrame:
    """
    Create the blanks count sheet by provider type.

    Args:
        current_month_df: The current month's Reformat data
        processing_month: The month being processed (for MONTH column validation)
        processing_year: The year being processed (for YEAR column validation)
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
        # Filter to this provider type - handle both internal and display names
        provider_type_col = 'PROVIDER TYPE' if 'PROVIDER TYPE' in current_month_df.columns else 'PROVIDER_TYPE'
        type_df = current_month_df[current_month_df[provider_type_col] == provider_type]

        if type_df.empty:
            # No data for this provider type - all fields are effectively blank
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
                'PROVIDER GROUP INDEX #': 0
            })
        else:
            # Count blanks in each field - v300 column order: Provider Type, MONTH, YEAR, then rest
            row_data = {}

            # Column A: Provider Type (always populated)
            row_data['PROVIDER_TYPE'] = provider_type

            # Column B & C: MONTH and YEAR - check if they match processing month/year
            if 'MONTH' in type_df.columns:
                # Count records where MONTH doesn't match the processing month
                if processing_month is not None:
                    month_blank_count = type_df['MONTH'].apply(
                        lambda x: pd.isna(x) or x != processing_month
                    ).sum()
                else:
                    # No processing month provided, count actual blanks
                    month_blank_count = type_df['MONTH'].apply(
                        lambda x: pd.isna(x) or str(x).strip() in ['', 'NAN', 'N/A']
                    ).sum()
                row_data['MONTH'] = month_blank_count
            else:
                row_data['MONTH'] = len(type_df)

            if 'YEAR' in type_df.columns:
                # Count records where YEAR doesn't match the processing year
                if processing_year is not None:
                    year_blank_count = type_df['YEAR'].apply(
                        lambda x: pd.isna(x) or x != processing_year
                    ).sum()
                else:
                    # No processing year provided, count actual blanks
                    year_blank_count = type_df['YEAR'].apply(
                        lambda x: pd.isna(x) or str(x).strip() in ['', 'NAN', 'N/A']
                    ).sum()
                row_data['YEAR'] = year_blank_count
            else:
                row_data['YEAR'] = len(type_df)

            # Columns D-K: Other fields in v300 order - handle both internal and display names
            fields_ordered = [
                'PROVIDER',   # Column D
                'ADDRESS',    # Column E
                'CITY',       # Column F
                'ZIP',        # Column G
                'CAPACITY',   # Column H
                'LONGITUDE',  # Column I
                'LATITUDE',   # Column J
                'PROVIDER GROUP INDEX #' if 'PROVIDER GROUP INDEX #' in type_df.columns else 'PROVIDER_GROUP_INDEX_#'  # Column K
            ]

            for field in fields_ordered:
                if field in type_df.columns:
                    # Count empty, NaN, or 'NAN' values
                    blank_count = type_df[field].apply(
                        lambda x: pd.isna(x) or str(x).strip() in ['', 'NAN', 'N/A']
                    ).sum()
                    # Use v300 exact column name
                    output_field = field  # Keep exact column name, no conversion
                    row_data[output_field] = blank_count
                else:
                    # Use v300 exact column name
                    output_field = field  # Keep exact column name, no conversion
                    row_data[output_field] = len(type_df)  # All blank if column doesn't exist

            blanks_data.append(row_data)

    # Create DataFrame with columns in v300 order (using display names)
    columns_ordered = [
        'PROVIDER_TYPE',  # Column A (Unnamed: 0 in Excel) - keep internal name as it's not renamed
        'MONTH',          # Column B
        'YEAR',           # Column C
        'PROVIDER',       # Column D
        'ADDRESS',        # Column E
        'CITY',           # Column F
        'ZIP',            # Column G
        'CAPACITY',       # Column H
        'LONGITUDE',      # Column I
        'LATITUDE',       # Column J
        'PROVIDER_GROUP_INDEX_#'  # Column K - use v300 exact name
    ]

    return pd.DataFrame(blanks_data, columns=columns_ordered)