#!/usr/bin/env python3
"""
BatchData V1 Endpoint Validation Script
Validates that all code uses correct V1 endpoint format
"""

import re
import sys
import os
from pathlib import Path
from typing import List, Dict, Set

# Correct V1 endpoints
VALID_V1_ENDPOINTS = {
    '/api/v1/property/skip-trace',
    '/api/v1/property/skip-trace/async',
    '/api/v1/phone/verification',
    '/api/v1/phone/verification/async',
    '/api/v1/phone/dnc',
    '/api/v1/phone/dnc/async',
    '/api/v1/phone/tcpa',
    '/api/v1/phone/tcpa/async',
    '/api/v1/address/verify',
    '/api/v1/property/search/async',
    '/api/v1/property/lookup/async',
    '/api/v1/jobs',
    'property/skip-trace',  # Relative paths (used with base_url)
    'property/skip-trace/async',
    'phone/verification',
    'phone/verification/async',
    'phone/dnc',
    'phone/dnc/async',
    'phone/tcpa',
    'phone/tcpa/async',
    'address/verify',
    'property/search/async',
    'property/lookup/async'
}

# Incorrect patterns to detect
INCORRECT_PATTERNS = [
    # Hyphenated endpoints (wrong)
    (r'property-skip-trace-async', 'property/skip-trace/async'),
    (r'property-skip-trace', 'property/skip-trace'),
    (r'phone-verification-async', 'phone/verification/async'),
    (r'phone-verification', 'phone/verification'),
    (r'phone-dnc-async', 'phone/dnc/async'),
    (r'phone-dnc', 'phone/dnc'),
    (r'phone-tcpa-async', 'phone/tcpa/async'),
    (r'phone-tcpa', 'phone/tcpa'),
    (r'property-search-async', 'property/search/async'),
    (r'property-lookup-async', 'property/lookup/async'),
    (r'address-verify', 'address/verify'),

    # Wrong API versions
    (r'/api/v2/', '/api/v1/'),
    (r'/api/v3/', '/api/v1/'),
    (r'api\.batchdata\.com/v1', 'api.batchdata.com/api/v1'),
    (r'api\.batchdata\.com/v2', 'api.batchdata.com/api/v1'),
    (r'api\.batchdata\.com/v3', 'api.batchdata.com/api/v1'),
]

def check_file_for_incorrect_endpoints(file_path: Path) -> Dict[str, List[str]]:
    """Check a file for incorrectly formatted endpoints"""
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return {'error': [f"Could not read file: {e}"]}

    for line_num, line in enumerate(lines, 1):
        # Skip lines that are comments about what NOT to do
        if 'WRONG' in line or '❌' in line or 'incorrect' in line.lower():
            continue

        # Check for incorrect patterns
        for pattern, correct in INCORRECT_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                errors.append(f"Line {line_num}: Found '{pattern}' - should be '{correct}'")
                errors.append(f"  Content: {line.strip()[:100]}...")

    return {'errors': errors} if errors else {}

def validate_python_file(file_path: Path) -> Dict[str, List[str]]:
    """Validate Python files for correct endpoint usage"""
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return {'error': [f"Could not read file: {e}"]}

    # Look for endpoint definitions
    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith('#'):
            continue

        # Check for string literals containing endpoints
        if 'phone' in line or 'property' in line or 'address' in line:
            # Look for hyphenated patterns in strings
            string_matches = re.findall(r'["\']([^"\']*(?:phone|property|address)[^"\']*)["\']', line)
            for match in string_matches:
                # Check if it's a hyphenated endpoint
                if re.search(r'(phone|property|address)-\w+-\w+', match):
                    errors.append(f"Line {line_num}: Hyphenated endpoint '{match}'")
                    errors.append(f"  Should use forward slashes instead of hyphens")
                elif re.search(r'(phone|property|address)-\w+', match):
                    if match not in ['phone-number', 'property-data', 'address-data']:  # Allow some non-endpoint hyphens
                        errors.append(f"Line {line_num}: Potentially incorrect endpoint '{match}'")

    return {'errors': errors} if errors else {}

def check_base_urls(file_path: Path) -> Dict[str, List[str]]:
    """Check that base URLs use V1"""
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return {'error': [f"Could not read file: {e}"]}

    for line_num, line in enumerate(lines, 1):
        # Look for base URL definitions
        if 'api.batchdata.com' in line:
            # Skip comments and documentation
            if line.strip().startswith('#') or line.strip().startswith('*'):
                continue

            # Check for V2 or V3
            if '/api/v2' in line or '/api/v3' in line:
                # Skip if it's in a comment about what NOT to do
                if 'WRONG' not in line and '❌' not in line:
                    errors.append(f"Line {line_num}: Using wrong API version")
                    errors.append(f"  Content: {line.strip()}")
                    errors.append(f"  Should use /api/v1")

    return {'errors': errors} if errors else {}

def main():
    """Main validation function"""
    print("="*60)
    print("BatchData V1 Endpoint Validation")
    print("="*60)

    # Get Batchdata directory
    base_dir = Path(__file__).parent

    # Find all Python files
    python_files = list(base_dir.rglob('*.py'))

    # Find all Markdown files
    markdown_files = list(base_dir.rglob('*.md'))

    all_issues = {}

    print(f"\nChecking {len(python_files)} Python files...")

    # Check Python files
    for file_path in python_files:
        # Skip this validation script
        if 'test_v1_endpoints.py' in str(file_path):
            continue

        # Skip __pycache__ directories
        if '__pycache__' in str(file_path):
            continue

        issues = validate_python_file(file_path)
        if not issues:
            issues = check_base_urls(file_path)

        if issues:
            relative_path = file_path.relative_to(base_dir)
            all_issues[str(relative_path)] = issues

    print(f"Checking {len(markdown_files)} Markdown files...")

    # Check Markdown files
    for file_path in markdown_files:
        issues = check_file_for_incorrect_endpoints(file_path)
        if not issues:
            issues = check_base_urls(file_path)

        if issues:
            relative_path = file_path.relative_to(base_dir)
            all_issues[str(relative_path)] = issues

    # Report results
    if all_issues:
        print("\n" + "="*60)
        print("❌ ISSUES FOUND")
        print("="*60)

        for file_path, issues in all_issues.items():
            print(f"\n📄 {file_path}:")
            if 'error' in issues:
                for error in issues['error']:
                    print(f"  ⚠️  {error}")
            if 'errors' in issues:
                for error in issues['errors']:
                    print(f"  ❌ {error}")

        print("\n" + "="*60)
        print(f"Total files with issues: {len(all_issues)}")
        print("="*60)

        return 1
    else:
        print("\n" + "="*60)
        print("✅ ALL ENDPOINTS USE CORRECT V1 FORMAT!")
        print("="*60)
        print("\nValidation successful:")
        print("  • All endpoints use forward slashes (not hyphens)")
        print("  • All base URLs use /api/v1")
        print("  • No incorrect patterns found")

        return 0

if __name__ == "__main__":
    sys.exit(main())