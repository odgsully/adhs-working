"""MCAO API integration for geocoding (stub implementation)."""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MCAPGeocoder:
    """Geocodes addresses using MCAO API."""

    def __init__(self, api_key: Optional[str] = None, api_url: str = ""):
        """Initialize with API credentials."""
        self.api_key = api_key
        self.api_url = api_url

        if not api_key:
            logger.warning("MCAO API key not provided - geocoding disabled")

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode an address to latitude/longitude."""
        if not self.api_key:
            return None

        # Stub implementation - would call actual API
        logger.debug(f"Geocoding address: {address} (stub)")
        return None

    def batch_geocode(
        self, addresses: List[str]
    ) -> Dict[str, Optional[Tuple[float, float]]]:
        """Geocode multiple addresses in batch."""
        results = {}
        for address in addresses:
            results[address] = self.geocode_address(address)
        return results

    def get_parcel_info(self, parcel_id: str) -> Optional[Dict]:
        """Get parcel information from MCAO."""
        if not self.api_key:
            return None

        # Stub implementation
        logger.debug(f"Fetching parcel info: {parcel_id} (stub)")
        return None
