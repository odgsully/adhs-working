"""Tests for name_matching module."""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from name_matching import (
    fuzzy_name_match,
    extract_ecorp_names_from_complete,
    extract_batch_names,
    calculate_match_percentage,
    apply_name_matching,
)


class TestFuzzyNameMatch:
    """Tests for fuzzy_name_match function."""

    def test_exact_match(self):
        """Identical names should match."""
        assert fuzzy_name_match("JOHN SMITH", "JOHN SMITH") is True

    def test_case_insensitive(self):
        """Matching should be case insensitive."""
        assert fuzzy_name_match("john smith", "JOHN SMITH") is True
        assert fuzzy_name_match("John Smith", "john smith") is True

    def test_name_order_invariant(self):
        """'JOHN SMITH' should match 'SMITH JOHN'."""
        assert fuzzy_name_match("JOHN SMITH", "SMITH JOHN") is True

    def test_fuzzy_match_above_threshold(self):
        """Names within 85% similarity should match."""
        # "JOHN D SMITH" vs "JOHN SMITH" should be above 85%
        assert fuzzy_name_match("JOHN D SMITH", "JOHN SMITH") is True

    def test_fuzzy_match_below_threshold(self):
        """Names below 85% similarity should not match."""
        assert fuzzy_name_match("JOHN", "JANE") is False
        assert fuzzy_name_match("JOHN SMITH", "BOB JONES") is False

    def test_empty_names(self):
        """Empty or None names should not match."""
        assert fuzzy_name_match("", "JOHN") is False
        assert fuzzy_name_match("JOHN", "") is False
        assert fuzzy_name_match("", "") is False
        assert fuzzy_name_match(None, "JOHN") is False
        assert fuzzy_name_match("JOHN", None) is False

    def test_whitespace_handling(self):
        """Extra whitespace should be stripped."""
        assert fuzzy_name_match("  JOHN SMITH  ", "JOHN SMITH") is True


class TestExtractEcorpNamesFromComplete:
    """Tests for extract_ecorp_names_from_complete function."""

    def test_extracts_statutory_agents(self):
        """Should extract StatutoryAgent1-3_Name fields."""
        row = pd.Series({
            'StatutoryAgent1_Name': 'Agent One',
            'StatutoryAgent2_Name': 'Agent Two',
            'StatutoryAgent3_Name': 'Agent Three',
        })
        names = extract_ecorp_names_from_complete(row)
        assert 'Agent One' in names
        assert 'Agent Two' in names
        assert 'Agent Three' in names

    def test_extracts_managers(self):
        """Should extract Manager1-5_Name fields."""
        row = pd.Series({
            'Manager1_Name': 'Manager One',
            'Manager2_Name': 'Manager Two',
        })
        names = extract_ecorp_names_from_complete(row)
        assert 'Manager One' in names
        assert 'Manager Two' in names

    def test_extracts_members(self):
        """Should extract Member1-5_Name fields."""
        row = pd.Series({
            'Member1_Name': 'Member One',
        })
        names = extract_ecorp_names_from_complete(row)
        assert 'Member One' in names

    def test_extracts_manager_members(self):
        """Should extract Manager/Member1-5_Name fields."""
        row = pd.Series({
            'Manager/Member1_Name': 'MM One',
        })
        names = extract_ecorp_names_from_complete(row)
        assert 'MM One' in names

    def test_extracts_individual_names(self):
        """Should extract IndividualName1-4 fields."""
        row = pd.Series({
            'IndividualName1': 'Individual One',
            'IndividualName2': 'Individual Two',
        })
        names = extract_ecorp_names_from_complete(row)
        assert 'Individual One' in names
        assert 'Individual Two' in names

    def test_deduplicates_names(self):
        """Same name in multiple fields should appear once."""
        row = pd.Series({
            'Manager1_Name': 'JOHN SMITH',
            'Member1_Name': 'John Smith',  # Same name, different case
        })
        names = extract_ecorp_names_from_complete(row)
        # Should only appear once (first occurrence)
        assert len([n for n in names if n.upper() == 'JOHN SMITH']) == 1

    def test_skips_empty_values(self):
        """Empty strings and NaN should be excluded."""
        row = pd.Series({
            'Manager1_Name': 'Valid Name',
            'Manager2_Name': '',
            'Manager3_Name': None,
        })
        names = extract_ecorp_names_from_complete(row)
        assert 'Valid Name' in names
        assert '' not in names
        assert len(names) == 1

    def test_empty_row(self):
        """Empty row should return empty list."""
        row = pd.Series({})
        names = extract_ecorp_names_from_complete(row)
        assert names == []


class TestExtractBatchNames:
    """Tests for extract_batch_names function."""

    def test_extracts_phone_names(self):
        """Should extract BD_PHONE_1-10_FIRST + BD_PHONE_1-10_LAST."""
        row = pd.Series({
            'BD_PHONE_1_FIRST': 'John',
            'BD_PHONE_1_LAST': 'Smith',
            'BD_PHONE_2_FIRST': 'Jane',
            'BD_PHONE_2_LAST': 'Doe',
        })
        names = extract_batch_names(row)
        assert 'John Smith' in names
        assert 'Jane Doe' in names

    def test_extracts_email_names(self):
        """Should extract BD_EMAIL_1-10_FIRST + BD_EMAIL_1-10_LAST."""
        row = pd.Series({
            'BD_EMAIL_1_FIRST': 'Bob',
            'BD_EMAIL_1_LAST': 'Jones',
        })
        names = extract_batch_names(row)
        assert 'Bob Jones' in names

    def test_concatenates_first_last(self):
        """'JOHN' + 'SMITH' should become 'JOHN SMITH'."""
        row = pd.Series({
            'BD_PHONE_1_FIRST': 'JOHN',
            'BD_PHONE_1_LAST': 'SMITH',
        })
        names = extract_batch_names(row)
        assert 'JOHN SMITH' in names

    def test_handles_first_only(self):
        """First name only should still be extracted."""
        row = pd.Series({
            'BD_PHONE_1_FIRST': 'John',
            'BD_PHONE_1_LAST': '',
        })
        names = extract_batch_names(row)
        assert 'John' in names

    def test_handles_last_only(self):
        """Last name only should still be extracted."""
        row = pd.Series({
            'BD_PHONE_1_FIRST': '',
            'BD_PHONE_1_LAST': 'Smith',
        })
        names = extract_batch_names(row)
        assert 'Smith' in names

    def test_deduplicates_names(self):
        """Same person across multiple phones should appear once."""
        row = pd.Series({
            'BD_PHONE_1_FIRST': 'John',
            'BD_PHONE_1_LAST': 'Smith',
            'BD_PHONE_2_FIRST': 'John',
            'BD_PHONE_2_LAST': 'Smith',
        })
        names = extract_batch_names(row)
        assert names.count('John Smith') == 1

    def test_skips_empty_pairs(self):
        """Pairs with both first and last empty should be skipped."""
        row = pd.Series({
            'BD_PHONE_1_FIRST': '',
            'BD_PHONE_1_LAST': '',
            'BD_PHONE_2_FIRST': 'John',
            'BD_PHONE_2_LAST': 'Smith',
        })
        names = extract_batch_names(row)
        assert len(names) == 1
        assert 'John Smith' in names


class TestCalculateMatchPercentage:
    """Tests for calculate_match_percentage function."""

    def test_empty_ecorp_names_returns_100(self):
        """No Ecorp names = trivial 100% match."""
        pct, missing = calculate_match_percentage([], ['John Smith'])
        assert pct == "100"
        assert missing == []

    def test_empty_batch_names_returns_zero(self):
        """No API names = 0% match, all Ecorp names missing."""
        pct, missing = calculate_match_percentage(['John Smith', 'Jane Doe'], [])
        assert pct == "0"
        assert 'John Smith' in missing
        assert 'Jane Doe' in missing

    def test_exact_match_returns_100(self):
        """Identical names = 100% match."""
        pct, missing = calculate_match_percentage(
            ['John Smith'],
            ['John Smith']
        )
        assert pct == "100"
        assert missing == []

    def test_partial_match_calculates_percentage(self):
        """1 of 2 names matching = 50%."""
        pct, missing = calculate_match_percentage(
            ['John Smith', 'Jane Doe'],
            ['John Smith']
        )
        assert pct == "50"
        assert 'Jane Doe' in missing
        assert 'John Smith' not in missing

    def test_100_plus_when_extras_from_batch(self):
        """100+ when all Ecorp matched AND Batchdata has extras."""
        pct, missing = calculate_match_percentage(
            ['John Smith'],
            ['John Smith', 'Jane Doe', 'Bob Jones']
        )
        assert pct == "100+"
        assert missing == []

    def test_unmatched_names_limited_to_8(self):
        """Only first 8 unmatched names returned."""
        ecorp_names = [f'Person {i}' for i in range(1, 12)]  # 11 names
        pct, missing = calculate_match_percentage(ecorp_names, [])
        assert len(missing) == 8

    def test_fuzzy_match_counts(self):
        """Names matching at 85%+ should count as matched."""
        pct, missing = calculate_match_percentage(
            ['JOHN D SMITH'],
            ['JOHN SMITH']
        )
        assert pct == "100"
        assert missing == []

    def test_both_empty(self):
        """Both empty = 100% (nothing to match)."""
        pct, missing = calculate_match_percentage([], [])
        assert pct == "100"
        assert missing == []


class TestApplyNameMatching:
    """Integration tests for apply_name_matching function."""

    def test_adds_all_nine_columns(self):
        """Should add ECORP_TO_BATCH_MATCH_% and MISSING_1-8_FULL_NAME."""
        batchdata_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST'],
            'BD_OWNER_NAME_FULL': ['John Smith'],
        })
        ecorp_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST'],
            'Manager1_Name': ['John Smith'],
        })

        result = apply_name_matching(batchdata_df, ecorp_df)

        assert 'ECORP_TO_BATCH_MATCH_%' in result.columns
        for i in range(1, 9):
            assert f'MISSING_{i}_FULL_NAME' in result.columns

    def test_preserves_existing_columns(self):
        """Original columns should remain unchanged."""
        batchdata_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST'],
            'BD_OWNER_NAME_FULL': ['John Smith'],
            'EXISTING_COL': ['value'],
        })
        ecorp_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST'],
        })

        result = apply_name_matching(batchdata_df, ecorp_df)

        assert 'EXISTING_COL' in result.columns
        assert result['EXISTING_COL'].iloc[0] == 'value'

    def test_handles_empty_dataframe(self):
        """Empty DataFrame should return empty with new columns."""
        batchdata_df = pd.DataFrame(columns=['FULL_ADDRESS'])
        ecorp_df = pd.DataFrame(columns=['FULL_ADDRESS'])

        result = apply_name_matching(batchdata_df, ecorp_df)

        assert 'ECORP_TO_BATCH_MATCH_%' in result.columns
        assert len(result) == 0

    def test_fallback_to_bd_owner_name(self):
        """When no Ecorp match, should use BD_OWNER_NAME_FULL."""
        batchdata_df = pd.DataFrame({
            'FULL_ADDRESS': ['999 UNKNOWN ST'],
            'BD_OWNER_NAME_FULL': ['Fallback Name'],
            'BD_PHONE_1_FIRST': ['Fallback'],
            'BD_PHONE_1_LAST': ['Name'],
        })
        ecorp_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 DIFFERENT ST'],
            'Manager1_Name': ['Other Person'],
        })

        result = apply_name_matching(batchdata_df, ecorp_df)

        # Should match Fallback Name to itself
        assert result['ECORP_TO_BATCH_MATCH_%'].iloc[0] == "100"

    def test_joins_on_full_address(self):
        """Should correctly join Batchdata to Ecorp on FULL_ADDRESS."""
        batchdata_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST', '456 OAK AVE'],
            'BD_PHONE_1_FIRST': ['John', 'Jane'],
            'BD_PHONE_1_LAST': ['Smith', 'Doe'],
        })
        ecorp_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST', '456 OAK AVE'],
            'Manager1_Name': ['John Smith', 'Jane Doe'],
        })

        result = apply_name_matching(batchdata_df, ecorp_df)

        # Both should be 100% match
        assert result['ECORP_TO_BATCH_MATCH_%'].iloc[0] == "100"
        assert result['ECORP_TO_BATCH_MATCH_%'].iloc[1] == "100"

    def test_populates_missing_columns(self):
        """Should populate MISSING columns when names not found."""
        batchdata_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST'],
            # No phone/email names - API returned nothing
        })
        ecorp_df = pd.DataFrame({
            'FULL_ADDRESS': ['123 MAIN ST'],
            'Manager1_Name': ['John Smith'],
            'Manager2_Name': ['Jane Doe'],
        })

        result = apply_name_matching(batchdata_df, ecorp_df)

        assert result['ECORP_TO_BATCH_MATCH_%'].iloc[0] == "0"
        assert result['MISSING_1_FULL_NAME'].iloc[0] == 'John Smith'
        assert result['MISSING_2_FULL_NAME'].iloc[0] == 'Jane Doe'
