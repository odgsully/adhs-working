"""
normalize.py - Data normalization and cleaning functions
"""

import re
import pandas as pd
from typing import Tuple, Optional, Set


def split_full_name(full_name: str) -> Tuple[str, str]:
    """Split full name into first and last name.
    
    Args:
        full_name: Full name string
        
    Returns:
        Tuple of (first_name, last_name)
    """
    if not full_name or pd.isna(full_name):
        return "", ""
    
    name_str = str(full_name).strip()
    if not name_str:
        return "", ""
    
    # Handle common suffixes
    suffixes = ['Jr', 'Jr.', 'Sr', 'Sr.', 'II', 'III', 'IV', 'V']
    suffix_pattern = r'\b(' + '|'.join(re.escape(s) for s in suffixes) + r')\b'
    name_str = re.sub(suffix_pattern, '', name_str, flags=re.IGNORECASE).strip()
    
    # Split on whitespace
    parts = name_str.split()
    
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        # More than 2 parts - first word is first name, rest is last name
        return parts[0], " ".join(parts[1:])


def normalize_state(state: str, fallback: Optional[str] = None) -> str:
    """Normalize state to 2-letter code.
    
    Args:
        state: State string (full name or abbreviation)
        fallback: Fallback state if normalization fails
        
    Returns:
        2-letter state code
    """
    if not state or pd.isna(state):
        return fallback or ""
    
    state_str = str(state).strip().upper()
    
    # Common state mappings
    state_map = {
        'ARIZONA': 'AZ',
        'CALIFORNIA': 'CA',
        'COLORADO': 'CO',
        'NEVADA': 'NV',
        'NEW MEXICO': 'NM',
        'TEXAS': 'TX',
        'UTAH': 'UT',
        'WYOMING': 'WY'
    }
    
    # If already 2-letter code, return as-is
    if len(state_str) == 2 and state_str.isalpha():
        return state_str
    
    # Try to map full state name
    if state_str in state_map:
        return state_map[state_str]
    
    # Return fallback if available, otherwise original
    return fallback or state_str


def is_blacklisted_name(name: str, blacklist: Set[str]) -> bool:
    """Check if name is in blacklist (registered agents, etc.).
    
    Args:
        name: Name to check
        blacklist: Set of blacklisted names (uppercase)
        
    Returns:
        True if name is blacklisted
    """
    if not name or pd.isna(name):
        return False
    
    name_upper = str(name).strip().upper()
    
    # Direct match
    if name_upper in blacklist:
        return True
    
    # Check for partial matches (blacklist entries contained in name)
    for blacklist_entry in blacklist:
        if blacklist_entry in name_upper:
            return True
    
    return False


def clean_address_line(address: str) -> str:
    """Clean and normalize address line.
    
    Args:
        address: Address string
        
    Returns:
        Cleaned address string
    """
    if not address or pd.isna(address):
        return ""
    
    addr_str = str(address).strip()
    
    # Remove extra whitespace and normalize case
    addr_str = re.sub(r'\s+', ' ', addr_str)
    
    # Convert to title case for consistency
    addr_str = addr_str.title()
    
    # Common abbreviations (standardize)
    abbrev_map = {
        ' St ': ' St ',
        ' St,': ' St,',
        ' St$': ' St',
        ' Ave ': ' Ave ',
        ' Ave,': ' Ave,',
        ' Ave$': ' Ave',
        ' Blvd ': ' Blvd ',
        ' Blvd,': ' Blvd,',
        ' Blvd$': ' Blvd',
        ' Dr ': ' Dr ',
        ' Dr,': ' Dr,',
        ' Dr$': ' Dr',
        ' Rd ': ' Rd ',
        ' Rd,': ' Rd,',
        ' Rd$': ' Rd',
        ' Ln ': ' Ln ',
        ' Ln,': ' Ln,',
        ' Ln$': ' Ln'
    }
    
    for abbrev, standard in abbrev_map.items():
        addr_str = re.sub(abbrev, standard, addr_str)
    
    return addr_str.strip()


def normalize_zip_code(zip_code: str) -> str:
    """Normalize ZIP code to 5-digit format.
    
    Args:
        zip_code: ZIP code string
        
    Returns:
        5-digit ZIP code
    """
    if not zip_code or pd.isna(zip_code):
        return ""
    
    zip_str = str(zip_code).strip()
    
    # Extract digits only
    digits = re.findall(r'\d+', zip_str)
    if not digits:
        return ""
    
    # Take first sequence of digits, pad or truncate to 5 digits
    zip_digits = digits[0]
    if len(zip_digits) >= 5:
        return zip_digits[:5]
    else:
        return zip_digits.zfill(5)


def extract_title_role(title: str) -> str:
    """Normalize title/role field.
    
    Args:
        title: Title string
        
    Returns:
        Normalized title
    """
    if not title or pd.isna(title):
        return ""
    
    title_str = str(title).strip()
    
    # Common title mappings
    title_map = {
        'MEMBER': 'Member',
        'MANAGER': 'Manager', 
        'MEMBER AND MANAGER': 'Member and Manager',
        'PRESIDENT': 'President',
        'SECRETARY': 'Secretary',
        'TREASURER': 'Treasurer',
        'DIRECTOR': 'Director',
        'OFFICER': 'Officer',
        'OWNER': 'Owner',
        'PARTNER': 'Partner'
    }
    
    title_upper = title_str.upper()
    if title_upper in title_map:
        return title_map[title_upper]
    
    # Return title case version
    return title_str.title()


def apply_blacklist_filter(df: pd.DataFrame, blacklist: Set[str], 
                          name_column: str = 'owner_name_full') -> pd.DataFrame:
    """Filter out blacklisted names from DataFrame.
    
    Args:
        df: Input DataFrame
        blacklist: Set of blacklisted names
        name_column: Column to check against blacklist
        
    Returns:
        Filtered DataFrame
    """
    if name_column not in df.columns:
        return df
    
    # Create mask for non-blacklisted records
    mask = ~df[name_column].apply(lambda name: is_blacklisted_name(name, blacklist))
    
    return df[mask].reset_index(drop=True)


def normalize_phone_e164(phone: str) -> str:
    """Normalize phone to E.164 format (+1XXXXXXXXXX).
    
    Args:
        phone: Phone number string
        
    Returns:
        E.164 formatted phone or empty string
    """
    if not phone or pd.isna(phone):
        return ""
    
    # Extract digits only
    digits = re.sub(r'\D', '', str(phone))
    
    # US phone number should have 10 or 11 digits
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    else:
        return ""  # Invalid format