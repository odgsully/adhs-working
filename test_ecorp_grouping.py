#!/usr/bin/env python3
"""
Test script for Ecorp individual-based grouping logic.

Tests the three new functions:
1. extract_individual_names() - Extract all individual names from a record
2. calculate_person_overlap() - Calculate similarity between person sets
3. assign_grouped_indexes_by_individuals() - Assign grouped indexes
"""

from src.adhs_etl.ecorp import (
    extract_individual_names,
    calculate_person_overlap,
    assign_grouped_indexes_by_individuals,
    get_blank_acc_record
)


def test_extract_individual_names():
    """Test extraction of individual names from various fields."""
    print("=" * 70)
    print("TEST 1: extract_individual_names()")
    print("=" * 70)

    # Test record with various individuals
    record = {
        'Manager1_Name': 'JOHN SMITH',
        'Manager2_Name': 'JANE DOE',
        'Manager3_Name': '',
        'Member1_Name': 'BOB JONES',
        'Member2_Name': '',
        'StatutoryAgent1_Name': 'ALICE WILLIAMS',
        'StatutoryAgent2_Name': '',
        'IndividualName1': 'CHARLIE BROWN',
        'IndividualName2': '',
    }

    names = extract_individual_names(record)
    print(f"\nExtracted {len(names)} unique names:")
    for name in sorted(names):
        print(f"  - {name}")

    expected = {'JOHN SMITH', 'JANE DOE', 'BOB JONES', 'ALICE WILLIAMS', 'CHARLIE BROWN'}
    assert names == expected, f"Expected {expected}, got {names}"
    print("✅ PASSED")


def test_calculate_person_overlap():
    """Test person overlap calculation with fuzzy matching."""
    print("\n" + "=" * 70)
    print("TEST 2: calculate_person_overlap()")
    print("=" * 70)

    # Test case 1: Exact matches
    names1 = {'JOHN SMITH', 'JANE DOE'}
    names2 = {'JOHN SMITH', 'JANE DOE'}
    overlap = calculate_person_overlap(names1, names2, threshold=85.0)
    print(f"\nTest Case 1: Exact match")
    print(f"  Names 1: {names1}")
    print(f"  Names 2: {names2}")
    print(f"  Overlap: {overlap:.1f}%")
    assert overlap == 100.0, f"Expected 100%, got {overlap}%"
    print("  ✅ PASSED")

    # Test case 2: Fuzzy match (name variations)
    names1 = {'JOHN A SMITH', 'JANE DOE'}
    names2 = {'JOHN SMITH', 'JANE DOE'}
    overlap = calculate_person_overlap(names1, names2, threshold=85.0)
    print(f"\nTest Case 2: Fuzzy match")
    print(f"  Names 1: {names1}")
    print(f"  Names 2: {names2}")
    print(f"  Overlap: {overlap:.1f}%")
    assert overlap >= 50.0, f"Expected >=50%, got {overlap}%"
    print("  ✅ PASSED")

    # Test case 3: Partial overlap
    names1 = {'JOHN SMITH', 'JANE DOE', 'BOB JONES'}
    names2 = {'JOHN SMITH', 'JANE DOE'}
    overlap = calculate_person_overlap(names1, names2, threshold=85.0)
    print(f"\nTest Case 3: Partial overlap")
    print(f"  Names 1: {names1}")
    print(f"  Names 2: {names2}")
    print(f"  Overlap: {overlap:.1f}%")
    print(f"  Expected: ~83.3% (bidirectional: 2/3 from names1 + 2/2 from names2 = avg 83.3%)")
    assert 80 <= overlap <= 85, f"Expected 80-85%, got {overlap}%"
    print("  ✅ PASSED")

    # Test case 4: No overlap
    names1 = {'JOHN SMITH', 'JANE DOE'}
    names2 = {'ALICE WILLIAMS', 'BOB JONES'}
    overlap = calculate_person_overlap(names1, names2, threshold=85.0)
    print(f"\nTest Case 4: No overlap")
    print(f"  Names 1: {names1}")
    print(f"  Names 2: {names2}")
    print(f"  Overlap: {overlap:.1f}%")
    assert overlap == 0.0, f"Expected 0%, got {overlap}%"
    print("  ✅ PASSED")


def test_assign_grouped_indexes():
    """Test grouped index assignment."""
    print("\n" + "=" * 70)
    print("TEST 3: assign_grouped_indexes_by_individuals()")
    print("=" * 70)

    # Create test records
    records = []

    # Record 1: JOHN SMITH & JANE DOE (Group 1)
    rec1 = get_blank_acc_record()
    rec1['Manager1_Name'] = 'JOHN SMITH'
    rec1['Manager2_Name'] = 'JANE DOE'
    rec1['Entity Name(s)'] = 'ABC PROPERTIES LLC'
    records.append(rec1)

    # Record 2: JOHN SMITH & JANE DOE (Should be Group 1 - same people)
    rec2 = get_blank_acc_record()
    rec2['Manager1_Name'] = 'JOHN SMITH'
    rec2['Manager2_Name'] = 'JANE DOE'
    rec2['Entity Name(s)'] = 'XYZ HOLDINGS INC'
    records.append(rec2)

    # Record 3: ALICE WILLIAMS (Group 2 - different person)
    rec3 = get_blank_acc_record()
    rec3['Manager1_Name'] = 'ALICE WILLIAMS'
    rec3['Entity Name(s)'] = 'WILLIAMS VENTURES LLC'
    records.append(rec3)

    # Record 4: BOB JONES & CHARLIE BROWN (Group 3)
    rec4 = get_blank_acc_record()
    rec4['Manager1_Name'] = 'BOB JONES'
    rec4['Member1_Name'] = 'CHARLIE BROWN'
    rec4['Entity Name(s)'] = 'JONES & BROWN ASSOCIATES'
    records.append(rec4)

    # Record 5: JOHN A SMITH & JANE DOE (Should be Group 1 - fuzzy match)
    rec5 = get_blank_acc_record()
    rec5['Manager1_Name'] = 'JOHN A SMITH'
    rec5['Manager2_Name'] = 'JANE DOE'
    rec5['Entity Name(s)'] = 'SMITH DOE ENTERPRISES'
    records.append(rec5)

    # Assign indexes
    indexes = assign_grouped_indexes_by_individuals(records, threshold=85.0)

    print(f"\nAssigned indexes for {len(records)} records:")
    for i, (rec, idx) in enumerate(zip(records, indexes)):
        entity = rec.get('Entity Name(s)', 'N/A')
        names = extract_individual_names(rec)
        print(f"  Record {i+1}: ECORP_INDEX_# = {idx}")
        print(f"    Entity: {entity}")
        print(f"    People: {', '.join(sorted(names))}")

    # Verify grouping
    print("\nVerifying grouping:")
    assert indexes[0] == indexes[1], "Records 1 & 2 should have same index (same people)"
    print("  ✅ Records 1 & 2 grouped together (same managers)")

    assert indexes[0] == indexes[4], "Records 1 & 5 should have same index (fuzzy match)"
    print("  ✅ Records 1 & 5 grouped together (fuzzy name match)")

    assert indexes[2] != indexes[0], "Record 3 should have different index"
    print("  ✅ Record 3 has unique index (different person)")

    assert indexes[3] != indexes[0] and indexes[3] != indexes[2], "Record 4 should be unique"
    print("  ✅ Record 4 has unique index (different people)")

    unique_groups = len(set(indexes))
    print(f"\n  Total unique groups: {unique_groups}")
    assert unique_groups == 3, f"Expected 3 groups, got {unique_groups}"
    print("  ✅ PASSED")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("ECORP INDIVIDUAL-BASED GROUPING TESTS")
    print("=" * 70)

    try:
        test_extract_individual_names()
        test_calculate_person_overlap()
        test_assign_grouped_indexes()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✅")
        print("=" * 70)
        print("\nThe grouping logic correctly:")
        print("  1. Extracts individual names from all role fields")
        print("  2. Calculates overlap using fuzzy name matching")
        print("  3. Groups records with similar sets of individuals")
        print("  4. Identifies corporate families under common control")
        print()

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
