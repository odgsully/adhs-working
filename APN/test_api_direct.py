#!/usr/bin/env python3
"""
Direct test of Maricopa County GIS API endpoints.
Usage: python3 APN/test_api_direct.py
"""
import requests
import json

# Test addresses from recent Upload file
TEST_ADDRESSES = [
    "14650 WEST ACAPULCO LANE, SURPRISE, 85379",
    "7403 WEST MALDONADO ROAD, LAVEEN, 85339",
    "3003 EAST MCDOWELL ROAD, PHOENIX, 85008"
]

# Test 1: Geocoder endpoint
print("="*80)
print("TEST 1: Geocoding Endpoint")
print("="*80)

geocoder_url = "https://gis.mcassessor.maricopa.gov/arcgis/rest/services/AssessorCompositeLocator/GeocodeServer/findAddressCandidates"

for addr in TEST_ADDRESSES:
    print(f"\nAddress: {addr}")
    params = {
        'SingleLine': addr,
        'f': 'json'
    }

    try:
        response = requests.get(geocoder_url, params=params, timeout=10)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and data['candidates']:
                candidate = data['candidates'][0]
                print(f"  ✓ Geocoded: ({candidate['location']['x']}, {candidate['location']['y']})")
                print(f"    Score: {candidate.get('score', 'N/A')}")
            else:
                print(f"  ✗ No candidates found")
                print(f"  Response: {json.dumps(data, indent=2)[:200]}")
        else:
            print(f"  ✗ HTTP Error: {response.text[:200]}")
    except Exception as e:
        print(f"  ✗ Exception: {e}")

# Test 2: Parcels query endpoint
print("\n" + "="*80)
print("TEST 2: Parcels Query Endpoint")
print("="*80)

parcels_url = "https://gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/0/query"

test_where = "PHYSICAL_STREET_NUM = '14650' AND PHYSICAL_STREET_NAME = 'ACAPULCO' AND PHYSICAL_STREET_TYPE = 'LN' AND PHYSICAL_CITY = 'SURPRISE'"

print(f"\nWHERE clause: {test_where}")

params = {
    'where': test_where,
    'outFields': 'APN,APN_DASH,PHYSICAL_ADDRESS',
    'f': 'json',
    'returnGeometry': 'false'
}

try:
    response = requests.get(parcels_url, params=params, timeout=10)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if 'features' in data and data['features']:
            print(f"✓ Found {len(data['features'])} parcels")
            for feature in data['features']:
                attrs = feature.get('attributes', {})
                print(f"  APN: {attrs.get('APN_DASH', 'N/A')}")
                print(f"  Address: {attrs.get('PHYSICAL_ADDRESS', 'N/A')}")
        else:
            print(f"✗ No features found")
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"✗ HTTP Error: {response.text[:200]}")
except Exception as e:
    print(f"✗ Exception: {e}")

print("\n" + "="*80)
print("API TEST COMPLETE")
print("="*80)
