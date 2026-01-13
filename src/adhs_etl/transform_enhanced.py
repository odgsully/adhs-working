"""Enhanced transformation logic for ADHS ETL pipeline with full analysis capabilities."""

import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import re
import gc
import os

# Optional import for memory monitoring
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

import pandas as pd
from rapidfuzz import fuzz

from .transform import FieldMapper, normalize_provider_data

logger = logging.getLogger(__name__)


def log_memory_usage(context: str = ""):
    """Log current memory usage if psutil is available."""
    if PSUTIL_AVAILABLE:
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Memory usage {context}: {memory_mb:.1f} MB")
        except Exception:
            pass  # Don't fail if psutil has issues
    # If psutil not available, just skip memory logging silently


def clear_memory():
    """Force garbage collection to free memory."""
    gc.collect()


def validate_data_completeness(df: pd.DataFrame, file_name: str) -> str:
    """Validate data completeness and return summary."""
    if df.empty:
        return "No data"

    _total_rows = len(df)  # noqa: F841 - reserved for future validation
    issues = []

    # Check critical fields
    critical_fields = ["PROVIDER", "ADDRESS", "ZIP"]
    for field in critical_fields:
        if field in df.columns:
            empty_count = df[field].isna().sum() + (df[field] == "").sum()
            if empty_count > 0:
                issues.append(f"{field}:{empty_count}")

    # Special validation for PROVIDER field to detect if it contains codes instead of names
    if "PROVIDER" in df.columns:
        provider_sample = df["PROVIDER"].dropna().head(3).astype(str).tolist()
        code_like_count = sum(
            1 for val in provider_sample if val.isdigit() or len(val) < 5
        )
        if (
            code_like_count > len(provider_sample) * 0.5
        ):  # More than 50% look like codes
            logger.warning(
                f"PROVIDER field in {file_name} may contain codes instead of names. Sample: {provider_sample}"
            )

    # Check coordinate fields (less critical)
    coord_fields = ["LONGITUDE", "LATITUDE"]
    coord_missing = 0
    for field in coord_fields:
        if field in df.columns:
            coord_missing += df[field].isna().sum()

    if coord_missing > 0:
        issues.append(f"Coordinates:{coord_missing//2}")

    if issues:
        return f"Missing: {', '.join(issues)}"
    else:
        return "Complete data"


class EnhancedFieldMapper(FieldMapper):
    """Enhanced field mapper with uppercase transformation."""

    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply field mapping and uppercase transformation."""
        # First apply standard mapping
        mapped_df = super().map_columns(df)

        # Check if we have a valid DataFrame with columns
        if mapped_df is None or mapped_df.empty or len(mapped_df.columns) == 0:
            return mapped_df

        # Convert all string columns to uppercase
        for col in mapped_df.columns:
            try:
                if mapped_df[col].dtype == "object":
                    mapped_df[col] = mapped_df[col].astype(str).str.upper()
            except Exception as e:
                logger.warning(f"Error converting column {col} to uppercase: {e}")
                continue

        return mapped_df


class ProviderGrouper:
    """Enhanced provider grouping with address and name matching."""

    def __init__(self, name_threshold: float = 85.0):
        """Initialize with thresholds."""
        self.name_threshold = name_threshold
        self.address_match_length = 20

    def group_providers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group providers by both address matching and name fuzzy matching - optimized version."""
        if df.empty:
            return df

        df = df.copy()
        log_memory_usage("start of group_providers")

        # Get unique combinations of provider and address
        unique_providers = (
            df[["PROVIDER", "ADDRESS"]].drop_duplicates().reset_index(drop=True)
        )
        n_unique = len(unique_providers)
        logger.info(f"Grouping {n_unique} unique provider-address combinations")

        # Initialize group assignments
        group_assignments = {}
        current_group = 1

        # Create address prefix for fast matching
        unique_providers["ADDR_PREFIX"] = (
            unique_providers["ADDRESS"].fillna("").astype(str).str[:20]
        )

        # Process in batches to avoid memory issues
        batch_size = 100
        for start_idx in range(0, n_unique, batch_size):
            end_idx = min(start_idx + batch_size, n_unique)
            _batch = unique_providers.iloc[
                start_idx:end_idx
            ]  # noqa: F841 - batch bounds checking

            for idx in range(start_idx, end_idx):
                if idx in group_assignments:
                    continue

                provider_row = unique_providers.iloc[idx]
                addr_prefix = provider_row["ADDR_PREFIX"]
                provider_name = (
                    str(provider_row["PROVIDER"])
                    if pd.notna(provider_row["PROVIDER"])
                    else ""
                )

                # Find all matching addresses (vectorized)
                if addr_prefix:
                    addr_matches = unique_providers.index[
                        (unique_providers.index > idx)
                        & (unique_providers["ADDR_PREFIX"] == addr_prefix)
                        & (~unique_providers.index.isin(group_assignments))
                    ].tolist()
                else:
                    addr_matches = []

                # Check name similarity only for non-address matches (more selective)
                remaining_indices = [
                    i
                    for i in range(idx + 1, n_unique)
                    if i not in group_assignments and i not in addr_matches
                ]

                name_matches = []
                if provider_name and remaining_indices:
                    # Check name similarity in small batches
                    for i in remaining_indices[
                        :20
                    ]:  # Limit to first 20 to avoid excessive computation
                        other_name = (
                            str(unique_providers.iloc[i]["PROVIDER"])
                            if pd.notna(unique_providers.iloc[i]["PROVIDER"])
                            else ""
                        )
                        if (
                            other_name
                            and fuzz.ratio(provider_name, other_name)
                            >= self.name_threshold
                        ):
                            name_matches.append(i)

                # Combine all matches
                all_matches = [idx] + addr_matches + name_matches

                # Assign group to all matches
                for match_idx in all_matches:
                    group_assignments[match_idx] = current_group

                current_group += 1

            # Clear memory periodically
            if start_idx % 500 == 0:
                clear_memory()

        # Create a mapping dataframe
        unique_providers["GROUP_ID"] = unique_providers.index.map(group_assignments)

        # Handle any remaining ungrouped providers
        ungrouped_mask = unique_providers["GROUP_ID"].isna()
        if ungrouped_mask.any():
            n_ungrouped = ungrouped_mask.sum()
            unique_providers.loc[ungrouped_mask, "GROUP_ID"] = range(
                current_group, current_group + n_ungrouped
            )
            current_group += n_ungrouped

        # Merge back to original dataframe using vectorized operation
        df = df.merge(
            unique_providers[["PROVIDER", "ADDRESS", "GROUP_ID"]],
            on=["PROVIDER", "ADDRESS"],
            how="left",
        )
        df.rename(columns={"GROUP_ID": "PROVIDER GROUP INDEX #"}, inplace=True)

        # Ensure integer type
        df["PROVIDER GROUP INDEX #"] = df["PROVIDER GROUP INDEX #"].astype(int)

        logger.info(f"Created {current_group - 1} provider groups")
        log_memory_usage("end of group_providers")

        return df


def extract_month_year_from_path(path: Path) -> Tuple[int, int]:
    """Extract month and year from folder name like 'Raw 1.25' or filename."""
    # Try to match pattern like "1.25" or "12.24"
    pattern = r"(\d{1,2})\.(\d{2})"
    match = re.search(pattern, str(path))

    if match:
        month = int(match.group(1))
        year = 2000 + int(match.group(2))  # Convert 25 to 2025
        return month, year

    # Default to current month/year if not found
    now = datetime.now()
    return now.month, now.year


def process_month_data(
    raw_path: Path,
    field_mapper: EnhancedFieldMapper,
    provider_grouper: ProviderGrouper,
    month: Optional[int] = None,
    year: Optional[int] = None,
    batch_size: int = 1000,
) -> pd.DataFrame:
    """Process all Excel files for a single month with memory management."""
    log_memory_usage("at start of process_month_data")

    # Determine month/year if not provided
    if month is None or year is None:
        month, year = extract_month_year_from_path(raw_path)

    # Get all Excel files
    excel_files = list(raw_path.glob("*.xlsx"))
    logger.info(f"Processing {len(excel_files)} files for {month}/{year}")

    # Process files one at a time to reduce memory usage
    all_processed_data = []

    for idx, file_path in enumerate(excel_files):
        try:
            logger.info(f"Processing file {idx+1}/{len(excel_files)}: {file_path.name}")
            log_memory_usage(f"before processing {file_path.name}")

            # Process each sheet separately
            with pd.ExcelFile(file_path) as xl_file:
                for sheet_name in xl_file.sheet_names:
                    # Read in chunks if file is large
                    df = pd.read_excel(xl_file, sheet_name=sheet_name)

                    if df.empty:
                        continue

                    # Add metadata columns
                    df["MONTH"] = month
                    df["YEAR"] = year
                    df["PROVIDER TYPE"] = file_path.stem  # Filename without extension

                    # Apply field mapping
                    df_mapped = field_mapper.map_columns(df)
                    del df  # Free original dataframe

                    # Normalize data
                    df_normalized = normalize_provider_data(df_mapped)
                    del df_mapped  # Free mapped dataframe

                    # Ensure required columns exist and debug missing data
                    # Note: FULL_ADDRESS will be created later after all data is combined
                    required_cols = [
                        "MONTH",
                        "YEAR",
                        "PROVIDER TYPE",
                        "PROVIDER",
                        "ADDRESS",
                        "CITY",
                        "ZIP",
                        "CAPACITY",
                        "LONGITUDE",
                        "LATITUDE",
                        "COUNTY",
                    ]

                    # Debug: Log available columns for troubleshooting
                    available_cols = list(df_normalized.columns)
                    logger.debug(
                        f"Available columns in {file_path.name}: {available_cols}"
                    )

                    for col in required_cols:
                        if col not in df_normalized.columns:
                            # Try to find data in unmapped columns before defaulting to empty
                            found_data = False

                            if col == "PROVIDER":
                                # Look for provider name columns with priority order
                                # Priority 1: Explicit name columns
                                name_priority_patterns = [
                                    "facility_name",
                                    "account name",
                                    "provider_name",
                                    "organization_name",
                                ]
                                for pattern in name_priority_patterns:
                                    for potential_col in available_cols:
                                        if pattern.replace(
                                            "_", ""
                                        ) in potential_col.lower().replace(
                                            "_", ""
                                        ).replace(
                                            " ", ""
                                        ):
                                            if (
                                                not df_normalized[potential_col]
                                                .isna()
                                                .all()
                                            ):
                                                # Verify this isn't an ID column by checking sample values
                                                sample_value = (
                                                    str(
                                                        df_normalized[potential_col]
                                                        .dropna()
                                                        .iloc[0]
                                                    )
                                                    if not df_normalized[potential_col]
                                                    .dropna()
                                                    .empty
                                                    else ""
                                                )
                                                if sample_value and not (
                                                    sample_value.isdigit()
                                                    or len(sample_value) < 5
                                                ):
                                                    df_normalized[col] = df_normalized[
                                                        potential_col
                                                    ]
                                                    logger.info(
                                                        f"Mapped {potential_col} -> {col} for {file_path.name} (Priority: Name column)"
                                                    )
                                                    found_data = True
                                                    break
                                    if found_data:
                                        break

                                # Priority 2: If no name column found, look for other patterns (excluding ID/TYPE columns)
                                if not found_data:
                                    exclude_patterns = ["id", "type", "number", "code"]
                                    for potential_col in available_cols:
                                        col_lower = potential_col.lower()
                                        # Must contain name-like patterns AND not contain exclusion patterns
                                        if any(
                                            pattern in col_lower
                                            for pattern in [
                                                "name",
                                                "account",
                                                "provider",
                                            ]
                                        ) and not any(
                                            exclude in col_lower
                                            for exclude in exclude_patterns
                                        ):
                                            if (
                                                not df_normalized[potential_col]
                                                .isna()
                                                .all()
                                            ):
                                                # Double-check sample value isn't just a code
                                                sample_value = (
                                                    str(
                                                        df_normalized[potential_col]
                                                        .dropna()
                                                        .iloc[0]
                                                    )
                                                    if not df_normalized[potential_col]
                                                    .dropna()
                                                    .empty
                                                    else ""
                                                )
                                                if sample_value and not (
                                                    sample_value.isdigit()
                                                    or len(sample_value) < 4
                                                ):
                                                    df_normalized[col] = df_normalized[
                                                        potential_col
                                                    ]
                                                    logger.info(
                                                        f"Mapped {potential_col} -> {col} for {file_path.name} (Secondary: Non-ID column)"
                                                    )
                                                    found_data = True
                                                    break

                            elif col == "ADDRESS":
                                # Look for address patterns
                                for potential_col in available_cols:
                                    if any(
                                        pattern in potential_col.lower()
                                        for pattern in ["address", "street", "physical"]
                                    ):
                                        # Accept address columns that contain 'street', 'address', or 'physical' patterns
                                        if (
                                            any(
                                                addr_pattern in potential_col.lower()
                                                for addr_pattern in [
                                                    "street",
                                                    "address",
                                                    "physical",
                                                ]
                                            )
                                            and not df_normalized[potential_col]
                                            .isna()
                                            .all()
                                        ):
                                            df_normalized[col] = df_normalized[
                                                potential_col
                                            ]
                                            logger.info(
                                                f"Mapped {potential_col} -> {col} for {file_path.name}"
                                            )
                                            found_data = True
                                            break

                            elif col == "ZIP":
                                # Look for ZIP patterns
                                for potential_col in available_cols:
                                    if any(
                                        pattern in potential_col.lower()
                                        for pattern in ["zip", "postal"]
                                    ):
                                        if (
                                            not df_normalized[potential_col]
                                            .isna()
                                            .all()
                                        ):
                                            df_normalized[col] = df_normalized[
                                                potential_col
                                            ]
                                            logger.info(
                                                f"Mapped {potential_col} -> {col} for {file_path.name}"
                                            )
                                            found_data = True
                                            break

                            elif col == "LONGITUDE":
                                # Look for longitude patterns
                                for potential_col in available_cols:
                                    if any(
                                        pattern in potential_col.lower()
                                        for pattern in ["lon", "lng", "longitude"]
                                    ):
                                        if (
                                            not df_normalized[potential_col]
                                            .isna()
                                            .all()
                                        ):
                                            df_normalized[col] = df_normalized[
                                                potential_col
                                            ]
                                            logger.info(
                                                f"Mapped {potential_col} -> {col} for {file_path.name}"
                                            )
                                            found_data = True
                                            break

                            elif col == "LATITUDE":
                                # Look for latitude patterns
                                for potential_col in available_cols:
                                    if any(
                                        pattern in potential_col.lower()
                                        for pattern in ["lat", "latitude"]
                                    ):
                                        if (
                                            not df_normalized[potential_col]
                                            .isna()
                                            .all()
                                        ):
                                            df_normalized[col] = df_normalized[
                                                potential_col
                                            ]
                                            logger.info(
                                                f"Mapped {potential_col} -> {col} for {file_path.name}"
                                            )
                                            found_data = True
                                            break

                            elif col == "CAPACITY":
                                # Look for capacity patterns
                                for potential_col in available_cols:
                                    if any(
                                        pattern in potential_col.lower()
                                        for pattern in ["capacity", "licensed", "beds"]
                                    ):
                                        if (
                                            not df_normalized[potential_col]
                                            .isna()
                                            .all()
                                        ):
                                            df_normalized[col] = df_normalized[
                                                potential_col
                                            ]
                                            logger.info(
                                                f"Mapped {potential_col} -> {col} for {file_path.name}"
                                            )
                                            found_data = True
                                            break

                            elif col == "CITY":
                                # Look for city patterns
                                for potential_col in available_cols:
                                    if any(
                                        pattern in potential_col.lower()
                                        for pattern in ["city", "physical_city"]
                                    ):
                                        if (
                                            not df_normalized[potential_col]
                                            .isna()
                                            .all()
                                        ):
                                            df_normalized[col] = df_normalized[
                                                potential_col
                                            ]
                                            logger.info(
                                                f"Mapped {potential_col} -> {col} for {file_path.name}"
                                            )
                                            found_data = True
                                            break

                            elif col == "COUNTY":
                                # Look for county patterns
                                for potential_col in available_cols:
                                    if any(
                                        pattern in potential_col.lower()
                                        for pattern in ["county", "physical_county"]
                                    ):
                                        if (
                                            not df_normalized[potential_col]
                                            .isna()
                                            .all()
                                        ):
                                            df_normalized[col] = df_normalized[
                                                potential_col
                                            ]
                                            logger.info(
                                                f"Mapped {potential_col} -> {col} for {file_path.name}"
                                            )
                                            found_data = True
                                            break

                            # If no data found, set to appropriate default
                            if not found_data:
                                if col in ["LONGITUDE", "LATITUDE", "CAPACITY"]:
                                    df_normalized[col] = (
                                        pd.NA
                                    )  # Use pandas NA for numeric columns
                                else:
                                    df_normalized[col] = ""
                                if col not in [
                                    "MONTH",
                                    "YEAR",
                                    "PROVIDER TYPE",
                                ]:  # Don't warn for metadata columns
                                    logger.warning(
                                        f"No data found for {col} in {file_path.name}"
                                    )

                    # Select only required columns
                    df_final = df_normalized[required_cols].copy()
                    del df_normalized  # Free normalized dataframe

                    all_processed_data.append(df_final)

                    # Validate data completeness
                    validation_results = validate_data_completeness(
                        df_final, file_path.name
                    )
                    logger.info(
                        f"  Processed {sheet_name}: {len(df_final)} rows - {validation_results}"
                    )

            # Clear memory after each file
            clear_memory()
            log_memory_usage(f"after processing {file_path.name}")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue

    if all_processed_data:
        logger.info("Combining all processed data...")
        log_memory_usage("before concatenation")

        # Combine in batches if there are many dataframes
        if len(all_processed_data) > 10:
            combined_df = pd.DataFrame()
            for i in range(0, len(all_processed_data), 5):
                batch = all_processed_data[i : i + 5]
                batch_df = pd.concat(batch, ignore_index=True)
                combined_df = pd.concat([combined_df, batch_df], ignore_index=True)
                del batch_df
                clear_memory()
        else:
            combined_df = pd.concat(all_processed_data, ignore_index=True)

        # Clear the list of dataframes
        all_processed_data.clear()
        clear_memory()
        log_memory_usage("after concatenation")

        # Apply provider grouping
        logger.info("Applying provider grouping...")
        combined_df = provider_grouper.group_providers(combined_df)

        # Convert all to uppercase more efficiently
        logger.info("Converting to uppercase...")
        string_cols = combined_df.select_dtypes(include=["object"]).columns
        for col in string_cols:
            combined_df[col] = combined_df[col].astype(str).str.upper()

        # Create FULL_ADDRESS column (Column M in Reformat)
        logger.info("Creating FULL_ADDRESS column...")
        if all(col in combined_df.columns for col in ["ADDRESS", "CITY", "ZIP"]):

            def build_full_address(row):
                parts = []
                addr = str(row.get("ADDRESS", "")).strip()
                city = str(row.get("CITY", "")).strip()

                # Convert ZIP from float to int to remove .0 suffix
                zip_raw = row.get("ZIP", "")
                try:
                    zip_code = str(int(float(zip_raw))).strip()
                except (ValueError, TypeError):
                    zip_code = str(zip_raw).strip()

                if addr and addr.upper() not in ("NAN", "NONE", ""):
                    parts.append(addr)
                if city and city.upper() not in ("NAN", "NONE", ""):
                    parts.append(city)

                # Add "AZ ZIP" as a single part (no comma between state and ZIP)
                if zip_code and zip_code.upper() not in ("NAN", "NONE", ""):
                    if city or addr:  # Only add AZ+ZIP if we have address components
                        parts.append(f"AZ {zip_code}")
                    else:
                        parts.append(zip_code)

                return ", ".join(parts) if parts else ""

            combined_df["FULL_ADDRESS"] = combined_df.apply(build_full_address, axis=1)
            logger.info(
                f"FULL_ADDRESS created for {combined_df['FULL_ADDRESS'].notna().sum()} records"
            )
        else:
            logger.warning(
                "Cannot create FULL_ADDRESS - missing required columns (ADDRESS, CITY, or ZIP)"
            )
            combined_df["FULL_ADDRESS"] = ""

        # Reorder columns to ensure proper layout:
        # Columns A-L: MONTH, YEAR, PROVIDER TYPE, PROVIDER, ADDRESS, CITY, ZIP, CAPACITY, LONGITUDE, LATITUDE, COUNTY, PROVIDER GROUP INDEX #
        # Column M: FULL_ADDRESS
        desired_order = [
            "MONTH",
            "YEAR",
            "PROVIDER TYPE",
            "PROVIDER",
            "ADDRESS",
            "CITY",
            "ZIP",
            "CAPACITY",
            "LONGITUDE",
            "LATITUDE",
            "COUNTY",
            "PROVIDER GROUP INDEX #",
            "FULL_ADDRESS",
        ]

        # Keep desired columns in order, then append any extra columns
        existing_desired = [col for col in desired_order if col in combined_df.columns]
        other_cols = [col for col in combined_df.columns if col not in desired_order]
        combined_df = combined_df[existing_desired + other_cols]

        logger.info(f"Column order set: {', '.join(combined_df.columns[:15])}")

        # Final validation summary
        final_validation = validate_data_completeness(combined_df, "FINAL_OUTPUT")
        logger.info(f"Final data validation: {final_validation}")

        # Log summary by provider type
        provider_type_summary = (
            combined_df.groupby("PROVIDER TYPE")
            .agg(
                {
                    "PROVIDER": lambda x: (x.isna() | (x == "")).sum(),
                    "ADDRESS": lambda x: (x.isna() | (x == "")).sum(),
                    "ZIP": lambda x: (x.isna() | (x == "")).sum(),
                    "LONGITUDE": lambda x: x.isna().sum(),
                    "LATITUDE": lambda x: x.isna().sum(),
                }
            )
            .reset_index()
        )

        for _, row in provider_type_summary.iterrows():
            provider_type = row["PROVIDER TYPE"]
            missing_fields = []
            if row["PROVIDER"] > 0:
                missing_fields.append(f"PROVIDER:{row['PROVIDER']}")
            if row["ADDRESS"] > 0:
                missing_fields.append(f"ADDRESS:{row['ADDRESS']}")
            if row["ZIP"] > 0:
                missing_fields.append(f"ZIP:{row['ZIP']}")
            if row["LONGITUDE"] > 0:
                missing_fields.append(f"COORDS:{row['LONGITUDE']}")

            if missing_fields:
                logger.warning(f"{provider_type}: Missing {', '.join(missing_fields)}")
            else:
                logger.info(f"{provider_type}: Complete data")

        log_memory_usage("at end of process_month_data")
        return combined_df

    return pd.DataFrame()


def create_reformat_output(
    df: pd.DataFrame, month: int, year: int, output_dir: Path
) -> Path:
    """Create the M.YY Reformat.xlsx file."""
    # Format month for filename
    if month >= 10:
        filename = f"{month}.{year % 100} Reformat.xlsx"
    else:
        filename = f"{month}.{year % 100} Reformat.xlsx"

    output_path = output_dir / filename

    # Ensure MONTH and YEAR are integers
    df["MONTH"] = df["MONTH"].astype(int)
    df["YEAR"] = df["YEAR"].astype(int)

    # Ensure output directory exists and is visible
    import os

    output_dir.mkdir(exist_ok=True)

    # Save with proper formatting
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)

        # Format MONTH and YEAR columns as numbers
        worksheet = writer.sheets["Sheet1"]
        for col in ["A", "B"]:  # MONTH and YEAR columns
            for cell in worksheet[col][1:]:  # Skip header
                cell.number_format = "0"

    # Ensure file is visible and accessible
    try:
        # Set file permissions to be readable/writable by owner and readable by others
        os.chmod(output_path, 0o644)
        # Also ensure the directory is accessible
        os.chmod(output_dir, 0o755)
        logger.info(f"Set file permissions for {output_path}")

        # Remove any extended attributes that might make the file hidden
        try:
            # Remove quarantine and other extended attributes on macOS
            import subprocess

            subprocess.run(
                ["xattr", "-c", str(output_path)], check=False, capture_output=True
            )
            logger.info(f"Cleared extended attributes for {output_path}")
        except Exception:
            pass  # Not critical if this fails

    except Exception as e:
        logger.warning(f"Could not set permissions for {output_path}: {e}")

    logger.info(f"Created Reformat file: {output_path}")
    return output_path


def rebuild_all_to_date_from_monthly_files(
    all_months_dir: Path,
    month: int,
    year: int,
    all_to_date_dir: Path,
    chunk_size: int = 5000,
) -> Path:
    """Rebuild the All to Date file from scratch using all monthly files."""
    log_memory_usage("start of rebuild_all_to_date_from_monthly_files")

    # Create output filename
    if month >= 10:
        filename = f"Reformat All to Date {month}.{year % 100}.xlsx"
    else:
        filename = f"Reformat All to Date {month}.{year % 100}.xlsx"

    output_path = all_to_date_dir / filename

    # Find all monthly Excel files
    monthly_files = []
    for month_dir in all_months_dir.iterdir():
        if month_dir.is_dir() and re.match(r"\d{1,2}\.\d{2}", month_dir.name):
            # Look for Excel files in this month directory
            for excel_file in month_dir.glob("*.xlsx"):
                if not excel_file.name.startswith("~"):  # Skip temp files
                    monthly_files.append(excel_file)

    if not monthly_files:
        logger.warning("No monthly files found to rebuild All to Date")
        return None

    logger.info(f"Found {len(monthly_files)} monthly files to process")

    # Process monthly files in batches to avoid memory issues
    all_monthly_data = []

    for file_path in monthly_files:
        try:
            logger.info(f"Processing monthly file: {file_path}")

            # Read the file
            df = pd.read_excel(file_path, sheet_name="Sheet1")

            if df.empty:
                continue

            # Ensure required columns exist
            required_cols = [
                "MONTH",
                "YEAR",
                "PROVIDER TYPE",
                "PROVIDER",
                "ADDRESS",
                "CITY",
                "ZIP",
                "CAPACITY",
                "LONGITUDE",
                "LATITUDE",
            ]

            # Check if this is a Reformat file (has all required columns)
            if all(col in df.columns for col in required_cols):
                # Extract month/year from filename or data
                if "MONTH" in df.columns and "YEAR" in df.columns:
                    # Use month/year from data
                    all_monthly_data.append(df)
                    logger.info(f"Added {len(df)} rows from {file_path.name}")
                else:
                    logger.warning(
                        f"Skipping {file_path.name} - missing MONTH/YEAR columns"
                    )
            else:
                logger.warning(f"Skipping {file_path.name} - not a Reformat file")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue

    if not all_monthly_data:
        logger.warning("No valid monthly data found")
        return None

    # Combine all monthly data
    logger.info("Combining all monthly data...")
    log_memory_usage("before combining monthly data")

    # Combine in batches
    if len(all_monthly_data) > 10:
        combined_df = pd.DataFrame()
        for i in range(0, len(all_monthly_data), 5):
            batch = all_monthly_data[i : i + 5]
            batch_df = pd.concat(batch, ignore_index=True)
            combined_df = pd.concat([combined_df, batch_df], ignore_index=True)
            del batch_df
            clear_memory()
    else:
        combined_df = pd.concat(all_monthly_data, ignore_index=True)

    # Clear the list
    all_monthly_data.clear()
    clear_memory()

    # Remove duplicates (same provider, address, month, year)
    logger.info("Removing duplicates...")
    combined_df = combined_df.drop_duplicates(
        subset=["MONTH", "YEAR", "PROVIDER TYPE", "PROVIDER", "ADDRESS"], keep="first"
    )

    # Sort by year, month, provider type
    logger.info("Sorting combined data...")
    combined_df = combined_df.sort_values(["YEAR", "MONTH", "PROVIDER TYPE"])

    # Ensure output directory exists and is visible
    all_to_date_dir.mkdir(exist_ok=True)

    # Save with formatting
    logger.info(f"Writing {len(combined_df)} rows to {output_path}")
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        combined_df.to_excel(writer, sheet_name="Sheet1", index=False)

        # Format MONTH and YEAR columns as numbers
        worksheet = writer.sheets["Sheet1"]
        for col in ["A", "B"]:  # MONTH and YEAR columns
            for cell in worksheet[col][1:]:  # Skip header
                cell.number_format = "0"

    # Ensure file is visible and accessible
    try:
        # Set file permissions to be readable/writable by owner and readable by others
        os.chmod(output_path, 0o644)
        # Also ensure the directory is accessible
        os.chmod(all_to_date_dir, 0o755)
        logger.info(f"Set file permissions for {output_path}")

        # Remove any extended attributes that might make the file hidden
        try:
            # Remove quarantine and other extended attributes on macOS
            import subprocess

            subprocess.run(
                ["xattr", "-c", str(output_path)], check=False, capture_output=True
            )
            logger.info(f"Cleared extended attributes for {output_path}")
        except Exception:
            pass  # Not critical if this fails

    except Exception as e:
        logger.warning(f"Could not set permissions for {output_path}: {e}")

    logger.info(
        f"Rebuilt All to Date file: {output_path} with {len(combined_df)} total rows"
    )
    log_memory_usage("end of rebuild_all_to_date_from_monthly_files")

    # Clear the combined dataframe
    del combined_df
    clear_memory()

    return output_path


def create_all_to_date_output(
    new_df: pd.DataFrame,
    month: int,
    year: int,
    all_to_date_dir: Path,
    chunk_size: int = 5000,
) -> Path:
    """Create or update the Reformat All to Date M.YY file with memory optimization."""
    log_memory_usage("start of create_all_to_date_output")

    # Look for most recent All to Date file
    existing_files = list(all_to_date_dir.glob("Reformat All to Date *.xlsx"))

    # Create output filename
    if month >= 10:
        filename = f"Reformat All to Date {month}.{year % 100}.xlsx"
    else:
        filename = f"Reformat All to Date {month}.{year % 100}.xlsx"

    output_path = all_to_date_dir / filename

    if existing_files:
        # Sort by modification time to get most recent
        latest_file = max(existing_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Found existing All to Date file: {latest_file}")

        # Read the entire file at once instead of chunks to avoid data loss
        logger.info("Reading existing data...")
        try:
            existing_df = pd.read_excel(latest_file, sheet_name="Sheet1")
            logger.info(f"Read {len(existing_df)} rows from existing file")

            # Remove records for current month/year to avoid duplicates
            existing_df = existing_df[
                ~((existing_df["MONTH"] == month) & (existing_df["YEAR"] == year))
            ]
            logger.info(f"After removing current month data: {len(existing_df)} rows")

            # Combine existing data with new data
            logger.info("Combining existing and new data...")
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            del existing_df
            clear_memory()

        except Exception as e:
            logger.error(f"Error reading existing file {latest_file}: {e}")
            logger.info("Using only new data")
            combined_df = new_df.copy()
    else:
        logger.info("No existing All to Date file found, using only new data")
        combined_df = new_df.copy()

    # Sort by year, month, provider type
    logger.info("Sorting combined data...")
    combined_df = combined_df.sort_values(["YEAR", "MONTH", "PROVIDER TYPE"])

    # Ensure output directory exists and is visible
    all_to_date_dir.mkdir(exist_ok=True)

    # Save with formatting
    logger.info(f"Writing {len(combined_df)} rows to {output_path}")
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        combined_df.to_excel(writer, sheet_name="Sheet1", index=False)

        # Format MONTH and YEAR columns as numbers
        worksheet = writer.sheets["Sheet1"]
        for col in ["A", "B"]:  # MONTH and YEAR columns
            for cell in worksheet[col][1:]:  # Skip header
                cell.number_format = "0"

    # Ensure file is visible and accessible
    try:
        # Set file permissions to be readable/writable by owner and readable by others
        os.chmod(output_path, 0o644)
        # Also ensure the directory is accessible
        os.chmod(all_to_date_dir, 0o755)
        logger.info(f"Set file permissions for {output_path}")

        # Remove any extended attributes that might make the file hidden
        try:
            # Remove quarantine and other extended attributes on macOS
            import subprocess

            subprocess.run(
                ["xattr", "-c", str(output_path)], check=False, capture_output=True
            )
            logger.info(f"Cleared extended attributes for {output_path}")
        except Exception:
            pass  # Not critical if this fails

    except Exception as e:
        logger.warning(f"Could not set permissions for {output_path}: {e}")

    logger.info(
        f"Created All to Date file: {output_path} with {len(combined_df)} total rows"
    )
    log_memory_usage("end of create_all_to_date_output")

    # Clear the combined dataframe
    del combined_df
    clear_memory()

    return output_path
