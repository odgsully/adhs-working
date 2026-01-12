#!/usr/bin/env python3
"""Test full search flow: login + 2FA + search."""

import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from adhs_etl.config import get_ecorp_settings
from adhs_etl.ecorp import (
    setup_driver,
    search_entities,
    get_ecorp_settings as get_settings_func,
)


def test_full_search():
    """Test the complete search flow with a sample entity."""
    settings = get_ecorp_settings()

    print("=" * 60)
    print("FULL SEARCH TEST")
    print("=" * 60)
    print(f"Email: {settings.email[:3]}...{settings.email[-10:] if settings.email else 'NOT SET'}")
    print(f"Base URL: {settings.base_url}")
    print("=" * 60)

    # Test search term
    test_name = "SUENOS PROPERTIES LLC"
    print(f"\nTest search: '{test_name}'")

    print("\nInitializing browser...")
    driver = setup_driver(headless=True)

    try:
        print("Performing search (will prompt for 2FA if needed)...")
        results = search_entities(driver, test_name, settings)

        print(f"\n{'=' * 60}")
        print("SEARCH RESULTS")
        print("=" * 60)

        if results:
            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                # Show key fields
                key_fields = [
                    "ECORP_SEARCH_NAME",
                    "ECORP_NAME_S",
                    "ECORP_ENTITY_ID_S",
                    "ECORP_STATUS",
                    "ECORP_ENTITY_TYPE",
                    "ECORP_COMMENTS",
                    "ECORP_URL",
                ]
                for field in key_fields:
                    value = result.get(field, "")
                    if value:
                        print(f"  {field}: {value}")

            # Save screenshot
            screenshot_path = project_root / "Ecorp" / "search_test_result.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"\nScreenshot saved: {screenshot_path}")

            # Check if we got real data or error
            first_result = results[0]
            if first_result.get("ECORP_COMMENTS"):
                print(f"\n⚠️  Note: {first_result['ECORP_COMMENTS']}")
            elif first_result.get("ECORP_NAME_S"):
                print("\n✅ SEARCH SUCCESSFUL - Got entity data!")
            else:
                print("\n⚠️  Search completed but no entity found")

        else:
            print("No results returned")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

        # Save error screenshot
        screenshot_path = project_root / "Ecorp" / "search_test_error.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"Error screenshot saved: {screenshot_path}")

    finally:
        driver.quit()
        print("\nBrowser closed.")


if __name__ == "__main__":
    test_full_search()
