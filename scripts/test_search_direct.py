#!/usr/bin/env python3
"""Direct test of search_entities function with debug output."""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from adhs_etl.ecorp import (
    setup_driver,
    search_entities,
    find_element_with_fallback,
    find_elements_with_fallback,
    SELECTORS,
)
from adhs_etl.config import get_ecorp_settings


def debug_test():
    """Debug test with step-by-step output."""
    settings = get_ecorp_settings(headless=True)  # Headless for automation
    print(f"Debug testing search...")
    print(f"Base URL: {settings.base_url}")

    driver = setup_driver(headless=True)
    try:
        # Navigate to search page
        print("\n1. Navigating to search page...")
        driver.get(settings.base_url)
        time.sleep(8)  # Wait longer for Angular SPA to fully load and route
        print(f"   Initial URL: {driver.current_url}")
        print(f"   Page title: {driver.title}")

        # Check visible page content
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text[:300] if body else ""
        if "Online Services Login" in body_text or "Register Here" in body_text:
            print("   WARNING: Still on login/landing page!")
        elif "Search" in body_text or "Entity" in body_text or "Business" in body_text:
            print("   SUCCESS: Search page loaded!")

        # Try alternate URLs if needed
        alt_urls = [
            "https://arizonabusinesscenter.azcc.gov/PublicSearch/EntitySearch",
            "https://arizonabusinesscenter.azcc.gov/search",
            "https://arizonabusinesscenter.azcc.gov/entity-search",
        ]
        print("\n1b. Trying alternate URLs...")
        for url in alt_urls:
            try:
                driver.get(url)
                time.sleep(2)
                current = driver.current_url
                title = driver.title
                # Check if we found a search form
                inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"   {url}")
                print(f"      -> {current}")
                print(f"      Title: {title}, Inputs: {len(inputs)}")
            except Exception as e:
                print(f"   {url} -> Error: {e}")

        # Try to find search input
        print("\n2. Looking for search input...")
        print(f"   Selectors to try: {len(SELECTORS['search_input'])}")
        for i, (by, sel) in enumerate(SELECTORS["search_input"]):
            try:
                elem = driver.find_element(by, sel)
                print(f"   [{i+1}] FOUND: {sel}")
                break
            except Exception:
                print(f"   [{i+1}] NOT FOUND: {sel}")

        # Enter search term
        print("\n3. Entering search term...")
        search_input = find_element_with_fallback(driver, "search_input", timeout=10)
        search_input.clear()
        search_input.send_keys("SUENOS PROPERTIES LLC")
        search_input.send_keys(Keys.RETURN)
        print("   Search submitted, waiting for results...")
        time.sleep(5)  # Wait for results

        # Check for results rows
        print("\n4. Looking for results table rows...")
        print(f"   Selectors to try: {len(SELECTORS['results_rows'])}")
        for i, (by, sel) in enumerate(SELECTORS["results_rows"]):
            try:
                elems = driver.find_elements(by, sel)
                print(f"   [{i+1}] {sel}: {len(elems)} found")
            except Exception as e:
                print(f"   [{i+1}] {sel}: ERROR - {e}")

        # Get page source snippet
        print("\n5. Page body sample...")
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text[:500] if body else "N/A"
        print(f"   Body text preview:\n{body_text}\n...")

        # Check what elements exist
        print("\n6. Checking for any table-like elements...")
        for tag in ["table", "mat-table", "mat-row", "tr", "tbody"]:
            try:
                elems = driver.find_elements(By.TAG_NAME, tag)
                print(f"   {tag}: {len(elems)} found")
            except Exception:
                print(f"   {tag}: not found")

        # Save screenshot for debugging
        screenshot_path = project_root / "Ecorp" / "debug_screenshot.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"\n7. Screenshot saved: {screenshot_path}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_test()
