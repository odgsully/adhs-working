"""
main.py
This script reads an input Excel file containing company names (column
``Owner_Ownership``) and performs a live lookup against the Arizona
Corporation Commission (ACC) eCorp website to fetch detailed
registration information for each company.  The results are written to
an output Excel file.

The process closely mirrors the manual workflow executed during the
analysis: a headless Chromium browser (via Selenium) navigates to
``EntitySearch/PublicSearch`` on the ACC site, enters each search name
into the search bar, parses the resulting table, and opens each
entity’s detail page to collect relevant fields.  If no results are
found, the script records the search as ``Not found``.  When multiple
records are returned for the same search term (for example, both a
limited partnership and its general partner), each record is recorded
separately.

Usage:

    python main.py --input "8.25 ecorp in progress.xlsx" --output "8.25 ecorp complete.xlsx"

Requirements:
    - pandas
    - openpyxl
    - selenium
    - webdriver-manager
    - beautifulsoup4

The script automatically downloads the appropriate ChromeDriver using
webdriver-manager.  Running in a headless environment is enabled by
default.  You may disable headless mode for debugging by setting the
``--headless`` flag to ``false``.
"""

import argparse
import time
from typing import List, Dict

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
        'MEDICAL', 'HEALTH', 'CARE', 'SOBER', 'LEARNING', 'PRESCHOOL'
    ]
    
    # Check for entity keywords
    for keyword in entity_keywords:
        if keyword in name_upper:
            return "Entity"
    
    # Check for individual patterns
    # Names with slashes (joint ownership)
    if '/' in name:
        return "Individual(s)"
    
    # Simple name patterns (2-4 words, likely person names)
    words = name.strip().split()
    if len(words) >= 2 and len(words) <= 4:
        # Additional check: if it doesn't contain entity-like words
        if not any(word.upper() in ['PROPERTY', 'REAL', 'ESTATE', 'DEVELOPMENT', 'RENTAL'] 
                   for word in words):
            return "Individual(s)"
    
    # Default to Entity for unclear cases
    return "Entity"


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
            return [
                {
                    "Search Name": name,
                    "Type": classify_name_type(name),
                    "Entity Name(s)": "—",
                    "Entity ID(s)": "—",
                    "Entity Type": "—",
                    "Status": "Not found",
                    "Formation Date": "—",
                    "Business Type": "—",
                    "Domicile State": "—",
                    "Statutory Agent": "—",
                    "Agent Address": "—",
                    "County": "—",
                    "Comments": "No search results",
                    "Title1": "—",
                    "Name1": "—",
                    "Address1": "—",
                    "Title2": "—",
                    "Name2": "—",
                    "Address2": "—",
                    "Title3": "—",
                    "Name3": "—",
                    "Address3": "—",
                }
            ]
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
                            # by looking for "Statutory Agent Information" in previous elements
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
                
                # Ensure we have at least empty strings for the first 3 principals
                for i in range(1, 4):
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
                    "Entity Name(s)": entity_name,
                    "Entity ID(s)": entity_id,
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
                }
            )
            # Close tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        
        # If no entities were found, return a "Not found" record
        if not entities:
            return [
                {
                    "Search Name": name,
                    "Type": classify_name_type(name),
                    "Entity Name(s)": "—",
                    "Entity ID(s)": "—",
                    "Entity Type": "—",
                    "Status": "Not found",
                    "Formation Date": "—",
                    "Business Type": "—",
                    "Domicile State": "—",
                    "Statutory Agent": "—",
                    "Agent Address": "—",
                    "County": "—",
                    "Comments": "No search results",
                    "Title1": "—",
                    "Name1": "—",
                    "Address1": "—",
                    "Title2": "—",
                    "Name2": "—",
                    "Address2": "—",
                    "Title3": "—",
                    "Name3": "—",
                    "Address3": "—",
                }
            ]
        
        return entities
    except Exception as e:
        # In the event of unexpected errors, return a not-found record
        return [
            {
                "Search Name": name,
                "Type": classify_name_type(name),
                "Entity Name(s)": "—",
                "Entity ID(s)": "—",
                "Entity Type": "—",
                "Status": "Error",
                "Formation Date": "—",
                "Business Type": "—",
                "Domicile State": "—",
                "Statutory Agent": "—",
                "Agent Address": "—",
                "County": "—",
                "Comments": f"Lookup error: {e}",
                "Title1": "—",
                "Name1": "—",
                "Address1": "—",
                "Title2": "—",
                "Name2": "—",
                "Address2": "—",
                "Title3": "—",
                "Name3": "—",
                "Address3": "—",
            }
        ]


def deduplicate_records(df):
    """Remove duplicate records where all fields are identical except Entity ID(s) and Formation Date.
    
    Keeps the record with the most recent Formation Date.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing search results
        
    Returns
    -------
    pandas.DataFrame
        DataFrame with duplicates removed
    """
    import pandas as pd
    
    if len(df) <= 1:
        return df
    
    def parse_formation_date(date_str):
        """Parse formation date string into datetime, handling placeholders."""
        if pd.isna(date_str) or str(date_str) == '—' or str(date_str) == 'nan':
            return pd.Timestamp.min  # Earliest possible date for "no date"
        try:
            return pd.to_datetime(str(date_str))
        except:
            return pd.Timestamp.min
    
    # Create a copy to avoid modifying original
    df_work = df.copy()
    
    # Add parsed date column for sorting
    df_work['_parsed_date'] = df_work['Formation Date'].apply(parse_formation_date)
    
    # Define columns to compare (all except Entity ID(s) and Formation Date)
    comparison_cols = [col for col in df.columns if col not in ['Entity ID(s)', 'Formation Date']]
    
    # Group by comparison columns and keep the one with most recent date
    # Sort by parsed date descending (most recent first), then keep first in each group
    df_work = df_work.sort_values('_parsed_date', ascending=False)
    df_deduplicated = df_work.drop_duplicates(subset=comparison_cols, keep='first')
    
    # Remove the helper column and return
    df_deduplicated = df_deduplicated.drop('_parsed_date', axis=1)
    
    # Reset index to maintain clean numbering
    df_deduplicated = df_deduplicated.reset_index(drop=True)
    
    return df_deduplicated


def replace_placeholders(df):
    """Replace '—' placeholder characters with empty strings.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing search results
        
    Returns
    -------
    pandas.DataFrame
        DataFrame with placeholders replaced
    """
    # Replace '—' with empty string across all columns
    df_clean = df.replace('—', '')
    return df_clean


def process_file(input_path: str, output_path: str, headless: bool = True) -> None:
    """Read input Excel, perform lookups, and write results to output Excel.

    Parameters
    ----------
    input_path : str
        Path to the input Excel file containing a column ``Owner_Ownership``
        with names to search.
    output_path : str
        Destination path for the output Excel file.
    headless : bool
        Whether to run the browser headlessly.
    """
    df = pd.read_excel(input_path)
    if 'Owner_Ownership' not in df.columns:
        raise ValueError("Input file must contain a column named 'Owner_Ownership'")
    names = df['Owner_Ownership'].fillna('').astype(str).tolist()
    unique_names = []
    # preserve duplicates by enumerating
    for name in names:
        unique_names.append(name.strip())
    driver = setup_driver(headless=headless)
    results = []
    try:
        for name in unique_names:
            records = search_entities(driver, name)
            results.extend(records)
    finally:
        driver.quit()
    result_df = pd.DataFrame(results)
    
    # Apply deduplication logic to remove redundant records
    result_df = deduplicate_records(result_df)
    
    # Replace placeholder characters with blanks
    result_df = replace_placeholders(result_df)
    
    result_df.to_excel(output_path, index=False)


def main():
    parser = argparse.ArgumentParser(description="ACC entity lookup automation")
    parser.add_argument("--input", required=True, help="Path to input Excel file")
    parser.add_argument("--output", required=True, help="Path to output Excel file")
    parser.add_argument(
        "--headless",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Run browser in headless mode (default True)",
    )
    args = parser.parse_args()
    process_file(args.input, args.output, headless=args.headless)


if __name__ == "__main__":
    main()