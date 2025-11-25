"""
batchdata_sync.py - Synchronous HTTP client for BatchData JSON endpoints

This module provides a synchronous client for the BatchData API V1 that:
1. Uses JSON requests instead of CSV upload + polling
2. Preserves BD_RECORD_ID through the API via requestId
3. Flattens nested JSON responses to wide format (BD_PHONE_1, BD_PHONE_2, etc.)
4. Maintains all INPUT_MASTER columns
5. Implements automatic batching (max 100 records per request)
"""

import os
import time
import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Iterator
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchDataSyncClient:
    """Synchronous client for BatchData V1 API with JSON request/response handling."""

    def __init__(self, api_keys: Dict[str, str], base_url: str = "https://api.batchdata.com/api/v1"):
        """Initialize BatchData sync client.

        Args:
            api_keys: Dictionary of API keys for different services
                     (BD_PROPERTY_KEY, BD_ADDRESS_KEY, BD_PHONE_KEY)
            base_url: Base API URL (defaults to v1 API)

        Note: Skip-trace and phone endpoints are v1 endpoints.
        """
        self.base_url = base_url.rstrip('/')
        self.api_keys = api_keys
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'BatchData-Pipeline-Sync/1.0'})

    def _get_headers(self, service_type: str) -> Dict[str, str]:
        """Get headers with appropriate API key for service type.

        Args:
            service_type: Type of service (skiptrace, address, property, phone)

        Returns:
            Request headers with authorization
        """
        # Primary key mapping
        key_map = {
            'skiptrace': 'BD_PROPERTY_KEY',  # Skip-trace uses property key (includes skip-trace permission)
            'address': 'BD_ADDRESS_KEY',
            'property': 'BD_PROPERTY_KEY',
            'phone': 'BD_PHONE_KEY'
        }

        # Fallback for legacy BD_SKIPTRACE_KEY support
        fallback_map = {
            'skiptrace': 'BD_SKIPTRACE_KEY'
        }

        primary_key = key_map.get(service_type, '')
        api_key = self.api_keys.get(primary_key)

        # Try fallback if primary not found
        if not api_key and service_type in fallback_map:
            fallback_key = fallback_map[service_type]
            api_key = self.api_keys.get(fallback_key)
            if api_key:
                logger.debug(f"Using fallback key {fallback_key} for {service_type}")

        if not api_key:
            raise ValueError(f"API key not found for service type: {service_type}. Expected {primary_key}")

        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def process_skip_trace(self, input_df: pd.DataFrame, batch_size: int = 50) -> pd.DataFrame:
        """Main entry point - handles batching and schema conversion for skip-trace.

        Args:
            input_df: DataFrame with INPUT_MASTER columns
            batch_size: Number of records per API request (max 100, recommend 50)

        Returns:
            DataFrame with all input columns plus enrichment fields
        """
        if batch_size > 100:
            logger.warning(f"Batch size {batch_size} exceeds maximum of 100. Setting to 100.")
            batch_size = 100

        logger.info(f"Processing {len(input_df)} records in batches of {batch_size}")

        # Initialize result list
        all_results = []

        # Process in chunks
        for chunk_idx, chunk_df in enumerate(self._chunk_dataframe(input_df, batch_size)):
            logger.info(f"Processing chunk {chunk_idx + 1} ({len(chunk_df)} records)")

            try:
                # Convert DataFrame to API request format
                request_data = self._df_to_sync_request(chunk_df)

                # Make API call
                response_data = self._call_skip_trace_api(request_data)

                # Parse response to schema
                chunk_results = self._parse_sync_response_to_schema(response_data, chunk_df)
                all_results.append(chunk_results)

                # Brief pause between batches to avoid rate limiting
                if chunk_idx < len(input_df) // batch_size:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error processing chunk {chunk_idx + 1}: {str(e)}")
                # Create empty results for failed chunk (preserves input data)
                chunk_results = chunk_df.copy()
                chunk_results['BD_API_STATUS'] = 'error'
                chunk_results['BD_API_ERROR'] = str(e)
                all_results.append(chunk_results)

        # Combine all results
        if all_results:
            final_df = pd.concat(all_results, ignore_index=True)
            logger.info(f"✅ Successfully processed {len(final_df)} records")
            return final_df
        else:
            logger.warning("No results generated. Returning input DataFrame.")
            return input_df

    def _df_to_sync_request(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Convert DataFrame to V3 JSON request format.

        Args:
            df: DataFrame chunk to convert

        Returns:
            Dictionary in BatchData V3 request format
        """
        requests_list = []

        for _, row in df.iterrows():
            # Build individual request
            request_item = {
                "requestId": str(row.get('BD_RECORD_ID', '')),  # CRITICAL: enables merging
                "propertyAddress": {
                    "street": str(row.get('BD_ADDRESS', '')),
                    "city": str(row.get('BD_CITY', '')),
                    "state": str(row.get('BD_STATE', '')),
                    "zip": str(row.get('BD_ZIP', ''))
                }
            }

            # Add name if available (improves match rate)
            first_name = row.get('BD_TARGET_FIRST_NAME', '')
            last_name = row.get('BD_TARGET_LAST_NAME', '')
            full_name = row.get('BD_OWNER_NAME_FULL', '')

            if first_name or last_name:
                request_item["name"] = {
                    "first": str(first_name) if first_name else "",
                    "last": str(last_name) if last_name else ""
                }
            elif full_name:
                # Parse full name if we don't have separate first/last
                name_parts = str(full_name).strip().split(' ', 1)
                if len(name_parts) == 2:
                    request_item["name"] = {
                        "first": name_parts[0],
                        "last": name_parts[1]
                    }
                elif len(name_parts) == 1:
                    request_item["name"] = {
                        "first": "",
                        "last": name_parts[0]
                    }

            requests_list.append(request_item)

        return {"requests": requests_list}

    def _call_skip_trace_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make synchronous API call to skip-trace endpoint.

        Args:
            request_data: Formatted request dictionary

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/property/skip-trace"
        headers = self._get_headers('skiptrace')

        logger.debug(f"Calling API: {url}")
        logger.debug(f"Request contains {len(request_data.get('requests', []))} records")

        try:
            response = self.session.post(
                url,
                json=request_data,
                headers=headers,
                timeout=120  # 2 minute timeout for sync calls
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(f"Response content: {e.response.text if e.response else 'No response'}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise

    def _parse_sync_response_to_schema(self, response: Dict[str, Any], input_df: pd.DataFrame) -> pd.DataFrame:
        """Convert nested JSON response to wide-format DataFrame.

        Args:
            response: API response dictionary
            input_df: Original input DataFrame chunk

        Returns:
            DataFrame with input columns plus flattened enrichment fields
        """
        # Start with copy of input to preserve all columns
        result_df = input_df.copy()

        # Add default enrichment columns
        for i in range(1, 11):  # BD_PHONE_1 through BD_PHONE_10
            result_df[f'BD_PHONE_{i}'] = ''
            result_df[f'BD_PHONE_{i}_FIRST'] = ''  # Person first name
            result_df[f'BD_PHONE_{i}_LAST'] = ''   # Person last name
            result_df[f'BD_PHONE_{i}_TYPE'] = ''
            result_df[f'BD_PHONE_{i}_CARRIER'] = ''
            result_df[f'BD_PHONE_{i}_DNC'] = False
            result_df[f'BD_PHONE_{i}_TCPA'] = False
            result_df[f'BD_PHONE_{i}_CONFIDENCE'] = 0.0

        for i in range(1, 11):  # BD_EMAIL_1 through BD_EMAIL_10
            result_df[f'BD_EMAIL_{i}'] = ''
            result_df[f'BD_EMAIL_{i}_FIRST'] = ''  # Person first name
            result_df[f'BD_EMAIL_{i}_LAST'] = ''   # Person last name
            result_df[f'BD_EMAIL_{i}_TESTED'] = False

        # Add API status columns
        result_df['BD_API_STATUS'] = 'success'
        result_df['BD_API_RESPONSE_TIME'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result_df['BD_PERSONS_FOUND'] = 0
        result_df['BD_PHONES_FOUND'] = 0
        result_df['BD_EMAILS_FOUND'] = 0

        # Check for valid response - V1 uses 'results' not 'result'
        if not response:
            logger.warning("Empty API response")
            result_df['BD_API_STATUS'] = 'invalid_response'
            return result_df

        # V1 format: results.persons[] (single request returns array directly)
        # For batch requests, each person result corresponds to a request
        if 'results' in response:
            result_data = response.get('results', {}).get('persons', [])
            # Wrap each person as a single-person result for consistent processing
            result_data = [{'persons': [person]} for person in result_data] if result_data else []
        elif 'result' in response:
            # V2/V3 format: result.data[]
            result_data = response.get('result', {}).get('data', [])
        else:
            logger.warning("Invalid API response format")
            result_df['BD_API_STATUS'] = 'invalid_response'
            return result_df

        # V1 returns results in order, not by requestId
        # Create lookup: if no requestId, match by index
        response_by_id = {}
        for idx_item, item in enumerate(result_data):
            # Try to get requestId from input (V2/V3 format)
            request_id = item.get('input', {}).get('requestId')
            if request_id:
                response_by_id[request_id] = item
            else:
                # V1 format: match by index to input row
                if idx_item < len(result_df):
                    record_id = str(result_df.iloc[idx_item].get('BD_RECORD_ID', ''))
                    response_by_id[record_id] = item

        # Update each row with response data
        for idx, row in result_df.iterrows():
            record_id = str(row.get('BD_RECORD_ID', ''))

            if record_id in response_by_id:
                item = response_by_id[record_id]
                persons = item.get('persons', [])

                # Count persons found
                result_df.at[idx, 'BD_PERSONS_FOUND'] = len(persons)

                # Collect all phones and emails from all persons
                all_phones = []
                all_emails = []

                for person in persons:
                    # Extract person name once per person (handles missing name gracefully)
                    person_name = person.get('name', {}) or {}
                    person_first = person_name.get('first', '') or ''
                    person_last = person_name.get('last', '') or ''

                    # Process phones - V1 uses 'phoneNumbers', V2/V3 uses 'phones'
                    phones = person.get('phoneNumbers', person.get('phones', []))
                    for phone in phones:
                        phone_data = {
                            'number': phone.get('number', ''),
                            'first': person_first,  # Denormalized person name
                            'last': person_last,    # Denormalized person name
                            'type': phone.get('type', ''),
                            'carrier': phone.get('carrier', ''),
                            'dnc': phone.get('dnc', False),
                            'tcpa': phone.get('tcpa', False),
                            'confidence': phone.get('score', 0.0)  # May be 'score' or 'confidence'
                        }
                        all_phones.append(phone_data)

                    # Process emails
                    emails = person.get('emails', [])
                    for email in emails:
                        email_data = {
                            'address': email.get('address', ''),
                            'first': person_first,  # Denormalized person name
                            'last': person_last,    # Denormalized person name
                            'tested': email.get('tested', False)
                        }
                        all_emails.append(email_data)

                # Update phone columns (up to 10)
                result_df.at[idx, 'BD_PHONES_FOUND'] = len(all_phones)
                for i, phone in enumerate(all_phones[:10], 1):
                    result_df.at[idx, f'BD_PHONE_{i}'] = phone['number']
                    result_df.at[idx, f'BD_PHONE_{i}_FIRST'] = phone['first']
                    result_df.at[idx, f'BD_PHONE_{i}_LAST'] = phone['last']
                    result_df.at[idx, f'BD_PHONE_{i}_TYPE'] = phone['type']
                    result_df.at[idx, f'BD_PHONE_{i}_CARRIER'] = phone['carrier']
                    result_df.at[idx, f'BD_PHONE_{i}_DNC'] = phone['dnc']
                    result_df.at[idx, f'BD_PHONE_{i}_TCPA'] = phone['tcpa']
                    result_df.at[idx, f'BD_PHONE_{i}_CONFIDENCE'] = phone['confidence']

                # Update email columns (up to 10)
                result_df.at[idx, 'BD_EMAILS_FOUND'] = len(all_emails)
                for i, email in enumerate(all_emails[:10], 1):
                    result_df.at[idx, f'BD_EMAIL_{i}'] = email['address']
                    result_df.at[idx, f'BD_EMAIL_{i}_FIRST'] = email['first']
                    result_df.at[idx, f'BD_EMAIL_{i}_LAST'] = email['last']
                    result_df.at[idx, f'BD_EMAIL_{i}_TESTED'] = email['tested']
            else:
                # No response for this record
                result_df.at[idx, 'BD_API_STATUS'] = 'no_match'
                logger.debug(f"No match found for BD_RECORD_ID: {record_id}")

        return result_df

    def _chunk_dataframe(self, df: pd.DataFrame, chunk_size: int) -> Iterator[pd.DataFrame]:
        """Split large DataFrames into API-sized chunks.

        Args:
            df: DataFrame to split
            chunk_size: Maximum records per chunk

        Yields:
            DataFrame chunks
        """
        for start_idx in range(0, len(df), chunk_size):
            end_idx = min(start_idx + chunk_size, len(df))
            yield df.iloc[start_idx:end_idx].copy()

    def phone_verification_sync(self, input_df: pd.DataFrame, batch_size: int = 100) -> pd.DataFrame:
        """Verify phone numbers for validity and type.

        Args:
            input_df: DataFrame with phone columns
            batch_size: Number of phones per API request

        Returns:
            DataFrame with updated phone verification fields
        """
        logger.info("Running phone verification...")

        # Collect all phones from BD_PHONE_1 through BD_PHONE_10
        phones_to_verify = []
        for _, row in input_df.iterrows():
            for i in range(1, 11):
                phone = row.get(f'BD_PHONE_{i}', '')
                if phone and str(phone).strip():
                    phones_to_verify.append({
                        'BD_RECORD_ID': row['BD_RECORD_ID'],
                        'phone_index': i,
                        'phone': str(phone).strip()
                    })

        if not phones_to_verify:
            logger.info("No phones to verify")
            return input_df

        logger.info(f"Verifying {len(phones_to_verify)} phone numbers")

        # Process in batches
        result_df = input_df.copy()

        for start_idx in range(0, len(phones_to_verify), batch_size):
            batch = phones_to_verify[start_idx:start_idx + batch_size]

            # Call phone verification API
            request_data = {
                "phones": [item['phone'] for item in batch]
            }

            try:
                url = f"{self.base_url}/phone/verification"
                headers = self._get_headers('phone')
                response = self.session.post(url, json=request_data, headers=headers, timeout=60)
                response.raise_for_status()
                response_data = response.json()

                # Update DataFrame with results
                results = response_data.get('result', {}).get('data', [])
                for item, result in zip(batch, results):
                    idx = result_df[result_df['BD_RECORD_ID'] == item['BD_RECORD_ID']].index[0]
                    phone_col = f"BD_PHONE_{item['phone_index']}"

                    # Update verification fields
                    if result.get('valid', False):
                        result_df.at[idx, f"{phone_col}_VERIFIED"] = True
                        result_df.at[idx, f"{phone_col}_TYPE"] = result.get('type', '')
                        result_df.at[idx, f"{phone_col}_CARRIER"] = result.get('carrier', '')
                    else:
                        result_df.at[idx, f"{phone_col}_VERIFIED"] = False

            except Exception as e:
                logger.error(f"Error in phone verification: {e}")
                continue

        return result_df

    def phone_dnc_sync(self, input_df: pd.DataFrame, batch_size: int = 100) -> pd.DataFrame:
        """Check Do-Not-Call status for phone numbers.

        Args:
            input_df: DataFrame with phone columns
            batch_size: Number of phones per API request

        Returns:
            DataFrame with updated DNC fields
        """
        logger.info("Running DNC checks...")

        # Similar structure to phone_verification_sync
        phones_to_check = []
        for _, row in input_df.iterrows():
            for i in range(1, 11):
                phone = row.get(f'BD_PHONE_{i}', '')
                if phone and str(phone).strip():
                    phones_to_check.append({
                        'BD_RECORD_ID': row['BD_RECORD_ID'],
                        'phone_index': i,
                        'phone': str(phone).strip()
                    })

        if not phones_to_check:
            logger.info("No phones to check for DNC")
            return input_df

        logger.info(f"Checking DNC for {len(phones_to_check)} phone numbers")

        result_df = input_df.copy()

        for start_idx in range(0, len(phones_to_check), batch_size):
            batch = phones_to_check[start_idx:start_idx + batch_size]

            request_data = {
                "phones": [item['phone'] for item in batch]
            }

            try:
                url = f"{self.base_url}/phone/dnc"
                headers = self._get_headers('phone')
                response = self.session.post(url, json=request_data, headers=headers, timeout=60)
                response.raise_for_status()
                response_data = response.json()

                # Update DataFrame with DNC results
                results = response_data.get('result', {}).get('data', [])
                for item, result in zip(batch, results):
                    idx = result_df[result_df['BD_RECORD_ID'] == item['BD_RECORD_ID']].index[0]
                    phone_col = f"BD_PHONE_{item['phone_index']}"
                    result_df.at[idx, f"{phone_col}_DNC"] = result.get('dnc', False)

            except Exception as e:
                logger.error(f"Error in DNC check: {e}")
                continue

        return result_df

    def phone_tcpa_sync(self, input_df: pd.DataFrame, batch_size: int = 100) -> pd.DataFrame:
        """Check TCPA litigator status for phone numbers.

        Args:
            input_df: DataFrame with phone columns
            batch_size: Number of phones per API request

        Returns:
            DataFrame with updated TCPA fields
        """
        logger.info("Running TCPA checks...")

        # Similar structure to phone_verification_sync
        phones_to_check = []
        for _, row in input_df.iterrows():
            for i in range(1, 11):
                phone = row.get(f'BD_PHONE_{i}', '')
                if phone and str(phone).strip():
                    phones_to_check.append({
                        'BD_RECORD_ID': row['BD_RECORD_ID'],
                        'phone_index': i,
                        'phone': str(phone).strip()
                    })

        if not phones_to_check:
            logger.info("No phones to check for TCPA")
            return input_df

        logger.info(f"Checking TCPA for {len(phones_to_check)} phone numbers")

        result_df = input_df.copy()

        for start_idx in range(0, len(phones_to_check), batch_size):
            batch = phones_to_check[start_idx:start_idx + batch_size]

            request_data = {
                "phones": [item['phone'] for item in batch]
            }

            try:
                url = f"{self.base_url}/phone/tcpa"
                headers = self._get_headers('phone')
                response = self.session.post(url, json=request_data, headers=headers, timeout=60)
                response.raise_for_status()
                response_data = response.json()

                # Update DataFrame with TCPA results
                results = response_data.get('result', {}).get('data', [])
                for item, result in zip(batch, results):
                    idx = result_df[result_df['BD_RECORD_ID'] == item['BD_RECORD_ID']].index[0]
                    phone_col = f"BD_PHONE_{item['phone_index']}"
                    result_df.at[idx, f"{phone_col}_TCPA"] = result.get('tcpa', False)

            except Exception as e:
                logger.error(f"Error in TCPA check: {e}")
                continue

        return result_df

    def run_enrichment_pipeline(self, input_df: pd.DataFrame, stage_config: Dict[str, bool],
                                batch_size: int = 50) -> pd.DataFrame:
        """Run the full enrichment pipeline with conditional stages.

        Args:
            input_df: DataFrame with INPUT_MASTER columns
            stage_config: Dictionary of stages to enable/disable
                         {'skip_trace': True, 'phone_verify': False, 'dnc': False, 'tcpa': False}
            batch_size: Number of records per batch

        Returns:
            Fully enriched DataFrame
        """
        current_df = input_df.copy()

        # Stage 1: Skip-trace (always if enabled)
        if stage_config.get('skip_trace', True):
            logger.info("🔍 Stage 1: Skip-trace enrichment")
            current_df = self.process_skip_trace(current_df, batch_size)

        # Stage 2: Phone verification (conditional)
        if stage_config.get('phone_verify', False):
            logger.info("📱 Stage 2: Phone verification")
            current_df = self.phone_verification_sync(current_df)

        # Stage 3: DNC (conditional)
        if stage_config.get('dnc', False):
            logger.info("🚫 Stage 3: Do-Not-Call screening")
            current_df = self.phone_dnc_sync(current_df)

        # Stage 4: TCPA (conditional)
        if stage_config.get('tcpa', False):
            logger.info("⚖️ Stage 4: TCPA litigator screening")
            current_df = self.phone_tcpa_sync(current_df)

        # Add pipeline metadata
        current_df['BD_PIPELINE_VERSION'] = 'sync_v1'
        current_df['BD_PIPELINE_TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_df['BD_STAGES_APPLIED'] = json.dumps(stage_config)

        return current_df


# Example usage and testing
if __name__ == "__main__":
    # Example: Create test DataFrame
    test_df = pd.DataFrame({
        'BD_RECORD_ID': ['ecorp_123_1_abc', 'ecorp_124_1_def'],
        'BD_SOURCE_TYPE': ['Entity', 'Entity'],
        'BD_ENTITY_NAME': ['Test Corp 1', 'Test Corp 2'],
        'BD_SOURCE_ENTITY_ID': ['123', '124'],
        'BD_TITLE_ROLE': ['Manager', 'Member'],
        'BD_TARGET_FIRST_NAME': ['John', 'Jane'],
        'BD_TARGET_LAST_NAME': ['Smith', 'Doe'],
        'BD_OWNER_NAME_FULL': ['John Smith', 'Jane Doe'],
        'BD_ADDRESS': ['123 Main St', '456 Oak Ave'],
        'BD_ADDRESS_2': ['', 'Suite 200'],
        'BD_CITY': ['Phoenix', 'Scottsdale'],
        'BD_STATE': ['AZ', 'AZ'],
        'BD_ZIP': ['85001', '85250'],
        'BD_COUNTY': ['MARICOPA', 'MARICOPA'],
        'BD_APN': ['123-45-678', '987-65-432'],
        'BD_MAILING_LINE1': ['', ''],
        'BD_MAILING_CITY': ['', ''],
        'BD_MAILING_STATE': ['', ''],
        'BD_MAILING_ZIP': ['', ''],
        'BD_NOTES': ['Test note 1', 'Test note 2']
    })

    # Example API keys (would come from environment)
    # BD_PROPERTY_KEY is used for skip-trace (includes property-skip-trace permission)
    api_keys = {
        'BD_PROPERTY_KEY': os.getenv('BD_PROPERTY_KEY', 'test_key'),
        'BD_ADDRESS_KEY': os.getenv('BD_ADDRESS_KEY', 'test_key'),
        'BD_PHONE_KEY': os.getenv('BD_PHONE_KEY', 'test_key')
    }

    # Create client
    client = BatchDataSyncClient(api_keys)

    # Process with specific stages
    stage_config = {
        'skip_trace': True,
        'phone_verify': False,
        'dnc': False,
        'tcpa': False
    }

    logger.info("Starting test run...")
    logger.info(f"Input records: {len(test_df)}")

    # Note: This would make actual API calls in production
    # result_df = client.run_enrichment_pipeline(test_df, stage_config)

    logger.info("Test client initialization successful!")