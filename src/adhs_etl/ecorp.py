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

Output Files:
- Ecorp Upload: 4 columns (FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE)
- Ecorp Complete: 32 columns (Upload + 28 ACC entity fields)
"""

import time
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
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
                """Extract Statutory Agent information from the specific section."""
                agent_name = ""
                agent_addr = ""

                try:
                    # Method 1: Look for section-header approach
                    agent_header = soup.find(text=lambda t: t and "Statutory Agent Information" in t)
                    if agent_header:
                        header_parent = agent_header.find_parent()
                        if header_parent and 'section-header' in str(header_parent.get('class', [])):
                            next_row = header_parent.find_next_sibling('div', class_='row')
                            if next_row:
                                name_label = next_row.find(text=lambda t: t and "Name:" in t)
                                if name_label:
                                    name_div = name_label.find_parent().find_next_sibling()
                                    if name_div:
                                        agent_name = name_div.get_text(strip=True)

                                addr_label = next_row.find(text=lambda t: t and "Address:" in t)
                                if addr_label:
                                    addr_div = addr_label.find_parent().find_next_sibling()
                                    if addr_div:
                                        agent_addr = addr_div.get_text(strip=True)

                    # Method 2: If method 1 fails, look for all Name: labels and find the one in statutory section
                    if not agent_name:
                        all_name_labels = soup.find_all(text=lambda t: t and "Name:" in t)
                        for name_label in all_name_labels:
                            # Check if this Name: label is in the statutory agent section
                            label_parent = name_label.find_parent()
                            previous_labels = label_parent.find_all_previous('label', limit=5)
                            for prev_label in previous_labels:
                                if "Statutory Agent Information" in prev_label.get_text():
                                    # This Name: is in the statutory section
                                    name_div = label_parent.find_next_sibling()
                                    if name_div:
                                        agent_name = name_div.get_text(strip=True)
                                        break
                            if agent_name:
                                break

                    # Method 3: Similar approach for address
                    if not agent_addr:
                        all_addr_labels = soup.find_all(text=lambda t: t and "Address:" in t)
                        for addr_label in all_addr_labels:
                            label_parent = addr_label.find_parent()
                            previous_labels = label_parent.find_all_previous('label', limit=5)
                            for prev_label in previous_labels:
                                if "Statutory Agent Information" in prev_label.get_text():
                                    addr_div = label_parent.find_next_sibling()
                                    if addr_div:
                                        agent_addr = addr_div.get_text(strip=True)
                                        break
                            if agent_addr:
                                break

                except Exception:
                    pass

                # Fallback to original method if new method fails
                if not agent_name:
                    agent_name = get_field("Name:")
                if not agent_addr:
                    agent_addr = get_field("Address:")

                return agent_name, agent_addr

            def extract_principal_info():
                """Extract Principal Information from the table/grid section."""
                principals = {}

                try:
                    # Look for the principal information table by id
                    principal_table = soup.find('table', id='grid_principalList')
                    if principal_table:
                        # Find all data rows (skip header)
                        tbody = principal_table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')

                            principal_count = 0
                            for row in rows:
                                if principal_count >= 5:  # Limit to 5 principals
                                    break

                                cells = row.find_all('td')
                                if len(cells) >= 4:  # Title, Name, Attention, Address
                                    principal_count += 1

                                    title_text = cells[0].get_text(strip=True) if cells[0] else ""
                                    name_text = cells[1].get_text(strip=True) if cells[1] else ""
                                    # Skip attention field (cells[2])
                                    addr_text = cells[3].get_text(strip=True) if cells[3] else ""

                                    principals[f"Title{principal_count}"] = title_text
                                    principals[f"Name{principal_count}"] = name_text
                                    principals[f"Address{principal_count}"] = addr_text
                except Exception:
                    pass

                # Ensure we have at least empty strings for the first 5 principals
                for i in range(1, 6):
                    if f"Title{i}" not in principals:
                        principals[f"Title{i}"] = ""
                    if f"Name{i}" not in principals:
                        principals[f"Name{i}"] = ""
                    if f"Address{i}" not in principals:
                        principals[f"Address{i}"] = ""

                return principals

            entity_type = get_field("Entity Type:")
            status = get_field("Entity Status:")
            formation_date = get_field("Formation Date:")
            business_type = get_field("Business Type:")
            domicile_state = get_field("Domicile State:")
            agent_name, agent_addr = get_statutory_agent_info()
            county = get_field("County:")
            principal_info = extract_principal_info()

            entities.append(
                {
                    "Search Name": name,
                    "Type": classify_name_type(name),
                    "Entity Name(s)": entity_name if entity_name else "",
                    "Entity ID(s)": entity_id if entity_id else "",
                    "Entity Type": entity_type if entity_type else "",
                    "Status": status if status else "",
                    "Formation Date": formation_date if formation_date else "",
                    "Business Type": business_type if business_type else "",
                    "Domicile State": domicile_state if domicile_state else "",
                    "Statutory Agent": agent_name if agent_name else "",
                    "Agent Address": agent_addr if agent_addr else "",
                    "County": county if county else "",
                    "Comments": "",
                    "Title1": principal_info.get("Title1", ""),
                    "Name1": principal_info.get("Name1", ""),
                    "Address1": principal_info.get("Address1", ""),
                    "Title2": principal_info.get("Title2", ""),
                    "Name2": principal_info.get("Name2", ""),
                    "Address2": principal_info.get("Address2", ""),
                    "Title3": principal_info.get("Title3", ""),
                    "Name3": principal_info.get("Name3", ""),
                    "Address3": principal_info.get("Address3", ""),
                    "Title4": principal_info.get("Title4", ""),
                    "Name4": principal_info.get("Name4", ""),
                    "Address4": principal_info.get("Address4", ""),
                    "Title5": principal_info.get("Title5", ""),
                    "Name5": principal_info.get("Name5", ""),
                    "Address5": principal_info.get("Address5", ""),
                }
            )
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
    """Return ACC record with all 22 fields as empty strings.

    Returns
    -------
    dict
        Dictionary with all ACC field keys set to empty strings
    """
    return {
        'Search Name': '',
        'Type': '',
        'Entity Name(s)': '',
        'Entity ID(s)': '',
        'Entity Type': '',
        'Status': '',
        'Formation Date': '',
        'Business Type': '',
        'Domicile State': '',
        'Statutory Agent': '',
        'Agent Address': '',
        'County': '',
        'Comments': '',
        'Title1': '', 'Name1': '', 'Address1': '',
        'Title2': '', 'Name2': '', 'Address2': '',
        'Title3': '', 'Name3': '', 'Address3': '',
        'Title4': '', 'Name4': '', 'Address4': '',
        'Title5': '', 'Name5': '', 'Address5': ''
    }


def save_checkpoint(path: Path, results: list, idx: int) -> None:
    """Save progress checkpoint to disk for resume capability.

    Parameters
    ----------
    path : Path
        Path to checkpoint file
    results : list
        List of completed records
    idx : int
        Current index in processing
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump((results, idx), f)


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

        # Generate timestamp (12-hour format)
        timestamp = datetime.now().strftime("%m.%d.%I-%M-%S")

        # Save
        output_dir = Path("Ecorp/Upload")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{month_code}_Ecorp_Upload {timestamp}.xlsx"

        upload_df.to_excel(output_path, index=False, engine='xlsxwriter')
        print(f"✅ Created Ecorp Upload: {output_path}")

        return output_path

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

    Output has 32 columns:
    - A-D: FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE (from Upload)
    - E-AF: 28 ACC fields (Search Name, Type, Entity details, Principals)

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

        # Load checkpoint if exists
        if checkpoint_file.exists():
            with open(checkpoint_file, 'rb') as f:
                results, start_idx = pickle.load(f)
            print(f"📂 Resuming from checkpoint: record {start_idx + 1}/{total_records}")

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

                # Base record (columns A-D from Upload)
                base = {
                    'FULL_ADDRESS': row['FULL_ADDRESS'],
                    'COUNTY': row['COUNTY'],
                    'Owner_Ownership': row['Owner_Ownership'],
                    'OWNER_TYPE': row['OWNER_TYPE']
                }

                # ACC lookup (columns E-Z)
                owner_name = row['Owner_Ownership']

                if pd.isna(owner_name) or str(owner_name).strip() == '':
                    # Blank owner - use empty ACC record
                    acc_data = get_blank_acc_record()
                else:
                    # Lookup with caching
                    acc_results = get_cached_or_lookup(cache, str(owner_name), driver)
                    acc_data = acc_results[0] if acc_results else get_blank_acc_record()

                # Combine Upload cols (A-D) + ACC cols (E-Z)
                complete_record = {**base, **acc_data}
                results.append(complete_record)

                # Checkpoint every 50 records
                if (idx + 1) % 50 == 0:
                    save_checkpoint(checkpoint_file, results, idx + 1)
                    print(f"   💾 Checkpoint saved at {idx + 1} records")

            # Save final Complete file
            timestamp = extract_timestamp_from_path(upload_path)
            output_dir = Path("Ecorp/Complete")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{month_code}_Ecorp_Complete {timestamp}.xlsx"

            df_complete = pd.DataFrame(results)
            df_complete.to_excel(output_path, index=False, engine='xlsxwriter')

            elapsed_total = time.time() - start_time
            print(f"\n✅ Created Ecorp Complete: {output_path}")
            print(f"   Total time: {elapsed_total/60:.1f} minutes")
            print(f"   Cache hits: {total_records - len(cache)} lookups saved")

            # Clean up checkpoint
            if checkpoint_file.exists():
                checkpoint_file.unlink()

            return True

        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user - saving progress...")
            save_checkpoint(checkpoint_file, results, idx)
            print(f"💾 Progress saved to checkpoint. Run again to resume from record {idx + 1}")
            return False

        finally:
            driver.quit()

    except Exception as e:
        print(f"❌ Error processing Ecorp Complete: {e}")
        import traceback
        traceback.print_exc()
        return False