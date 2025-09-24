"""
MCAO API Client for Property Data Enrichment
=============================================

This module provides a client for the Maricopa County Assessor's Office API
to retrieve comprehensive property data based on Assessor Parcel Numbers (APNs).
"""

import os
import time
import json
import random
from typing import Dict, Optional, List, Any, Tuple
from pathlib import Path
from datetime import datetime
import requests
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class MCAAOAPIClient:
    """Client for Maricopa County Assessor's Office API."""

    BASE_URL = "https://mcassessor.maricopa.gov"

    def __init__(self, api_key: Optional[str] = None, rate_limit: float = 5.0):
        """
        Initialize MCAO API client.

        Args:
            api_key: MCAO API key (defaults to env var MCAO_API_KEY)
            rate_limit: Requests per second limit (default 5.0)
        """
        self.api_key = api_key or os.getenv("MCAO_API_KEY")
        if not self.api_key:
            raise ValueError("MCAO_API_KEY must be provided or set in environment")

        self.rate_limit = rate_limit
        self.last_request_time = 0

        # Setup session with required headers
        self.session = requests.Session()
        self.session.headers.update({
            "AUTHORIZATION": self.api_key,
            "user-agent": "null"  # Required by MCAO API
        })

    def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        if self.rate_limit <= 0:
            return

        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self.last_request_time

        if elapsed < min_interval:
            # Add small random jitter (0-150ms)
            sleep_time = (min_interval - elapsed) + random.uniform(0, 0.15)
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Make a request to the MCAO API with retry logic.

        Args:
            endpoint: API endpoint path
            max_retries: Maximum number of retry attempts

        Returns:
            JSON response as dictionary or None if failed
        """
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(max_retries):
            try:
                self._rate_limit_wait()
                response = self.session.get(url, timeout=20)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.debug(f"404 Not Found: {endpoint}")
                    return None
                elif response.status_code == 401:
                    logger.error("401 Unauthorized: Invalid API key")
                    return None
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    if attempt < max_retries - 1:
                        sleep_time = min(2 ** attempt, 8) + random.uniform(0, 0.25)
                        time.sleep(sleep_time)
                        continue
                    else:
                        logger.error(f"Server error {response.status_code}: {endpoint}")
                        return None
                else:
                    logger.warning(f"Unexpected status {response.status_code}: {endpoint}")
                    return None

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries}): {endpoint}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                return None

        return None

    def get_parcel_details(self, apn: str) -> Optional[Dict]:
        """Get comprehensive parcel details."""
        endpoint = f"/parcel/{apn}"
        return self._make_request(endpoint)

    def get_property_info(self, apn: str) -> Optional[Dict]:
        """Get property information."""
        endpoint = f"/parcel/{apn}/propertyinfo"
        return self._make_request(endpoint)

    def get_property_address(self, apn: str) -> Optional[Dict]:
        """Get property address details."""
        endpoint = f"/parcel/{apn}/address"
        return self._make_request(endpoint)

    def get_valuations(self, apn: str) -> Optional[Dict]:
        """Get property valuations (past 5 years)."""
        endpoint = f"/parcel/{apn}/valuations"
        return self._make_request(endpoint)

    def get_residential_details(self, apn: str) -> Optional[Dict]:
        """Get residential property details."""
        endpoint = f"/parcel/{apn}/residential-details"
        return self._make_request(endpoint)

    def get_owner_details(self, apn: str) -> Optional[Dict]:
        """Get owner information."""
        endpoint = f"/parcel/{apn}/owner-details"
        return self._make_request(endpoint)

    def get_all_property_data(self, apn: str) -> Dict[str, Any]:
        """
        Get all available property data for an APN.

        Calls all relevant endpoints and combines the results.

        Args:
            apn: Assessor Parcel Number

        Returns:
            Combined dictionary with all property data
        """
        result = {
            'apn': apn,
            'retrieval_timestamp': datetime.now().isoformat(),
            'data_complete': False,
            'errors': []
        }

        # Call all endpoints
        endpoints = [
            ('parcel', self.get_parcel_details),
            ('property_info', self.get_property_info),
            ('address', self.get_property_address),
            ('valuations', self.get_valuations),
            ('residential', self.get_residential_details),
            ('owner', self.get_owner_details)
        ]

        successful_calls = 0

        for name, func in endpoints:
            try:
                data = func(apn)
                if data:
                    result[name] = data
                    successful_calls += 1
                else:
                    result['errors'].append(f"{name}: No data returned")
            except Exception as e:
                result['errors'].append(f"{name}: {str(e)}")
                logger.error(f"Error calling {name} for APN {apn}: {e}")

        # Mark as complete if we got data from at least one endpoint
        result['data_complete'] = successful_calls > 0

        return result

    def map_to_max_headers(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map API response data to MAX_HEADERS column structure.
        Based on actual MCAO API response structure discovered through testing.

        Args:
            api_data: Combined API response data

        Returns:
            Dictionary with MAX_HEADERS column names as keys
        """
        mapped = {}

        # Process parcel endpoint data
        if 'parcel' in api_data and api_data['parcel']:
            parcel = api_data['parcel']

            # Owner data (nested in parcel response)
            if 'Owner' in parcel:
                owner = parcel['Owner']
                mapped['Owner_OwnerID'] = str(owner.get('OwnerID', ''))
                mapped['Owner_Ownership'] = str(owner.get('Ownership', ''))
                mapped['Owner_OwnerName'] = str(owner.get('Ownership', ''))  # Same as Ownership
                mapped['Owner_FullMailingAddress'] = str(owner.get('FullMailingAddress', ''))
                mapped['Owner_MailingAddress_Street'] = str(owner.get('MailingAddress1', ''))
                mapped['Owner_MailingAddress_City'] = str(owner.get('MailingCity', ''))
                mapped['Owner_MailingAddress_State'] = str(owner.get('MailingState', ''))
                mapped['Owner_MailingAddress_Zip'] = str(owner.get('MailingZip', ''))
                mapped['Owner_DeedDate'] = str(owner.get('DeedDate', ''))
                mapped['Owner_SalePrice'] = str(owner.get('SalePrice', '')) if owner.get('SalePrice') else ''
                mapped['Owner_Mailing_CareOf'] = str(owner.get('InCareOf', '')) if owner.get('InCareOf') else ''

            # Property data (direct fields in parcel)
            mapped['PropertyID'] = str(parcel.get('MCR', ''))  # MCR seems to be the property ID
            mapped['PropertyType'] = str(parcel.get('PropertyType', ''))
            mapped['LotSize'] = str(parcel.get('LotSize', ''))
            mapped['IsResidential'] = str(parcel.get('IsResidential', ''))
            mapped['YearBuilt'] = ''  # Will be filled from ResidentialPropertyData
            mapped['TaxDistrict'] = str(parcel.get('TaxAreaCode', ''))
            mapped['SubdivisionName'] = str(parcel.get('SubdivisionName', ''))
            mapped['LegalDescription'] = str(parcel.get('PropertyDescription', ''))

            # Zoning (it's an array in the response)
            if 'Zoning' in parcel and isinstance(parcel['Zoning'], list):
                mapped['Zoning'] = ', '.join(str(z) for z in parcel['Zoning']) if parcel['Zoning'] else ''
            else:
                mapped['Zoning'] = ''

            mapped['LandUse'] = str(parcel.get('PropertyUseCode', ''))
            mapped['EffectiveDate'] = ''  # Not in response

            # GIS data (Geo object in parcel)
            if 'Geo' in parcel:
                geo = parcel['Geo']
                mapped['GIS_Latitude'] = str(geo.get('lat', '')) if geo.get('lat') else ''
                mapped['GIS_Longitude'] = str(geo.get('long', '')) if geo.get('long') else ''

            # Section/Township/Range
            str_value = parcel.get('SectionTownshipRange', '')
            if str_value:
                # Parse "26 3N 3E" format
                parts = str(str_value).split()
                if len(parts) >= 3:
                    mapped['GIS_Section'] = parts[0]
                    mapped['GIS_Township'] = parts[1] if len(parts) > 1 else ''
                    mapped['GIS_Range'] = parts[2] if len(parts) > 2 else ''
                else:
                    mapped['GIS_Section'] = str_value
                    mapped['GIS_Township'] = ''
                    mapped['GIS_Range'] = ''

            mapped['GIS_MapNumber'] = ''  # Not in response

            # School districts
            mapped['SchoolDistrict'] = str(parcel.get('ElementarySchoolDistrict', ''))

            # Additional fields
            mapped['CensusBlock'] = ''  # Not in response
            mapped['FireDistrict'] = ''  # Not in response
            mapped['AssessmentRatio'] = ''  # Will get from valuations
            mapped['ExemptionCode'] = ''  # Not in response
            mapped['ExemptionValue'] = ''  # Not in response
            mapped['SpecialAssessments'] = ''  # Not in response
            mapped['TotalTaxes'] = ''  # Not in response
            mapped['DelinquentTaxes'] = ''  # Not in response
            mapped['PropertyClass'] = ''  # Not in response
            mapped['UseCode'] = str(parcel.get('PropertyUseCode', ''))

            # Residential Property Data (nested in parcel)
            if 'ResidentialPropertyData' in parcel:
                res = parcel['ResidentialPropertyData']
                mapped['ResidentialPropertyData_LivableSpace'] = str(res.get('LivableSpace', ''))
                mapped['ResidentialPropertyData_NumberOfGarages'] = str(res.get('NumberOfGarages', ''))
                mapped['ResidentialPropertyData_OriginalConstructionYear'] = str(res.get('OriginalConstructionYear', ''))
                mapped['ResidentialPropertyData_Detached_Livable_sqft'] = str(res.get('Detached_Livable_sqft', '')) if res.get('Detached_Livable_sqft') else ''
                mapped['ResidentialPropertyData_Bedrooms'] = ''  # Not in response
                mapped['ResidentialPropertyData_Bathrooms'] = str(res.get('BathFixtures', ''))  # Using BathFixtures
                mapped['ResidentialPropertyData_Pools'] = 'Yes' if res.get('Pool') else 'No'
                mapped['ResidentialPropertyData_AirConditioning'] = str(res.get('Cooling', ''))
                mapped['ResidentialPropertyData_HeatingType'] = 'Yes' if res.get('Heating') else 'No'
                mapped['ResidentialPropertyData_WaterHeater'] = ''  # Not in response

                # Also set YearBuilt from residential data
                mapped['YearBuilt'] = str(res.get('ConstructionYear', ''))

            # Valuations (array in parcel)
            if 'Valuations' in parcel and isinstance(parcel['Valuations'], list):
                vals = parcel['Valuations']
                # Sort by TaxYear descending
                vals_sorted = sorted(vals, key=lambda x: int(x.get('TaxYear', 0)), reverse=True)

                for i, val in enumerate(vals_sorted[:2]):  # Get up to 2 most recent
                    prefix = f'Valuations_{i}_'
                    mapped[f'{prefix}LegalClassification'] = str(val.get('LegalClassification', ''))
                    mapped[f'{prefix}TaxYear'] = str(val.get('TaxYear', ''))
                    mapped[f'{prefix}FullCashValue'] = str(val.get('FullCashValue', ''))
                    mapped[f'{prefix}AssessedValue'] = str(val.get('AssessedFCV', ''))
                    mapped[f'{prefix}LimitedPropertyValue'] = str(val.get('LimitedPropertyValue', ''))

                    # These aren't broken down in the response
                    mapped[f'{prefix}Land_FullCashValue'] = ''
                    mapped[f'{prefix}Improvements_FullCashValue'] = ''

                    # Get assessment ratio from first valuation
                    if i == 0 and val.get('AssessmentRatioPercentage'):
                        mapped['AssessmentRatio'] = str(val.get('AssessmentRatioPercentage', ''))

        # Process owner-details endpoint data (overwrites some fields with more detail)
        if 'owner' in api_data and api_data['owner']:
            owner = api_data['owner']
            mapped['Owner_OwnerID'] = str(owner.get('OwnerID', ''))
            mapped['Owner_Ownership'] = str(owner.get('Ownership', ''))
            mapped['Owner_OwnerName'] = str(owner.get('Ownership', ''))
            mapped['Owner_FullMailingAddress'] = str(owner.get('FullMailingAddress', ''))
            mapped['Owner_MailingAddress_Street'] = str(owner.get('MailingAddress1', ''))
            mapped['Owner_MailingAddress_City'] = str(owner.get('MailingCity', ''))
            mapped['Owner_MailingAddress_State'] = str(owner.get('MailingState', ''))
            mapped['Owner_MailingAddress_Zip'] = str(owner.get('MailingZip', ''))
            mapped['Owner_DeedDate'] = str(owner.get('DeedDate', ''))
            mapped['Owner_SalePrice'] = str(owner.get('SalePrice', '')) if owner.get('SalePrice') else ''
            mapped['Owner_Mailing_CareOf'] = str(owner.get('InCareOf', '')) if owner.get('InCareOf') else ''

        # Process valuations endpoint data (overwrites/supplements)
        if 'valuations' in api_data and isinstance(api_data['valuations'], list):
            vals = api_data['valuations']
            # Sort by TaxYear descending
            vals_sorted = sorted(vals, key=lambda x: int(x.get('TaxYear', 0)), reverse=True)

            for i, val in enumerate(vals_sorted[:2]):  # Get up to 2 most recent
                prefix = f'Valuations_{i}_'
                mapped[f'{prefix}LegalClassification'] = str(val.get('LegalClassification', ''))
                mapped[f'{prefix}TaxYear'] = str(val.get('TaxYear', ''))
                mapped[f'{prefix}FullCashValue'] = str(val.get('FullCashValue', ''))
                mapped[f'{prefix}AssessedValue'] = str(val.get('AssessedFCV', ''))
                mapped[f'{prefix}LimitedPropertyValue'] = str(val.get('LimitedPropertyValue', ''))

        # Process residential-details endpoint data (overwrites/supplements)
        if 'residential' in api_data and api_data['residential']:
            res = api_data['residential']
            mapped['YearBuilt'] = str(res.get('ConstructionYear', ''))
            mapped['ResidentialPropertyData_LivableSpace'] = str(res.get('LivableSpace', ''))
            mapped['ResidentialPropertyData_NumberOfGarages'] = str(res.get('NumberOfGarages', ''))
            mapped['ResidentialPropertyData_OriginalConstructionYear'] = str(res.get('OriginalConstructionYear', ''))
            mapped['ResidentialPropertyData_Detached_Livable_sqft'] = str(res.get('Detached_Livable_sqft', '')) if res.get('Detached_Livable_sqft') else ''
            mapped['ResidentialPropertyData_Bathrooms'] = str(res.get('BathFixtures', ''))
            mapped['ResidentialPropertyData_Pools'] = 'Yes' if res.get('Pool') else 'No'
            mapped['ResidentialPropertyData_AirConditioning'] = str(res.get('Cooling', ''))
            mapped['ResidentialPropertyData_HeatingType'] = 'Yes' if res.get('Heating') else 'No'

        # Sales history - not in current API responses but leave structure
        mapped['Sales_0_SaleDate'] = mapped.get('Owner_DeedDate', '')  # Use deed date as sale date
        mapped['Sales_0_SalePrice'] = mapped.get('Owner_SalePrice', '')
        mapped['Sales_0_SaleType'] = ''
        mapped['Sales_0_Grantor'] = ''
        mapped['Sales_0_Grantee'] = mapped.get('Owner_OwnerName', '')
        mapped['Sales_1_SaleDate'] = ''
        mapped['Sales_1_SalePrice'] = ''
        mapped['Sales_1_SaleType'] = ''

        # Commercial data - not in residential responses but structure remains
        mapped['CommercialPropertyData_GrossSquareFeet'] = ''
        mapped['CommercialPropertyData_NetLeasableArea'] = ''
        mapped['CommercialPropertyData_NumberOfUnits'] = ''
        mapped['CommercialPropertyData_NumberOfStories'] = ''
        mapped['CommercialPropertyData_ParkingSpaces'] = ''
        mapped['CommercialPropertyData_ConstructionType'] = ''

        # Permits - not in current response
        mapped['Permits_0_PermitDate'] = ''
        mapped['Permits_0_PermitType'] = ''
        mapped['Permits_0_PermitValue'] = ''

        # Improvements - Pool info is in ResidentialPropertyData
        mapped['Improvements_Pool'] = mapped.get('ResidentialPropertyData_Pools', '')
        mapped['Improvements_Tennis'] = ''
        mapped['Improvements_Other'] = ''

        return mapped