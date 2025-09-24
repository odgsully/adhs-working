#!/usr/bin/env python3
"""
MCAO API Response Discovery Script
===================================

Tests the MCAO API with known APNs to discover the actual response structure.
This will help us understand what fields the API returns and how they're structured.
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mcao_api(apn: str, save_responses: bool = True):
    """
    Test all MCAO API endpoints with a given APN and display/save raw responses.

    Args:
        apn: Assessor Parcel Number to test
        save_responses: Whether to save responses to files
    """

    # Get API key
    api_key = os.getenv("MCAO_API_KEY")
    if not api_key:
        print("❌ MCAO_API_KEY not found in environment")
        return

    print(f"🔑 Using API Key: {api_key[:8]}...")
    print(f"🏠 Testing APN: {apn}")
    print("="*60)

    # Setup session
    session = requests.Session()
    session.headers.update({
        "AUTHORIZATION": api_key,
        "user-agent": "null"  # Required by MCAO API
    })

    # Base URL
    base_url = "https://mcassessor.maricopa.gov"

    # Define all endpoints to test
    endpoints = [
        (f"/parcel/{apn}", "Parcel Details"),
        (f"/parcel/{apn}/propertyinfo", "Property Info"),
        (f"/parcel/{apn}/address", "Property Address"),
        (f"/parcel/{apn}/valuations", "Valuations (5 years)"),
        (f"/parcel/{apn}/residential-details", "Residential Details"),
        (f"/parcel/{apn}/owner-details", "Owner Details"),
    ]

    # Create output directory if saving
    if save_responses:
        output_dir = Path("MCAO/API_Responses")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_responses = {}

    for endpoint, description in endpoints:
        print(f"\n📍 Testing: {description}")
        print(f"   Endpoint: {endpoint}")
        print("-"*50)

        try:
            # Make request
            url = base_url + endpoint
            response = session.get(url, timeout=20)

            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                # Parse JSON
                data = response.json()

                # Save to collection
                endpoint_name = endpoint.split('/')[-1] if '/' in endpoint else 'parcel'
                if endpoint_name == apn:
                    endpoint_name = 'parcel'
                all_responses[endpoint_name] = data

                # Display structure
                print(f"   ✅ Success! Response structure:")

                # Show keys and types
                if isinstance(data, dict):
                    print(f"   Root type: dict with {len(data)} keys")
                    for key in list(data.keys())[:10]:  # Show first 10 keys
                        value = data[key]
                        value_type = type(value).__name__
                        if isinstance(value, dict):
                            print(f"     • {key}: dict ({len(value)} keys)")
                        elif isinstance(value, list):
                            print(f"     • {key}: list ({len(value)} items)")
                        elif isinstance(value, str):
                            preview = value[:50] + "..." if len(value) > 50 else value
                            print(f"     • {key}: str = '{preview}'")
                        else:
                            print(f"     • {key}: {value_type} = {value}")

                    if len(data) > 10:
                        print(f"     ... and {len(data) - 10} more keys")

                elif isinstance(data, list):
                    print(f"   Root type: list with {len(data)} items")
                    if data and isinstance(data[0], dict):
                        print(f"   First item keys: {list(data[0].keys())[:10]}")

                # Save full response if requested
                if save_responses:
                    filename = f"{apn}_{endpoint_name}_{timestamp}.json"
                    filepath = output_dir / filename
                    with open(filepath, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"   💾 Saved to: {filepath.name}")

            elif response.status_code == 404:
                print(f"   ⚠️  404 Not Found - This endpoint may not have data for this APN")
                all_responses[endpoint.split('/')[-1]] = None

            else:
                print(f"   ❌ Error: Status {response.status_code}")
                print(f"   Response: {response.text[:200]}")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"   ❌ Failed to parse JSON: {e}")
            print(f"   Raw response: {response.text[:200]}")

    # Display summary
    print("\n" + "="*60)
    print("📊 SUMMARY OF API RESPONSES")
    print("="*60)

    # Analyze field mappings
    print("\n🔍 Field Analysis for MAX_HEADERS Mapping:")

    # Expected MAX_HEADERS fields (first few as examples)
    expected_fields = [
        'Owner_OwnerID',
        'Owner_Ownership',
        'Owner_OwnerName',
        'Owner_FullMailingAddress',
        'PropertyID',
        'PropertyType',
        'YearBuilt'
    ]

    print("\nSearching for fields that might map to MAX_HEADERS...")

    # Search all responses for potential matches
    for endpoint_name, data in all_responses.items():
        if data is None:
            continue

        print(f"\n📌 From {endpoint_name}:")

        if isinstance(data, dict):
            # Flatten nested structure for analysis
            flat_fields = flatten_dict(data)

            # Look for potential matches
            for field_path, value in flat_fields.items():
                # Check if field name might relate to our expected columns
                field_lower = field_path.lower()

                if any(term in field_lower for term in ['owner', 'sale', 'price', 'year', 'property', 'address', 'mail']):
                    value_preview = str(value)[:50] if value else "None"
                    print(f"   • {field_path} = {value_preview}")

    # Save combined response for analysis
    if save_responses:
        combined_file = output_dir / f"{apn}_COMBINED_{timestamp}.json"
        with open(combined_file, 'w') as f:
            json.dump(all_responses, f, indent=2)
        print(f"\n💾 Combined responses saved to: {combined_file}")

        # Also save a field mapping analysis
        analysis_file = output_dir / f"{apn}_FIELD_ANALYSIS_{timestamp}.txt"
        with open(analysis_file, 'w') as f:
            f.write("MCAO API Field Analysis\n")
            f.write("="*60 + "\n\n")

            for endpoint_name, data in all_responses.items():
                if data is None:
                    continue

                f.write(f"\nEndpoint: {endpoint_name}\n")
                f.write("-"*40 + "\n")

                if isinstance(data, dict):
                    flat = flatten_dict(data)
                    for path, value in flat.items():
                        f.write(f"{path} = {value}\n")
                elif isinstance(data, list) and data:
                    f.write(f"List with {len(data)} items\n")
                    if isinstance(data[0], dict):
                        flat = flatten_dict(data[0])
                        for path, value in flat.items():
                            f.write(f"[0].{path} = {value}\n")

        print(f"📝 Field analysis saved to: {analysis_file}")

def flatten_dict(d, parent_key='', sep='.'):
    """
    Flatten a nested dictionary to make field analysis easier.
    """
    items = []
    if isinstance(d, dict):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                if v and isinstance(v[0], dict):
                    items.extend(flatten_dict(v[0], f"{new_key}[0]", sep=sep).items())
                else:
                    items.append((new_key, v))
            else:
                items.append((new_key, v))
    return dict(items)

def main():
    """Main function to test MCAO API."""

    print("\n🔬 MCAO API Response Discovery Tool")
    print("="*60)

    # Test APNs - using ones from your data
    test_apns = [
        "165-28-054",  # From 1.25_APN_Complete
        "301-97-837",  # From 1.25_APN_Complete
        # Add more known valid APNs here
    ]

    print(f"Available test APNs:")
    for i, apn in enumerate(test_apns, 1):
        print(f"  {i}. {apn}")

    # Get user choice
    choice = input("\nEnter APN number (1-{}) or custom APN: ".format(len(test_apns)))

    if choice.isdigit() and 1 <= int(choice) <= len(test_apns):
        selected_apn = test_apns[int(choice) - 1]
    else:
        selected_apn = choice.strip()

    if not selected_apn:
        print("No APN selected")
        return

    # Test the API
    test_mcao_api(selected_apn)

    print("\n✅ Discovery complete! Check MCAO/API_Responses/ for saved responses.")
    print("📋 Next steps:")
    print("   1. Review the JSON files to understand the structure")
    print("   2. Update field mappings in mcao_client.py")
    print("   3. Test with the updated mappings")

if __name__ == "__main__":
    main()