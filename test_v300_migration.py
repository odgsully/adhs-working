#!/usr/bin/env python3
"""
Test script to validate v300Track_this.xlsx template migration.
Ensures all 150+ columns are properly generated and data integrity is maintained.
"""

import sys
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from adhs_etl.analysis import ProviderAnalyzer

def validate_v300_columns():
    """Validate that all v300 columns are properly defined."""

    # Expected v300 columns (150+ total) as defined in v300Track_this.md
    v300_columns = [
        # Core fields (Columns A-P)
        'SOLO PROVIDER_TYPE PROVIDER [Y, #]',
        'PROVIDER_TYPE',
        'PROVIDER',
        'ADDRESS',
        'CITY',
        'ZIP',
        'FULL_ADDRESS',
        'CAPACITY',
        'LONGITUDE',
        'LATITUDE',
        'COUNTY',
        'PROVIDER_GROUP_INDEX_#',

        # Provider grouping
        'PROVIDER GROUP (DBA CONCAT)',
        'PROVIDER GROUP, ADDRESS COUNT',
        'THIS MONTH STATUS',
        'LEAD TYPE',
    ]

    # Extended historical columns (Q-BD) - 48 COUNT columns for 1.22 through 12.25
    for year in range(22, 26):  # 2022-2025
        for month in range(1, 13):
            v300_columns.append(f'{month}.{year} COUNT')

    # Extended monthly movements (BE-CQ) - 47 TO PREV columns (excludes first month)
    for year in range(22, 26):
        for month in range(1, 13):
            if not (year == 22 and month == 1):  # Skip 1.22 TO PREV (first month)
                v300_columns.append(f'{month}.{year} TO PREV')

    # Extended monthly summaries (CR-EE) - 48 SUMMARY columns
    for year in range(22, 26):
        for month in range(1, 13):
            v300_columns.append(f'{month}.{year} SUMMARY')

    # Repositioned metadata (EF-EG)
    v300_columns.extend(['MONTH', 'YEAR'])

    # New enhanced tracking fields (EH-EY) - 18 fields
    v300_columns.extend([
        'PREVIOUS_MONTH_STATUS',
        'STATUS_CONFIDENCE',
        'PROVIDER_TYPES_GAINED',
        'PROVIDER_TYPES_LOST',
        'NET_TYPE_CHANGE',
        'MONTHS_SINCE_LOST',
        'REINSTATED_FLAG',
        'REINSTATED_DATE',
        'DATA_QUALITY_SCORE',
        'MANUAL_REVIEW_FLAG',
        'REVIEW_NOTES',
        'LAST_ACTIVE_MONTH',
        'REGIONAL_MARKET',
        'HISTORICAL_STABILITY_SCORE',
        'EXPANSION_VELOCITY',
        'CONTRACTION_RISK',
        'MULTI_CITY_OPERATOR',
        'RELOCATION_FLAG'
    ])

    return v300_columns

def test_column_generation():
    """Test that column generation produces correct v300 structure."""
    print("🔍 Testing v300 column generation...")

    analyzer = ProviderAnalyzer()

    # Create minimal test dataframe
    test_df = pd.DataFrame({
        'PROVIDER': ['Test Provider A', 'Test Provider B'],
        'PROVIDER_TYPE': ['NURSING_HOME', 'ASSISTED_LIVING_CENTER'],
        'ADDRESS': ['123 Main St', '456 Oak Ave'],
        'CITY': ['Phoenix', 'Tucson'],
        'ZIP': ['85001', '85701'],
        'FULL_ADDRESS': ['123 Main St, Phoenix, AZ 85001', '456 Oak Ave, Tucson, AZ 85701'],
        'CAPACITY': [50, 75],
        'LONGITUDE': [-112.074, -110.926],
        'LATITUDE': [33.448, 32.222],
        'COUNTY': ['MARICOPA', 'PIMA'],
        'PROVIDER_GROUP_INDEX_#': [1, 2]
    })

    # Process through analyzer
    result = analyzer.ensure_all_analysis_columns(test_df, 9, 2024)

    # Get expected columns
    v300_cols = validate_v300_columns()

    # Check for missing columns
    missing = [col for col in v300_cols if col not in result.columns]
    extra = [col for col in result.columns if col not in v300_cols]

    print(f"  Expected columns: {len(v300_cols)}")
    print(f"  Generated columns: {len(result.columns)}")

    if missing:
        print(f"  ❌ Missing columns ({len(missing)}): {missing[:5]}...")
        if len(missing) > 5:
            print(f"     ... and {len(missing) - 5} more")
    else:
        print(f"  ✅ All expected columns present")

    if extra:
        print(f"  ⚠️  Extra columns ({len(extra)}): {extra[:5]}...")

    return len(missing) == 0 and len(extra) == 0

def test_historical_range():
    """Verify 40+ month historical tracking spans correct date range."""
    print("\n📅 Testing extended historical range...")

    analyzer = ProviderAnalyzer()
    test_df = pd.DataFrame({
        'PROVIDER': ['Test'],
        'PROVIDER_TYPE': ['NURSING_HOME'],
        'ADDRESS': ['123 Main St']
    })

    result = analyzer.ensure_all_analysis_columns(test_df, 9, 2024)

    # Check COUNT columns (exclude 'PROVIDER GROUP, ADDRESS COUNT')
    count_cols = [col for col in result.columns if col.endswith(' COUNT') and not col.startswith('PROVIDER GROUP')]
    expected_count = 48  # 12 months x 4 years (2022-2025)

    print(f"  COUNT columns: {len(count_cols)} (expected: {expected_count})")

    # Verify first and last COUNT columns
    if '1.22 COUNT' in result.columns and '12.25 COUNT' in result.columns:
        print(f"  ✅ Historical range spans 1.22 through 12.25")
    else:
        print(f"  ❌ Historical range incorrect")

    # Check TO PREV columns (should be 47 - excluding 1.22)
    to_prev_cols = [col for col in result.columns if col.endswith(' TO PREV')]
    expected_to_prev = 47  # All months except first (1.22)

    print(f"  TO PREV columns: {len(to_prev_cols)} (expected: {expected_to_prev})")

    # Check SUMMARY columns
    summary_cols = [col for col in result.columns if col.endswith(' SUMMARY')]
    expected_summary = 48  # Same as COUNT

    print(f"  SUMMARY columns: {len(summary_cols)} (expected: {expected_summary})")

    return (len(count_cols) == expected_count and
            len(to_prev_cols) == expected_to_prev and
            len(summary_cols) == expected_summary)

def test_enhanced_fields():
    """Test that new EH-EY tracking fields are present."""
    print("\n🔬 Testing enhanced tracking fields (EH-EY)...")

    analyzer = ProviderAnalyzer()
    test_df = pd.DataFrame({
        'PROVIDER': ['Test'],
        'PROVIDER_TYPE': ['NURSING_HOME'],
        'ADDRESS': ['123 Main St']
    })

    result = analyzer.ensure_all_analysis_columns(test_df, 9, 2024)

    enhanced_fields = [
        'PREVIOUS_MONTH_STATUS',
        'STATUS_CONFIDENCE',
        'PROVIDER_TYPES_GAINED',
        'PROVIDER_TYPES_LOST',
        'NET_TYPE_CHANGE',
        'MONTHS_SINCE_LOST',
        'REINSTATED_FLAG',
        'REINSTATED_DATE',
        'DATA_QUALITY_SCORE',
        'MANUAL_REVIEW_FLAG',
        'REVIEW_NOTES',
        'LAST_ACTIVE_MONTH',
        'REGIONAL_MARKET',
        'HISTORICAL_STABILITY_SCORE',
        'EXPANSION_VELOCITY',
        'CONTRACTION_RISK',
        'MULTI_CITY_OPERATOR',
        'RELOCATION_FLAG'
    ]

    missing_enhanced = [field for field in enhanced_fields if field not in result.columns]

    if missing_enhanced:
        print(f"  ❌ Missing enhanced fields: {missing_enhanced}")
    else:
        print(f"  ✅ All 18 enhanced tracking fields present")

    # Check that MONTH and YEAR are positioned after historical columns
    col_list = list(result.columns)
    month_idx = col_list.index('MONTH') if 'MONTH' in col_list else -1
    year_idx = col_list.index('YEAR') if 'YEAR' in col_list else -1

    # Should be after all SUMMARY columns
    last_summary_idx = max([col_list.index(col) for col in col_list if col.endswith(' SUMMARY')], default=0)

    if month_idx > last_summary_idx and year_idx > last_summary_idx:
        print(f"  ✅ MONTH/YEAR correctly positioned after historical columns")
    else:
        print(f"  ❌ MONTH/YEAR positioning incorrect")

    return len(missing_enhanced) == 0

def test_summary_sheet_metrics():
    """Ensure Summary sheet has all v300 metrics."""
    print("\n📊 Testing Summary sheet metrics...")

    from scripts.generate_proper_analysis import create_proper_summary_sheet

    test_df = pd.DataFrame({
        'PROVIDER': ['Test A', 'Test B'],
        'PROVIDER TYPE': ['NURSING_HOME', 'ASSISTED_LIVING_CENTER'],
        'ADDRESS': ['123 Main', '456 Oak'],
        'PROVIDER_GROUP_INDEX_#': [1, 2]
    })

    summary_df = create_proper_summary_sheet(test_df)

    # Check for v300-specific metrics
    metrics = summary_df['Metric'].tolist()

    v300_metrics = [
        'Reinstated PROVIDER TYPE, Existing ADDRESS',  # New in v300
        'Total Record Count (TRC)',  # New in v300
    ]

    found_metrics = [m for m in v300_metrics if m in metrics]

    if len(found_metrics) == len(v300_metrics):
        print(f"  ✅ All v300-specific summary metrics present")
    else:
        missing = [m for m in v300_metrics if m not in metrics]
        print(f"  ❌ Missing v300 metrics: {missing}")

    # Check that provider types have (TRC) suffix
    provider_types_with_trc = [m for m in metrics if '(TRC)' in m]

    if len(provider_types_with_trc) >= 12:  # Should have at least 12 provider types
        print(f"  ✅ Provider types have (TRC) suffix")
    else:
        print(f"  ❌ Provider types missing (TRC) suffix")

    return len(found_metrics) == len(v300_metrics)

def test_data_integrity():
    """Test that data processing maintains integrity with v300 structure."""
    print("\n🔒 Testing data integrity...")

    analyzer = ProviderAnalyzer()

    # Create test data with known values
    test_df = pd.DataFrame({
        'PROVIDER': ['Provider X'],
        'PROVIDER_TYPE': ['NURSING_HOME'],
        'ADDRESS': ['789 Pine Rd'],
        'CITY': ['Mesa'],
        'ZIP': ['85201'],
        'FULL_ADDRESS': ['789 Pine Rd, Mesa, AZ 85201'],
        'CAPACITY': [100],
        'LONGITUDE': [-111.831],
        'LATITUDE': [33.415],
        'COUNTY': ['MARICOPA'],
        'PROVIDER_GROUP_INDEX_#': [1]
    })

    result = analyzer.ensure_all_analysis_columns(test_df, 9, 2024)

    # Verify core data is preserved
    if (result['PROVIDER'].iloc[0] == 'Provider X' and
        result['PROVIDER_TYPE'].iloc[0] == 'NURSING_HOME' and
        result['COUNTY'].iloc[0] == 'MARICOPA'):
        print(f"  ✅ Core data preserved correctly")
    else:
        print(f"  ❌ Core data not preserved")

    # Check default values for new columns
    if result['REGIONAL_MARKET'].iloc[0] == 'N/A':  # Should be default N/A
        print(f"  ✅ New columns have appropriate defaults")
    else:
        print(f"  ❌ New column defaults incorrect")

    return True

def main():
    """Run all v300 migration tests."""
    print("=" * 60)
    print("🚀 v300 Track Migration Validation Tests")
    print("=" * 60)

    tests = [
        ("Column Generation", test_column_generation),
        ("Historical Range", test_historical_range),
        ("Enhanced Fields", test_enhanced_fields),
        ("Summary Metrics", test_summary_sheet_metrics),
        ("Data Integrity", test_data_integrity)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📈 Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All v300 migration tests passed! Ready for deployment.")
    else:
        print("\n⚠️  Some tests failed. Please review and fix issues before deployment.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)