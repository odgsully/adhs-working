"""
Utility functions for ADHS ETL pipeline.

Provides standardized timestamp generation and filename formatting
to ensure consistency across all pipeline stages.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd


def get_standard_timestamp() -> str:
    """Generate standard timestamp in MM.DD.HH-MM-SS format (12-hour).

    Returns:
        Timestamp string in format MM.DD.HH-MM-SS
        Example: "01.15.03-45-30" for Jan 15, 3:45:30

    Note:
        Uses 12-hour format (01-12) without AM/PM indicator.
        This format is used consistently across all pipeline outputs.
    """
    return datetime.now().strftime("%m.%d.%I-%M-%S")


def format_output_filename(month_code: str, stage: str, timestamp: str, extension: str = "xlsx") -> str:
    """Format output filename with standardized naming convention.

    Args:
        month_code: Month code in M.YY or MM.YY format (e.g., "1.25", "12.24")
        stage: Pipeline stage name (e.g., "Reformat", "Analysis", "MCAO_Upload")
        timestamp: Timestamp from get_standard_timestamp()
        extension: File extension without dot (default: "xlsx")

    Returns:
        Formatted filename: M.YY_{Stage}_{timestamp}.{extension}
        Example: "1.25_Reformat_01.15.03-45-30.xlsx"
    """
    return f"{month_code}_{stage}_{timestamp}.{extension}"


def get_legacy_filename(month_code: str, stage: str, timestamp: Optional[str] = None) -> str:
    """Get legacy format filename for backward compatibility.

    Args:
        month_code: Month code in M.YY or MM.YY format
        stage: Pipeline stage name
        timestamp: Optional timestamp (for stages that used timestamps in old format)

    Returns:
        Legacy format filename

    Examples:
        >>> get_legacy_filename("1.25", "Reformat")
        "1.25 Reformat.xlsx"
        >>> get_legacy_filename("1.25", "MCAO_Upload", "01.15.03-45-30")
        "1.25_MCAO_Upload 01.15.03-45-30.xlsx"
    """
    # Map stage names to legacy patterns
    legacy_patterns = {
        "Reformat": f"{month_code} Reformat.xlsx",
        "Reformat_All_to_Date": f"Reformat All to Date {month_code}.xlsx",
        "Analysis": f"{month_code} Analysis.xlsx",
    }

    # Stages that had timestamps with space before timestamp
    if stage in ["APN_Upload", "APN_Complete", "MCAO_Upload", "MCAO_Complete",
                  "Ecorp_Upload", "Ecorp_Complete"]:
        if timestamp:
            return f"{month_code}_{stage} {timestamp}.xlsx"
        else:
            # If no timestamp provided, just use the pattern without timestamp
            return f"{month_code}_{stage}.xlsx"

    # Stages without timestamps
    if stage in legacy_patterns:
        return legacy_patterns[stage]

    # Default: same as new format (shouldn't happen for well-defined stages)
    if timestamp:
        return f"{month_code}_{stage} {timestamp}.xlsx"
    else:
        return f"{month_code} {stage}.xlsx"


def save_with_legacy_copy(df: pd.DataFrame, new_path: Path, legacy_path: Path) -> None:
    """Save DataFrame to new path and create legacy copy for backward compatibility.

    Args:
        df: DataFrame to save
        new_path: Path for new naming convention
        legacy_path: Path for legacy naming convention

    Example:
        >>> df = pd.DataFrame({"col": [1, 2, 3]})
        >>> new_path = Path("output/1.25_Reformat_01.15.03-45-30.xlsx")
        >>> legacy_path = Path("output/1.25 Reformat.xlsx")
        >>> save_with_legacy_copy(df, new_path, legacy_path)
        # Creates both files
    """
    # Ensure parent directory exists
    new_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to new path
    df.to_excel(new_path, index=False)

    # Copy to legacy path
    shutil.copy2(new_path, legacy_path)


def save_excel_with_legacy_copy(writer_or_path, legacy_path: Path) -> None:
    """Save Excel file and create legacy copy (for ExcelWriter objects).

    Args:
        writer_or_path: ExcelWriter object that has been saved, or path to new file
        legacy_path: Path for legacy naming convention

    Note:
        This function should be called AFTER the ExcelWriter has been saved/closed.

    Example:
        >>> with pd.ExcelWriter(new_path) as writer:
        >>>     df1.to_excel(writer, sheet_name="Sheet1")
        >>>     df2.to_excel(writer, sheet_name="Sheet2")
        >>> save_excel_with_legacy_copy(new_path, legacy_path)
    """
    # If writer_or_path is an ExcelWriter, get its path
    if hasattr(writer_or_path, 'path'):
        source_path = Path(writer_or_path.path)
    else:
        source_path = Path(writer_or_path)

    # Ensure legacy parent directory exists
    legacy_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy to legacy path
    shutil.copy2(source_path, legacy_path)


def extract_timestamp_from_filename(filename: str) -> Optional[str]:
    """Extract timestamp from filename (handles both old and new formats).

    Args:
        filename: Filename to extract timestamp from

    Returns:
        Extracted timestamp string, or None if not found

    Examples:
        >>> extract_timestamp_from_filename("1.25_MCAO_Upload_01.15.03-45-30.xlsx")
        "01.15.03-45-30"
        >>> extract_timestamp_from_filename("1.25_MCAO_Upload 01.15.03-45-30.xlsx")
        "01.15.03-45-30"
        >>> extract_timestamp_from_filename("1.25 Reformat.xlsx")
        None
    """
    import re

    # Pattern for timestamp: MM.DD.HH-MM-SS
    timestamp_pattern = r'(\d{2}\.\d{2}\.\d{2}-\d{2}-\d{2})'

    match = re.search(timestamp_pattern, filename)
    if match:
        return match.group(1)

    return None


def extract_month_code_from_filename(filename: str) -> Optional[str]:
    """Extract month code from filename.

    Args:
        filename: Filename to extract month code from

    Returns:
        Extracted month code (M.YY or MM.YY), or None if not found

    Examples:
        >>> extract_month_code_from_filename("1.25_Reformat_01.15.03-45-30.xlsx")
        "1.25"
        >>> extract_month_code_from_filename("12.24_Analysis_01.15.03-45-30.xlsx")
        "12.24"
    """
    import re

    # Pattern for month code at start: M.YY or MM.YY
    month_pattern = r'^(\d{1,2}\.\d{2})'

    match = re.match(month_pattern, filename)
    if match:
        return match.group(1)

    return None
