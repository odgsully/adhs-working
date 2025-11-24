"""
transform.py - Data transformation between eCorp and BatchData formats
"""

import pandas as pd
import uuid
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add Ecorp directory to path for blacklist import
ecorp_path = Path(__file__).parent.parent.parent / "Ecorp"
if str(ecorp_path) not in sys.path:
    sys.path.insert(0, str(ecorp_path))

try:
    from professional_services_blacklist import StatutoryAgentBlacklist
except ImportError:
    print("⚠️ Warning: Could not import StatutoryAgentBlacklist - statutory agents will not be filtered")
    StatutoryAgentBlacklist = None

try:
    from .normalize import (
        split_full_name, normalize_state, clean_address_line,
        normalize_zip_code, extract_title_role, normalize_phone_e164
    )
except ImportError:
    from normalize import (
        split_full_name, normalize_state, clean_address_line,
        normalize_zip_code, extract_title_role, normalize_phone_e164
    )


def prepare_ecorp_for_batchdata(ecorp_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare Ecorp_Complete data for batchdata pipeline by mapping columns.

    This function handles both the new categorized structure (StatutoryAgent/Manager/Member)
    and the legacy structure (Title1/Name1/Address1) for backward compatibility.

    Args:
        ecorp_df: DataFrame from Ecorp_Complete file

    Returns:
        DataFrame with columns mapped for batchdata compatibility
    """
    df = ecorp_df.copy()

    # Check which structure we have
    has_new_structure = 'StatutoryAgent1_Name' in df.columns
    has_legacy_structure = 'Title1' in df.columns

    if has_new_structure and not has_legacy_structure:
        # New structure detected - need to transform
        print("📊 Detected new Ecorp_Complete structure - transforming for batchdata compatibility...")

        # Initialize blacklist if available
        blacklist = None
        if StatutoryAgentBlacklist:
            try:
                blacklist = StatutoryAgentBlacklist()
                print(f"   ✅ Loaded statutory agent blacklist with {len(blacklist.blacklist)} entries")
            except Exception as e:
                print(f"   ⚠️ Could not load blacklist: {e}")

        # Map statutory agent fields
        if 'StatutoryAgent1_Name' in df.columns:
            df['Statutory Agent'] = df['StatutoryAgent1_Name']
        if 'StatutoryAgent1_Address' in df.columns:
            df['Agent Address'] = df['StatutoryAgent1_Address']

        # Consolidate principals from categorized structure
        for idx, row in df.iterrows():
            principals = []

            # Priority order: Manager/Member > Manager > Member > Statutory Agent > Individual
            # Collect Manager/Member entries
            for i in range(1, 6):
                name = row.get(f'Manager/Member{i}_Name', '')
                if name and pd.notna(name) and str(name).strip():
                    principals.append({
                        'title': 'Manager/Member',
                        'name': name,
                        'address': row.get(f'Manager/Member{i}_Address', '')
                    })

            # Collect Manager entries
            for i in range(1, 6):
                name = row.get(f'Manager{i}_Name', '')
                if name and pd.notna(name) and str(name).strip():
                    principals.append({
                        'title': 'Manager',
                        'name': name,
                        'address': row.get(f'Manager{i}_Address', '')
                    })

            # Collect Member entries
            for i in range(1, 6):
                name = row.get(f'Member{i}_Name', '')
                if name and pd.notna(name) and str(name).strip():
                    principals.append({
                        'title': 'Member',
                        'name': name,
                        'address': row.get(f'Member{i}_Address', '')
                    })

            # NEW: Collect Statutory Agent entries (if not blacklisted)
            for i in range(1, 4):  # Up to 3 statutory agents
                name = row.get(f'StatutoryAgent{i}_Name', '')
                if name and pd.notna(name) and str(name).strip():
                    # Check blacklist if available
                    if blacklist and blacklist.is_blacklisted(name):
                        # Skip professional service companies
                        continue

                    # Include individual statutory agents
                    principals.append({
                        'title': 'Statutory Agent',
                        'name': name,
                        'address': row.get(f'StatutoryAgent{i}_Address', '')
                    })

            # Collect Individual entries
            for i in range(1, 5):
                name = row.get(f'IndividualName{i}', '')
                if name and pd.notna(name) and str(name).strip():
                    principals.append({
                        'title': 'Individual',
                        'name': name,
                        'address': ''  # Individuals don't have addresses in the structure
                    })

            # Map first 3 principals to Title/Name/Address columns
            for i in range(1, 4):
                if i <= len(principals):
                    principal = principals[i-1]
                    df.at[idx, f'Title{i}'] = principal['title']
                    df.at[idx, f'Name{i}'] = principal['name']
                    df.at[idx, f'Address{i}'] = principal['address']
                else:
                    df.at[idx, f'Title{i}'] = ''
                    df.at[idx, f'Name{i}'] = ''
                    df.at[idx, f'Address{i}'] = ''

        print(f"✅ Transformed {len(df)} records for batchdata compatibility")

    elif has_legacy_structure:
        print("📊 Detected legacy Ecorp_Complete structure - no transformation needed")

    else:
        print("⚠️ Warning: Unknown Ecorp_Complete structure - attempting to proceed")

    return df


def ecorp_to_batchdata_records(ecorp_row: pd.Series) -> List[Dict[str, Any]]:
    """Transform single eCorp row into BatchData records (explode principals).

    Args:
        ecorp_row: Single row from eCorp DataFrame

    Returns:
        List of BatchData record dictionaries
    """
    records = []

    # Base information from eCorp record
    base_info = {
        'source_type': 'Entity',
        'source_entity_name': ecorp_row.get('ECORP_NAME_S', ''),
        'source_entity_id': ecorp_row.get('ECORP_ENTITY_ID_S', ''),
        'notes': f"Derived from eCorp search: {ecorp_row.get('ECORP_SEARCH_NAME', '')}"
    }

    # Extract address information with fallback for new structure
    # Try legacy 'Agent Address' first, then new 'StatutoryAgent1_Address'
    agent_address = ecorp_row.get('Agent Address', '')
    if not agent_address:
        agent_address = ecorp_row.get('StatutoryAgent1_Address', '')

    if agent_address:
        address_parts = parse_address(agent_address)
        # Use parsed state or fallback to ECORP_STATE from ecorp data
        parsed_state = address_parts.get('state', '')
        domicile_state = ecorp_row.get('ECORP_STATE', '')
        state_field = ecorp_row.get('State', '')

        # Convert to strings and handle NaN/None values
        parsed_state = str(parsed_state) if pd.notna(parsed_state) else ''
        domicile_state = str(domicile_state) if pd.notna(domicile_state) else ''
        state_field = str(state_field) if pd.notna(state_field) else ''

        # Properly handle empty strings and None values, normalize state names
        state = ''
        if parsed_state and parsed_state.strip():
            state = normalize_state(parsed_state)
        elif domicile_state and domicile_state.strip():
            state = normalize_state(domicile_state)
        elif state_field and state_field.strip():
            state = normalize_state(state_field)
        else:
            state = ''
        base_info.update({
            'address_line1': address_parts['line1'],
            'address_line2': address_parts['line2'],
            'city': address_parts['city'],
            'state': state,
            'zip': address_parts['zip'],
            'county': ecorp_row.get('ECORP_COUNTY', '') or ecorp_row.get('COUNTY', '')
        })

    # Process up to 3 principals
    for i in range(1, 4):
        title_col = f'Title{i}'
        name_col = f'Name{i}'
        address_col = f'Address{i}'

        title = ecorp_row.get(title_col, '')
        name = ecorp_row.get(name_col, '')
        address = ecorp_row.get(address_col, '')
        
        # Skip if no name provided
        if not name or pd.isna(name) or str(name).strip() == '':
            continue
        
        # Generate unique record ID
        record_id = f"ecorp_{ecorp_row.get('ECORP_ENTITY_ID_S', 'unknown')}_{i}_{str(uuid.uuid4())[:8]}"
        
        # Split name into first/last
        first_name, last_name = split_full_name(name)
        
        # Parse address if provided, otherwise use base address
        if address and not pd.isna(address) and str(address).strip():
            addr_parts = parse_address(address)
        else:
            addr_parts = {
                'line1': base_info.get('address_line1', ''),
                'line2': base_info.get('address_line2', ''),
                'city': base_info.get('city', ''),
                'state': base_info.get('state', ''),
                'zip': base_info.get('zip', '')
            }
        
        # Use parsed state or fallback to ECORP_STATE/State from ecorp data
        parsed_state = addr_parts.get('state', '')
        domicile_state = ecorp_row.get('ECORP_STATE', '')
        state_field = ecorp_row.get('State', '')
        base_state = base_info.get('state', '')

        # Convert to strings and handle NaN/None values
        parsed_state = str(parsed_state) if pd.notna(parsed_state) else ''
        domicile_state = str(domicile_state) if pd.notna(domicile_state) else ''
        state_field = str(state_field) if pd.notna(state_field) else ''
        base_state = str(base_state) if pd.notna(base_state) else ''

        # Properly handle empty strings and None values - check each in order, normalize state names
        state = ''
        if parsed_state and parsed_state.strip():
            state = normalize_state(parsed_state)
        elif domicile_state and domicile_state.strip():
            state = normalize_state(domicile_state)
        elif state_field and state_field.strip():
            state = normalize_state(state_field)
        elif base_state and base_state.strip():
            state = normalize_state(base_state)
        else:
            state = ''

        record = {
            'BD_RECORD_ID': record_id,
            'BD_SOURCE_TYPE': base_info['source_type'],
            'BD_ENTITY_NAME': base_info['source_entity_name'],
            'BD_SOURCE_ENTITY_ID': base_info['source_entity_id'],
            'BD_TITLE_ROLE': extract_title_role(title),
            'BD_TARGET_FIRST_NAME': first_name,
            'BD_TARGET_LAST_NAME': last_name,
            'BD_OWNER_NAME_FULL': str(name).strip(),
            'BD_ADDRESS': addr_parts['line1'],
            'BD_ADDRESS_2': addr_parts['line2'],
            'BD_CITY': addr_parts['city'],
            'BD_STATE': normalize_state(state) if state else '',
            'BD_ZIP': normalize_zip_code(addr_parts['zip']),
            'BD_COUNTY': base_info.get('county', ''),
            'BD_APN': '',  # Not available in eCorp data
            'BD_MAILING_LINE1': '',  # Could be populated from different address if available
            'BD_MAILING_CITY': '',
            'BD_MAILING_STATE': '',
            'BD_MAILING_ZIP': '',
            'BD_NOTES': base_info['notes']
        }
        
        records.append(record)
    
    # If no principals were found, create record for the entity itself
    if not records:
        # Try to use Statutory Agent as the contact (with fallback to new structure)
        statutory_agent = ecorp_row.get('Statutory Agent', '')
        if not statutory_agent:
            statutory_agent = ecorp_row.get('StatutoryAgent1_Name', '')

        if statutory_agent and not pd.isna(statutory_agent):
            # Check if statutory agent is an entity (contains business keywords)
            agent_upper = str(statutory_agent).upper()
            entity_keywords = [
                'LLC', 'L.L.C.', 'CORP', 'CORPORATION', 'INC', 'INCORPORATED', 
                'LTD', 'LIMITED', 'LP', 'L.P.', 'COMPANY', 'CO.', 'SERVICES',
                'SYSTEM', 'SOLUTIONS', 'GROUP', 'ASSOCIATES'
            ]
            
            is_entity_agent = any(keyword in agent_upper for keyword in entity_keywords)
            
            if is_entity_agent:
                # Statutory agent is an entity, don't split name
                first_name, last_name = '', ''
                owner_name = statutory_agent
                title_role = 'Statutory Agent (Entity)'
            else:
                # Statutory agent appears to be an individual
                first_name, last_name = split_full_name(statutory_agent)
                owner_name = statutory_agent
                title_role = 'Statutory Agent'
        else:
            # Fall back to entity name
            first_name, last_name = '', ''
            owner_name = base_info['source_entity_name']
            title_role = 'Entity'
        
        record_id = f"ecorp_{ecorp_row.get('ECORP_ENTITY_ID_S', 'unknown')}_entity_{str(uuid.uuid4())[:8]}"

        # Use state from base_info or fallback to ECORP_STATE from ecorp data
        base_state = base_info.get('state', '')
        domicile_state = ecorp_row.get('ECORP_STATE', '')
        state_field = ecorp_row.get('State', '')

        # Convert to strings and handle NaN/None values
        base_state = str(base_state) if pd.notna(base_state) else ''
        domicile_state = str(domicile_state) if pd.notna(domicile_state) else ''
        state_field = str(state_field) if pd.notna(state_field) else ''

        # Properly handle empty strings and None values, normalize state names
        state = ''
        if base_state and base_state.strip():
            state = normalize_state(base_state)
        elif domicile_state and domicile_state.strip():
            state = normalize_state(domicile_state)
        elif state_field and state_field.strip():
            state = normalize_state(state_field)
        else:
            state = ''

        record = {
            'BD_RECORD_ID': record_id,
            'BD_SOURCE_TYPE': base_info['source_type'],
            'BD_ENTITY_NAME': base_info['source_entity_name'],
            'BD_SOURCE_ENTITY_ID': base_info['source_entity_id'],
            'BD_TITLE_ROLE': title_role,
            'BD_TARGET_FIRST_NAME': first_name,
            'BD_TARGET_LAST_NAME': last_name,
            'BD_OWNER_NAME_FULL': owner_name,
            'BD_ADDRESS': base_info.get('address_line1', ''),
            'BD_ADDRESS_2': base_info.get('address_line2', ''),
            'BD_CITY': base_info.get('city', ''),
            'BD_STATE': state,
            'BD_ZIP': base_info.get('zip', ''),
            'BD_COUNTY': base_info.get('county', ''),
            'BD_APN': '',
            'BD_MAILING_LINE1': '',
            'BD_MAILING_CITY': '',
            'BD_MAILING_STATE': '',
            'BD_MAILING_ZIP': '',
            'BD_NOTES': base_info['notes']
        }
        
        records.append(record)
    
    return records


def parse_address(address_str: str) -> Dict[str, str]:
    """Parse address string into components with improved extraction logic.
    
    Args:
        address_str: Full address string
        
    Returns:
        Dictionary with address components
    """
    import re
    
    if not address_str or pd.isna(address_str):
        return {'line1': '', 'line2': '', 'city': '', 'state': '', 'zip': ''}
    
    addr = str(address_str).strip()
    
    # Enhanced patterns for better extraction
    # Pattern 1: "123 Main St, Suite 100, Phoenix, AZ 85001"
    # Pattern 2: "123 Main St, Phoenix AZ 85001"
    # Pattern 3: "123 Main St Phoenix AZ 85001"
    
    # Try to extract ZIP code first (most reliable)
    zip_pattern = r'\b(\d{5})(?:-\d{4})?\b'
    zip_match = re.search(zip_pattern, addr)
    zip_code = zip_match.group(1) if zip_match else ''
    
    # Extract state (2-letter abbreviation or full state name)
    state_abbr_pattern = r'\b([A-Z]{2})\b(?=\s*\d{5}|\s*$)'
    state_match = re.search(state_abbr_pattern, addr.upper())
    state = ''
    
    if state_match:
        state = normalize_state(state_match.group(1))
    else:
        # Try to find full state names
        state_names = ['ARIZONA', 'CALIFORNIA', 'TEXAS', 'NEW YORK', 'FLORIDA', 'NEVADA', 
                      'COLORADO', 'UTAH', 'NEW MEXICO', 'WASHINGTON', 'OREGON']
        for state_name in state_names:
            if state_name in addr.upper():
                state = normalize_state(state_name)
                break
    
    # Split address by comma for structured parsing
    parts = [p.strip() for p in addr.split(',')]
    
    # Initialize components
    line1 = ''
    line2 = ''
    city = ''
    
    if len(parts) >= 1:
        # First part is always street address
        line1 = clean_address_line(parts[0])
        
        # Check if second part might be suite/apt/unit
        if len(parts) >= 2:
            second_part = parts[1].upper()
            if any(keyword in second_part for keyword in ['SUITE', 'STE', 'APT', 'UNIT', '#', 'FLOOR', 'BLDG']):
                line2 = parts[1].strip()
                city_index = 2
            else:
                city_index = 1
                
            # Try to extract city
            if len(parts) > city_index:
                city_part = parts[city_index]
                
                # Remove state and zip from city part if present
                if state and state in city_part.upper():
                    city_part = city_part.upper().replace(state, '').strip()
                if zip_code and zip_code in city_part:
                    city_part = city_part.replace(zip_code, '').strip()
                
                # Clean up city
                city = city_part.strip(' ,')
                
                # Additional cleanup for common patterns
                city = re.sub(r'\b[A-Z]{2}\b\s*$', '', city).strip()  # Remove trailing state abbr
                city = re.sub(r'\d{5}.*$', '', city).strip()  # Remove trailing zip
    
    # If we still don't have a city but have parts, try alternative parsing
    if not city and len(parts) >= 2:
        # Look for city in the part before state/zip
        for i in range(len(parts) - 1, 0, -1):
            part = parts[i].strip()
            # Skip if this part contains state or zip
            if (state and state in part.upper()) or (zip_code and zip_code in part):
                continue
            # Skip if it's a country
            if part.upper() in ['USA', 'UNITED STATES', 'US']:
                continue
            # This might be the city
            if part and not re.search(r'^\d+\s', part):  # Not starting with street number
                city = part
                break
    
    # Final validation and cleanup
    if city:
        # Remove any remaining state/zip artifacts
        city = re.sub(r'\s+[A-Z]{2}\s*$', '', city).strip()
        city = re.sub(r'\s+\d{5}.*$', '', city).strip()
        
    return {
        'line1': line1,
        'line2': line2,
        'city': city,
        'state': state,
        'zip': normalize_zip_code(zip_code)
    }


def transform_ecorp_to_batchdata(ecorp_df: pd.DataFrame) -> pd.DataFrame:
    """Transform entire eCorp DataFrame to BatchData format.

    This function now includes a preprocessing step to handle the new
    Ecorp_Complete structure if needed.

    Args:
        ecorp_df: eCorp DataFrame

    Returns:
        BatchData formatted DataFrame
    """
    # Preprocess the DataFrame to ensure compatibility
    ecorp_df = prepare_ecorp_for_batchdata(ecorp_df)

    all_records = []

    for _, row in ecorp_df.iterrows():
        # Skip "Not found" records
        status = row.get('ECORP_STATUS', '')
        if pd.notna(status) and str(status).strip().lower() in ['not found', 'error']:
            continue

        records = ecorp_to_batchdata_records(row)
        all_records.extend(records)

    return pd.DataFrame(all_records)


def explode_phones_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Convert wide phone format to long format for processing.
    
    Args:
        df: DataFrame with phone columns
        
    Returns:
        Long format DataFrame with record_id, phone, type, confidence, carrier
    """
    phone_records = []
    
    for _, row in df.iterrows():
        record_id = row.get('BD_RECORD_ID', '')

        # Look for phone columns (varies by API response structure)
        phone_cols = [col for col in df.columns if 'phone' in col.lower()]

        for col in phone_cols:
            phone_value = row.get(col, '')
            if phone_value and not pd.isna(phone_value):
                # Extract phone details if structured, otherwise treat as phone number
                if isinstance(phone_value, dict):
                    phone_record = {
                        'BD_RECORD_ID': record_id,
                        'phone': normalize_phone_e164(phone_value.get('number', '')),
                        'type': phone_value.get('type', ''),
                        'confidence': phone_value.get('confidence', ''),
                        'carrier': phone_value.get('carrier', '')
                    }
                else:
                    phone_record = {
                        'BD_RECORD_ID': record_id,
                        'phone': normalize_phone_e164(phone_value),
                        'type': '',
                        'confidence': '',
                        'carrier': ''
                    }

                if phone_record['phone']:  # Only add valid phones
                    phone_records.append(phone_record)
    
    return pd.DataFrame(phone_records)


def apply_phone_scrubs(phones_df: pd.DataFrame, 
                      verification_df: pd.DataFrame = None,
                      dnc_df: pd.DataFrame = None,
                      tcpa_df: pd.DataFrame = None) -> pd.DataFrame:
    """Apply phone verification and compliance scrubs.
    
    Args:
        phones_df: Base phone DataFrame
        verification_df: Phone verification results
        dnc_df: DNC check results  
        tcpa_df: TCPA check results
        
    Returns:
        Scrubbed phone DataFrame
    """
    result_df = phones_df.copy()
    
    # Apply verification results
    if verification_df is not None:
        verification_merge = verification_df[['phone', 'is_active', 'line_type']].drop_duplicates()
        result_df = result_df.merge(verification_merge, on='phone', how='left')
        
        # Filter to active mobile numbers only
        result_df = result_df[
            (result_df['is_active'] == True) & 
            (result_df['line_type'] == 'mobile')
        ]
    
    # Apply DNC results
    if dnc_df is not None:
        dnc_merge = dnc_df[['phone', 'on_dnc']].drop_duplicates()
        result_df = result_df.merge(dnc_merge, on='phone', how='left')
        
        # Filter out DNC numbers
        result_df = result_df[result_df['on_dnc'] != True]
    
    # Apply TCPA results  
    if tcpa_df is not None:
        tcpa_merge = tcpa_df[['phone', 'is_litigator']].drop_duplicates()
        result_df = result_df.merge(tcpa_merge, on='phone', how='left')
        
        # Filter out litigator numbers
        result_df = result_df[result_df['is_litigator'] != True]
    
    return result_df


def aggregate_top_phones(phones_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Aggregate top phones per record_id back to wide format.
    
    Args:
        phones_df: Long format phone DataFrame
        top_n: Maximum number of phones per record
        
    Returns:
        Wide format DataFrame with phone columns
    """
    # Define confidence ranking
    confidence_order = {'high': 3, 'medium': 2, 'low': 1}
    phones_df['confidence_rank'] = phones_df['confidence'].map(confidence_order).fillna(0)
    
    # Sort by confidence and deduplicate
    sorted_phones = phones_df.sort_values(['BD_RECORD_ID', 'confidence_rank', 'phone'], ascending=[True, False, True])

    result_records = []

    for record_id in sorted_phones['BD_RECORD_ID'].unique():
        record_phones = sorted_phones[sorted_phones['BD_RECORD_ID'] == record_id].head(top_n)

        phone_dict = {'BD_RECORD_ID': record_id}

        for i, (_, phone_row) in enumerate(record_phones.iterrows(), 1):
            phone_dict[f'BD_PHONE_{i}'] = phone_row['phone']
            phone_dict[f'BD_PHONE_{i}_TYPE'] = phone_row.get('type', '')
            phone_dict[f'BD_PHONE_{i}_CONFIDENCE'] = phone_row.get('confidence', '')
            phone_dict[f'BD_PHONE_{i}_CARRIER'] = phone_row.get('carrier', '')
        
        result_records.append(phone_dict)
    
    return pd.DataFrame(result_records)


def deduplicate_batchdata_records(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate BatchData records for the same person to reduce API costs.
    
    Identifies duplicates by comparing name, address, and entity information.
    Keeps the record with the most complete data or alphabetically first record_id.
    
    Args:
        df: BatchData DataFrame
        
    Returns:
        Deduplicated DataFrame with statistics logged
    """
    if len(df) <= 1:
        return df
    
    original_count = len(df)
    
    # Define fields to compare for identifying duplicates (focus on person, not entity)
    comparison_fields = [
        'BD_TARGET_FIRST_NAME', 'BD_TARGET_LAST_NAME', 'BD_OWNER_NAME_FULL',
        'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP'
    ]
    
    # Ensure all comparison fields exist
    for field in comparison_fields:
        if field not in df.columns:
            comparison_fields.remove(field)
    
    # Create working copy
    df_work = df.copy()
    
    # Fill NaN values for comparison
    df_work[comparison_fields] = df_work[comparison_fields].fillna('')
    
    # Create a comparison key for grouping
    df_work['_comparison_key'] = df_work[comparison_fields].apply(
        lambda row: '|'.join(str(row[col]).strip().upper() for col in comparison_fields), 
        axis=1
    )
    
    # Group by comparison key to find duplicates
    grouped = df_work.groupby('_comparison_key')
    
    deduplicated_records = []
    duplicates_removed = 0
    
    for comparison_key, group in grouped:
        if len(group) == 1:
            # No duplicates, keep the record
            deduplicated_records.append(group.iloc[0])
        else:
            # Multiple records found - select the best one
            duplicates_removed += len(group) - 1
            
            # Score each record by data completeness
            def score_record(row):
                score = 0
                # Count non-empty fields
                for field in comparison_fields:
                    if field in row and row[field] and str(row[field]).strip() and str(row[field]).lower() != 'nan':
                        score += 1
                
                # Bonus points for having phone/email data
                if 'phone' in str(row.get('notes', '')).lower():
                    score += 2
                if 'email' in str(row.get('notes', '')).lower():
                    score += 2
                    
                return score
            
            # Calculate scores for all records in group
            group['_completeness_score'] = group.apply(score_record, axis=1)
            
            # Sort by completeness score (descending), then by BD_RECORD_ID (ascending) for stable sort
            group_sorted = group.sort_values(['_completeness_score', 'BD_RECORD_ID'], ascending=[False, True])
            
            # Keep the best record (first after sorting)
            best_record = group_sorted.iloc[0]
            deduplicated_records.append(best_record)
    
    # Create result DataFrame
    result_df = pd.DataFrame(deduplicated_records)
    
    # Remove helper columns
    helper_columns = ['_comparison_key', '_completeness_score']
    for col in helper_columns:
        if col in result_df.columns:
            result_df = result_df.drop(col, axis=1)
    
    # Reset index
    result_df = result_df.reset_index(drop=True)
    
    final_count = len(result_df)
    reduction_percent = (duplicates_removed / original_count) * 100 if original_count > 0 else 0
    
    print(f"📊 Deduplication Results:")
    print(f"   Original records: {original_count}")
    print(f"   Deduplicated records: {final_count}")
    print(f"   Removed duplicates: {duplicates_removed}")
    print(f"   Reduction: {reduction_percent:.1f}%")
    
    return result_df


def simple_fuzzy_ratio(s1: str, s2: str) -> float:
    """Simple fuzzy string matching ratio (0.0 to 1.0).
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Similarity ratio between 0.0 (no match) and 1.0 (exact match)
    """
    if not s1 or not s2:
        return 0.0
    
    s1_clean = str(s1).upper().strip()
    s2_clean = str(s2).upper().strip()
    
    if s1_clean == s2_clean:
        return 1.0
    
    # Simple Jaccard similarity using word tokens
    words1 = set(s1_clean.split())
    words2 = set(s2_clean.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def detect_entity_families(entities: list, similarity_threshold: float = 0.6) -> dict:
    """Detect related entity families using fuzzy matching and patterns.
    
    Args:
        entities: List of entity names
        similarity_threshold: Minimum similarity for grouping
        
    Returns:
        Dictionary mapping family_id to list of entity names
    """
    families = {}
    used_entities = set()
    family_id = 0
    
    # Predefined patterns for known entity families
    patterns = [
        ('LEGACY_TRADITIONAL_SCHOOL', ['LEGACY TRADITIONAL SCHOOL']),
        ('ZION_PROPERTY', ['ZION PROPERTY']),
        ('METHODIST_CHURCH', ['METHODIST CHURCH', 'METHODIST']),
        ('NAZARENE_CHURCH', ['NAZARENE']),
        ('CHURCH_OF_CHRIST', ['CHURCH OF CHRIST']),
        ('CONGREGATIONAL_CHURCH', ['CONGREGATIONAL CHURCH']),
    ]
    
    # First, group by predefined patterns
    for pattern_name, keywords in patterns:
        matching_entities = []
        for entity in entities:
            if entity not in used_entities:
                entity_upper = str(entity).upper()
                if any(keyword in entity_upper for keyword in keywords):
                    matching_entities.append(entity)
                    used_entities.add(entity)
        
        if len(matching_entities) > 1:  # Only create family if multiple entities
            families[f'{pattern_name}_{family_id}'] = matching_entities
            family_id += 1
    
    # Then, use fuzzy matching for remaining entities
    remaining_entities = [e for e in entities if e not in used_entities]
    
    while remaining_entities:
        current_entity = remaining_entities.pop(0)
        current_family = [current_entity]
        
        # Find similar entities
        i = 0
        while i < len(remaining_entities):
            similarity = simple_fuzzy_ratio(current_entity, remaining_entities[i])
            if similarity >= similarity_threshold:
                current_family.append(remaining_entities.pop(i))
            else:
                i += 1
        
        # Create family only if multiple entities
        if len(current_family) > 1:
            families[f'FUZZY_FAMILY_{family_id}'] = current_family
            family_id += 1
    
    return families


def filter_entity_only_records(df: pd.DataFrame, filter_enabled: bool = False) -> pd.DataFrame:
    """Filter out entity-only records with no individual names for API cost savings.
    
    Args:
        df: BatchData DataFrame
        filter_enabled: If True, removes entity-only records
        
    Returns:
        Filtered DataFrame with entity-only records removed
    """
    if not filter_enabled or len(df) <= 1:
        return df
    
    original_count = len(df)
    
    # Identify entity-only records (no individual names)
    entity_only_mask = (
        (df['BD_TARGET_FIRST_NAME'].isna() | (df['BD_TARGET_FIRST_NAME'] == '')) &
        (df['BD_TARGET_LAST_NAME'].isna() | (df['BD_TARGET_LAST_NAME'] == ''))
    )
    
    entity_only_records = df[entity_only_mask]
    individual_records = df[~entity_only_mask]
    
    entity_only_count = len(entity_only_records)
    individual_count = len(individual_records)
    
    print(f"📊 Entity-Only Record Filter:")
    print(f"   Total records: {original_count}")
    print(f"   Entity-only records: {entity_only_count}")
    print(f"   Individual records: {individual_count}")
    
    if entity_only_count > 0:
        # Calculate potential savings
        cost_per_record = 0.07  # Typical API cost per record
        potential_savings = entity_only_count * cost_per_record
        
        print(f"   Potential cost savings: ${potential_savings:.2f}")
        print(f"   Records removed: {entity_only_count} ({(entity_only_count/original_count)*100:.1f}%)")
        
        # Show what types of records are being filtered
        if not entity_only_records.empty:
            role_counts = entity_only_records['title_role'].value_counts()
            print(f"   Record types being filtered:")
            for role, count in role_counts.head(3).items():
                print(f"     - {role}: {count} records")
    
    return individual_records.reset_index(drop=True)


def validate_input_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and report on input field completeness for API optimization.
    
    Args:
        df: Input DataFrame to validate
        
    Returns:
        DataFrame with validation flags added
    """
    df_validated = df.copy()
    
    # Add validation flags
    df_validated['has_valid_name'] = (
        (df_validated['BD_TARGET_FIRST_NAME'].notna() & (df_validated['BD_TARGET_FIRST_NAME'] != '')) |
        (df_validated['BD_TARGET_LAST_NAME'].notna() & (df_validated['BD_TARGET_LAST_NAME'] != '')) |
        (df_validated['BD_OWNER_NAME_FULL'].notna() & (df_validated['BD_OWNER_NAME_FULL'] != ''))
    )

    df_validated['has_valid_address'] = (
        df_validated['BD_ADDRESS'].notna() &
        (df_validated['BD_ADDRESS'] != '') &
        df_validated['BD_CITY'].notna() &
        (df_validated['BD_CITY'] != '') &
        df_validated['BD_STATE'].notna() &
        (df_validated['BD_STATE'] != '') &
        df_validated['BD_ZIP'].notna() &
        (df_validated['BD_ZIP'] != '')
    )
    
    # Report statistics
    total_records = len(df_validated)
    valid_names = df_validated['has_valid_name'].sum()
    valid_addresses = df_validated['has_valid_address'].sum()
    fully_valid = (df_validated['has_valid_name'] & df_validated['has_valid_address']).sum()
    
    print("📊 Input Data Quality Report:")
    print(f"   Total records: {total_records}")
    print(f"   Records with valid names: {valid_names} ({valid_names/total_records*100:.1f}%)")
    print(f"   Records with complete addresses: {valid_addresses} ({valid_addresses/total_records*100:.1f}%)")
    print(f"   Fully valid records: {fully_valid} ({fully_valid/total_records*100:.1f}%)")
    
    # Report missing fields
    missing_fields = []
    for field in ['BD_TARGET_FIRST_NAME', 'BD_TARGET_LAST_NAME', 'BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP']:
        missing_count = df_validated[field].isna().sum() + (df_validated[field] == '').sum()
        if missing_count > 0:
            missing_fields.append(f"{field}: {missing_count} records")
    
    if missing_fields:
        print("   Missing fields:")
        for field_info in missing_fields[:5]:  # Show top 5
            print(f"     - {field_info}")
    
    return df_validated


def optimize_for_api(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize input fields for better API results.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Optimized DataFrame with filled and formatted fields
    """
    df_optimized = df.copy()
    
    # Fill missing first/last names from full name if available
    for idx, row in df_optimized.iterrows():
        if pd.isna(row.get('BD_TARGET_FIRST_NAME')) or row.get('BD_TARGET_FIRST_NAME') == '':
            if pd.notna(row.get('BD_OWNER_NAME_FULL')) and row.get('BD_OWNER_NAME_FULL') != '':
                first_name, last_name = split_full_name(row['BD_OWNER_NAME_FULL'])
                df_optimized.at[idx, 'BD_TARGET_FIRST_NAME'] = first_name
                df_optimized.at[idx, 'BD_TARGET_LAST_NAME'] = last_name

    # Normalize and clean address fields
    df_optimized['BD_ADDRESS'] = df_optimized['BD_ADDRESS'].apply(
        lambda x: clean_address_line(x) if pd.notna(x) else ''
    )

    df_optimized['BD_CITY'] = df_optimized['BD_CITY'].apply(
        lambda x: str(x).strip().title() if pd.notna(x) and x != '' else ''
    )

    df_optimized['BD_STATE'] = df_optimized['BD_STATE'].apply(
        lambda x: normalize_state(x) if pd.notna(x) and x != '' else ''
    )

    df_optimized['BD_ZIP'] = df_optimized['BD_ZIP'].apply(
        lambda x: normalize_zip_code(x) if pd.notna(x) and x != '' else ''
    )

    # Try to fill missing city/state from other records with same address
    address_groups = df_optimized.groupby('BD_ADDRESS')
    improvements = 0

    for address, group in address_groups:
        if len(group) > 1 and address and str(address).strip():
            # Find the most complete record in this group
            non_empty_cities = group['BD_CITY'][group['BD_CITY'] != ''].dropna()
            non_empty_states = group['BD_STATE'][group['BD_STATE'] != ''].dropna()
            non_empty_zips = group['BD_ZIP'][group['BD_ZIP'] != ''].dropna()

            best_city = non_empty_cities.mode().iloc[0] if not non_empty_cities.empty else ''
            best_state = non_empty_states.mode().iloc[0] if not non_empty_states.empty else ''
            best_zip = non_empty_zips.mode().iloc[0] if not non_empty_zips.empty else ''

            # Fill missing values in group
            for idx in group.index:
                if df_optimized.at[idx, 'BD_CITY'] == '' and best_city:
                    df_optimized.at[idx, 'BD_CITY'] = best_city
                    improvements += 1
                if df_optimized.at[idx, 'BD_STATE'] == '' and best_state:
                    df_optimized.at[idx, 'BD_STATE'] = best_state
                    improvements += 1
                if df_optimized.at[idx, 'BD_ZIP'] == '' and best_zip:
                    df_optimized.at[idx, 'BD_ZIP'] = best_zip
                    improvements += 1
    
    # Report improvements
    original_complete = ((df['BD_CITY'] != '') & (df['BD_STATE'] != '') & (df['BD_ZIP'] != '')).sum()
    optimized_complete = ((df_optimized['BD_CITY'] != '') & (df_optimized['BD_STATE'] != '') & (df_optimized['BD_ZIP'] != '')).sum()
    
    if optimized_complete > original_complete:
        print(f"✅ Field optimization improved {optimized_complete - original_complete} records")
    
    return df_optimized


def consolidate_entity_families(df: pd.DataFrame, similarity_threshold: float = 0.6) -> pd.DataFrame:
    """Consolidate principals who appear across related entity families.
    
    Args:
        df: BatchData DataFrame
        similarity_threshold: Threshold for entity family grouping
        
    Returns:
        Consolidated DataFrame with entity family information
    """
    if len(df) <= 1:
        return df
    
    original_count = len(df)
    
    # Get unique entities
    unique_entities = df['source_entity_name'].unique().tolist()
    
    # Detect entity families
    entity_families = detect_entity_families(unique_entities, similarity_threshold)
    
    if not entity_families:
        print("📊 Entity Family Consolidation: No related entity families detected")
        return df
    
    print(f"📊 Entity Family Consolidation:")
    print(f"   Detected families: {len(entity_families)}")
    
    # Create entity to family mapping
    entity_to_family = {}
    for family_id, entities in entity_families.items():
        for entity in entities:
            entity_to_family[entity] = family_id
        print(f"   {family_id}: {len(entities)} entities")
        for entity in entities[:3]:  # Show first 3
            print(f"     - {entity}")
        if len(entities) > 3:
            print(f"     ... and {len(entities)-3} more")
    
    # Add family information to dataframe
    df_work = df.copy()
    df_work['_entity_family'] = df_work['source_entity_name'].map(entity_to_family).fillna('SINGLETON')
    
    # Group by person identity within families
    consolidation_fields = [
        'target_first_name', 'target_last_name', 'owner_name_full',
        'address_line1', 'city', 'state', 'zip', '_entity_family'
    ]
    
    # Fill NaN values for comparison
    df_work[consolidation_fields] = df_work[consolidation_fields].fillna('')
    
    # Create comparison key
    df_work['_consolidation_key'] = df_work[consolidation_fields].apply(
        lambda row: '|'.join(str(row[col]).strip().upper() for col in consolidation_fields),
        axis=1
    )
    
    # Group and consolidate
    consolidated_records = []
    consolidations_made = 0
    
    grouped = df_work.groupby('_consolidation_key')
    
    for consolidation_key, group in grouped:
        if len(group) == 1:
            # No consolidation needed
            record = group.iloc[0]
            consolidated_records.append(record)
        else:
            # Consolidate multiple records for same person in entity family
            consolidations_made += len(group) - 1
            
            # Score and select best record
            def score_record(row):
                score = 0
                fields_to_check = ['target_first_name', 'target_last_name', 'address_line1', 'city', 'state', 'zip']
                for field in fields_to_check:
                    if field in row and row[field] and str(row[field]).strip() and str(row[field]).lower() != 'nan':
                        score += 1
                return score
            
            group['_score'] = group.apply(score_record, axis=1)
            group_sorted = group.sort_values(['_score', 'record_id'], ascending=[False, True])
            best_record = group_sorted.iloc[0].copy()
            
            # Enhance notes with entity consolidation information
            entities_info = []
            for _, row in group.iterrows():
                entity = row['source_entity_name']
                role = row.get('title_role', '')
                if entity and role:
                    entities_info.append(f"{entity} ({role})")
                elif entity:
                    entities_info.append(entity)
            
            # Create consolidated notes
            original_notes = best_record.get('notes', '')
            family_info = f"Consolidated across entity family: {'; '.join(entities_info)}"
            
            if original_notes and str(original_notes).strip():
                enhanced_notes = f"{original_notes}. {family_info}"
            else:
                enhanced_notes = family_info
            
            best_record['notes'] = enhanced_notes
            
            # Update record_id to indicate consolidation
            original_record_id = best_record['record_id']
            best_record['record_id'] = f"{original_record_id}_consolidated"
            
            consolidated_records.append(best_record)
    
    # Create result DataFrame
    result_df = pd.DataFrame(consolidated_records)
    
    # Remove helper columns
    helper_columns = ['_entity_family', '_consolidation_key', '_score']
    for col in helper_columns:
        if col in result_df.columns:
            result_df = result_df.drop(col, axis=1)
    
    # Reset index
    result_df = result_df.reset_index(drop=True)
    
    final_count = len(result_df)
    reduction_percent = (consolidations_made / original_count) * 100 if original_count > 0 else 0
    
    print(f"   Original records: {original_count}")
    print(f"   Consolidated records: {final_count}")
    print(f"   Family consolidations: {consolidations_made}")
    print(f"   Additional reduction: {reduction_percent:.1f}%")
    
    return result_df