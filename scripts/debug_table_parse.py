#!/usr/bin/env python3
"""Debug script to understand table parsing."""

import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from selenium.webdriver.common.by import By
from adhs_etl.config import get_ecorp_settings
from adhs_etl.ecorp import setup_driver, perform_login, detect_login_page, detect_2fa_page


def debug_table():
    settings = get_ecorp_settings()
    print("Initializing browser...")
    driver = setup_driver(headless=True)

    try:
        # Navigate to search page
        driver.get(settings.base_url)
        time.sleep(3)

        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")

        # Handle login if needed
        if detect_login_page(driver) or detect_2fa_page(driver):
            print("Login/2FA required...")
            if not perform_login(driver, settings):
                print("Login failed!")
                return
            driver.get(settings.base_url)
            time.sleep(3)

        print(f"After login - URL: {driver.current_url}")

        # Find search input with fallbacks
        search_input = None
        for selector in ["input[placeholder='Enter Business Name']", "input[placeholder*='Business']", ".mat-mdc-form-field-infix input"]:
            try:
                search_input = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"Found search input with: {selector}")
                break
            except:
                continue

        if not search_input:
            print("ERROR: Could not find search input!")
            driver.save_screenshot(str(project_root / "Ecorp" / "debug_no_input.png"))
            return

        search_input.clear()
        search_input.send_keys("SUENOS PROPERTIES LLC")

        # Click search button with fallbacks
        search_btn = None
        for selector in ["//button[normalize-space()='Business Search']", "//button[contains(text(), 'Search')]", "button[type='submit']"]:
            try:
                if selector.startswith("//"):
                    search_btn = driver.find_element(By.XPATH, selector)
                else:
                    search_btn = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"Found search button with: {selector}")
                break
            except:
                continue

        if search_btn:
            search_btn.click()
        else:
            print("No search button found, pressing Enter")
            from selenium.webdriver.common.keys import Keys
            search_input.send_keys(Keys.RETURN)

        time.sleep(5)

        print("\n" + "=" * 60)
        print("DEBUG: Analyzing page structure")
        print("=" * 60)

        # Check for tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\nFound {len(tables)} <table> elements")

        # Check for tbody
        tbodies = driver.find_elements(By.TAG_NAME, "tbody")
        print(f"Found {len(tbodies)} <tbody> elements")

        # Check for tr elements
        all_trs = driver.find_elements(By.TAG_NAME, "tr")
        print(f"Found {len(all_trs)} <tr> elements total")

        # Check tbody tr specifically
        tbody_trs = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        print(f"Found {len(tbody_trs)} <tbody tr> elements")

        # Check table tbody tr
        table_tbody_trs = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        print(f"Found {len(table_tbody_trs)} <table tbody tr> elements")

        # Let's examine the first tbody tr if it exists
        if tbody_trs:
            print(f"\n--- First tbody tr ---")
            first_row = tbody_trs[0]
            print(f"Row HTML (first 500 chars): {first_row.get_attribute('outerHTML')[:500]}")

            # Get td elements
            tds = first_row.find_elements(By.TAG_NAME, "td")
            print(f"\nFound {len(tds)} <td> elements in first row:")
            for i, td in enumerate(tds):
                text = td.text.strip()[:50]
                print(f"  [{i}] {text}")

            # Check for links
            links = first_row.find_elements(By.TAG_NAME, "a")
            print(f"\nFound {len(links)} <a> elements in first row:")
            for i, link in enumerate(links):
                href = link.get_attribute("href")
                text = link.text.strip()[:30]
                print(f"  [{i}] '{text}' -> {href}")

        # Check if there's a header row we might be picking up
        if all_trs:
            print(f"\n--- All TR elements ---")
            for i, tr in enumerate(all_trs[:5]):  # First 5
                tds = tr.find_elements(By.TAG_NAME, "td")
                ths = tr.find_elements(By.TAG_NAME, "th")
                text_preview = tr.text.strip()[:60].replace('\n', ' ')
                print(f"  [{i}] {len(tds)} tds, {len(ths)} ths: '{text_preview}...'")

        # Save screenshot
        driver.save_screenshot(str(project_root / "Ecorp" / "debug_table.png"))
        print("\nScreenshot saved to Ecorp/debug_table.png")

    finally:
        driver.quit()
        print("\nBrowser closed.")


if __name__ == "__main__":
    debug_table()
