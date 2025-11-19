"""
batchdata.py - HTTP client for BatchData async endpoints
"""

import os
import time
import asyncio
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json


class BatchDataClient:
    """Client for BatchData API endpoints with async job management."""
    
    def __init__(self, api_keys: Dict[str, str], base_url: str = "https://api.batchdata.com/api/v2"):
        """Initialize BatchData client.

        Args:
            api_keys: Dictionary of API keys for different services
            base_url: Base API URL (defaults to v2 API for wallet credit accounts)
        """
        self.base_url = base_url.rstrip('/')
        self.api_keys = api_keys
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'BatchData-Pipeline/1.0'})
        
    def _get_headers(self, service_type: str) -> Dict[str, str]:
        """Get headers with appropriate API key for service type.
        
        Args:
            service_type: Type of service (skiptrace, address, property, phone)
            
        Returns:
            Request headers with authorization
        """
        key_map = {
            'skiptrace': 'BD_SKIPTRACE_KEY',
            'address': 'BD_ADDRESS_KEY', 
            'property': 'BD_PROPERTY_KEY',
            'phone': 'BD_PHONE_KEY'
        }
        
        api_key = self.api_keys.get(key_map.get(service_type, ''))
        if not api_key:
            raise ValueError(f"API key not found for service type: {service_type}")
            
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def submit_csv_batch(self, csv_path: str, endpoint: str, service_type: str) -> str:
        """Submit CSV batch for async processing.
        
        Args:
            csv_path: Path to CSV file
            endpoint: API endpoint name
            service_type: Service type for API key selection
            
        Returns:
            Job ID for polling
        """
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers(service_type)
        headers.pop('Content-Type')  # Remove for multipart upload
        
        with open(csv_path, 'rb') as f:
            files = {'file': (os.path.basename(csv_path), f, 'text/csv')}
            
            response = self.session.post(url, files=files, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result.get('job_id')
    
    def poll_job_status(self, job_id: str, service_type: str, 
                       poll_interval: int = 15, max_attempts: int = 120) -> Dict[str, Any]:
        """Poll job status until completion.
        
        Args:
            job_id: Job ID to poll
            service_type: Service type for API key
            poll_interval: Seconds between polls
            max_attempts: Maximum polling attempts
            
        Returns:
            Final job status response
        """
        url = f"{self.base_url}/jobs/{job_id}"
        headers = self._get_headers(service_type)
        
        for attempt in range(max_attempts):
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            status_data = response.json()
            status = status_data.get('status', '').lower()
            
            print(f"Job {job_id}: {status} (attempt {attempt + 1})")
            
            if status in ['completed', 'failed', 'cancelled']:
                return status_data
            elif status in ['pending', 'running', 'processing']:
                time.sleep(poll_interval)
            else:
                raise ValueError(f"Unknown job status: {status}")
        
        raise TimeoutError(f"Job {job_id} did not complete within {max_attempts} attempts")
    
    def download_job_results(self, job_id: str, service_type: str, output_path: str) -> str:
        """Download job results to file.
        
        Args:
            job_id: Job ID
            service_type: Service type for API key
            output_path: Local path to save results
            
        Returns:
            Path to downloaded file
        """
        url = f"{self.base_url}/jobs/{job_id}/download"
        headers = self._get_headers(service_type)
        
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        return output_path
    
    def process_batch_async(self, csv_path: str, endpoint: str, service_type: str,
                           output_path: str, poll_interval: int = 15) -> pd.DataFrame:
        """Submit batch, poll until complete, and return results.
        
        Args:
            csv_path: Input CSV path
            endpoint: API endpoint
            service_type: Service type
            output_path: Output file path
            poll_interval: Polling interval in seconds
            
        Returns:
            Results DataFrame
        """
        print(f"Submitting batch to {endpoint}...")
        job_id = self.submit_csv_batch(csv_path, endpoint, service_type)
        print(f"Job submitted: {job_id}")
        
        print("Polling for completion...")
        status_data = self.poll_job_status(job_id, service_type, poll_interval)
        
        if status_data.get('status', '').lower() != 'completed':
            raise RuntimeError(f"Job {job_id} failed: {status_data}")
        
        print("Downloading results...")
        self.download_job_results(job_id, service_type, output_path)
        
        # Load results as DataFrame
        try:
            if output_path.endswith('.xlsx'):
                return pd.read_excel(output_path)
            else:
                return pd.read_csv(output_path)
        except Exception as e:
            print(f"Error loading results: {e}")
            return pd.DataFrame()
    
    def estimate_cost(self, record_count: int, config: Dict[str, Any]) -> Dict[str, float]:
        """Estimate processing costs based on configuration.
        
        Args:
            record_count: Number of records to process
            config: Configuration dictionary
            
        Returns:
            Cost breakdown by service
        """
        costs = {}
        
        # Skip-trace base cost: 7¢ per record
        costs['skip_trace'] = record_count * 0.07
        
        # Estimate phone results (assume 2 phones per record on average)
        estimated_phones = record_count * 2
        
        if config.get('workflow.enable_phone_verification', False):
            costs['phone_verification'] = estimated_phones * 0.007  # 0.7¢
            
        if config.get('workflow.enable_phone_dnc', False):
            costs['phone_dnc'] = estimated_phones * 0.002  # 0.2¢
            
        if config.get('workflow.enable_phone_tcpa', False):
            costs['phone_tcpa'] = estimated_phones * 0.002  # 0.2¢
        
        # Optional services
        if config.get('workflow.enable_address_verify', False):
            costs['address_verify'] = record_count * 0.01  # Estimated 1¢
            
        if config.get('workflow.enable_property_search', False):
            costs['property_search'] = record_count * 0.05  # Estimated 5¢
            
        if config.get('workflow.enable_property_lookup', False):
            costs['property_lookup'] = record_count * 0.03  # Estimated 3¢
        
        costs['total'] = sum(costs.values())
        return costs
    
    def run_skip_trace_pipeline(self, input_df: pd.DataFrame, results_dir: str, 
                               config: Dict[str, Any]) -> Tuple[pd.DataFrame, List[pd.DataFrame]]:
        """Run complete skip-trace pipeline with optional scrubs.
        
        Args:
            input_df: Input DataFrame in BatchData format
            results_dir: Results directory
            config: Configuration settings
            
        Returns:
            Tuple of (final_results_df, intermediate_results_list)
        """
        timestamp = datetime.now().strftime("%m.%d.%I-%M-%S")
        intermediate_results = []
        
        # Import save_api_result for organized output
        from .io import save_api_result
        
        # Step 1: Skip-trace
        print("=== Running Skip-Trace ===")
        # Save input in skiptrace subfolder
        skiptrace_input_path = save_api_result(input_df, results_dir, 'skiptrace', f"input_{timestamp}", 'csv')  # BatchData APIs require CSV
        print(f"Skip-trace input saved: {skiptrace_input_path}")
        
        # Process skip-trace
        skiptrace_output = os.path.join(results_dir, 'skiptrace', f"results_{timestamp}.xlsx")
        skiptrace_df = self.process_batch_async(
            skiptrace_input_path, 'property/skip-trace/async', 'property', skiptrace_output
        )
        
        # Save complete results with ALL fields
        if not skiptrace_df.empty:
            complete_output_path = save_api_result(skiptrace_df, results_dir, 'skiptrace', f"complete_{timestamp}", 'xlsx')
            print(f"Complete skip-trace results saved: {complete_output_path}")
        
        intermediate_results.append(skiptrace_df)
        current_df = skiptrace_df
        
        # Step 2: Phone Verification (if enabled)
        if config.get('workflow.enable_phone_verification', False):
            print("=== Running Phone Verification ===")
            # Extract phones for verification
            phone_df = self._extract_phones_for_verification(current_df)
            if not phone_df.empty:
                # Save in phoneverify subfolder
                phone_input_path = save_api_result(phone_df, results_dir, 'phoneverify', f"input_{timestamp}", 'csv')  # BatchData APIs require CSV
                print(f"Phone verification input saved: {phone_input_path}")
                
                verification_output = os.path.join(results_dir, 'phoneverify', f"results_{timestamp}.xlsx")
                verification_df = self.process_batch_async(
                    phone_input_path, 'phone/verification/async', 'phone', verification_output
                )
                
                # Save complete results
                if not verification_df.empty:
                    complete_output_path = save_api_result(verification_df, results_dir, 'phoneverify', f"complete_{timestamp}", 'xlsx')
                    print(f"Complete phone verification results saved: {complete_output_path}")
                
                intermediate_results.append(verification_df)
        
        # Step 3: DNC Check (if enabled)
        if config.get('workflow.enable_phone_dnc', False):
            print("=== Running DNC Check ===")
            phone_df = self._extract_phones_for_dnc(current_df)
            if not phone_df.empty:
                # Save in dnc subfolder
                dnc_input_path = save_api_result(phone_df, results_dir, 'dnc', f"input_{timestamp}", 'csv')  # BatchData APIs require CSV
                print(f"DNC check input saved: {dnc_input_path}")
                
                dnc_output = os.path.join(results_dir, 'dnc', f"results_{timestamp}.xlsx")
                dnc_df = self.process_batch_async(
                    dnc_input_path, 'phone/dnc/async', 'phone', dnc_output
                )
                
                # Save complete results
                if not dnc_df.empty:
                    complete_output_path = save_api_result(dnc_df, results_dir, 'dnc', f"complete_{timestamp}", 'xlsx')
                    print(f"Complete DNC results saved: {complete_output_path}")
                
                intermediate_results.append(dnc_df)
        
        # Step 4: TCPA Check (if enabled)  
        if config.get('workflow.enable_phone_tcpa', False):
            print("=== Running TCPA Check ===")
            phone_df = self._extract_phones_for_tcpa(current_df)
            if not phone_df.empty:
                # Save in tcpa subfolder
                tcpa_input_path = save_api_result(phone_df, results_dir, 'tcpa', f"input_{timestamp}", 'csv')  # BatchData APIs require CSV
                print(f"TCPA check input saved: {tcpa_input_path}")
                
                tcpa_output = os.path.join(results_dir, 'tcpa', f"results_{timestamp}.xlsx")
                tcpa_df = self.process_batch_async(
                    tcpa_input_path, 'phone/tcpa/async', 'phone', tcpa_output
                )
                
                # Save complete results
                if not tcpa_df.empty:
                    complete_output_path = save_api_result(tcpa_df, results_dir, 'tcpa', f"complete_{timestamp}", 'xlsx')
                    print(f"Complete TCPA results saved: {complete_output_path}")
                
                intermediate_results.append(tcpa_df)
        
        return current_df, intermediate_results
    
    def _extract_phones_for_verification(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique phones for verification."""
        phone_cols = [col for col in df.columns if 'phone' in col.lower() and 'number' in col.lower()]
        
        phones = []
        for col in phone_cols:
            unique_phones = df[col].dropna().unique()
            for phone in unique_phones:
                phones.append({'phone': phone})
        
        return pd.DataFrame(phones).drop_duplicates()
    
    def _extract_phones_for_dnc(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract phones for DNC check."""
        return self._extract_phones_for_verification(df)
    
    def _extract_phones_for_tcpa(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract phones for TCPA check."""  
        return self._extract_phones_for_verification(df)


def create_client_from_env() -> BatchDataClient:
    """Create BatchData client using environment variables.
    
    Returns:
        Configured BatchDataClient instance
    """
    api_keys = {
        'BD_SKIPTRACE_KEY': os.getenv('BD_SKIPTRACE_KEY'),
        'BD_ADDRESS_KEY': os.getenv('BD_ADDRESS_KEY'),
        'BD_PROPERTY_KEY': os.getenv('BD_PROPERTY_KEY'),
        'BD_PHONE_KEY': os.getenv('BD_PHONE_KEY')
    }
    
    # Check that at least skip-trace key is available
    if not api_keys['BD_SKIPTRACE_KEY']:
        raise ValueError("BD_SKIPTRACE_KEY environment variable is required")
    
    return BatchDataClient(api_keys)