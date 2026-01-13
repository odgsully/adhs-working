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
from typing import List, Dict, Optional

import pandas as pd
from bs4 import BeautifulSoup

# Import timestamp utilities for standardized naming
try:
    from .utils import (
        get_standard_timestamp,
        format_output_filename,
        get_legacy_filename,
        save_excel_with_legacy_copy,
        extract_timestamp_from_filename,
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
        extract_timestamp_from_filename,
    )
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Import monitoring and configuration
import random
import logging

try:
    from .config import get_ecorp_settings, EcorpSettings
    from .ecorp_monitoring import (
        send_alert,
        alert_captcha_detected,
        alert_rate_limited,
        alert_consecutive_failures,
    )
except ImportError:
    # Fallback for standalone execution
    get_ecorp_settings = None
    EcorpSettings = None
    send_alert = None
    alert_captcha_detected = None
    alert_rate_limited = None
    alert_consecutive_failures = None

logger = logging.getLogger(__name__)

# ============================================================================
# SELECTOR CONFIGURATION - Angular Material Fallback Chains
# ============================================================================
# Each selector has multiple fallback options for the new Arizona Business Connect
# platform (arizonabusinesscenter.azcc.gov). The first match wins.
# This handles variations in Angular Material component rendering.

SELECTORS = {
    # Search input field - Arizona Business Connect (Jan 2026+)
    "search_input": [
        # New Arizona Business Connect selectors
        (By.CSS_SELECTOR, "input[placeholder='Enter Business Name']"),
        (By.CSS_SELECTOR, "input[placeholder*='Business Name']"),
        (By.CSS_SELECTOR, "input[formcontrolname='businessName']"),
        (By.CSS_SELECTOR, "input[formcontrolname='entityName']"),
        # Generic Material selectors
        (By.CSS_SELECTOR, ".mat-mdc-form-field-infix input"),
        (By.CSS_SELECTOR, "mat-form-field input[type='text']"),
        (By.CSS_SELECTOR, "input.mat-mdc-input-element"),
        # Legacy fallbacks
        (By.CSS_SELECTOR, "input[placeholder*='Entity']"),
        (By.CSS_SELECTOR, "input[placeholder*='Search for an Entity Name']"),
    ],
    # Results table rows - Arizona Business Connect uses standard HTML table
    "results_rows": [
        # New platform - standard HTML table
        (By.CSS_SELECTOR, "table tbody tr"),
        (By.CSS_SELECTOR, "tbody tr"),
        # Angular Material fallbacks
        (By.CSS_SELECTOR, "mat-row"),
        (By.CSS_SELECTOR, ".mat-mdc-row"),
        (By.CSS_SELECTOR, "tr.mat-row"),
        (By.CSS_SELECTOR, "[role='row']:not([aria-rowindex='1'])"),
    ],
    # Table cells
    "table_cells": [
        # Standard HTML table cells
        (By.TAG_NAME, "td"),
        (By.CSS_SELECTOR, "td"),
        # Angular Material fallbacks
        (By.CSS_SELECTOR, "mat-cell"),
        (By.CSS_SELECTOR, ".mat-mdc-cell"),
    ],
    # Entity link in results - business name is a clickable link
    "entity_link": [
        (By.CSS_SELECTOR, "a"),
        (By.CSS_SELECTOR, "a[href*='business']"),
        (By.CSS_SELECTOR, "a[href*='entity']"),
        (By.CSS_SELECTOR, "a[routerlink]"),
    ],
    # No results indicator (mat-dialog or mat-snackbar)
    "no_results": [
        (By.XPATH, "//*[contains(text(), 'No') and contains(text(), 'found')]"),
        (By.XPATH, "//*[contains(text(), 'no results')]"),
        (By.XPATH, "//*[contains(text(), 'No search results')]"),
        (By.CSS_SELECTOR, "mat-dialog-content"),
        (By.CSS_SELECTOR, ".mat-mdc-snack-bar-container"),
        (By.CSS_SELECTOR, "snack-bar-container"),
        # Legacy fallback
        (By.XPATH, "//div[contains(text(), 'No search results were found')]"),
    ],
    # Dialog dismiss button
    "dialog_dismiss": [
        (By.CSS_SELECTOR, "mat-dialog-actions button"),
        (By.CSS_SELECTOR, ".mat-mdc-dialog-actions button"),
        (By.XPATH, "//mat-dialog-actions//button"),
        (By.CSS_SELECTOR, "button.mat-mdc-button"),
        (By.XPATH, "//button[normalize-space()='OK']"),
        (By.XPATH, "//button[normalize-space()='Close']"),
        (By.XPATH, "//button[contains(@class, 'close')]"),
    ],
    # Entity detail page load indicator
    "detail_loaded": [
        (By.XPATH, "//*[contains(text(),'Entity Information')]"),
        (By.XPATH, "//*[contains(text(),'Entity Details')]"),
        (By.CSS_SELECTOR, "mat-card"),
        (By.CSS_SELECTOR, ".entity-details"),
        (By.CSS_SELECTOR, "[class*='entity']"),
        (By.CSS_SELECTOR, "mat-expansion-panel"),
        # Legacy fallback
        (By.XPATH, "//h2[contains(text(),'Entity Information')]"),
    ],
    # Principal table (for manager/member extraction)
    "principal_table": [
        (By.CSS_SELECTOR, "mat-table#grid_principalList"),
        (By.ID, "grid_principalList"),
        (By.CSS_SELECTOR, "[id*='principal']"),
        (By.CSS_SELECTOR, "mat-table"),
        # Legacy fallback
        (By.CSS_SELECTOR, "table#grid_principalList"),
    ],
    # Statutory agent section
    "statutory_agent": [
        (By.XPATH, "//*[contains(text(),'Statutory Agent')]"),
        (By.CSS_SELECTOR, "[class*='statutory']"),
        (
            By.CSS_SELECTOR,
            "mat-expansion-panel:has(mat-panel-title:contains('Statutory'))",
        ),
    ],
}

# CAPTCHA detection indicators (future-proofing)
CAPTCHA_INDICATORS = [
    "captcha",
    "verify you're human",
    "security check",
    "recaptcha",
    "hcaptcha",
    "prove you're not a robot",
    "challenge",
    "i'm not a robot",
]

# Rate limit / blocking indicators - context-aware patterns
# These should appear in visible error messages, not just anywhere in page source
RATE_LIMIT_INDICATORS = [
    "too many requests",
    "rate limit exceeded",
    "you have been temporarily blocked",
    "access denied",
    "request blocked",
    "please try again later",
    "http error 429",
    "http error 503",
    "service unavailable",
    "temporarily unavailable",
]


# ============================================================================
# HELPER FUNCTIONS - Selector Fallback and Safety Detection
# ============================================================================


def find_element_with_fallback(
    driver: webdriver.Chrome,
    selector_key: str,
    timeout: int = 5,
    raise_on_failure: bool = True,
    parent=None,
) -> Optional[any]:
    """Find element using fallback selector chain.

    Tries each selector in SELECTORS[selector_key] until one succeeds.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance
    selector_key : str
        Key in SELECTORS dict (e.g., "search_input", "results_rows")
    timeout : int
        Timeout per selector attempt (seconds)
    raise_on_failure : bool
        If True, raise exception when all selectors fail
    parent : WebElement, optional
        Parent element to search within (uses driver if None)

    Returns
    -------
    Optional[WebElement]
        Found element, or None if raise_on_failure=False and not found

    Raises
    ------
    Exception
        If raise_on_failure=True and no selector succeeds
    """
    selectors = SELECTORS.get(selector_key, [])
    if not selectors:
        raise ValueError(f"Unknown selector key: {selector_key}")

    _search_context = parent if parent else driver  # noqa: F841 - kept for debugging
    last_error = None

    for idx, (by_type, selector) in enumerate(selectors):
        try:
            if parent:
                # Direct find from parent element
                element = parent.find_element(by_type, selector)
            else:
                # Use WebDriverWait for driver-level search
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by_type, selector))
                )
            logger.debug(
                f"Found '{selector_key}' using selector {idx + 1}/{len(selectors)}: {selector}"
            )
            return element
        except Exception as e:
            last_error = e
            continue

    if raise_on_failure:
        raise Exception(
            f"Could not locate element with key '{selector_key}'. "
            f"Tried {len(selectors)} selectors. Last error: {last_error}"
        )
    return None


def find_elements_with_fallback(
    driver: webdriver.Chrome,
    selector_key: str,
    parent=None,
) -> List[any]:
    """Find multiple elements using fallback selector chain.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance
    selector_key : str
        Key in SELECTORS dict
    parent : WebElement, optional
        Parent element to search within (uses driver if None)

    Returns
    -------
    List[WebElement]
        List of found elements (may be empty)
    """
    selectors = SELECTORS.get(selector_key, [])
    search_context = parent if parent else driver

    for idx, (by_type, selector) in enumerate(selectors):
        try:
            elements = search_context.find_elements(by_type, selector)
            if elements:
                logger.debug(
                    f"Found {len(elements)} '{selector_key}' elements using "
                    f"selector {idx + 1}/{len(selectors)}: {selector}"
                )
                return elements
        except Exception:
            continue

    return []


def detect_captcha(driver: webdriver.Chrome) -> bool:
    """Detect if CAPTCHA challenge is present.

    Checks page source for common CAPTCHA indicators.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance

    Returns
    -------
    bool
        True if CAPTCHA detected, False otherwise
    """
    try:
        page_source = driver.page_source.lower()
        return any(indicator in page_source for indicator in CAPTCHA_INDICATORS)
    except Exception:
        return False


def detect_rate_limit(driver: webdriver.Chrome) -> bool:
    """Detect if rate limiting or blocking is active.

    Checks visible page text (not scripts/CSS) for rate limit indicators.
    Also checks for HTTP error status in title or body.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance

    Returns
    -------
    bool
        True if rate limit/block detected, False otherwise
    """
    try:
        # Check page title for error indicators
        title = driver.title.lower() if driver.title else ""
        if any(x in title for x in ["error", "blocked", "denied", "unavailable"]):
            return True

        # Get visible body text (excludes scripts and styles)
        body_element = driver.find_element(By.TAG_NAME, "body")
        visible_text = body_element.text.lower() if body_element else ""

        # Check visible text for rate limit indicators
        return any(indicator in visible_text for indicator in RATE_LIMIT_INDICATORS)
    except Exception:
        return False


def get_random_delay(min_delay: float = 2.0, max_delay: float = 5.0) -> float:
    """Get randomized delay to avoid detection patterns.

    Uses uniform distribution between min and max.

    Parameters
    ----------
    min_delay : float
        Minimum delay in seconds
    max_delay : float
        Maximum delay in seconds

    Returns
    -------
    float
        Random delay value
    """
    return random.uniform(min_delay, max_delay)


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
        "LLC",
        "CORP",
        "INC",
        "SCHOOL",
        "DISTRICT",
        "TRUST",
        "FOUNDATION",
        "COMPANY",
        "CO.",
        "ASSOCIATION",
        "CHURCH",
        "PROPERTIES",
        "LP",
        "LTD",
        "PARTNERSHIP",
        "FUND",
        "HOLDINGS",
        "INVESTMENTS",
        "VENTURES",
        "GROUP",
        "ENTERPRISE",
        "BORROWER",
        "ACADEMY",
        "COLLEGE",
        "UNIVERSITY",
        "MEDICAL",
        "HEALTH",
        "CARE",
        "SOBER",
        "LEARNING",
        "PRESCHOOL",
        # Additional business/organization keywords
        "CENTERS",
        "CENTER",
        "HOSPICE",
        "HOSPITAL",
        "CLINIC",
        "STATE OF",
        "CITY OF",
        "COUNTY OF",
        "TOWN OF",
        "UNITED STATES",
        "GOVERNMENT",
        "FEDERAL",
        "MUNICIPAL",
        "ARMY",
        "NAVY",
        "AIR FORCE",
        "MILITARY",
        "SALVATION",
        "ARC",
        "HOUSE",
        "HOME",
        "HOMES",
        "LIVING",
        "SENIOR",
        "FACILITY",
        "FACILITIES",
        "SERVICES",
        "SERVICE",
        "UNITED",
        "METHODIST",
        "LUTHERAN",
        "EVANGELICAL",
        "BAPTIST",
        "CATHOLIC",
        "CHRISTIAN",
        "CONGREGATION",
        "PRESBYTERY",
        "ASSEMBLY",
        "LEAGUE",
        "ASSOCIATES",
        "JOINT VENTURE",
        "DST",
        "LIMITED",
        "PARTNERS",
        "SETTLEMENT",
        "HABILITATION",
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
        if not any(
            word.upper() in ["PROPERTY", "REAL", "ESTATE", "DEVELOPMENT", "RENTAL"]
            for word in words
        ):
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
    if pd.isna(name) or str(name).strip() == "":
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
    if pd.isna(name_str) or str(name_str).strip() == "":
        return []

    names = []
    name_str = str(name_str).strip()

    # Remove common suffixes that aren't part of the name
    suffixes_to_remove = [
        "TR",
        "TRUST",
        "TRUSTEE",
        "ET AL",
        "JT TEN",
        "JTRS",
        "JT",
        "EST",
        "ESTATE",
    ]
    for suffix in suffixes_to_remove:
        if name_str.endswith(" " + suffix):
            name_str = name_str[: -(len(suffix) + 1)].strip()

    # Split by forward slash to get individual components
    parts = [p.strip() for p in name_str.split("/") if p.strip()]

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
                reordered = " ".join(words[1:]) + " " + words[0]
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
            first_firstname = " ".join(first_part_words[1:])

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
                        reordered = " ".join(part_words[1:]) + " " + part_words[0]
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
                    reordered = " ".join(part_words[1:]) + " " + part_words[0]
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
        name = " ".join(name.split())
        # Keep uppercase as provided (these are typically already uppercase)
        cleaned_names.append(name)

    return cleaned_names


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """Configure and return a Selenium Chrome WebDriver with anti-detection.

    Includes measures to avoid bot detection:
    - Hides navigator.webdriver flag
    - Sets realistic user-agent
    - Excludes automation-related Chrome switches
    - Disables automation extensions

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

    # Headless mode configuration
    if headless:
        chrome_options.add_argument(
            "--headless=new"
        )  # New headless mode (more realistic)
        chrome_options.add_argument("--disable-gpu")

    # Standard stability options
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--window-size=1920,1080")

    # Anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Realistic user-agent (Chrome 120 on macOS)
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument(f"--user-agent={user_agent}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Execute CDP command to hide webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        },
    )

    return driver


def detect_login_page(driver: webdriver.Chrome) -> bool:
    """Detect if the browser is on a login/authentication page.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance

    Returns
    -------
    bool
        True if on login page, False if on search page
    """
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text.lower() if body else ""

        # Login page indicators
        login_indicators = [
            "online services login",
            "email address",
            "password",
            "register here",
            "don't have an account",
            "sign in",
            "log in to your account",
        ]

        # Search page indicators (if present, we're NOT on login)
        search_indicators = [
            "entity search",
            "search for",
            "entity name",
            "business search",
            "corporation search",
        ]

        # Check for login indicators
        has_login_indicators = any(
            indicator in body_text for indicator in login_indicators
        )

        # Check for search indicators
        has_search_indicators = any(
            indicator in body_text for indicator in search_indicators
        )

        # If we have search indicators, we're good
        if has_search_indicators and not has_login_indicators:
            return False

        # If we have login indicators but no search, we're on login page
        if has_login_indicators:
            return True

        return False
    except Exception:
        return False


def perform_login(driver: webdriver.Chrome, settings) -> bool:
    """Perform login to Arizona Business Connect.

    The new platform (launched January 2026) requires authentication for
    entity searches. This function handles the login process.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance
    settings : EcorpSettings
        Configuration settings containing email and password

    Returns
    -------
    bool
        True if login successful, False otherwise
    """
    if not settings or not settings.email or not settings.password:
        logger.warning(
            "Authentication credentials not configured. "
            "Set ADHS_ECORP_EMAIL and ADHS_ECORP_PASSWORD environment variables."
        )
        return False

    login_url = getattr(
        settings, "login_url", "https://arizonabusinesscenter.azcc.gov/login"
    )

    try:
        logger.info(f"Navigating to login page: {login_url}")
        driver.get(login_url)
        time.sleep(3)  # Wait for Angular

        # Find and fill email field
        email_selectors = [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[formcontrolname='email']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email']"),
            (By.CSS_SELECTOR, ".mat-mdc-form-field-infix input"),
        ]

        email_input = None
        for by_type, selector in email_selectors:
            try:
                email_input = driver.find_element(by_type, selector)
                if email_input:
                    break
            except Exception:
                continue

        if not email_input:
            logger.error("Could not find email input field on login page")
            return False

        email_input.clear()
        email_input.send_keys(settings.email)
        time.sleep(1)

        # Click Next/Continue button - this is a two-step login
        next_button_selectors = [
            (By.XPATH, "//button[normalize-space()='Next']"),
            (By.XPATH, "//button[contains(text(), 'Next')]"),
            (By.XPATH, "//button[contains(text(), 'Continue')]"),
            (By.CSS_SELECTOR, "button.mat-mdc-raised-button"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "button[color='primary']"),
        ]

        next_button = None
        for by_type, selector in next_button_selectors:
            try:
                buttons = driver.find_elements(by_type, selector)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        next_button = btn
                        logger.debug(f"Found Next button with selector: {selector}")
                        break
                if next_button:
                    break
            except Exception:
                continue

        if next_button:
            logger.info("Clicking Next button...")
            next_button.click()
            time.sleep(3)  # Wait for password field to load
        else:
            logger.warning("Could not find Next button, trying Enter key...")
            email_input.send_keys(Keys.RETURN)
            time.sleep(3)

        # Find and fill password field
        password_selectors = [
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[formcontrolname='password']"),
            (By.CSS_SELECTOR, "input[name='password']"),
        ]

        password_input = None
        for by_type, selector in password_selectors:
            try:
                password_input = driver.find_element(by_type, selector)
                if password_input:
                    break
            except Exception:
                continue

        if password_input:
            password_input.clear()
            password_input.send_keys(settings.password)
            time.sleep(0.5)

            # Submit login
            password_input.send_keys(Keys.RETURN)
            time.sleep(3)  # Wait for login to process

        # Check if we hit 2FA page
        if detect_2fa_page(driver):
            logger.info("Two-Factor Authentication required")
            if not handle_2fa_prompt(driver):
                logger.error("2FA authentication failed")
                return False

        # Verify login success by checking we're not on login page
        if not detect_login_page(driver) and not detect_2fa_page(driver):
            logger.info("Login successful!")
            return True
        else:
            logger.warning("Login may have failed - still on login/2FA page")
            return False

    except Exception as e:
        logger.error(f"Login failed with error: {e}")
        return False


def detect_2fa_page(driver: webdriver.Chrome) -> bool:
    """Detect if we're on the Two-Factor Authentication page.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance

    Returns
    -------
    bool
        True if on 2FA page, False otherwise
    """
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text.lower() if body else ""

        tfa_indicators = [
            "two-factor authentication",
            "verification code",
            "code has been sent",
            "enter the code",
            "authenticate",
            "otp",
        ]

        return any(indicator in body_text for indicator in tfa_indicators)
    except Exception:
        return False


def handle_2fa_prompt(driver: webdriver.Chrome, timeout: int = 300) -> bool:
    """Handle Two-Factor Authentication by prompting user for code.

    Pauses execution and asks the user to enter the 2FA code sent to their email.
    The code is then entered into the form and submitted.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance
    timeout : int
        Maximum seconds to wait for user input (default 5 minutes)

    Returns
    -------
    bool
        True if 2FA completed successfully, False otherwise
    """
    print("\n" + "=" * 60)
    print("🔐 TWO-FACTOR AUTHENTICATION REQUIRED")
    print("=" * 60)
    print("A verification code has been sent to your email.")
    print("Check your inbox and enter the 6-digit code below.")
    print("(Code typically expires in 5 minutes)")
    print("=" * 60)

    try:
        # Get user input
        code = input("\nEnter 2FA code: ").strip()

        if not code:
            print("No code entered. Aborting.")
            return False

        if len(code) != 6 or not code.isdigit():
            print(
                f"Warning: Code '{code}' doesn't look like a 6-digit code, but trying anyway..."
            )

        # Find the OTP input fields - Arizona Business Connect uses 6 separate input boxes
        otp_input = None
        is_split_input = False

        # First, try to find 6 separate OTP input boxes (most common for this site)
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        visible_text_inputs = [
            inp
            for inp in all_inputs
            if inp.is_displayed()
            and inp.get_attribute("type") in ["text", "number", "tel", None, ""]
        ]

        # Check if we have exactly 6 single-character inputs (split OTP)
        if len(visible_text_inputs) >= 6:
            # Check if first 6 look like OTP boxes
            potential_otp = visible_text_inputs[:6]
            is_split_input = True
            otp_input = potential_otp
            print(f"Found {len(potential_otp)} OTP input boxes")

        # Fallback: try specific selectors
        if not otp_input:
            otp_selectors = [
                (By.CSS_SELECTOR, "input[maxlength='1']"),
                (By.CSS_SELECTOR, "input[type='text'][maxlength='6']"),
                (By.CSS_SELECTOR, "input[formcontrolname*='otp']"),
                (By.CSS_SELECTOR, "input[formcontrolname*='code']"),
            ]

            for by_type, selector in otp_selectors:
                try:
                    inputs = driver.find_elements(by_type, selector)
                    visible_inputs = [i for i in inputs if i.is_displayed()]
                    if len(visible_inputs) >= 6:
                        is_split_input = True
                        otp_input = visible_inputs[:6]
                        print(f"Found OTP inputs with selector: {selector}")
                        break
                    elif len(visible_inputs) == 1:
                        otp_input = visible_inputs[0]
                        is_split_input = False
                        break
                except Exception:
                    continue

        if not otp_input:
            print("Could not find OTP input fields. Trying first visible input...")
            if visible_text_inputs:
                otp_input = visible_text_inputs[0]
                is_split_input = False

        if otp_input:
            if is_split_input:
                # Enter one digit per input
                print("Entering code into split input fields...")
                for i, digit in enumerate(code[:6]):
                    otp_input[i].clear()
                    otp_input[i].send_keys(digit)
                    time.sleep(0.1)
            else:
                # Single input field
                print("Entering code...")
                otp_input.clear()
                otp_input.send_keys(code)

            time.sleep(0.5)

            # Click Authenticate/Submit button
            auth_button_selectors = [
                (By.XPATH, "//button[normalize-space()='Authenticate']"),
                (By.XPATH, "//button[contains(text(), 'Authenticate')]"),
                (By.XPATH, "//button[contains(text(), 'Verify')]"),
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "button.mat-mdc-raised-button"),
            ]

            auth_button = None
            for by_type, selector in auth_button_selectors:
                try:
                    buttons = driver.find_elements(by_type, selector)
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_text = btn.text.lower()
                            if "cancel" not in btn_text:
                                auth_button = btn
                                break
                    if auth_button:
                        break
                except Exception:
                    continue

            if auth_button:
                print("Clicking Authenticate button...")
                auth_button.click()
            else:
                print("No Authenticate button found, pressing Enter...")
                if is_split_input:
                    otp_input[-1].send_keys(Keys.RETURN)
                else:
                    otp_input.send_keys(Keys.RETURN)

            time.sleep(3)  # Wait for authentication to process

            # Check if we're past 2FA
            if not detect_2fa_page(driver):
                print("✅ 2FA authentication successful!")
                return True
            else:
                print("❌ Still on 2FA page - code may be incorrect")
                return False

        else:
            print("ERROR: Could not find any input field for OTP code")
            return False

    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return False
    except Exception as e:
        print(f"ERROR during 2FA: {e}")
        return False


def find_working_search_url(driver: webdriver.Chrome, settings=None) -> str:
    """Try multiple URLs to find a working public search page.

    The new Arizona Business Connect platform has multiple potential endpoints.
    This function tries each until it finds one that works without authentication.

    Parameters
    ----------
    driver : webdriver.Chrome
        Selenium WebDriver instance
    settings : EcorpSettings, optional
        Configuration settings

    Returns
    -------
    str
        The URL of a working public search page

    Raises
    ------
    Exception
        If no working public search URL is found
    """
    # URLs to try in order of preference
    candidate_urls = [
        # Primary: public business search (no login required)
        "https://arizonabusinesscenter.azcc.gov/businesssearch",
        # Alternative paths that may work
        "https://arizonabusinesscenter.azcc.gov/PublicSearch/EntitySearch",
        "https://arizonabusinesscenter.azcc.gov/search",
        "https://arizonabusinesscenter.azcc.gov/entity-search",
        "https://arizonabusinesscenter.azcc.gov/entitysearch/index",
        # Old URLs (for reference/fallback)
        "https://ecorp.azcc.gov/EntitySearch/Index",
    ]

    _page_timeout = (
        settings.page_load_timeout if settings else 10
    )  # noqa: F841 - reserved for future use

    for url in candidate_urls:
        try:
            logger.debug(f"Trying URL: {url}")
            driver.get(url)
            time.sleep(3)  # Wait for Angular SPA to initialize

            # Check if we landed on a login page
            if detect_login_page(driver):
                logger.debug(f"  → Login page detected at {url}")
                continue

            # Check if we can find a search input
            search_input = find_element_with_fallback(
                driver, "search_input", timeout=5, raise_on_failure=False
            )
            if search_input:
                logger.info(f"Found working search page at: {url}")
                return url

            logger.debug(f"  → No search input found at {url}")

        except Exception as e:
            logger.debug(f"  → Error at {url}: {e}")
            continue

    raise Exception(
        "Could not find a working public search URL. "
        "The Arizona Business Connect site may require authentication for all searches. "
        "Consider using Form M027 for official database extraction."
    )


def search_entities(
    driver: webdriver.Chrome, name: str, settings=None
) -> List[Dict[str, str]]:
    """Search the ACC site for a company name and return entity details.

    This function navigates to the Arizona Business Connect search page
    (formerly eCorp), enters ``name`` into the search bar, parses any
    results table that appears, and retrieves detailed fields for each
    entity by opening the detail page in a new tab.

    The function automatically discovers the working public search URL,
    handling the transition from the old eCorp site to the new Arizona
    Business Connect platform (launched January 12, 2026).

    Parameters
    ----------
    driver : selenium.webdriver.Chrome
        The active Selenium driver.
    name : str
        The company name to search for.
    settings : EcorpSettings, optional
        Configuration settings. If None, defaults are used.

    Returns
    -------
    List[Dict[str, str]]
        A list of dictionaries where each dictionary contains details
        about an entity.  If no results are found, a single
        dictionary with ``Status`` set to ``Not found`` is returned.
    """
    # Get settings (use defaults if not provided)
    if settings is None and get_ecorp_settings is not None:
        settings = get_ecorp_settings()

    # Use configured URL or default to new Arizona Business Connect
    if settings:
        base_url = settings.base_url
        min_delay = settings.min_delay
        max_delay = settings.max_delay
        page_timeout = settings.page_load_timeout
    else:
        # Fallback defaults
        base_url = "https://arizonabusinesscenter.azcc.gov/businesssearch"
        min_delay = 2.0
        max_delay = 5.0
        page_timeout = 10

    driver.get(base_url)
    time.sleep(3)  # Wait for Angular SPA to initialize

    # Check if we landed on a login page
    if detect_login_page(driver):
        logger.warning(f"Login page detected at {base_url}")

        # Try to authenticate if credentials are available
        if settings and settings.email and settings.password:
            logger.info("Attempting authentication with configured credentials...")
            if perform_login(driver, settings):
                # Navigate to search page after successful login
                driver.get(base_url)
                time.sleep(3)
            else:
                blank = get_blank_acc_record()
                blank["ECORP_COMMENTS"] = "Authentication failed - check credentials"
                return [blank]
        else:
            # No credentials - cannot proceed
            logger.error(
                "Arizona Business Connect requires authentication for entity searches. "
                "Configure ADHS_ECORP_EMAIL and ADHS_ECORP_PASSWORD, "
                "or use Form M027 for official database extraction."
            )
            blank = get_blank_acc_record()
            blank["ECORP_COMMENTS"] = (
                "Login required - set ADHS_ECORP_EMAIL and ADHS_ECORP_PASSWORD "
                "or use Form M027 (https://www.azcc.gov/docs/default-source/corps-files/forms/m027-database-extraction-request.pdf)"
            )
            return [blank]

    # Verify we're now on a search page
    if detect_login_page(driver):
        blank = get_blank_acc_record()
        blank["ECORP_COMMENTS"] = "Still on login page after authentication attempt"
        return [blank]

    try:
        # Wait for search bar using fallback selectors
        search_input = find_element_with_fallback(
            driver, "search_input", timeout=page_timeout
        )
        # Clear and enter search term
        search_input.clear()
        search_input.send_keys(name)

        # Click "Business Search" button instead of pressing Enter
        search_button_selectors = [
            (By.XPATH, "//button[normalize-space()='Business Search']"),
            (By.XPATH, "//button[contains(text(), 'Business Search')]"),
            (By.XPATH, "//button[contains(text(), 'Search')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "button.mat-mdc-raised-button"),
        ]

        search_clicked = False
        for by_type, selector in search_button_selectors:
            try:
                buttons = driver.find_elements(by_type, selector)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_text = btn.text.lower()
                        if "clear" not in btn_text and "cancel" not in btn_text:
                            logger.debug(f"Clicking search button: {btn.text}")
                            btn.click()
                            search_clicked = True
                            break
                if search_clicked:
                    break
            except Exception:
                continue

        if not search_clicked:
            logger.debug("No search button found, pressing Enter")
            search_input.send_keys(Keys.RETURN)

        # Wait for results with randomized delay (anti-detection)
        time.sleep(get_random_delay(min_delay, max_delay))

        # Safety checks: CAPTCHA and rate limit detection
        if settings and settings.enable_captcha_detection and detect_captcha(driver):
            logger.warning(f"CAPTCHA detected while searching for: {name}")
            if alert_captcha_detected:
                alert_captcha_detected({"owner_name": name, "url": base_url}, settings)
            blank = get_blank_acc_record()
            blank["ECORP_COMMENTS"] = "CAPTCHA detected - manual intervention required"
            return [blank]

        if (
            settings
            and settings.enable_rate_limit_detection
            and detect_rate_limit(driver)
        ):
            logger.warning(f"Rate limit detected while searching for: {name}")
            if alert_rate_limited:
                alert_rate_limited({"owner_name": name, "url": base_url}, settings)
            blank = get_blank_acc_record()
            blank["ECORP_COMMENTS"] = "Rate limited - try again later"
            return [blank]

        # Check for no results modal using fallback selectors
        try:
            no_results = find_element_with_fallback(
                driver, "no_results", timeout=2, raise_on_failure=False
            )
            if no_results:
                # Try to dismiss the dialog
                dismiss_btn = find_element_with_fallback(
                    driver, "dialog_dismiss", timeout=2, raise_on_failure=False
                )
                if dismiss_btn:
                    dismiss_btn.click()
                    time.sleep(0.5)
                return [get_blank_acc_record()]
        except Exception:
            pass

        # Parse results table rows using fallback selectors
        # New Arizona Business Connect table columns:
        # 0: Business Name (link), 1: Former Name, 2: Business ID, 3: Business Type,
        # 4: Statutory Agent, 5: Physical Address, 6: Status
        entities = []
        rows = find_elements_with_fallback(driver, "results_rows")
        logger.debug(f"Found {len(rows)} result rows")

        for row in rows:
            cols = find_elements_with_fallback(driver, "table_cells", parent=row)
            if not cols or len(cols) < 3:
                logger.debug(f"Skipping row with {len(cols) if cols else 0} columns")
                continue

            # Extract data from columns (new Arizona Business Connect format)
            entity_name = cols[0].text.strip() if len(cols) > 0 else ""
            entity_id = cols[2].text.strip() if len(cols) > 2 else ""
            business_type = cols[3].text.strip() if len(cols) > 3 else ""
            _statutory_agent = (
                cols[4].text.strip() if len(cols) > 4 else ""
            )  # noqa: F841
            _physical_address = (
                cols[5].text.strip() if len(cols) > 5 else ""
            )  # noqa: F841
            status = cols[6].text.strip() if len(cols) > 6 else ""

            logger.debug(f"Found entity: {entity_name} (ID: {entity_id})")

            # Find link in the first column (Business Name)
            link = find_element_with_fallback(
                driver, "entity_link", parent=cols[0], timeout=2, raise_on_failure=False
            )
            if not link:
                # Try finding link in the entire row
                link = find_element_with_fallback(
                    driver, "entity_link", parent=row, timeout=2, raise_on_failure=False
                )
            if not link:
                logger.debug(f"No link found for {entity_name}, skipping")
                continue

            # Arizona Business Connect uses Angular routing - links may not have href
            # We need to click the link directly instead of opening URL in new tab
            detail_url = link.get_attribute("href") or link.get_attribute("routerlink")

            # Store current window handle
            main_window = driver.current_window_handle
            _original_url = driver.current_url  # noqa: F841 - kept for debugging

            if detail_url and detail_url.startswith("http"):
                # Traditional link - open in new tab
                logger.debug(f"Opening detail page via URL: {detail_url}")
                driver.execute_script("window.open(arguments[0]);", detail_url)
                driver.switch_to.window(driver.window_handles[-1])
            else:
                # Angular routing - click the link directly
                logger.debug(f"Clicking link for: {entity_name}")
                try:
                    link.click()
                    time.sleep(2)  # Wait for Angular navigation
                except Exception as click_err:
                    logger.debug(f"Click failed, trying JS click: {click_err}")
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(2)
            # Wait for entity info to load using fallback selectors
            find_element_with_fallback(driver, "detail_loaded", timeout=page_timeout)
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
                        r"Statutory Agent Information.*?Name:\s*\n\s*([^\n\r]+?)(?:\s*\n|\s*Appointed)",
                        page_text,
                        re.DOTALL | re.IGNORECASE,
                    )

                    agent_name = ""
                    agent_addr = ""

                    if stat_agent_section:
                        agent_name = stat_agent_section.group(1).strip()
                        # Clean up - remove extra spaces
                        agent_name = " ".join(agent_name.split())
                    else:
                        # Try alternative pattern where name might be on same line
                        alt_pattern = re.search(
                            r"Statutory Agent Information.*?Name:\s*([^\n\r]+?)(?:\s+Attention:|Appointed|$)",
                            page_text,
                            re.DOTALL | re.IGNORECASE,
                        )
                        if alt_pattern:
                            agent_name = alt_pattern.group(1).strip()
                            agent_name = " ".join(agent_name.split())

                    # Look for Address in the same section
                    addr_section = re.search(
                        r"Statutory Agent Information.*?Address:\s*\n?\s*([^\n\r]+?)(?:\s*\n|\s*Agent Last|E-mail:|County:|Mailing)",
                        page_text,
                        re.DOTALL | re.IGNORECASE,
                    )

                    if addr_section:
                        agent_addr = addr_section.group(1).strip()
                        agent_addr = " ".join(agent_addr.split())

                    # If we found name or address, add to agents list
                    if agent_name or agent_addr:
                        agents.append(
                            {
                                "Name": agent_name,
                                "Address": agent_addr,
                                "Phone": "",
                                "Mail": "",
                            }
                        )

                except Exception:
                    # Silent fail - return empty list
                    pass

                return agents

            def extract_principal_info():
                """Extract Principal Information from the table/grid section and categorize by role."""
                categorized_principals = {
                    "Manager": [],
                    "Member": [],
                    "Manager/Member": [],
                }

                try:
                    # Look for the principal information table by id
                    principal_table = soup.find("table", id="grid_principalList")
                    if principal_table:
                        # Find all data rows (skip header)
                        tbody = principal_table.find("tbody")
                        if tbody:
                            rows = tbody.find_all("tr")

                            for row in rows:
                                cells = row.find_all("td")
                                if len(cells) >= 4:  # Title, Name, Attention, Address
                                    title_text = (
                                        cells[0].get_text(strip=True)
                                        if cells[0]
                                        else ""
                                    )
                                    name_text = (
                                        cells[1].get_text(strip=True)
                                        if cells[1]
                                        else ""
                                    )
                                    # Skip attention field (cells[2])
                                    addr_text = (
                                        cells[3].get_text(strip=True)
                                        if cells[3]
                                        else ""
                                    )

                                    # Look for phone/email if present (conservative approach)
                                    phone_text = ""
                                    mail_text = ""
                                    if len(cells) > 4:
                                        # Check if additional cells might contain phone/email
                                        for cell in cells[4:]:
                                            cell_text = cell.get_text(strip=True)
                                            if "@" in cell_text:
                                                mail_text = cell_text
                                            elif (
                                                any(
                                                    char.isdigit() for char in cell_text
                                                )
                                                and len(cell_text) >= 7
                                            ):
                                                phone_text = cell_text

                                    # Categorize based on title
                                    title_upper = title_text.upper()
                                    principal_data = {
                                        "Name": name_text,
                                        "Address": addr_text,
                                        "Phone": phone_text,
                                        "Mail": mail_text,
                                    }

                                    if (
                                        "MANAGER" in title_upper
                                        and "MEMBER" in title_upper
                                    ):
                                        if (
                                            len(
                                                categorized_principals["Manager/Member"]
                                            )
                                            < 5
                                        ):
                                            categorized_principals[
                                                "Manager/Member"
                                            ].append(principal_data)
                                    elif "MANAGER" in title_upper:
                                        if len(categorized_principals["Manager"]) < 5:
                                            categorized_principals["Manager"].append(
                                                principal_data
                                            )
                                    elif "MEMBER" in title_upper:
                                        if len(categorized_principals["Member"]) < 5:
                                            categorized_principals["Member"].append(
                                                principal_data
                                            )
                                    else:
                                        # Default to Manager if title unclear
                                        if len(categorized_principals["Manager"]) < 5:
                                            categorized_principals["Manager"].append(
                                                principal_data
                                            )

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
                "ECORP_SEARCH_NAME": name,
                "ECORP_TYPE": classify_name_type(name),
                "ECORP_NAME_S": entity_name if entity_name else "",
                "ECORP_ENTITY_ID_S": entity_id if entity_id else "",
                "ECORP_ENTITY_TYPE": entity_type if entity_type else "",
                "ECORP_STATUS": status if status else "",
                "ECORP_FORMATION_DATE": formation_date if formation_date else "",
                "ECORP_BUSINESS_TYPE": business_type if business_type else "",
                "ECORP_STATE": domicile_state if domicile_state else "",
                "ECORP_COUNTY": county if county else "",
                "ECORP_COMMENTS": "",
            }

            # Add statutory agent fields (up to 3)
            for i in range(1, 4):
                if i <= len(statutory_agents):
                    agent = statutory_agents[i - 1]
                    record[f"StatutoryAgent{i}_Name"] = agent.get("Name", "")
                    record[f"StatutoryAgent{i}_Address"] = agent.get("Address", "")
                    record[f"StatutoryAgent{i}_Phone"] = agent.get("Phone", "")
                    record[f"StatutoryAgent{i}_Mail"] = agent.get("Mail", "")
                else:
                    record[f"StatutoryAgent{i}_Name"] = ""
                    record[f"StatutoryAgent{i}_Address"] = ""
                    record[f"StatutoryAgent{i}_Phone"] = ""
                    record[f"StatutoryAgent{i}_Mail"] = ""

            # Add Manager fields (up to 5)
            managers = principal_info.get("Manager", [])
            for i in range(1, 6):
                if i <= len(managers):
                    mgr = managers[i - 1]
                    record[f"Manager{i}_Name"] = mgr.get("Name", "")
                    record[f"Manager{i}_Address"] = mgr.get("Address", "")
                    record[f"Manager{i}_Phone"] = mgr.get("Phone", "")
                    record[f"Manager{i}_Mail"] = mgr.get("Mail", "")
                else:
                    record[f"Manager{i}_Name"] = ""
                    record[f"Manager{i}_Address"] = ""
                    record[f"Manager{i}_Phone"] = ""
                    record[f"Manager{i}_Mail"] = ""

            # Add Manager/Member fields (up to 5)
            mgr_members = principal_info.get("Manager/Member", [])
            for i in range(1, 6):
                if i <= len(mgr_members):
                    mm = mgr_members[i - 1]
                    record[f"Manager/Member{i}_Name"] = mm.get("Name", "")
                    record[f"Manager/Member{i}_Address"] = mm.get("Address", "")
                    record[f"Manager/Member{i}_Phone"] = mm.get("Phone", "")
                    record[f"Manager/Member{i}_Mail"] = mm.get("Mail", "")
                else:
                    record[f"Manager/Member{i}_Name"] = ""
                    record[f"Manager/Member{i}_Address"] = ""
                    record[f"Manager/Member{i}_Phone"] = ""
                    record[f"Manager/Member{i}_Mail"] = ""

            # Add Member fields (up to 5)
            members = principal_info.get("Member", [])
            for i in range(1, 6):
                if i <= len(members):
                    mbr = members[i - 1]
                    record[f"Member{i}_Name"] = mbr.get("Name", "")
                    record[f"Member{i}_Address"] = mbr.get("Address", "")
                    record[f"Member{i}_Phone"] = mbr.get("Phone", "")
                    record[f"Member{i}_Mail"] = mbr.get("Mail", "")
                else:
                    record[f"Member{i}_Name"] = ""
                    record[f"Member{i}_Address"] = ""
                    record[f"Member{i}_Phone"] = ""
                    record[f"Member{i}_Mail"] = ""

            # Add Individual name fields (empty for now - will be populated for INDIVIDUAL types)
            for i in range(1, 5):
                record[f"IndividualName{i}"] = ""

            # Add ECORP_URL - use current URL if we navigated via click
            record["ECORP_URL"] = driver.current_url if not detail_url else detail_url

            entities.append(record)

            # Navigate back to search results
            if len(driver.window_handles) > 1:
                # We opened a new tab - close it and switch back
                driver.close()
                driver.switch_to.window(main_window)
            else:
                # We used Angular routing - navigate back
                driver.back()
                time.sleep(2)  # Wait for search results to reload

        # If no entities were found, return a blank record
        if not entities:
            return [get_blank_acc_record()]

        return entities
    except Exception as e:
        # In the event of unexpected errors, return a blank record with error comment
        blank = get_blank_acc_record()
        blank["ECORP_COMMENTS"] = f"Lookup error: {e}"
        return [blank]


def get_blank_acc_record() -> dict:
    """Return ACC record with all fields as empty strings.

    Returns
    -------
    dict
        Dictionary with all ACC field keys set to empty strings
    """
    record = {
        "ECORP_SEARCH_NAME": "",
        "ECORP_TYPE": "",
        "ECORP_NAME_S": "",
        "ECORP_ENTITY_ID_S": "",
        "ECORP_ENTITY_TYPE": "",
        "ECORP_STATUS": "",
        "ECORP_FORMATION_DATE": "",
        "ECORP_BUSINESS_TYPE": "",
        "ECORP_STATE": "",
        "ECORP_COUNTY": "",
        "ECORP_COMMENTS": "",
    }

    # Add StatutoryAgent fields (3 agents)
    for i in range(1, 4):
        record[f"StatutoryAgent{i}_Name"] = ""
        record[f"StatutoryAgent{i}_Address"] = ""
        record[f"StatutoryAgent{i}_Phone"] = ""
        record[f"StatutoryAgent{i}_Mail"] = ""

    # Add Manager fields (5 managers)
    for i in range(1, 6):
        record[f"Manager{i}_Name"] = ""
        record[f"Manager{i}_Address"] = ""
        record[f"Manager{i}_Phone"] = ""
        record[f"Manager{i}_Mail"] = ""

    # Add Manager/Member fields (5 entries)
    for i in range(1, 6):
        record[f"Manager/Member{i}_Name"] = ""
        record[f"Manager/Member{i}_Address"] = ""
        record[f"Manager/Member{i}_Phone"] = ""
        record[f"Manager/Member{i}_Mail"] = ""

    # Add Member fields (5 members)
    for i in range(1, 6):
        record[f"Member{i}_Name"] = ""
        record[f"Member{i}_Address"] = ""
        record[f"Member{i}_Phone"] = ""
        record[f"Member{i}_Mail"] = ""

    # Add Individual name fields (4 individuals)
    for i in range(1, 5):
        record[f"IndividualName{i}"] = ""

    # Add ECORP_URL field
    record["ECORP_URL"] = ""

    return record


def save_checkpoint(
    path: Path, results: list, idx: int, total_records: int = None
) -> None:
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
    with open(path, "wb") as f:
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


def get_cached_or_lookup(
    cache: dict, owner_name: str, driver: webdriver.Chrome, settings=None
) -> List[Dict[str, str]]:
    """Check cache before performing ACC lookup to avoid duplicates.

    Parameters
    ----------
    cache : dict
        In-memory cache mapping owner names to ACC results
    owner_name : str
        Owner name to lookup
    driver : webdriver.Chrome
        Selenium driver instance
    settings : EcorpSettings, optional
        Configuration settings for the scraper

    Returns
    -------
    List[Dict[str, str]]
        ACC entity results from cache or fresh lookup
    """
    if owner_name in cache:
        return cache[owner_name]

    results = search_entities(driver, owner_name, settings)
    cache[owner_name] = results
    return results


def extract_individual_names(record: dict) -> set:
    """Extract all individual names from an Ecorp record.

    Extracts names from all person-related fields:
    - Manager1_Name through Manager5_Name
    - Member1_Name through Member5_Name
    - Manager/Member1_Name through Manager/Member5_Name
    - StatutoryAgent1_Name through StatutoryAgent3_Name
    - IndividualName1 through IndividualName4

    Parameters
    ----------
    record : dict
        Ecorp Complete record with ACC data

    Returns
    -------
    set
        Set of normalized individual names (uppercase, stripped)
    """
    names = set()

    # Extract Manager names (5)
    for i in range(1, 6):
        name = record.get(f"Manager{i}_Name", "")
        if name and str(name).strip():
            names.add(str(name).strip().upper())

    # Extract Member names (5)
    for i in range(1, 6):
        name = record.get(f"Member{i}_Name", "")
        if name and str(name).strip():
            names.add(str(name).strip().upper())

    # Extract Manager/Member names (5)
    for i in range(1, 6):
        name = record.get(f"Manager/Member{i}_Name", "")
        if name and str(name).strip():
            names.add(str(name).strip().upper())

    # Extract Statutory Agent names (3)
    for i in range(1, 4):
        name = record.get(f"StatutoryAgent{i}_Name", "")
        if name and str(name).strip():
            names.add(str(name).strip().upper())

    # Extract Individual names (4)
    for i in range(1, 5):
        name = record.get(f"IndividualName{i}", "")
        if name and str(name).strip():
            names.add(str(name).strip().upper())

    return names


def calculate_person_overlap(
    names1: set, names2: set, threshold: float = 85.0
) -> float:
    """Calculate similarity between two sets of individual names using fuzzy matching.

    Uses a bidirectional similarity metric that checks both directions:
    - What percentage of names1 have a fuzzy match in names2?
    - What percentage of names2 have a fuzzy match in names1?
    Returns the average of both percentages.

    Parameters
    ----------
    names1 : set
        First set of individual names
    names2 : set
        Second set of individual names
    threshold : float
        Fuzzy matching threshold (0-100) for considering names as matching

    Returns
    -------
    float
        Similarity score (0-100) representing percentage of overlap
    """
    if not names1 or not names2:
        return 0.0

    from rapidfuzz import fuzz

    # Count matches from names1 -> names2
    matches_from_1 = 0
    for name1 in names1:
        best_match_score = 0
        for name2 in names2:
            # Use token_sort_ratio for better handling of name variations
            similarity = fuzz.token_sort_ratio(name1, name2)
            best_match_score = max(best_match_score, similarity)

        if best_match_score >= threshold:
            matches_from_1 += 1

    # Count matches from names2 -> names1
    matches_from_2 = 0
    for name2 in names2:
        best_match_score = 0
        for name1 in names1:
            similarity = fuzz.token_sort_ratio(name2, name1)
            best_match_score = max(best_match_score, similarity)

        if best_match_score >= threshold:
            matches_from_2 += 1

    # Calculate bidirectional average
    # Average of: (matches_from_1 / len(names1)) and (matches_from_2 / len(names2))
    similarity_1 = (matches_from_1 / len(names1)) * 100 if names1 else 0.0
    similarity_2 = (matches_from_2 / len(names2)) * 100 if names2 else 0.0

    return (similarity_1 + similarity_2) / 2.0


def assign_grouped_indexes_by_individuals(
    results: List[dict], threshold: float = 85.0
) -> List[int]:
    """Assign ECORP_INDEX_# based on overlap of individual names.

    Groups records that share significant overlap in key individuals
    (managers, members, statutory agents). Records with >= threshold
    person overlap get the same ECORP_INDEX_#.

    This identifies corporate families and related entities under common control.

    Parameters
    ----------
    results : List[dict]
        List of Ecorp Complete records with ACC data
    threshold : float
        Overlap threshold (0-100) for grouping records together

    Returns
    -------
    List[int]
        List of ECORP_INDEX_# assignments, one per record

    Examples
    --------
    Record 1: Managers=["JOHN SMITH", "JANE DOE"]
    Record 2: Managers=["JOHN SMITH", "JANE DOE"]
    → Both get ECORP_INDEX_# = 1 (100% overlap)

    Record 3: Managers=["ALICE WILLIAMS"]
    → Gets ECORP_INDEX_# = 2 (new group)
    """
    index_assignments = []
    groups = []  # List of (representative_name_set, group_index) tuples
    next_group_index = 1

    for record in results:
        # Extract all individual names from this record
        individual_names = extract_individual_names(record)

        # If no names found, assign unique index
        if not individual_names:
            index_assignments.append(next_group_index)
            next_group_index += 1
            continue

        # Check if this set of individuals matches any existing group
        matched_group_idx = None
        best_similarity = 0

        for group_names, group_idx in groups:
            similarity = calculate_person_overlap(
                individual_names, group_names, threshold=threshold
            )

            if similarity >= threshold and similarity > best_similarity:
                matched_group_idx = group_idx
                best_similarity = similarity

        if matched_group_idx is not None:
            # Assign to existing group
            index_assignments.append(matched_group_idx)
        else:
            # Create new group with this set as representative
            index_assignments.append(next_group_index)
            groups.append((individual_names, next_group_index))
            next_group_index += 1

    return index_assignments


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
            print(
                f"❌ MCAO_Complete must have at least 5 columns, found {len(df.columns)}"
            )
            return None

        # Extract columns (0-indexed)
        upload_df = pd.DataFrame(
            {
                "FULL_ADDRESS": df.iloc[:, 0],  # Column A
                "COUNTY": df.iloc[:, 1],  # Column B
                "Owner_Ownership": df.iloc[:, 4],  # Column E (0-indexed = 4)
                "OWNER_TYPE": df.iloc[:, 4].apply(classify_owner_type),  # Classify
            }
        )

        print(f"📊 Extracted {len(upload_df)} records for Ecorp Upload")

        # Count blanks
        blank_count = (
            upload_df["Owner_Ownership"].isna().sum()
            + (upload_df["Owner_Ownership"] == "").sum()
        )
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

        upload_df.to_excel(new_path, index=False, engine="xlsxwriter")

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


def generate_ecorp_complete(
    month_code: str, upload_path: Path, headless: bool = True
) -> bool:
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
    - F-CN: 88 ACC fields (ECORP_SEARCH_NAME, ECORP_TYPE, Entity details, Principals, Individual Names)
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

        # Initialize Ecorp settings
        settings = None
        if get_ecorp_settings is not None:
            settings = get_ecorp_settings(headless=headless)
            print(f"🔧 Using base URL: {settings.base_url}")
            print(
                f"   Delays: {settings.min_delay}-{settings.max_delay}s | "
                f"CAPTCHA detection: {settings.enable_captcha_detection} | "
                f"Rate limit detection: {settings.enable_rate_limit_detection}"
            )

        # Load checkpoint if exists and validate it
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "rb") as f:
                    checkpoint_data = pickle.load(f)

                # Handle old format (results, idx) or new format (results, idx, total)
                if len(checkpoint_data) == 3:
                    results, start_idx, checkpoint_total = checkpoint_data

                    # Validate checkpoint matches current upload file
                    if checkpoint_total != total_records:
                        print(
                            f"⚠️  Checkpoint mismatch: checkpoint has {checkpoint_total} records, "
                            f"but upload has {total_records} records"
                        )
                        print("   Deleting stale checkpoint and starting fresh...")
                        checkpoint_file.unlink()
                        results = []
                        start_idx = 0
                    else:
                        print(
                            f"📂 Resuming from checkpoint: record {start_idx + 1}/{total_records}"
                        )
                else:
                    # Old format checkpoint - assume it's stale, start fresh
                    results, start_idx = checkpoint_data
                    print(
                        "⚠️  Old checkpoint format detected (no record count validation)"
                    )
                    print("   Deleting old checkpoint and starting fresh...")
                    checkpoint_file.unlink()
                    results = []
                    start_idx = 0

            except Exception as e:
                print(f"⚠️  Error loading checkpoint: {e}")
                print("   Deleting corrupted checkpoint and starting fresh...")
                checkpoint_file.unlink()
                results = []
                start_idx = 0

        # Initialize driver
        print("🌐 Initializing Chrome WebDriver...")
        driver = setup_driver(headless)

        try:
            start_time = time.time()

            for idx, row in df_upload.iloc[start_idx:].iterrows():
                # Progress indicator
                if idx > 0 and idx % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (total_records - idx) / rate if rate > 0 else 0
                    print(
                        f"   Progress: {idx}/{total_records} ({idx*100//total_records}%) | "
                        f"Rate: {rate:.1f} rec/sec | ETA: {remaining/60:.1f} min",
                        flush=True,
                    )

                # Get Upload data
                owner_name = row["Owner_Ownership"]
                owner_type = row["OWNER_TYPE"]

                # ACC lookup (columns F-CO)
                if pd.isna(owner_name) or str(owner_name).strip() == "":
                    # Blank owner - use empty ACC record
                    acc_data = get_blank_acc_record()
                elif owner_type == "INDIVIDUAL":
                    # For INDIVIDUAL type, skip ACC lookup and parse names instead
                    acc_data = get_blank_acc_record()
                    # Parse individual names
                    parsed_names = parse_individual_names(owner_name)
                    # Populate IndividualName fields
                    for i, parsed_name in enumerate(parsed_names[:4], 1):
                        acc_data[f"IndividualName{i}"] = parsed_name
                else:
                    # BUSINESS type - do ACC lookup with caching
                    acc_results = get_cached_or_lookup(
                        cache, str(owner_name), driver, settings
                    )
                    acc_data = acc_results[0] if acc_results else get_blank_acc_record()

                # Build complete record in correct column order (93 columns: A-CO)
                # A-C: Upload columns, D: Index, E: Owner Type, F-CO: ACC fields
                complete_record = {
                    "FULL_ADDRESS": row["FULL_ADDRESS"],  # A
                    "COUNTY": row["COUNTY"],  # B
                    "Owner_Ownership": row["Owner_Ownership"],  # C
                    "ECORP_INDEX_#": idx + 1,  # D (sequential number)
                    "OWNER_TYPE": row["OWNER_TYPE"],  # E
                    **acc_data,  # F-CO (ACC fields including ECORP_URL)
                }
                results.append(complete_record)

                # Checkpoint every 50 records
                if (idx + 1) % 50 == 0:
                    save_checkpoint(checkpoint_file, results, idx + 1, total_records)
                    print(f"   💾 Checkpoint saved at {idx + 1} records")

            # Group records by individual overlap and reassign ECORP_INDEX_#
            print("\n🔍 Grouping records by individual overlap (threshold: 85%)...")
            index_assignments = assign_grouped_indexes_by_individuals(
                results, threshold=85.0
            )

            # Update ECORP_INDEX_# in all records
            for idx, record in enumerate(results):
                record["ECORP_INDEX_#"] = index_assignments[idx]

            unique_groups = len(set(index_assignments))
            print(
                f"   ✅ Grouped {len(results)} records into {unique_groups} unique groups"
            )
            print(
                f"   📊 Average group size: {len(results)/unique_groups:.1f} records per group"
            )

            # Save final Complete file with new naming
            # Extract timestamp from Upload file (or use current if not found)
            timestamp = extract_timestamp_from_filename(upload_path.name)
            if not timestamp:
                timestamp = get_standard_timestamp()

            # Generate new format filename
            new_filename = format_output_filename(
                month_code, "Ecorp_Complete", timestamp
            )

            # Generate legacy format filename
            legacy_filename = get_legacy_filename(
                month_code, "Ecorp_Complete", timestamp
            )

            output_dir = Path("Ecorp/Complete")
            output_dir.mkdir(parents=True, exist_ok=True)

            new_path = output_dir / new_filename
            legacy_path = output_dir / legacy_filename

            df_complete = pd.DataFrame(results)
            df_complete.to_excel(new_path, index=False, engine="xlsxwriter")

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
            print("\n⚠️  Interrupted by user - saving progress...")
            save_checkpoint(checkpoint_file, results, idx, total_records)
            print(
                f"💾 Progress saved to checkpoint. Run again to resume from record {idx + 1}"
            )
            return False

        finally:
            driver.quit()

    except Exception as e:
        print(f"❌ Error processing Ecorp Complete: {e}")
        import traceback

        traceback.print_exc()
        return False
