"""Tests for transform module."""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from adhs_etl.transform import (
    FieldMapper,
    load_excel_workbook,
    normalize_provider_data,
    save_dataframes_to_excel,
)


class TestFieldMapper:
    """Test FieldMapper class."""

    def test_load_field_map(self, sample_field_map: Path, temp_dir: Path):
        """Test loading field map from YAML."""
        mapper = FieldMapper(sample_field_map, temp_dir / "todo.yml")
        assert len(mapper.field_map) == 7
        assert mapper.field_map["Provider Name"] == "name"
        assert mapper.field_map["License Number"] == "license_number"

    def test_load_missing_field_map(self, temp_dir: Path):
        """Test handling missing field map file."""
        mapper = FieldMapper(temp_dir / "missing.yml", temp_dir / "todo.yml")
        assert mapper.field_map == {}

    def test_map_columns(
        self, sample_field_map: Path, sample_provider_df: pd.DataFrame, temp_dir: Path
    ):
        """Test column mapping with known and unknown columns."""
        mapper = FieldMapper(sample_field_map, temp_dir / "todo.yml")

        # Map columns
        mapped_df = mapper.map_columns(sample_provider_df)

        # Check known columns were renamed
        assert "name" in mapped_df.columns
        assert "address" in mapped_df.columns
        assert "license_number" in mapped_df.columns

        # Check unknown column is preserved
        assert "Unknown Column" in mapped_df.columns

        # Check unknown columns were tracked
        assert "Unknown Column" in mapper.unknown_columns
        assert len(mapper.unknown_columns) == 1

    def test_save_unknown_columns(
        self, sample_field_map: Path, sample_provider_df: pd.DataFrame, temp_dir: Path
    ):
        """Test saving unknown columns to TODO file."""
        todo_path = temp_dir / "todo.yml"
        mapper = FieldMapper(sample_field_map, todo_path)

        # Map columns to detect unknown
        mapper.map_columns(sample_provider_df)

        # Save unknown columns
        mapper.save_unknown_columns(dry_run=False)

        # Check TODO file was created
        assert todo_path.exists()

        # Load and verify content
        with open(todo_path, "r") as f:
            todo_map = yaml.safe_load(f)

        assert "Unknown Column" in todo_map
        assert todo_map["Unknown Column"] is None

    def test_save_unknown_columns_dry_run(
        self, sample_field_map: Path, sample_provider_df: pd.DataFrame, temp_dir: Path
    ):
        """Test dry run doesn't save unknown columns."""
        todo_path = temp_dir / "todo.yml"
        mapper = FieldMapper(sample_field_map, todo_path)

        # Map columns to detect unknown
        mapper.map_columns(sample_provider_df)

        # Save with dry run
        mapper.save_unknown_columns(dry_run=True)

        # Check TODO file was NOT created
        assert not todo_path.exists()


class TestNormalizeProviderData:
    """Test data normalization functions."""

    def test_strip_whitespace(self):
        """Test whitespace stripping from string columns."""
        df = pd.DataFrame(
            {
                "name": ["  Test  ", "Provider  ", "  "],
                "number": [1, 2, 3],
            }
        )

        normalized = normalize_provider_data(df)

        # Check that whitespace was stripped and empty string became NA
        assert normalized["name"].iloc[0] == "Test"
        assert normalized["name"].iloc[1] == "Provider"
        assert pd.isna(normalized["name"].iloc[2])  # Empty string becomes NA
        assert normalized["number"].tolist() == [1, 2, 3]

    def test_standardize_empty_values(self):
        """Test standardization of empty/null values."""
        df = pd.DataFrame(
            {
                "col1": ["", "N/A", "n/a", "NA", "None", "Valid"],
                "col2": [1, 2, 3, 4, 5, 6],
            }
        )

        normalized = normalize_provider_data(df)

        # Check that empty values are converted to pd.NA
        assert pd.isna(normalized.loc[0, "col1"])
        assert pd.isna(normalized.loc[1, "col1"])
        assert pd.isna(normalized.loc[2, "col1"])
        assert pd.isna(normalized.loc[3, "col1"])
        assert pd.isna(normalized.loc[4, "col1"])
        assert normalized.loc[5, "col1"] == "Valid"

    def test_date_parsing(self):
        """Test automatic date parsing."""
        df = pd.DataFrame(
            {
                "license_date": ["2023-01-01", "2023-12-31", "invalid"],
                "expiry_date": ["2024-01-01", "2024-12-31", ""],
                "name": ["Provider 1", "Provider 2", "Provider 3"],
            }
        )

        normalized = normalize_provider_data(df)

        # Check date columns were parsed
        assert pd.api.types.is_datetime64_any_dtype(normalized["license_date"])
        assert pd.api.types.is_datetime64_any_dtype(normalized["expiry_date"])

        # Check invalid dates become NaT
        assert pd.isna(normalized.loc[2, "license_date"])


class TestExcelIO:
    """Test Excel file I/O functions."""

    def test_load_excel_workbook(self, sample_excel_file: Path):
        """Test loading Excel workbook with multiple sheets."""
        sheets = load_excel_workbook(sample_excel_file)

        assert len(sheets) == 2
        assert "Providers" in sheets
        assert "Summary" in sheets

        # Check provider sheet content
        providers_df = sheets["Providers"]
        assert len(providers_df) == 3
        assert "Provider Name" in providers_df.columns

    def test_load_missing_excel(self, temp_dir: Path):
        """Test error handling for missing Excel file."""
        with pytest.raises(Exception):
            load_excel_workbook(temp_dir / "missing.xlsx")

    def test_save_dataframes_to_excel(self, temp_dir: Path):
        """Test saving multiple dataframes to Excel."""
        output_path = temp_dir / "output.xlsx"

        dataframes = {
            "Sheet1": pd.DataFrame({"col1": [1, 2, 3]}),
            "Sheet2": pd.DataFrame({"col2": ["a", "b", "c"]}),
        }

        save_dataframes_to_excel(dataframes, output_path, dry_run=False)

        # Verify file exists
        assert output_path.exists()

        # Load and verify content
        loaded = load_excel_workbook(output_path)
        assert len(loaded) == 2
        assert list(loaded["Sheet1"]["col1"]) == [1, 2, 3]
        assert list(loaded["Sheet2"]["col2"]) == ["a", "b", "c"]

    def test_save_dataframes_dry_run(self, temp_dir: Path):
        """Test dry run doesn't create output file."""
        output_path = temp_dir / "output.xlsx"

        dataframes = {"Sheet1": pd.DataFrame({"col1": [1, 2, 3]})}

        save_dataframes_to_excel(dataframes, output_path, dry_run=True)

        # Verify file was NOT created
        assert not output_path.exists()
