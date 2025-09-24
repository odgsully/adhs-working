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

        Args:
            api_data: Combined API response data

        Returns:
            Dictionary with MAX_HEADERS column names as keys
        """
        mapped = {}

        # Owner data mapping
        if 'owner' in api_data:
            owner = api_data['owner']
            mapped['Owner_OwnerID'] = owner.get('id', '')
            mapped['Owner_Ownership'] = owner.get('ownership_type', '')
            mapped['Owner_OwnerName'] = owner.get('name', '')

            # Mailing address
            if 'mailing_address' in owner:
                addr = owner['mailing_address']
                mapped['Owner_FullMailingAddress'] = addr.get('full_address', '')
                mapped['Owner_MailingAddress_Street'] = addr.get('street', '')
                mapped['Owner_MailingAddress_City'] = addr.get('city', '')
                mapped['Owner_MailingAddress_State'] = addr.get('state', '')
                mapped['Owner_MailingAddress_Zip'] = addr.get('zip', '')

            mapped['Owner_DeedDate'] = owner.get('deed_date', '')
            mapped['Owner_SalePrice'] = owner.get('sale_price', '')
            mapped['Owner_Mailing_CareOf'] = owner.get('care_of', '')

        # Property data mapping
        if 'parcel' in api_data:
            parcel = api_data['parcel']
            mapped['PropertyID'] = parcel.get('property_id', '')
            mapped['PropertyType'] = parcel.get('property_type', '')
            mapped['LotSize'] = parcel.get('lot_size', '')
            mapped['IsResidential'] = parcel.get('is_residential', '')
            mapped['YearBuilt'] = parcel.get('year_built', '')
            mapped['TaxDistrict'] = parcel.get('tax_district', '')
            mapped['SubdivisionName'] = parcel.get('subdivision_name', '')
            mapped['LegalDescription'] = parcel.get('legal_description', '')
            mapped['Zoning'] = parcel.get('zoning', '')
            mapped['LandUse'] = parcel.get('land_use', '')
            mapped['EffectiveDate'] = parcel.get('effective_date', '')

        # Residential data mapping
        if 'residential' in api_data:
            res = api_data['residential']
            mapped['ResidentialPropertyData_LivableSpace'] = res.get('livable_space', '')
            mapped['ResidentialPropertyData_NumberOfGarages'] = res.get('garages', '')
            mapped['ResidentialPropertyData_OriginalConstructionYear'] = res.get('original_construction_year', '')
            mapped['ResidentialPropertyData_Detached_Livable_sqft'] = res.get('detached_livable_sqft', '')
            mapped['ResidentialPropertyData_Bedrooms'] = res.get('bedrooms', '')
            mapped['ResidentialPropertyData_Bathrooms'] = res.get('bathrooms', '')
            mapped['ResidentialPropertyData_Pools'] = res.get('pools', '')
            mapped['ResidentialPropertyData_AirConditioning'] = res.get('air_conditioning', '')
            mapped['ResidentialPropertyData_HeatingType'] = res.get('heating_type', '')
            mapped['ResidentialPropertyData_WaterHeater'] = res.get('water_heater', '')

        # Commercial data mapping (if present in parcel data)
        if 'parcel' in api_data and 'commercial' in api_data['parcel']:
            com = api_data['parcel']['commercial']
            mapped['CommercialPropertyData_GrossSquareFeet'] = com.get('gross_sqft', '')
            mapped['CommercialPropertyData_NetLeasableArea'] = com.get('net_leasable_area', '')
            mapped['CommercialPropertyData_NumberOfUnits'] = com.get('units', '')
            mapped['CommercialPropertyData_NumberOfStories'] = com.get('stories', '')
            mapped['CommercialPropertyData_ParkingSpaces'] = com.get('parking_spaces', '')
            mapped['CommercialPropertyData_ConstructionType'] = com.get('construction_type', '')

        # Valuations mapping (most recent 2 years)
        if 'valuations' in api_data:
            vals = api_data['valuations']
            if isinstance(vals, list):
                # Sort by year descending to get most recent first
                vals_sorted = sorted(vals, key=lambda x: x.get('tax_year', 0), reverse=True)

                for i, val in enumerate(vals_sorted[:2]):  # Get up to 2 most recent
                    prefix = f'Valuations_{i}_'
                    mapped[f'{prefix}LegalClassification'] = val.get('legal_classification', '')
                    mapped[f'{prefix}TaxYear'] = val.get('tax_year', '')
                    mapped[f'{prefix}FullCashValue'] = val.get('full_cash_value', '')
                    mapped[f'{prefix}AssessedValue'] = val.get('assessed_value', '')
                    mapped[f'{prefix}LimitedPropertyValue'] = val.get('limited_property_value', '')

                    # Land and improvements breakdown
                    if 'land' in val:
                        mapped[f'{prefix}Land_FullCashValue'] = val['land'].get('full_cash_value', '')
                    if 'improvements' in val:
                        mapped[f'{prefix}Improvements_FullCashValue'] = val['improvements'].get('full_cash_value', '')

        # Sales history mapping (most recent 2 sales)
        if 'parcel' in api_data and 'sales' in api_data['parcel']:
            sales = api_data['parcel']['sales']
            if isinstance(sales, list):
                # Sort by date descending
                sales_sorted = sorted(sales, key=lambda x: x.get('sale_date', ''), reverse=True)

                for i, sale in enumerate(sales_sorted[:2]):  # Get up to 2 most recent
                    prefix = f'Sales_{i}_'
                    mapped[f'{prefix}SaleDate'] = sale.get('sale_date', '')
                    mapped[f'{prefix}SalePrice'] = sale.get('sale_price', '')
                    mapped[f'{prefix}SaleType'] = sale.get('sale_type', '')
                    mapped[f'{prefix}Grantor'] = sale.get('grantor', '')
                    mapped[f'{prefix}Grantee'] = sale.get('grantee', '')

        # GIS data mapping
        if 'parcel' in api_data and 'gis' in api_data['parcel']:
            gis = api_data['parcel']['gis']
            mapped['GIS_Latitude'] = gis.get('latitude', '')
            mapped['GIS_Longitude'] = gis.get('longitude', '')
            mapped['GIS_MapNumber'] = gis.get('map_number', '')
            mapped['GIS_Township'] = gis.get('township', '')
            mapped['GIS_Range'] = gis.get('range', '')
            mapped['GIS_Section'] = gis.get('section', '')

        # Additional fields
        if 'parcel' in api_data:
            parcel = api_data['parcel']
            mapped['CensusBlock'] = parcel.get('census_block', '')
            mapped['SchoolDistrict'] = parcel.get('school_district', '')
            mapped['FireDistrict'] = parcel.get('fire_district', '')
            mapped['AssessmentRatio'] = parcel.get('assessment_ratio', '')
            mapped['ExemptionCode'] = parcel.get('exemption_code', '')
            mapped['ExemptionValue'] = parcel.get('exemption_value', '')
            mapped['SpecialAssessments'] = parcel.get('special_assessments', '')
            mapped['TotalTaxes'] = parcel.get('total_taxes', '')
            mapped['DelinquentTaxes'] = parcel.get('delinquent_taxes', '')
            mapped['PropertyClass'] = parcel.get('property_class', '')
            mapped['UseCode'] = parcel.get('use_code', '')

        # Permits (most recent)
        if 'parcel' in api_data and 'permits' in api_data['parcel']:
            permits = api_data['parcel']['permits']
            if isinstance(permits, list) and permits:
                permit = permits[0]  # Most recent
                mapped['Permits_0_PermitDate'] = permit.get('permit_date', '')
                mapped['Permits_0_PermitType'] = permit.get('permit_type', '')
                mapped['Permits_0_PermitValue'] = permit.get('permit_value', '')

        # Improvements
        if 'parcel' in api_data and 'improvements' in api_data['parcel']:
            imp = api_data['parcel']['improvements']
            mapped['Improvements_Pool'] = imp.get('pool', '')
            mapped['Improvements_Tennis'] = imp.get('tennis', '')
            mapped['Improvements_Other'] = imp.get('other', '')

        return mapped