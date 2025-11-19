"""
test_sync_client.py - Unit tests for BatchDataSyncClient

Tests the synchronous BatchData API client implementation for:
- JSON request format
- Response parsing
- Record ID preservation
- Wide format conversion
- Batching logic
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.batchdata_sync import BatchDataSyncClient


class TestBatchDataSyncClient(unittest.TestCase):
    """Unit tests for BatchDataSyncClient."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_keys = {
            'BD_SKIPTRACE_KEY': 'test_skiptrace_key',
            'BD_ADDRESS_KEY': 'test_address_key',
            'BD_PROPERTY_KEY': 'test_property_key',
            'BD_PHONE_KEY': 'test_phone_key'
        }
        self.client = BatchDataSyncClient(self.api_keys)

        # Create sample input DataFrame
        self.sample_df = pd.DataFrame({
            'record_id': ['ecorp_123_1_abc', 'ecorp_124_1_def', 'ecorp_125_1_ghi'],
            'source_type': ['Entity', 'Entity', 'Entity'],
            'source_entity_name': ['Test Corp 1', 'Test Corp 2', 'Test Corp 3'],
            'source_entity_id': ['123', '124', '125'],
            'title_role': ['Manager', 'Member', 'Manager/Member'],
            'target_first_name': ['John', 'Jane', 'Bob'],
            'target_last_name': ['Smith', 'Doe', 'Johnson'],
            'owner_name_full': ['John Smith', 'Jane Doe', 'Bob Johnson'],
            'address_line1': ['123 Main St', '456 Oak Ave', '789 Pine Rd'],
            'address_line2': ['', 'Suite 200', 'Apt 3B'],
            'city': ['Phoenix', 'Scottsdale', 'Tempe'],
            'state': ['AZ', 'AZ', 'AZ'],
            'zip': ['85001', '85250', '85281'],
            'county': ['MARICOPA', 'MARICOPA', 'MARICOPA'],
            'apn': ['123-45-678', '987-65-432', '456-78-901'],
            'mailing_line1': ['', '', 'PO Box 123'],
            'mailing_city': ['', '', 'Phoenix'],
            'mailing_state': ['', '', 'AZ'],
            'mailing_zip': ['', '', '85002'],
            'notes': ['Test note 1', 'Test note 2', 'Test note 3']
        })

    def test_sync_request_format(self):
        """Test that DataFrame is correctly converted to API request format."""
        # Convert single row to request
        single_row_df = self.sample_df.iloc[:1]
        request_data = self.client._df_to_sync_request(single_row_df)

        # Verify structure
        self.assertIn('requests', request_data)
        self.assertEqual(len(request_data['requests']), 1)

        # Check first request
        first_request = request_data['requests'][0]
        self.assertEqual(first_request['requestId'], 'ecorp_123_1_abc')
        self.assertEqual(first_request['propertyAddress']['street'], '123 Main St')
        self.assertEqual(first_request['propertyAddress']['city'], 'Phoenix')
        self.assertEqual(first_request['propertyAddress']['state'], 'AZ')
        self.assertEqual(first_request['propertyAddress']['zip'], '85001')
        self.assertEqual(first_request['name']['first'], 'John')
        self.assertEqual(first_request['name']['last'], 'Smith')

    def test_sync_response_parsing(self):
        """Test that API response is correctly parsed to DataFrame."""
        # Mock API response
        mock_response = {
            'status': {'code': 200, 'text': 'OK'},
            'result': {
                'data': [
                    {
                        'input': {'requestId': 'ecorp_123_1_abc'},
                        'persons': [
                            {
                                'phones': [
                                    {
                                        'number': '555-1234',
                                        'type': 'mobile',
                                        'carrier': 'Verizon',
                                        'dnc': False,
                                        'tcpa': False,
                                        'score': 0.95
                                    },
                                    {
                                        'number': '555-5678',
                                        'type': 'landline',
                                        'carrier': 'AT&T',
                                        'dnc': True,
                                        'tcpa': False,
                                        'score': 0.85
                                    }
                                ],
                                'emails': [
                                    {
                                        'address': 'john.smith@example.com',
                                        'tested': True
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        # Parse response
        input_df = self.sample_df.iloc[:1]
        result_df = self.client._parse_sync_response_to_schema(mock_response, input_df)

        # Verify phone data is flattened
        self.assertEqual(result_df.iloc[0]['phone_1'], '555-1234')
        self.assertEqual(result_df.iloc[0]['phone_1_type'], 'mobile')
        self.assertEqual(result_df.iloc[0]['phone_1_carrier'], 'Verizon')
        self.assertEqual(result_df.iloc[0]['phone_1_dnc'], False)
        self.assertEqual(result_df.iloc[0]['phone_1_tcpa'], False)
        self.assertEqual(result_df.iloc[0]['phone_1_confidence'], 0.95)

        self.assertEqual(result_df.iloc[0]['phone_2'], '555-5678')
        self.assertEqual(result_df.iloc[0]['phone_2_type'], 'landline')
        self.assertEqual(result_df.iloc[0]['phone_2_dnc'], True)

        # Verify email data
        self.assertEqual(result_df.iloc[0]['email_1'], 'john.smith@example.com')
        self.assertEqual(result_df.iloc[0]['email_1_tested'], True)

    def test_record_id_preservation(self):
        """Test that record_id is preserved through the API round-trip."""
        # Create request
        request_data = self.client._df_to_sync_request(self.sample_df)

        # Verify all record_ids are in requests
        request_ids = [req['requestId'] for req in request_data['requests']]
        expected_ids = ['ecorp_123_1_abc', 'ecorp_124_1_def', 'ecorp_125_1_ghi']
        self.assertEqual(request_ids, expected_ids)

        # Mock response with same IDs
        mock_response = {
            'status': {'code': 200, 'text': 'OK'},
            'result': {
                'data': [
                    {'input': {'requestId': rid}, 'persons': []}
                    for rid in expected_ids
                ]
            }
        }

        # Parse response
        result_df = self.client._parse_sync_response_to_schema(mock_response, self.sample_df)

        # Verify record_ids are preserved
        self.assertEqual(list(result_df['record_id']), expected_ids)

    def test_phone_wide_format_conversion(self):
        """Test conversion of multiple phones to wide format (phone_1, phone_2, etc.)."""
        # Mock response with many phones
        mock_response = {
            'status': {'code': 200, 'text': 'OK'},
            'result': {
                'data': [
                    {
                        'input': {'requestId': 'ecorp_123_1_abc'},
                        'persons': [
                            {
                                'phones': [
                                    {'number': f'555-{1000+i:04d}', 'type': 'mobile'}
                                    for i in range(12)  # More than 10 phones
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        # Parse response
        input_df = self.sample_df.iloc[:1]
        result_df = self.client._parse_sync_response_to_schema(mock_response, input_df)

        # Verify only first 10 phones are stored
        for i in range(1, 11):
            self.assertEqual(result_df.iloc[0][f'phone_{i}'], f'555-{999+i:04d}')

        # Verify phone_11 doesn't exist (only 10 phones max)
        self.assertNotIn('phone_11', result_df.columns)

    def test_batching_with_100_records(self):
        """Test that batching works correctly with exactly 100 records."""
        # Create DataFrame with 100 records
        large_df = pd.concat([self.sample_df] * 34, ignore_index=True)[:100]
        large_df['record_id'] = [f'ecorp_{i}_1_xyz' for i in range(100)]

        # Test chunking
        chunks = list(self.client._chunk_dataframe(large_df, 100))
        self.assertEqual(len(chunks), 1)  # Should be single chunk
        self.assertEqual(len(chunks[0]), 100)

    def test_batching_with_200_records(self):
        """Test that batching works correctly with 200 records (should split into 2 batches)."""
        # Create DataFrame with 200 records
        large_df = pd.concat([self.sample_df] * 67, ignore_index=True)[:200]
        large_df['record_id'] = [f'ecorp_{i}_1_xyz' for i in range(200)]

        # Test chunking with batch_size=100
        chunks = list(self.client._chunk_dataframe(large_df, 100))
        self.assertEqual(len(chunks), 2)  # Should be 2 chunks
        self.assertEqual(len(chunks[0]), 100)
        self.assertEqual(len(chunks[1]), 100)

        # Test chunking with batch_size=50 (recommended)
        chunks = list(self.client._chunk_dataframe(large_df, 50))
        self.assertEqual(len(chunks), 4)  # Should be 4 chunks
        for chunk in chunks:
            self.assertEqual(len(chunk), 50)

    def test_all_input_columns_preserved(self):
        """Test that all INPUT_MASTER columns are preserved in output."""
        # Mock empty response (no matches)
        mock_response = {
            'status': {'code': 200, 'text': 'OK'},
            'result': {'data': []}
        }

        # Parse response
        result_df = self.client._parse_sync_response_to_schema(mock_response, self.sample_df)

        # Verify all original columns are present
        for col in self.sample_df.columns:
            self.assertIn(col, result_df.columns)
            # Verify values are preserved
            for i in range(len(self.sample_df)):
                self.assertEqual(
                    str(result_df.iloc[i][col]),
                    str(self.sample_df.iloc[i][col])
                )

    def test_api_status_tracking(self):
        """Test that API status is properly tracked in results."""
        # Test successful response
        mock_response = {
            'status': {'code': 200, 'text': 'OK'},
            'result': {
                'data': [
                    {
                        'input': {'requestId': 'ecorp_123_1_abc'},
                        'persons': [{'phones': [], 'emails': []}]
                    }
                ]
            }
        }

        input_df = self.sample_df.iloc[:1]
        result_df = self.client._parse_sync_response_to_schema(mock_response, input_df)

        self.assertEqual(result_df.iloc[0]['api_status'], 'success')
        self.assertEqual(result_df.iloc[0]['persons_found'], 1)
        self.assertEqual(result_df.iloc[0]['phones_found'], 0)
        self.assertEqual(result_df.iloc[0]['emails_found'], 0)

        # Test no match
        mock_response_no_match = {
            'status': {'code': 200, 'text': 'OK'},
            'result': {'data': []}
        }

        result_df = self.client._parse_sync_response_to_schema(mock_response_no_match, input_df)
        self.assertEqual(result_df.iloc[0]['api_status'], 'no_match')

    @patch('requests.Session.post')
    def test_api_error_handling(self, mock_post):
        """Test handling of API errors."""
        # Mock 404 error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_post.return_value = mock_response

        # Should raise exception
        with self.assertRaises(Exception) as context:
            self.client._call_skip_trace_api({'requests': []})

        self.assertIn('404', str(context.exception))

    def test_stage_config_execution(self):
        """Test that stage configuration properly controls which APIs are called."""
        # Test with only skip_trace enabled
        stage_config = {
            'skip_trace': True,
            'phone_verify': False,
            'dnc': False,
            'tcpa': False
        }

        with patch.object(self.client, 'process_skip_trace') as mock_skip_trace:
            mock_skip_trace.return_value = self.sample_df

            result = self.client.run_enrichment_pipeline(self.sample_df, stage_config)

            # Verify skip_trace was called
            mock_skip_trace.assert_called_once()

            # Verify result has pipeline metadata
            self.assertIn('pipeline_version', result.columns)
            self.assertIn('pipeline_timestamp', result.columns)
            self.assertIn('stages_applied', result.columns)


if __name__ == '__main__':
    unittest.main()