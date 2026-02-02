"""Pytest configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pandas as pd
import pytest
import yaml


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_field_map(temp_dir: Path) -> Path:
    """Create a sample field mapping file."""
    field_map_path = temp_dir / "field_map.yml"
    field_map = {
        "Provider Name": "name",
        "Provider Address": "address",
        "Provider City": "city",
        "Provider State": "state",
        "Provider Zip": "zip_code",
        "License Number": "license_number",
        "License Type": "license_type",
    }

    with open(field_map_path, "w") as f:
        yaml.dump(field_map, f)

    return field_map_path


@pytest.fixture
def sample_provider_df() -> pd.DataFrame:
    """Create a sample provider dataframe."""
    data = {
        "Provider Name": ["Test Provider 1", "Test Provider 2", "Test Provider 3"],
        "Provider Address": ["123 Main St", "456 Oak Ave", "789 Pine Rd"],
        "Provider City": ["Phoenix", "Tempe", "Scottsdale"],
        "Provider State": ["AZ", "AZ", "AZ"],
        "Provider Zip": ["85001", "85281", "85251"],
        "License Number": ["LIC001", "LIC002", "LIC003"],
        "License Type": ["Type A", "Type B", "Type A"],
        "Unknown Column": ["Value1", "Value2", "Value3"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_excel_file(temp_dir: Path, sample_provider_df: pd.DataFrame) -> Path:
    """Create a sample Excel file with provider data."""
    excel_path = temp_dir / "sample_adhs_2025-05.xlsx"

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        sample_provider_df.to_excel(writer, sheet_name="Providers", index=False)
        # Add a second sheet
        pd.DataFrame({"test": [1, 2, 3]}).to_excel(
            writer, sheet_name="Summary", index=False
        )

    return excel_path
