"""
Arizona Corporation Commission (ACC) Entity Lookup Integration
==============================================================

This module provides functionality to extract ownership data from MCAO files
and enrich it with Arizona Corporation Commission entity details via web scraping.

Features:
- Generate Ecorp Upload files from MCAO Complete data
- Automated ACC entity lookup via Selenium
- Progress checkpointing for interruption recovery
- In-memory caching to avoid duplicate lookups
- Graceful handling of blank/missing owner names
- Sequential record indexing (ECORP_INDEX_#)
- Entity URL capture for reference tracking

Output Files:
- Ecorp Upload: 4 columns (FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE)
- Ecorp Complete: 93 columns (4 Upload + 1 Index + 1 Owner Type + 87 ACC + 1 URL)
  * ECORP_INDEX_# - Sequential record number (1, 2, 3...)
  * ECORP_URL - ACC entity detail page URL from ecorp.azcc.gov
"""

import time
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup

# Import timestamp utilities for standardized naming
try:
    from .utils import (
        get_standard_timestamp,
        format_output_filename,
        get_legacy_filename,
        save_excel_with_legacy_copy,
        extract_timestamp_from_filename
    )
except ImportError:
    # For standalone script execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from utils import (
        get_standard_timestamp,
        format_output_filename,
        get_legacy_filename,
        save_excel_with_legacy_copy,
        extract_timestamp_from_filename
    )
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def classify_name_type(name: str) -> str:
    """Classify a name as Entity or Individual(s) based on keywords and patterns.

    Parameters
    ----------
    name : str
        The name to classify

    Returns
    -------
    str
        "Entity" or "Individual(s)" or empty string for successful lookups
    """
    if not name:
        return ""

    name_upper = str(name).upper()

    # Entity keywords
    entity_keywords = [
        'LLC', 'CORP', 'INC', 'SCHOOL', 'DISTRICT', 'TRUST', 'FOUNDATION',
        'COMPANY', 'CO.', 'ASSOCIATION', 'CHURCH', 'PROPERTIES', 'LP',
        'LTD', 'PARTNERSHIP', 'FUND', 'HOLDINGS', 'INVESTMENTS', 'VENTURES',
        'GROUP', 'ENTERPRISE', 'BORROWER', 'ACADEMY', 'COLLEGE', 'UNIVERSITY',
        'MEDICAL', 'HEALTH', 'CARE', 'SOBER', 'LEARNING', 'PRESCHOOL',
        # Additional business/organization keywords
        'CENTERS', 'CENTER', 'HOSPICE', 'HOSPITAL', 'CLINIC',
        'STATE OF', 'CITY OF', 'COUNTY OF', 'TOWN OF',
        'UNITED STATES', 'GOVERNMENT', 'FEDERAL', 'MUNICIPAL',
        'ARMY', 'NAVY', 'AIR FORCE', 'MILITARY', 'SALVATION',
        'ARC', 'HOUSE', 'HOME', 'HOMES', 'LIVING', 'SENIOR',
        'FACILITY', 'FACILITIES', 'SERVICES', 'SERVICE',
        'UNITED', 'METHODIST', 'LUTHERAN', 'EVANGELICAL', 'BAPTIST',
        'CATHOLIC', 'CHRISTIAN', 'CONGREGATION', 'PRESBYTERY',
        'ASSEMBLY', 'LEAGUE', 'ASSOCIATES', 'JOINT VENTURE',
        'DST', 'LIMITED', 'PARTNERS', 'SETTLEMENT', 'HABILITATION'
    ]

    # Check for entity keywords
    for keyword in entity_keywords:
        if keyword in name_upper:
            return "Entity"

    # Check for individual patterns
    # Simple name patterns (2-4 words, likely person names)
    words = name.strip().split()
    if len(words) >= 2 and len(words) <= 4:
        # Additional check: if it doesn't contain entity-like words
        if not any(word.upper() in ['PROPERTY', 'REAL', 'ESTATE', 'DEVELOPMENT', 'RENTAL']
                   for word in words):
            return "Individual(s)"

    # Default to Entity for unclear cases
    return "Entity"


def classify_owner_type(name: str) -> str:
    """Classify owner name and map to BUSINESS/INDIVIDUAL for OWNER_TYPE column.

    Parameters
    ----------
    name : str
        Owner name to classify

    Returns
    -------
    str
        "BUSINESS" or "INDIVIDUAL"
    """
    if pd.isna(name) or str(name).strip() == '':
        return ""

    result = classify_name_type(name)
    return "BUSINESS" if result == "Entity" else "INDIVIDUAL"


def parse_individual_names(name_str: str) -> List[str]:
    """Parse concatenated individual names into separate formatted names.

    Handles patterns like:
    - "MCCORMICK TIMOTHY/ROBIN" → ["TIMOTHY MCCORMICK", "ROBIN MCCORMICK"]
    - "SOTO JEREMY/SIPES CAROLYN" → ["JEREMY SOTO", "CAROLYN SIPES"]
    - "GREEN JEROME V" → ["JEROME V GREEN"]
    - "BARATTI JAMES J/DEBORAH F TR" → ["JAMES J BARATTI", "DEBORAH F BARATTI"]

    Parameters
    ----------
    name_str : str
        The concatenated name string to parse

    Returns
    -------
    List[str]
        List of up to 4 parsed individual names
    """
    if pd.isna(name_str) or str(name_str).strip() == '':
        return []

    names = []
    name_str = str(name_str).strip()

    # Remove common suffixes that aren't part of the name
    suffixes_to_remove = ['TR', 'TRUST', 'TRUSTEE', 'ET AL', 'JT TEN', 'JTRS', 'JT', 'EST', 'ESTATE']
    for suffix in suffixes_to_remove:
        if name_str.endswith(' ' + suffix):
            name_str = name_str[:-(len(suffix) + 1)].strip()

    # Split by forward slash to get individual components
    parts = [p.strip() for p in name_str.split('/') if p.strip()]

    if len(parts) == 1:
        # Single name - check if it needs reordering (LASTNAME FIRSTNAME MIDDLE)
        single_name = parts[0]
        words = single_name.split()

        if len(words) >= 2:
            # Check if first word looks like a last name (all caps, longer than 2 chars)
            # and second word looks like a first name
            if len(words[0]) > 2:
                # Assume format is LASTNAME FIRSTNAME [MIDDLE]
                # Reorder to FIRSTNAME [MIDDLE] LASTNAME
                reordered = ' '.join(words[1:]) + ' ' + words[0]
                names.append(reordered)
            else:
                names.append(single_name)
        else:
            names.append(single_name)

    elif len(parts) == 2:
        # Two parts - check if they share a last name
        first_part_words = parts[0].split()
        second_part = parts[1]

        if len(first_part_words) >= 2:
            # Likely format: "LASTNAME FIRSTNAME1/FIRSTNAME2"
            potential_lastname = first_part_words[0]
            first_firstname = ' '.join(first_part_words[1:])

            # Check if second part is just a first name (no spaces or one middle initial)
            if len(second_part.split()) <= 2:
                # They share the last name
                names.append(f"{first_firstname} {potential_lastname}")
                names.append(f"{second_part} {potential_lastname}")
            else:
                # Two complete different names
                # Parse each separately
                for part in parts:
                    part_words = part.split()
                    if len(part_words) >= 2:
                        reordered = ' '.join(part_words[1:]) + ' ' + part_words[0]
                        names.append(reordered)
                    else:
                        names.append(part)
        else:
            # Simple case - treat as separate names
            for part in parts:
                names.append(part)

    else:
        # Multiple parts separated by slashes
        # Check if pattern is "LASTNAME1 FIRSTNAME1/LASTNAME2 FIRSTNAME2/..."
        all_have_multiple_words = all(len(p.split()) >= 2 for p in parts)

        if all_have_multiple_words:
            # Each part is likely "LASTNAME FIRSTNAME [MIDDLE]"
            for part in parts:
                part_words = part.split()
                if len(part_words) >= 2:
                    reordered = ' '.join(part_words[1:]) + ' ' + part_words[0]
                    names.append(reordered)
                else:
                    names.append(part)
        else:
            # Mixed format or unclear - preserve as is
            names.extend(parts)

    # Clean up names - remove extra spaces, capitalize properly
    cleaned_names = []
    for name in names[:4]:  # Limit to 4 names
        # Remove extra spaces
        name = ' '.join(name.split())
        # Keep uppercase as provided (these are typically already uppercase)
        cleaned_names.append(name)

    return cleaned_names


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """Configure and return a Selenium Chrome WebDriver.

    Parameters
    ----------
    headless : bool
        Whether to run Chrome in headless mode.

    Returns
    -------
    selenium.webdriver.Chrome
        An instance of the Chrome WebDriver.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def search_entities(driver: webdriver.Chrome, name: str) -> List[Dict[str, str]]:
    """Search the ACC site for a company name and return entity details.

    This function navigates to the ACC public search page, enters
    ``name`` into the search bar, parses any results table that
    appears, and retrieves detailed fields for each entity by opening
    the detail page in a new tab.

    Parameters
    ----------
    driver : selenium.webdriver.Chrome
        The active Selenium driver.
    name : str
        The company name to search for.

    Returns
    -------
    List[Dict[str, str]]
        A list of dictionaries where each dictionary contains details
        about an entity.  If no results are found, a single
        dictionary with ``Status`` set to ``Not found`` is returned.
    """
    base_url = "https://ecorp.azcc.gov/EntitySearch/Index"
    driver.get(base_url)

    try:
        # Wait for search bar
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Search for an Entity Name']"))
        )
        # Clear and enter search term
        search_input.clear()
        search_input.send_keys(name)
        search_input.send_keys(Keys.RETURN)

        # Wait for results table or no results message
        time.sleep(1.5)  # short wait for results to load

        # Check for no results modal
        try:
            no_results_modal = driver.find_element(By.XPATH, "//div[contains(text(), 'No search results were found')]")
            # Click OK button to close modal
            ok_button = driver.find_element(By.XPATH, "//button[normalize-space()='OK']")
            ok_button.click()
            return [get_blank_acc_record()]
        except Exception:
            pass

        # Parse results table rows
        entities = []
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if not cols or len(cols) < 2:
                continue
            entity_id = cols[0].text.strip()
            entity_name = cols[1].text.strip()
            # Open detail page in new tab
            link = cols[1].find_element(By.TAG_NAME, "a")
            detail_url = link.get_attribute("href")
            # Open in same driver (new tab)
            driver.execute_script("window.open(arguments[0]);", detail_url)
            driver.switch_to.window(driver.window_handles[-1])
            # Wait for entity info to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(text(),'Entity Information')]") )
            )
            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            # Extract fields
            def get_field(label: str) -> str:
                el = soup.find(text=lambda t: t and label in t)
                if el:
                    # Find the next sibling which holds the value
                    val = el.find_next()
                    return val.get_text(strip=True)
                return ""

            def get_statutory_agent_info():
                """Extract Statutory Agent information using simple text parsing."""
                agents = []

                try:
                    # Get the entire page text
                    page_text = soup.get_text()

                    # Find "Statutory Agent Information" section in the text
                    import re

                    # Look for the statutory agent section and extract Name
                    # Pattern: Find "Name:" then capture the next non-empty line
                    stat_agent_section = re.search(
                        r'Statutory Agent Information.*?Name:\s*\n\s*([^\n\r]+?)(?:\s*\n|\s*Appointed)',
                        page_text,
                        re.DOTALL | re.IGNORECASE
                    )

                    agent_name = ""
                    agent_addr = ""

                    if stat_agent_section:
                        agent_name = stat_agent_section.group(1).strip()
                        # Clean up - remove extra spaces
                        agent_name = ' '.join(agent_name.split())
                    else:
                        # Try alternative pattern where name might be on same line
                        alt_pattern = re.search(
                            r'Statutory Agent Information.*?Name:\s*([^\n\r]+?)(?:\s+Attention:|Appointed|$)',
                            page_text,
                            re.DOTALL | re.IGNORECASE
                        )
                        if alt_pattern:
                            agent_name = alt_pattern.group(1).strip()
                            agent_name = ' '.join(agent_name.split())

                    # Look for Address in the same section
                    addr_section = re.search(
                        r'Statutory Agent Information.*?Address:\s*\n?\s*([^\n\r]+?)(?:\s*\n|\s*Agent Last|E-mail:|County:|Mailing)',
                        page_text,
                        re.DOTALL | re.IGNORECASE
                    )

                    if addr_section:
                        agent_addr = addr_section.group(1).strip()
                        agent_addr = ' '.join(agent_addr.split())

                    # If we found name or address, add to agents list
                    if agent_name or agent_addr:
                        agents.append({
                            'Name': agent_name,
                            'Address': agent_addr,
                            'Phone': "",
                            'Mail': ""
                        })

                except Exception:
                    # Silent fail - return empty list
                    pass

                return agents

            def extract_principal_info():
                """Extract Principal Information from the table/grid section and categorize by role."""
                categorized_principals = {
                    'Manager': [],
                    'Member': [],
                    'Manager/Member': []
                }

                try:
                    # Look for the principal information table by id
                    principal_table = soup.find('table', id='grid_principalList')
                    if principal_table:
                        # Find all data rows (skip header)
                        tbody = principal_table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')

                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) >= 4:  # Title, Name, Attention, Address
                                    title_text = cells[0].get_text(strip=True) if cells[0] else ""
                                    name_text = cells[1].get_text(strip=True) if cells[1] else ""
                                    # Skip attention field (cells[2])
                                    addr_text = cells[3].get_text(strip=True) if cells[3] else ""

                                    # Look for phone/email if present (conservative approach)
                                    phone_text = ""
                                    mail_text = ""
                                    if len(cells) > 4:
                                        # Check if additional cells might contain phone/email
                                        for cell in cells[4:]:
                                            cell_text = cell.get_text(strip=True)
                                            if '@' in cell_text:
                                                mail_text = cell_text
                                            elif any(char.isdigit() for char in cell_text) and len(cell_text) >= 7:
                                                phone_text = cell_text

                                    # Categorize based on title
                                    title_upper = title_text.upper()
                                    principal_data = {
                                        'Name': name_text,
                                        'Address': addr_text,
                                        'Phone': phone_text,
                                        'Mail': mail_text
                                    }

                                    if 'MANAGER' in title_upper and 'MEMBER' in title_upper:
                                        if len(categorized_principals['Manager/Member']) < 5:
                                            categorized_principals['Manager/Member'].append(principal_data)
                                    elif 'MANAGER' in title_upper:
                                        if len(categorized_principals['Manager']) < 5:
                                            categorized_principals['Manager'].append(principal_data)
                                    elif 'MEMBER' in title_upper:
                                        if len(categorized_principals['Member']) < 5:
                                            categorized_principals['Member'].append(principal_data)
                                    else:
                                        # Default to Manager if title unclear
                                        if len(categorized_principals['Manager']) < 5:
                                            categorized_principals['Manager'].append(principal_data)

                except Exception:
                    pass

                return categorized_principals

            entity_type = get_field("Entity Type:")
            status = get_field("Entity Status:")
            formation_date = get_field("Formation Date:")
            business_type = get_field("Business Type:")
            domicile_state = get_field("Domicile State:")
            statutory_agents = get_statutory_agent_info()
            county = get_field("County:")
            principal_info = extract_principal_info()

            # Build the record with new structure
            record = {
                "Search Name": name,
                "Type": classify_name_type(name),
                "Entity Name(s)": entity_name if entity_name else "",
                "Entity ID(s)": entity_id if entity_id else "",
                "Entity Type": entity_type if entity_type else "",
                "Status": status if status else "",
                "Formation Date": formation_date if formation_date else "",
                "Business Type": business_type if business_type else "",
                "Domicile State": domicile_state if domicile_state else "",
                "County": county if county else "",
                "Comments": ""
            }

            # Add statutory agent fields (up to 3)
            for i in range(1, 4):
                if i <= len(statutory_agents):
                    agent = statutory_agents[i-1]
                    record[f"StatutoryAgent{i}_Name"] = agent.get('Name', '')
                    record[f"StatutoryAgent{i}_Address"] = agent.get('Address', '')
                    record[f"StatutoryAgent{i}_Phone"] = agent.get('Phone', '')
                    record[f"StatutoryAgent{i}_Mail"] = agent.get('Mail', '')
                else:
                    record[f"StatutoryAgent{i}_Name"] = ''
                    record[f"StatutoryAgent{i}_Address"] = ''
                    record[f"StatutoryAgent{i}_Phone"] = ''
                    record[f"StatutoryAgent{i}_Mail"] = ''

            # Add Manager fields (up to 5)
            managers = principal_info.get('Manager', [])
            for i in range(1, 6):
                if i <= len(managers):
                    mgr = managers[i-1]
                    record[f"Manager{i}_Name"] = mgr.get('Name', '')
                    record[f"Manager{i}_Address"] = mgr.get('Address', '')
                    record[f"Manager{i}_Phone"] = mgr.get('Phone', '')
                    record[f"Manager{i}_Mail"] = mgr.get('Mail', '')
                else:
                    record[f"Manager{i}_Name"] = ''
                    record[f"Manager{i}_Address"] = ''
                    record[f"Manager{i}_Phone"] = ''
                    record[f"Manager{i}_Mail"] = ''

            # Add Manager/Member fields (up to 5)
            mgr_members = principal_info.get('Manager/Member', [])
            for i in range(1, 6):
                if i <= len(mgr_members):
                    mm = mgr_members[i-1]
                    record[f"Manager/Member{i}_Name"] = mm.get('Name', '')
                    record[f"Manager/Member{i}_Address"] = mm.get('Address', '')
                    record[f"Manager/Member{i}_Phone"] = mm.get('Phone', '')
                    record[f"Manager/Member{i}_Mail"] = mm.get('Mail', '')
                else:
                    record[f"Manager/Member{i}_Name"] = ''
                    record[f"Manager/Member{i}_Address"] = ''
                    record[f"Manager/Member{i}_Phone"] = ''
                    record[f"Manager/Member{i}_Mail"] = ''

            # Add Member fields (up to 5)
            members = principal_info.get('Member', [])
            for i in range(1, 6):
                if i <= len(members):
                    mbr = members[i-1]
                    record[f"Member{i}_Name"] = mbr.get('Name', '')
                    record[f"Member{i}_Address"] = mbr.get('Address', '')
                    record[f"Member{i}_Phone"] = mbr.get('Phone', '')
                    record[f"Member{i}_Mail"] = mbr.get('Mail', '')
                else:
                    record[f"Member{i}_Name"] = ''
                    record[f"Member{i}_Address"] = ''
                    record[f"Member{i}_Phone"] = ''
                    record[f"Member{i}_Mail"] = ''

            # Add Individual name fields (empty for now - will be populated for INDIVIDUAL types)
            for i in range(1, 5):
                record[f"IndividualName{i}"] = ''

            # Add ECORP_URL
            record["ECORP_URL"] = detail_url if detail_url else ''

            entities.append(record)
            # Close tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        # If no entities were found, return a blank record
        if not entities:
            return [get_blank_acc_record()]

        return entities
    except Exception as e:
        # In the event of unexpected errors, return a blank record with error comment
        blank = get_blank_acc_record()
        blank["Comments"] = f"Lookup error: {e}"
        return [blank]


def get_blank_acc_record() -> dict:
    """Return ACC record with all fields as empty strings.

    Returns
    -------
    dict
        Dictionary with all ACC field keys set to empty strings
    """
    record = {
        'Search Name': '',
        'Type': '',
        'Entity Name(s)': '',
        'Entity ID(s)': '',
        'Entity Type': '',
        'Status': '',
        'Formation Date': '',
        'Business Type': '',
        'Domicile State': '',
        'County': '',
        'Comments': ''
    }

    # Add StatutoryAgent fields (3 agents)
    for i in range(1, 4):
        record[f'StatutoryAgent{i}_Name'] = ''
        record[f'StatutoryAgent{i}_Address'] = ''
        record[f'StatutoryAgent{i}_Phone'] = ''
        record[f'StatutoryAgent{i}_Mail'] = ''

    # Add Manager fields (5 managers)
    for i in range(1, 6):
        record[f'Manager{i}_Name'] = ''
        record[f'Manager{i}_Address'] = ''
        record[f'Manager{i}_Phone'] = ''
        record[f'Manager{i}_Mail'] = ''

    # Add Manager/Member fields (5 entries)
    for i in range(1, 6):
        record[f'Manager/Member{i}_Name'] = ''
        record[f'Manager/Member{i}_Address'] = ''
        record[f'Manager/Member{i}_Phone'] = ''
        record[f'Manager/Member{i}_Mail'] = ''

    # Add Member fields (5 members)
    for i in range(1, 6):
        record[f'Member{i}_Name'] = ''
        record[f'Member{i}_Address'] = ''
        record[f'Member{i}_Phone'] = ''
        record[f'Member{i}_Mail'] = ''

    # Add Individual name fields (4 individuals)
    for i in range(1, 5):
        record[f'IndividualName{i}'] = ''

    # Add ECORP_URL field
    record['ECORP_URL'] = ''

    return record


def save_checkpoint(path: Path, results: list, idx: int, total_records: int = None) -> None:
    """Save progress checkpoint to disk for resume capability.

    Parameters
    ----------
    path : Path
        Path to checkpoint file
    results : list
        List of completed records
    idx : int
        Current index in processing
    total_records : int, optional
        Total number of records in current upload file (for validation)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump((results, idx, total_records), f)


def extract_timestamp_from_path(path: Path) -> str:
    """Extract timestamp from Upload filename for consistency.

    Parameters
    ----------
    path : Path
        Path to Upload file

    Returns
    -------
    str
        Timestamp string in format MM.DD.HH-MM-SS
    """
    stem = path.stem
    if "_Ecorp_Upload" in stem:
        parts = stem.split("_Ecorp_Upload")
        if len(parts) > 1 and parts[1].strip():
            return parts[1].strip()
    # Fallback to current time
    return datetime.now().strftime("%m.%d.%I-%M-%S")


def get_cached_or_lookup(cache: dict, owner_name: str, driver: webdriver.Chrome) -> List[Dict[str, str]]:
    """Check cache before performing ACC lookup to avoid duplicates.

    Parameters
    ----------
    cache : dict
        In-memory cache mapping owner names to ACC results
    owner_name : str
        Owner name to lookup
    driver : webdriver.Chrome
        Selenium driver instance

    Returns
    -------
    List[Dict[str, str]]
        ACC entity results from cache or fresh lookup
    """
    if owner_name in cache:
        return cache[owner_name]

    results = search_entities(driver, owner_name)
    cache[owner_name] = results
    return results


def generate_ecorp_upload(month_code: str, mcao_complete_path: Path) -> Optional[Path]:
    """Generate Ecorp Upload file from MCAO_Complete data.

    Extracts 4 columns from MCAO_Complete:
    - Column A: FULL_ADDRESS (MCAO col A)
    - Column B: COUNTY (MCAO col B)
    - Column C: Owner_Ownership (MCAO col E)
    - Column D: OWNER_TYPE (classified as BUSINESS/INDIVIDUAL)

    Parameters
    ----------
    month_code : str
        Month code (e.g., "1.25")
    mcao_complete_path : Path
        Path to MCAO_Complete file

    Returns
    -------
    Optional[Path]
        Path to created Upload file, or None if failed
    """
    try:
        # Read MCAO_Complete file
        print(f"📋 Reading MCAO_Complete: {mcao_complete_path.name}")
        df = pd.read_excel(mcao_complete_path)

        # Validate columns exist
        if len(df.columns) < 5:
            print(f"❌ MCAO_Complete must have at least 5 columns, found {len(df.columns)}")
            return None

        # Extract columns (0-indexed)
        upload_df = pd.DataFrame({
            'FULL_ADDRESS': df.iloc[:, 0],           # Column A
            'COUNTY': df.iloc[:, 1],                 # Column B
            'Owner_Ownership': df.iloc[:, 4],        # Column E (0-indexed = 4)
            'OWNER_TYPE': df.iloc[:, 4].apply(classify_owner_type)  # Classify
        })

        print(f"📊 Extracted {len(upload_df)} records for Ecorp Upload")

        # Count blanks
        blank_count = upload_df['Owner_Ownership'].isna().sum() + (upload_df['Owner_Ownership'] == '').sum()
        if blank_count > 0:
            print(f"   ⚠️  {blank_count} records have blank Owner_Ownership")

        # Generate timestamp using standard format
        timestamp = get_standard_timestamp()

        # Generate new format filename
        new_filename = format_output_filename(month_code, "Ecorp_Upload", timestamp)

        # Generate legacy format filename
        legacy_filename = get_legacy_filename(month_code, "Ecorp_Upload", timestamp)

        # Save
        output_dir = Path("Ecorp/Upload")
        output_dir.mkdir(parents=True, exist_ok=True)

        new_path = output_dir / new_filename
        legacy_path = output_dir / legacy_filename

        upload_df.to_excel(new_path, index=False, engine='xlsxwriter')

        # Create legacy copy for backward compatibility
        save_excel_with_legacy_copy(new_path, legacy_path)

        print(f"✅ Created Ecorp Upload: {new_path}")
        print(f"✅ Created legacy copy: {legacy_path}")

        return new_path

    except Exception as e:
        print(f"❌ Error creating Ecorp Upload: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_ecorp_complete(month_code: str, upload_path: Path, headless: bool = True) -> bool:
    """Enrich Upload file with ACC entity data to create Complete file.

    Features:
    - Progress checkpointing every 50 records
    - In-memory caching to avoid duplicate lookups
    - Ctrl+C interrupt handling with save
    - Graceful handling of blank Owner_Ownership
    - Sequential record indexing (ECORP_INDEX_#)
    - Entity URL capture (ECORP_URL)

    Output has 93 columns:
    - A-C: FULL_ADDRESS, COUNTY, Owner_Ownership (from Upload)
    - D: ECORP_INDEX_# (sequential record number)
    - E: OWNER_TYPE (from Upload)
    - F-CN: 88 ACC fields (Search Name, Type, Entity details, Principals, Individual Names)
    - CO: ECORP_URL (ACC entity detail page URL)

    Parameters
    ----------
    month_code : str
        Month code (e.g., "1.25")
    upload_path : Path
        Path to Upload file
    headless : bool
        Run Chrome in headless mode

    Returns
    -------
    bool
        True if successful, False if interrupted or failed
    """
    try:
        # Read Upload file
        print(f"📋 Processing Ecorp Upload: {upload_path.name}")
        df_upload = pd.read_excel(upload_path)
        total_records = len(df_upload)

        # Setup
        checkpoint_file = Path(f"Ecorp/.checkpoint_{month_code}.pkl")
        results = []
        start_idx = 0
        cache = {}  # In-memory cache

        # Load checkpoint if exists and validate it
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'rb') as f:
                    checkpoint_data = pickle.load(f)

                # Handle old format (results, idx) or new format (results, idx, total)
                if len(checkpoint_data) == 3:
                    results, start_idx, checkpoint_total = checkpoint_data

                    # Validate checkpoint matches current upload file
                    if checkpoint_total != total_records:
                        print(f"⚠️  Checkpoint mismatch: checkpoint has {checkpoint_total} records, "
                              f"but upload has {total_records} records")
                        print(f"   Deleting stale checkpoint and starting fresh...")
                        checkpoint_file.unlink()
                        results = []
                        start_idx = 0
                    else:
                        print(f"📂 Resuming from checkpoint: record {start_idx + 1}/{total_records}")
                else:
                    # Old format checkpoint - assume it's stale, start fresh
                    results, start_idx = checkpoint_data
                    print(f"⚠️  Old checkpoint format detected (no record count validation)")
                    print(f"   Deleting old checkpoint and starting fresh...")
                    checkpoint_file.unlink()
                    results = []
                    start_idx = 0

            except Exception as e:
                print(f"⚠️  Error loading checkpoint: {e}")
                print(f"   Deleting corrupted checkpoint and starting fresh...")
                checkpoint_file.unlink()
                results = []
                start_idx = 0

        # Initialize driver
        print(f"🌐 Initializing Chrome WebDriver...")
        driver = setup_driver(headless)

        try:
            start_time = time.time()

            for idx, row in df_upload.iloc[start_idx:].iterrows():
                # Progress indicator
                if idx > 0 and idx % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (total_records - idx) / rate if rate > 0 else 0
                    print(f"   Progress: {idx}/{total_records} ({idx*100//total_records}%) | "
                          f"Rate: {rate:.1f} rec/sec | ETA: {remaining/60:.1f} min", flush=True)

                # Get Upload data
                owner_name = row['Owner_Ownership']
                owner_type = row['OWNER_TYPE']

                # ACC lookup (columns F-CO)
                if pd.isna(owner_name) or str(owner_name).strip() == '':
                    # Blank owner - use empty ACC record
                    acc_data = get_blank_acc_record()
                elif owner_type == 'INDIVIDUAL':
                    # For INDIVIDUAL type, skip ACC lookup and parse names instead
                    acc_data = get_blank_acc_record()
                    # Parse individual names
                    parsed_names = parse_individual_names(owner_name)
                    # Populate IndividualName fields
                    for i, parsed_name in enumerate(parsed_names[:4], 1):
                        acc_data[f'IndividualName{i}'] = parsed_name
                else:
                    # BUSINESS type - do ACC lookup with caching
                    acc_results = get_cached_or_lookup(cache, str(owner_name), driver)
                    acc_data = acc_results[0] if acc_results else get_blank_acc_record()

                # Build complete record in correct column order (93 columns: A-CO)
                # A-C: Upload columns, D: Index, E: Owner Type, F-CO: ACC fields
                complete_record = {
                    'FULL_ADDRESS': row['FULL_ADDRESS'],        # A
                    'COUNTY': row['COUNTY'],                     # B
                    'Owner_Ownership': row['Owner_Ownership'],   # C
                    'ECORP_INDEX_#': idx + 1,                    # D (sequential number)
                    'OWNER_TYPE': row['OWNER_TYPE'],             # E
                    **acc_data                                   # F-CO (ACC fields including ECORP_URL)
                }
                results.append(complete_record)

                # Checkpoint every 50 records
                if (idx + 1) % 50 == 0:
                    save_checkpoint(checkpoint_file, results, idx + 1, total_records)
                    print(f"   💾 Checkpoint saved at {idx + 1} records")

            # Save final Complete file with new naming
            # Extract timestamp from Upload file (or use current if not found)
            timestamp = extract_timestamp_from_filename(upload_path.name)
            if not timestamp:
                timestamp = get_standard_timestamp()

            # Generate new format filename
            new_filename = format_output_filename(month_code, "Ecorp_Complete", timestamp)

            # Generate legacy format filename
            legacy_filename = get_legacy_filename(month_code, "Ecorp_Complete", timestamp)

            output_dir = Path("Ecorp/Complete")
            output_dir.mkdir(parents=True, exist_ok=True)

            new_path = output_dir / new_filename
            legacy_path = output_dir / legacy_filename

            df_complete = pd.DataFrame(results)
            df_complete.to_excel(new_path, index=False, engine='xlsxwriter')

            # Create legacy copy for backward compatibility
            save_excel_with_legacy_copy(new_path, legacy_path)

            elapsed_total = time.time() - start_time
            print(f"\n✅ Created Ecorp Complete: {new_path}")
            print(f"✅ Created legacy copy: {legacy_path}")
            print(f"   Total time: {elapsed_total/60:.1f} minutes")
            print(f"   Cache hits: {total_records - len(cache)} lookups saved")

            # Clean up checkpoint
            if checkpoint_file.exists():
                checkpoint_file.unlink()

            return True

        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user - saving progress...")
            save_checkpoint(checkpoint_file, results, idx, total_records)
            print(f"💾 Progress saved to checkpoint. Run again to resume from record {idx + 1}")
            return False

        finally:
            driver.quit()

    except Exception as e:
        print(f"❌ Error processing Ecorp Complete: {e}")
        import traceback
        traceback.print_exc()
        return False