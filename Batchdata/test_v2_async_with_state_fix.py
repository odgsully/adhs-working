#!/usr/bin/env python3
"""
Test script for BatchData V2 async API with state field fix
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from transform import transform_ecorp_to_batchdata, validate_input_fields, optimize_for_api
from batchdata import BatchDataClient
from dotenv import load_dotenv

def test_v2_async_pipeline():
    """Test V2 async pipeline with fixed state field using Domicile State fallback."""

    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}")

    # Get API key from environment
    api_key = os.getenv('BD_PROPERTY_KEY')
    if not api_key:
        print("❌ Error: BD_PROPERTY_KEY not found in .env file")
        print("   Please ensure your .env file contains: BD_PROPERTY_KEY=your_api_key")
        return False

    print(f"✓ API Key found (starts with: {api_key[:10]}...)")

    # Find the most recent Ecorp Complete file
    ecorp_pattern = "Ecorp/Complete/*.xlsx"
    ecorp_files = list(Path(__file__).parent.parent.glob(ecorp_pattern))

    if not ecorp_files:
        print(f"❌ No Ecorp Complete files found in {ecorp_pattern}")
        return False

    # Sort by modification time and get most recent
    ecorp_file = max(ecorp_files, key=lambda p: p.stat().st_mtime)
    print(f"✓ Using Ecorp file: {ecorp_file.name}")

    # Load Ecorp data
    print("\n📊 Loading Ecorp data...")
    ecorp_df = pd.read_excel(ecorp_file)
    print(f"   Loaded {len(ecorp_df)} Ecorp records")

    # Check if Domicile State column exists
    if 'Domicile State' in ecorp_df.columns:
        print(f"✓ Found 'Domicile State' column")
        non_empty_states = ecorp_df['Domicile State'].notna().sum()
        print(f"   {non_empty_states} records have Domicile State values")
    else:
        print("⚠️  'Domicile State' column not found in Ecorp data")

    # Transform to BatchData format (with state field fix)
    print("\n🔄 Transforming to BatchData format with state field fix...")
    batchdata_df = transform_ecorp_to_batchdata(ecorp_df)
    print(f"✓ Transformed to {len(batchdata_df)} BatchData records")

    # Validate state field population
    print("\n📊 Validating state field population...")
    states_populated = batchdata_df['state'].notna() & (batchdata_df['state'] != '')
    populated_count = states_populated.sum()
    total_count = len(batchdata_df)
    percentage = (populated_count / total_count * 100) if total_count > 0 else 0

    print(f"   State field populated: {populated_count}/{total_count} ({percentage:.1f}%)")

    # Show state value distribution
    if populated_count > 0:
        state_counts = batchdata_df[batchdata_df['state'] != '']['state'].value_counts().head(5)
        print("   Top states:")
        for state, count in state_counts.items():
            print(f"     - {state}: {count} records")

    # Validate all input fields
    print("\n📊 Validating all input fields...")
    validated_df = validate_input_fields(batchdata_df)

    # Optimize fields for better API results
    print("\n🔧 Optimizing fields for API...")
    optimized_df = optimize_for_api(validated_df)

    # Take a sample for testing (first 10 records)
    test_sample = optimized_df.head(10)
    print(f"\n📝 Using {len(test_sample)} sample records for V2 API test")

    # Save test input
    timestamp = datetime.now().strftime("%m.%d.%I-%M-%S")
    test_dir = Path(__file__).parent / 'test_results'
    test_dir.mkdir(exist_ok=True)

    input_file = test_dir / f"v2_test_input_{timestamp}.csv"
    test_sample.to_csv(input_file, index=False)
    print(f"✓ Test input saved to: {input_file.name}")

    # Display sample of data being sent
    print("\n📋 Sample of data being sent to V2 API:")
    display_cols = ['target_first_name', 'target_last_name', 'address_line1', 'city', 'state', 'zip']
    available_cols = [col for col in display_cols if col in test_sample.columns]
    print(test_sample[available_cols].head(3).to_string())

    # Initialize V2 client
    print("\n🚀 Initializing BatchData V2 client...")
    api_keys = {'BD_PROPERTY_KEY': api_key}
    client = BatchDataClient(api_keys, base_url="https://api.batchdata.com/api/v2")
    print(f"✓ Client initialized with base URL: {client.base_url}")

    # Test V2 async pipeline
    print("\n🔄 Testing V2 async pipeline...")
    try:
        # Submit CSV for processing
        print("   Submitting CSV to V2 skip-trace endpoint...")
        job_id = client.submit_csv_batch(
            str(input_file),
            'property/skip-trace/async',
            'property'
        )
        print(f"✓ Job submitted successfully! Job ID: {job_id}")

        # Poll for completion
        print("   Polling for job completion...")
        status_data = client.poll_job_status(job_id, 'property', poll_interval=10, max_attempts=30)

        if status_data.get('status', '').lower() == 'completed':
            print("✓ Job completed successfully!")

            # Download results
            output_file = test_dir / f"v2_test_results_{timestamp}.xlsx"
            print(f"   Downloading results to: {output_file.name}")
            client.download_job_results(job_id, 'property', str(output_file))

            # Load and analyze results
            results_df = pd.read_excel(output_file)
            print(f"✓ Results downloaded: {len(results_df)} records")

            # Check for enriched data
            print("\n📊 Analyzing enriched data:")

            # Check for phone columns
            phone_cols = [col for col in results_df.columns if 'phone' in col.lower()]
            if phone_cols:
                print(f"✓ Found {len(phone_cols)} phone columns:")
                for col in phone_cols[:5]:
                    non_empty = results_df[col].notna().sum()
                    if non_empty > 0:
                        print(f"     - {col}: {non_empty} values")

            # Check for email columns
            email_cols = [col for col in results_df.columns if 'email' in col.lower()]
            if email_cols:
                print(f"✓ Found {len(email_cols)} email columns:")
                for col in email_cols[:5]:
                    non_empty = results_df[col].notna().sum()
                    if non_empty > 0:
                        print(f"     - {col}: {non_empty} values")

            print("\n✅ V2 async pipeline test completed successfully!")
            print(f"   Results saved to: {output_file}")
            return True

        else:
            print(f"❌ Job failed with status: {status_data.get('status')}")
            print(f"   Error details: {status_data.get('error', 'No error details available')}")
            return False

    except Exception as e:
        print(f"❌ Error during V2 API test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("BatchData V2 Async Pipeline Test with State Field Fix")
    print("=" * 60)

    success = test_v2_async_pipeline()

    if success:
        print("\n✅ All tests passed! V2 async pipeline is working with state field fix.")
    else:
        print("\n❌ Tests failed. Please check the errors above.")

    sys.exit(0 if success else 1)