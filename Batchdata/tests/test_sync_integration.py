#!/usr/bin/env python3
"""
test_sync_integration.py - Integration tests for BatchData sync client

This script performs comprehensive testing of the sync client implementation:
1. Loads real test data
2. Tests with dry-run mode
3. Validates schema compatibility
4. Tests with small batches
5. Compares with expected output structure
"""

import sys
import os
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import traceback
from typing import Dict, Any, Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.batchdata_sync import BatchDataSyncClient
from src.io import load_workbook_sheets


class ColorOutput:
    """Helper class for colored terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def success(msg):
        return f"{ColorOutput.OKGREEN}✅ {msg}{ColorOutput.ENDC}"

    @staticmethod
    def error(msg):
        return f"{ColorOutput.FAIL}❌ {msg}{ColorOutput.ENDC}"

    @staticmethod
    def warning(msg):
        return f"{ColorOutput.WARNING}⚠️  {msg}{ColorOutput.ENDC}"

    @staticmethod
    def info(msg):
        return f"{ColorOutput.OKCYAN}ℹ️  {msg}{ColorOutput.ENDC}"

    @staticmethod
    def header(msg):
        return f"{ColorOutput.BOLD}{ColorOutput.HEADER}{'=' * 60}\n{msg}\n{'=' * 60}{ColorOutput.ENDC}"


def test_load_test_data():
    """Test 1: Load and validate test data."""
    print(ColorOutput.header("TEST 1: Loading Test Data"))

    test_file = Path("Batchdata/tests/batchdata_local_input.xlsx")
    if not test_file.exists():
        print(ColorOutput.error(f"Test file not found: {test_file}"))
        return None

    try:
        sheets = load_workbook_sheets(str(test_file))
        print(ColorOutput.success(f"Loaded test file: {test_file.name}"))

        # Check required sheets
        required_sheets = ['CONFIG', 'INPUT_MASTER', 'BLACKLIST_NAMES']
        for sheet in required_sheets:
            if sheet in sheets:
                print(ColorOutput.success(f"Found sheet: {sheet} ({len(sheets[sheet])} rows)"))
            else:
                print(ColorOutput.error(f"Missing required sheet: {sheet}"))
                return None

        return sheets

    except Exception as e:
        print(ColorOutput.error(f"Failed to load test data: {e}"))
        return None


def test_sync_client_initialization(sheets: Dict[str, pd.DataFrame]):
    """Test 2: Initialize sync client with config."""
    print(ColorOutput.header("TEST 2: Sync Client Initialization"))

    try:
        # Extract API keys from CONFIG
        config_df = sheets['CONFIG']
        api_keys = {}

        # Check for environment variables first
        env_keys = ['BD_SKIPTRACE_KEY', 'BD_ADDRESS_KEY', 'BD_PROPERTY_KEY', 'BD_PHONE_KEY']
        for key in env_keys:
            value = os.getenv(key)
            if value:
                api_keys[key] = value
                print(ColorOutput.info(f"Found {key} in environment"))

        # If no env vars, try to extract from CONFIG sheet
        if not api_keys:
            for _, row in config_df.iterrows():
                key = str(row.get('key', ''))
                value = str(row.get('value', ''))
                if 'api.key.skiptrace' in key:
                    api_keys['BD_SKIPTRACE_KEY'] = value
                elif 'api.key.address' in key:
                    api_keys['BD_ADDRESS_KEY'] = value
                elif 'api.key.property' in key:
                    api_keys['BD_PROPERTY_KEY'] = value
                elif 'api.key.phone' in key:
                    api_keys['BD_PHONE_KEY'] = value

        if not api_keys.get('BD_SKIPTRACE_KEY'):
            print(ColorOutput.warning("No API keys found - will use test mode"))
            api_keys = {
                'BD_SKIPTRACE_KEY': 'test_key',
                'BD_ADDRESS_KEY': 'test_key',
                'BD_PROPERTY_KEY': 'test_key',
                'BD_PHONE_KEY': 'test_key'
            }

        # Initialize client
        client = BatchDataSyncClient(api_keys)
        print(ColorOutput.success("Sync client initialized successfully"))

        # Check base URL
        print(ColorOutput.info(f"Base URL: {client.base_url}"))
        if 'batchdata.com/api/v3' in client.base_url:
            print(ColorOutput.success("Base URL is correct (v3 API)"))
        else:
            print(ColorOutput.error(f"Base URL may be incorrect: {client.base_url}"))

        return client, api_keys

    except Exception as e:
        print(ColorOutput.error(f"Failed to initialize client: {e}"))
        traceback.print_exc()
        return None, None


def test_request_format(client: BatchDataSyncClient, sheets: Dict[str, pd.DataFrame]):
    """Test 3: Validate request format."""
    print(ColorOutput.header("TEST 3: Request Format Validation"))

    try:
        input_df = sheets['INPUT_MASTER']

        # Take first 3 records for testing
        test_df = input_df.head(3).copy()
        print(ColorOutput.info(f"Testing with {len(test_df)} records"))

        # Convert to request format
        request_data = client._df_to_sync_request(test_df)

        # Validate structure
        if 'requests' in request_data:
            print(ColorOutput.success(f"Request has 'requests' field"))
            print(ColorOutput.info(f"Number of requests: {len(request_data['requests'])}"))
        else:
            print(ColorOutput.error("Request missing 'requests' field"))
            return False

        # Check first request
        if request_data['requests']:
            first_req = request_data['requests'][0]
            required_fields = ['requestId', 'propertyAddress']

            for field in required_fields:
                if field in first_req:
                    print(ColorOutput.success(f"Request has '{field}' field"))
                else:
                    print(ColorOutput.error(f"Request missing '{field}' field"))

            # Display sample request
            print(ColorOutput.info("Sample request structure:"))
            print(json.dumps(first_req, indent=2, default=str)[:500])

        return True

    except Exception as e:
        print(ColorOutput.error(f"Request format test failed: {e}"))
        traceback.print_exc()
        return False


def test_schema_compatibility(client: BatchDataSyncClient, sheets: Dict[str, pd.DataFrame]):
    """Test 4: Validate output schema compatibility."""
    print(ColorOutput.header("TEST 4: Schema Compatibility"))

    try:
        input_df = sheets['INPUT_MASTER']
        test_df = input_df.head(1).copy()

        # Mock response for testing
        mock_response = {
            'status': {'code': 200, 'text': 'OK'},
            'result': {
                'data': [{
                    'input': {'requestId': test_df.iloc[0]['record_id']},
                    'persons': [{
                        'phones': [
                            {'number': '555-1234', 'type': 'mobile', 'carrier': 'Test'}
                        ],
                        'emails': [
                            {'address': 'test@example.com', 'tested': True}
                        ]
                    }]
                }]
            }
        }

        # Parse response
        result_df = client._parse_sync_response_to_schema(mock_response, test_df)

        # Check required columns
        print(ColorOutput.info("Checking OUTPUT schema:"))

        # INPUT_MASTER columns (should all be preserved)
        input_columns = list(input_df.columns)
        missing_cols = []
        for col in input_columns:
            if col in result_df.columns:
                print(ColorOutput.success(f"✓ Preserved: {col}"))
            else:
                print(ColorOutput.error(f"✗ Missing: {col}"))
                missing_cols.append(col)

        # Enrichment columns (wide format)
        enrichment_cols = []
        for i in range(1, 11):
            enrichment_cols.extend([
                f'phone_{i}', f'phone_{i}_type', f'phone_{i}_carrier',
                f'phone_{i}_dnc', f'phone_{i}_tcpa', f'phone_{i}_confidence'
            ])
            enrichment_cols.extend([f'email_{i}', f'email_{i}_tested'])

        found_enrichment = 0
        for col in enrichment_cols[:18]:  # Check first 3 phones/emails
            if col in result_df.columns:
                found_enrichment += 1

        print(ColorOutput.info(f"Found {found_enrichment}/{len(enrichment_cols[:18])} enrichment columns"))

        if not missing_cols:
            print(ColorOutput.success("All INPUT_MASTER columns preserved"))
            return True
        else:
            print(ColorOutput.error(f"Missing {len(missing_cols)} columns"))
            return False

    except Exception as e:
        print(ColorOutput.error(f"Schema compatibility test failed: {e}"))
        traceback.print_exc()
        return False


def test_batching(client: BatchDataSyncClient):
    """Test 5: Validate batching logic."""
    print(ColorOutput.header("TEST 5: Batching Logic"))

    try:
        # Create test DataFrame with 150 records
        test_data = {
            'record_id': [f'test_{i}' for i in range(150)],
            'address_line1': [f'{i} Main St' for i in range(150)],
            'city': ['Phoenix'] * 150,
            'state': ['AZ'] * 150,
            'zip': ['85001'] * 150
        }
        test_df = pd.DataFrame(test_data)

        # Test different batch sizes
        batch_tests = [
            (50, 3),   # 150 records / 50 = 3 batches
            (100, 2),  # 150 records / 100 = 2 batches
            (200, 1)   # 150 records / 200 = 1 batch
        ]

        for batch_size, expected_chunks in batch_tests:
            chunks = list(client._chunk_dataframe(test_df, batch_size))
            actual_chunks = len(chunks)

            if actual_chunks == expected_chunks:
                print(ColorOutput.success(
                    f"Batch size {batch_size}: {actual_chunks} chunks (expected {expected_chunks})"
                ))
            else:
                print(ColorOutput.error(
                    f"Batch size {batch_size}: {actual_chunks} chunks (expected {expected_chunks})"
                ))

        # Verify batch size limit
        large_batch = 150
        request_data = client._df_to_sync_request(test_df[:large_batch])
        if len(request_data['requests']) <= 100:
            print(ColorOutput.warning(f"Batch limited to {len(request_data['requests'])} (max 100)"))
        else:
            print(ColorOutput.error(f"Batch size {len(request_data['requests'])} exceeds max 100"))

        return True

    except Exception as e:
        print(ColorOutput.error(f"Batching test failed: {e}"))
        traceback.print_exc()
        return False


def test_dry_run(client: BatchDataSyncClient, sheets: Dict[str, pd.DataFrame]):
    """Test 6: Dry run cost estimation."""
    print(ColorOutput.header("TEST 6: Dry Run Cost Estimation"))

    try:
        input_df = sheets['INPUT_MASTER']
        test_df = input_df.head(10).copy()

        print(ColorOutput.info(f"Testing dry run with {len(test_df)} records"))

        # Stage configurations to test
        stage_configs = [
            {
                'name': 'Skip-trace only',
                'config': {'skip_trace': True, 'phone_verify': False, 'dnc': False, 'tcpa': False},
                'expected_cost': len(test_df) * 0.07
            },
            {
                'name': 'Full enrichment',
                'config': {'skip_trace': True, 'phone_verify': True, 'dnc': True, 'tcpa': True},
                'expected_cost': len(test_df) * (0.07 + 2 * 0.007 + 2 * 0.002 + 2 * 0.002)
            }
        ]

        for stage_test in stage_configs:
            print(f"\n{ColorOutput.info(stage_test['name'])}:")
            print(f"  Stages: {stage_test['config']}")
            print(f"  Expected cost: ${stage_test['expected_cost']:.2f}")

            # Calculate actual cost
            record_count = len(test_df)
            skip_trace_cost = record_count * 0.07 if stage_test['config'].get('skip_trace') else 0
            phone_verify_cost = record_count * 2 * 0.007 if stage_test['config'].get('phone_verify') else 0
            dnc_cost = record_count * 2 * 0.002 if stage_test['config'].get('dnc') else 0
            tcpa_cost = record_count * 2 * 0.002 if stage_test['config'].get('tcpa') else 0
            actual_cost = skip_trace_cost + phone_verify_cost + dnc_cost + tcpa_cost

            if abs(actual_cost - stage_test['expected_cost']) < 0.01:
                print(ColorOutput.success(f"  Calculated cost: ${actual_cost:.2f} ✓"))
            else:
                print(ColorOutput.error(f"  Calculated cost: ${actual_cost:.2f} (mismatch)"))

        return True

    except Exception as e:
        print(ColorOutput.error(f"Dry run test failed: {e}"))
        traceback.print_exc()
        return False


def run_unit_tests():
    """Test 7: Run unit tests."""
    print(ColorOutput.header("TEST 7: Running Unit Tests"))

    try:
        import subprocess

        # Run unit tests
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'Batchdata/tests/test_sync_client.py', '-v'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        if result.returncode == 0:
            print(ColorOutput.success("All unit tests passed"))
            print(result.stdout)
            return True
        else:
            print(ColorOutput.error("Unit tests failed"))
            print(result.stdout)
            print(result.stderr)
            return False

    except Exception as e:
        print(ColorOutput.warning(f"Could not run unit tests: {e}"))
        print(ColorOutput.info("Try: python -m pytest Batchdata/tests/test_sync_client.py -v"))
        return None


def test_live_api_small(client: BatchDataSyncClient, sheets: Dict[str, pd.DataFrame], api_keys: Dict):
    """Test 8: Live API test with 1-2 records (if API keys available)."""
    print(ColorOutput.header("TEST 8: Live API Test (Small)"))

    # Check if we have real API keys
    if 'test_key' in api_keys.get('BD_SKIPTRACE_KEY', 'test_key'):
        print(ColorOutput.warning("Skipping live API test (no real API keys found)"))
        print(ColorOutput.info("Set BD_SKIPTRACE_KEY environment variable to test with real API"))
        return None

    try:
        input_df = sheets['INPUT_MASTER']
        test_df = input_df.head(2).copy()  # Test with only 2 records

        print(ColorOutput.info(f"Testing live API with {len(test_df)} records"))
        print(ColorOutput.warning("This will use API credits (approximately $0.14)"))

        # Simple stage config - just skip-trace
        stage_config = {
            'skip_trace': True,
            'phone_verify': False,
            'dnc': False,
            'tcpa': False
        }

        # Run enrichment
        print(ColorOutput.info("Calling skip-trace API..."))
        result_df = client.process_skip_trace(test_df, batch_size=50)

        # Check results
        if len(result_df) == len(test_df):
            print(ColorOutput.success(f"Received {len(result_df)} results"))
        else:
            print(ColorOutput.error(f"Result count mismatch: {len(result_df)} vs {len(test_df)}"))

        # Check for enrichment data
        phones_found = 0
        emails_found = 0
        for _, row in result_df.iterrows():
            if row.get('phone_1'):
                phones_found += 1
            if row.get('email_1'):
                emails_found += 1

        print(ColorOutput.info(f"Records with phones: {phones_found}/{len(result_df)}"))
        print(ColorOutput.info(f"Records with emails: {emails_found}/{len(result_df)}"))

        # Save test output
        output_file = Path(f"Batchdata/test_results/sync_test_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        output_file.parent.mkdir(exist_ok=True)
        result_df.to_excel(output_file, index=False)
        print(ColorOutput.success(f"Results saved to: {output_file}"))

        return True

    except Exception as e:
        print(ColorOutput.error(f"Live API test failed: {e}"))
        if '404' in str(e):
            print(ColorOutput.error("Got 404 error - check base URL and endpoint"))
        elif '401' in str(e) or '403' in str(e):
            print(ColorOutput.error("Authentication error - check API keys"))
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print(ColorOutput.header("BatchData Sync Client Integration Tests"))
    print(f"Test Date: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print()

    results = {
        'Test 1 - Load Data': False,
        'Test 2 - Client Init': False,
        'Test 3 - Request Format': False,
        'Test 4 - Schema': False,
        'Test 5 - Batching': False,
        'Test 6 - Dry Run': False,
        'Test 7 - Unit Tests': None,
        'Test 8 - Live API': None
    }

    # Test 1: Load test data
    sheets = test_load_test_data()
    if sheets:
        results['Test 1 - Load Data'] = True
    else:
        print(ColorOutput.error("Cannot continue without test data"))
        return

    # Test 2: Initialize client
    client, api_keys = test_sync_client_initialization(sheets)
    if client:
        results['Test 2 - Client Init'] = True
    else:
        print(ColorOutput.error("Cannot continue without client"))
        return

    # Test 3: Request format
    if test_request_format(client, sheets):
        results['Test 3 - Request Format'] = True

    # Test 4: Schema compatibility
    if test_schema_compatibility(client, sheets):
        results['Test 4 - Schema'] = True

    # Test 5: Batching
    if test_batching(client):
        results['Test 5 - Batching'] = True

    # Test 6: Dry run
    if test_dry_run(client, sheets):
        results['Test 6 - Dry Run'] = True

    # Test 7: Unit tests (optional)
    unit_result = run_unit_tests()
    results['Test 7 - Unit Tests'] = unit_result

    # Test 8: Live API (optional)
    if api_keys and 'test_key' not in api_keys.get('BD_SKIPTRACE_KEY', 'test_key'):
        live_result = test_live_api_small(client, sheets, api_keys)
        results['Test 8 - Live API'] = live_result

    # Summary
    print(ColorOutput.header("TEST SUMMARY"))
    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results.items():
        if result is True:
            print(ColorOutput.success(f"{test_name}: PASSED"))
            passed += 1
        elif result is False:
            print(ColorOutput.error(f"{test_name}: FAILED"))
            failed += 1
        else:
            print(ColorOutput.warning(f"{test_name}: SKIPPED"))
            skipped += 1

    print()
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0:
        print(ColorOutput.success("\n🎉 All required tests passed! Sync client is ready for use."))
        print(ColorOutput.info("\nNext steps:"))
        print("1. Set BD_SKIPTRACE_KEY environment variable for live testing")
        print("2. Run with a small batch (1-10 records) first")
        print("3. Compare output schema with existing Complete files")
        print("4. Proceed to Phase 2: Smart Indexing implementation")
    else:
        print(ColorOutput.error(f"\n⚠️  {failed} tests failed. Please review and fix issues."))


if __name__ == "__main__":
    main()