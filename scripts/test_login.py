#!/usr/bin/env python3
"""Test Arizona Business Connect login with configured credentials."""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from adhs_etl.config import get_ecorp_settings
from adhs_etl.ecorp import setup_driver, detect_login_page, perform_login


def test_login():
    """Test the login functionality."""
    # Load settings
    settings = get_ecorp_settings()

    print("Settings loaded:")
    if settings.email:
        masked_email = settings.email[:3] + "..." + settings.email[-10:]
        print(f"  Email: {masked_email}")
    else:
        print("  Email: NOT SET")
    print(f"  Password: {'*' * 8 if settings.password else 'NOT SET'}")
    print(f"  Login URL: {settings.login_url}")

    if not settings.email or not settings.password:
        print("\nERROR: Credentials not configured")
        return False

    print("\nInitializing browser...")
    driver = setup_driver(headless=True)

    try:
        print("Attempting login...")
        success = perform_login(driver, settings)

        if success:
            print("\n✅ LOGIN SUCCESSFUL!")
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")

            # Try navigating to search page
            print("\nNavigating to search page...")
            driver.get(settings.base_url)
            time.sleep(3)

            if not detect_login_page(driver):
                print("✅ Search page accessible after login!")

                # Save success screenshot
                screenshot_path = project_root / "Ecorp" / "login_success.png"
                driver.save_screenshot(str(screenshot_path))
                print(f"Screenshot saved: {screenshot_path}")
                return True
            else:
                print("⚠️  Still seeing login page - session may not have persisted")
                return False
        else:
            print("\n❌ LOGIN FAILED")
            print(f"Current URL: {driver.current_url}")

            # Save screenshot for debugging
            screenshot_path = project_root / "Ecorp" / "login_failed.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"Screenshot saved: {screenshot_path}")
            return False

    finally:
        driver.quit()
        print("\nBrowser closed.")


if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)
