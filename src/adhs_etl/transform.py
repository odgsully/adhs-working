"""Core transformation logic for ADHS ETL pipeline."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


class FieldMapper:
    """Handles field mapping and unknown column detection."""

    def __init__(self, field_map_path: Path, field_map_todo_path: Path):
        """Initialize with field mapping configuration."""
        self.field_map_path = field_map_path
        self.field_map_todo_path = field_map_todo_path
        self.field_map = self._load_field_map()
        self.unknown_columns: Set[str] = set()

    def _load_field_map(self) -> Dict[str, str]:
        """Load field mapping from YAML file."""
        if not self.field_map_path.exists():
            logger.warning(f"Field map not found at {self.field_map_path}")
            return {}
        
        with open(self.field_map_path, "r") as f:
            return yaml.safe_load(f) or {}

    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply field mapping to dataframe columns."""
        mapped_df = df.copy()
        
        # First, identify which target columns would have duplicates
        target_columns = {}
        for col in df.columns:
            if col in self.field_map:
                target = self.field_map[col]
                if target not in target_columns:
                    target_columns[target] = []
                target_columns[target].append(col)
        
        # For duplicates, choose the first non-empty column
        columns_to_keep = set(df.columns)
        new_columns = {}
        
        for target, source_cols in target_columns.items():
            if len(source_cols) > 1:
                # Multiple source columns map to same target
                logger.debug(f"Multiple columns map to '{target}': {source_cols}")
                
                # Find first non-empty column
                chosen_col = None
                for col in source_cols:
                    if not df[col].isna().all() and not (df[col] == '').all():
                        chosen_col = col
                        break
                
                # If no non-empty column found, use the first one
                if chosen_col is None:
                    chosen_col = source_cols[0]
                
                # Map the chosen column and drop the others
                new_columns[chosen_col] = target
                for col in source_cols:
                    if col != chosen_col:
                        columns_to_keep.discard(col)
                
                logger.info(f"For target '{target}', chose source column '{chosen_col}' from {source_cols}")
            else:
                # Single mapping
                new_columns[source_cols[0]] = target
        
        # Add unmapped columns
        for col in df.columns:
            if col in columns_to_keep and col not in new_columns:
                if col not in self.field_map:
                    # Track unknown columns
                    self.unknown_columns.add(col)
                    logger.warning(f"Unknown column encountered: {col}")
                new_columns[col] = col  # Keep original name
        
        # Drop columns we don't want to keep
        mapped_df = mapped_df[list(columns_to_keep)]
        
        # Rename columns
        mapped_df.rename(columns=new_columns, inplace=True)
        return mapped_df

    def save_unknown_columns(self, dry_run: bool = False) -> None:
        """Save unknown columns to TODO field map."""
        if not self.unknown_columns:
            return
        
        # Load existing TODO map
        todo_map = {}
        if self.field_map_todo_path.exists():
            with open(self.field_map_todo_path, "r") as f:
                todo_map = yaml.safe_load(f) or {}
        
        # Add new unknown columns
        for col in self.unknown_columns:
            if col not in todo_map:
                todo_map[col] = None  # Null mapping
        
        if not dry_run:
            with open(self.field_map_todo_path, "w") as f:
                yaml.dump(todo_map, f, default_flow_style=False, sort_keys=True)
            logger.info(f"Updated {self.field_map_todo_path} with {len(self.unknown_columns)} unknown columns")


def normalize_provider_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize provider data with standard transformations."""
    df = df.copy()
    
    # Strip whitespace from string columns
    string_cols = df.select_dtypes(include=["object"]).columns
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip()
    
    # Standardize empty values
    df.replace(["", "N/A", "n/a", "NA", "None"], pd.NA, inplace=True)
    
    # Ensure consistent date formatting if date columns exist
    date_cols = [col for col in df.columns if "date" in col.lower()]
    for col in date_cols:
        try:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        except Exception as e:
            logger.warning(f"Could not parse dates in column {col}: {e}")
    
    return df


def load_excel_workbook(file_path: Path) -> Dict[str, pd.DataFrame]:
    """Load all sheets from an Excel workbook."""
    try:
        xl_file = pd.ExcelFile(file_path)
        sheets = {}
        
        for sheet_name in xl_file.sheet_names:
            df = pd.read_excel(xl_file, sheet_name=sheet_name)
            sheets[sheet_name] = df
            logger.debug(f"Loaded sheet '{sheet_name}' with {len(df)} rows")
        
        return sheets
    except Exception as e:
        logger.error(f"Failed to load Excel file {file_path}: {e}")
        raise


def save_dataframes_to_excel(
    dataframes: Dict[str, pd.DataFrame],
    output_path: Path,
    dry_run: bool = False
) -> None:
    """Save multiple dataframes to an Excel workbook."""
    if dry_run:
        logger.info(f"[DRY RUN] Would save {len(dataframes)} sheets to {output_path}")
        return
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    logger.info(f"Saved {len(dataframes)} sheets to {output_path}")