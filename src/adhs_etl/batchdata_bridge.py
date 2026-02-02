"""
batchdata_bridge.py - Integration between ADHS ETL and BatchData pipeline

Provides functions to create BatchData Upload files from Ecorp Complete data
and orchestrate the BatchData enrichment process with standardized naming.
"""

import sys
from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import shutil

# Add Batchdata to path for imports (as a package)
batchdata_path = Path(__file__).parent.parent.parent / "Batchdata"
sys.path.insert(0, str(batchdata_path))

try:
    from src.transform import transform_ecorp_to_batchdata
    from src.run import run_pipeline
    # fmt: off
    from src.io import load_workbook_sheets, load_config_dict, load_blacklist_set  # noqa: F401
    # fmt: on
    from src.name_matching import apply_name_matching
except ImportError as e:
    print(f"Warning: Could not import BatchData modules: {e}")
    print(f"BatchData path: {batchdata_path}")
    apply_name_matching = None  # Fallback if import fails

from .utils import get_standard_timestamp, format_output_filename  # noqa: E402


# Canonical template path for output validation
BATCHDATA_COMPLETE_TEMPLATE = "Batchdata_Template.xlsx"


def validate_output_against_template(
    df: pd.DataFrame,
    template_path: str = BATCHDATA_COMPLETE_TEMPLATE,
    strict: bool = True,
) -> bool:
    """Validate DataFrame columns against canonical template.

    Args:
        df: DataFrame to validate
        template_path: Path to template Excel file
        strict: If True, raise ValueError on mismatch. If False, log warning only.

    Returns:
        True if columns match template exactly, False otherwise.

    Raises:
        ValueError: If strict=True and columns don't match template.
        FileNotFoundError: If template file doesn't exist.
    """
    template_file = Path(template_path)
    if not template_file.exists():
        if strict:
            raise FileNotFoundError(f"Template file not found: {template_path}")
        print(f"⚠️ Warning: Template file not found for validation: {template_path}")
        return False

    # Read template columns
    template_df = pd.read_excel(template_path, nrows=0)
    template_cols = list(template_df.columns)
    output_cols = list(df.columns)

    if output_cols == template_cols:
        print(f"✓ Output schema matches template ({len(template_cols)} columns)")
        return True

    # Find differences
    missing = set(template_cols) - set(output_cols)
    extra = set(output_cols) - set(template_cols)

    msg = (
        f"Output schema mismatch!\n"
        f"  Expected: {len(template_cols)} columns\n"
        f"  Got: {len(output_cols)} columns\n"
    )
    if missing:
        msg += f"  Missing: {sorted(missing)}\n"
    if extra:
        msg += f"  Extra: {sorted(extra)}\n"

    # Check order if sets match
    if not missing and not extra:
        msg += "  Note: Column sets match but ORDER differs from template\n"

    if strict:
        raise ValueError(msg)
    else:
        print(f"⚠️ Warning: {msg}")
        return False


def create_batchdata_upload(
    ecorp_complete_path: str,
    month_code: str,
    output_dir: str = "Batchdata/Upload",
    timestamp: Optional[str] = None,
    config_template_path: str = "Batchdata/template_config.xlsx",
) -> Path:
    """Create BatchData Upload file from Ecorp Complete data.

    This function:
    1. Loads Ecorp Complete Excel file
    2. Transforms it to BatchData format using transform_ecorp_to_batchdata()
    3. Loads CONFIG and BLACKLIST_NAMES from template
    4. Saves as new Upload file with standardized naming

    Args:
        ecorp_complete_path: Path to Ecorp Complete Excel file
        month_code: Month code (e.g., "1.25" for January 2025)
        output_dir: Directory for Upload file (default: "Batchdata/Upload")
        timestamp: Optional timestamp string (MM.DD.HH-MM-SS). If None, generates new one.
        config_template_path: Path to template config file with CONFIG and BLACKLIST_NAMES sheets

    Returns:
        Path object pointing to created Upload file

    Raises:
        FileNotFoundError: If ecorp_complete_path or config_template_path doesn't exist
        ValueError: If required sheets missing from template
    """
    if timestamp is None:
        timestamp = get_standard_timestamp()

    # Validate inputs
    ecorp_path = Path(ecorp_complete_path)
    template_path = Path(config_template_path)

    if not ecorp_path.exists():
        raise FileNotFoundError(f"Ecorp Complete file not found: {ecorp_complete_path}")
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template config file not found: {config_template_path}"
        )

    print(f"\n{'='*60}")
    print("Creating BatchData Upload from Ecorp Complete")
    print(f"{'='*60}")
    print(f"Ecorp file: {ecorp_path.name}")
    print(f"Month: {month_code}")
    print(f"Timestamp: {timestamp}")

    # Load Ecorp Complete data
    print("\nLoading Ecorp Complete data...")
    ecorp_df = pd.read_excel(ecorp_path)
    print(f"  Loaded {len(ecorp_df)} records")

    # Transform to BatchData format (with ECORP passthrough for traceability)
    print("\nTransforming to BatchData format...")
    batchdata_df = transform_ecorp_to_batchdata(ecorp_df, preserve_ecorp_context=True)
    print(
        f"  Transformed to {len(batchdata_df)} BatchData records ({len(batchdata_df.columns)} columns)"
    )

    # Load template sheets (CONFIG, BLACKLIST_NAMES)
    print("\nLoading template configuration...")
    template_sheets = pd.read_excel(template_path, sheet_name=None)

    required_sheets = ["CONFIG", "BLACKLIST_NAMES"]
    for sheet in required_sheets:
        if sheet not in template_sheets:
            raise ValueError(f"Required sheet '{sheet}' not found in template")

    config_df = template_sheets["CONFIG"]
    blacklist_df = template_sheets["BLACKLIST_NAMES"]
    print("  Loaded CONFIG and BLACKLIST_NAMES")

    # Create output directory if needed
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    filename = format_output_filename(month_code, "BatchData_Upload", timestamp)
    output_file = output_path / filename

    # Write Excel file with all sheets
    print(f"\nWriting Upload file: {filename}")
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        config_df.to_excel(writer, sheet_name="CONFIG", index=False)
        batchdata_df.to_excel(writer, sheet_name="INPUT_MASTER", index=False)
        blacklist_df.to_excel(writer, sheet_name="BLACKLIST_NAMES", index=False)

    print(f"✓ Created BatchData Upload: {output_file}")
    print(f"  - CONFIG: {len(config_df)} settings")
    print(
        f"  - INPUT_MASTER: {len(batchdata_df)} records x {len(batchdata_df.columns)} columns (17 ECORP + 16 BD)"
    )
    print(f"  - BLACKLIST_NAMES: {len(blacklist_df)} entries")

    return output_file


def run_batchdata_enrichment(
    upload_path: str,
    month_code: str,
    output_dir: str = "Batchdata/Complete",
    timestamp: Optional[str] = None,
    dry_run: bool = False,
    dedupe: bool = True,
    consolidate_families: bool = True,
    filter_entities: bool = True,
    use_sync: bool = True,  # NEW: Default to sync
    stage_config: Optional[Dict] = None,  # NEW: Stage selection
    ecorp_file: Optional[str] = None,  # Ecorp Complete file for name matching
) -> Optional[Path]:
    """Run BatchData enrichment pipeline on Upload file.

    This function:
    1. Runs the BatchData API enrichment pipeline (sync or async)
    2. Saves results with standardized naming to Complete directory
    3. Optionally runs in dry-run mode for cost estimation
    4. Computes Ecorp-to-Batchdata name matching (if ecorp_file provided)

    Args:
        upload_path: Path to BatchData Upload Excel file
        month_code: Month code (e.g., "1.25" for January 2025)
        output_dir: Directory for Complete file (default: "Batchdata/Complete")
        timestamp: Optional timestamp string (MM.DD.HH-MM-SS). If None, extracts from upload filename.
        dry_run: If True, only estimate costs without processing (default: False)
        dedupe: Remove duplicate records to reduce API costs (default: True)
        consolidate_families: Consolidate principals across entity families (default: True)
        filter_entities: Remove entity-only records with no individuals (default: True)
        use_sync: If True, use synchronous API client; else use async (default: True)
        stage_config: Optional dict specifying which enrichment stages to run
                     {'skip_trace': True, 'phone_verify': False, 'dnc': False, 'tcpa': False}
        ecorp_file: Optional path to Ecorp Complete file for name matching calculation

    Returns:
        Path to created Complete file, or None if dry-run or user cancelled

    Raises:
        FileNotFoundError: If upload_path doesn't exist
    """
    upload_file = Path(upload_path)

    if not upload_file.exists():
        raise FileNotFoundError(f"Upload file not found: {upload_path}")

    # Extract timestamp from filename if not provided
    if timestamp is None:
        # Parse from filename like "1.25_BatchData_Upload_01.15.03-45-30.xlsx"
        filename = upload_file.stem
        parts = filename.split("_")
        if len(parts) >= 4:
            timestamp = parts[-1]  # Last part is timestamp
        else:
            timestamp = get_standard_timestamp()

    print(f"\n{'='*60}")
    print("Running BatchData Enrichment Pipeline")
    print(f"{'='*60}")
    print(f"Upload file: {upload_file.name}")
    print(f"Month: {month_code}")
    print(f"Timestamp: {timestamp}")
    print(f"Dry run: {dry_run}")
    print(f"Dedupe: {dedupe}")
    print(f"Consolidate families: {consolidate_families}")
    print(f"Filter entities: {filter_entities}")
    print(f"Use sync client: {use_sync}")
    if stage_config:
        print(f"Stage config: {stage_config}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate expected output filename
    complete_filename = format_output_filename(
        month_code, "BatchData_Complete", timestamp
    )
    expected_output = output_path / complete_filename

    print(f"\nExpected output: {complete_filename}")

    # Choose between sync and async implementation
    if use_sync:
        # Use the new synchronous client
        print("\nUsing synchronous API client...")
        return _run_sync_enrichment(
            upload_file,
            expected_output,
            month_code,
            timestamp,
            dry_run,
            stage_config,
            ecorp_file,
        )
    else:
        # Use the legacy async client (may still have 404 issues)
        print("\nUsing async API client (legacy)...")
        return _run_async_enrichment(
            upload_file,
            expected_output,
            dry_run,
            dedupe,
            consolidate_families,
            filter_entities,
        )


def _run_sync_enrichment(
    upload_file: Path,
    expected_output: Path,
    month_code: str,
    timestamp: str,
    dry_run: bool,
    stage_config: Optional[Dict],
    ecorp_file: Optional[str] = None,
) -> Optional[Path]:
    """Run synchronous BatchData enrichment using JSON API.

    Internal function for sync client implementation.
    Includes Ecorp-to-Batchdata name matching if ecorp_file is provided.
    """
    import os
    from src.batchdata_sync import BatchDataSyncClient
    from src.io import load_workbook_sheets

    # Default stage configuration
    if stage_config is None:
        stage_config = {
            "skip_trace": True,
            "phone_verify": True,
            "dnc": True,
            "tcpa": True,
        }

    print("\nLoading input data from Upload file...")
    sheets = load_workbook_sheets(str(upload_file))

    # Validate required sheets
    required_sheets = ["CONFIG", "INPUT_MASTER", "BLACKLIST_NAMES"]
    for sheet in required_sheets:
        if sheet not in sheets:
            raise ValueError(f"Required sheet '{sheet}' not found in upload file")

    config_df = sheets["CONFIG"]
    input_df = sheets["INPUT_MASTER"]
    blacklist_df = sheets["BLACKLIST_NAMES"]

    print(f"  - INPUT_MASTER: {len(input_df)} records")
    print(f"  - CONFIG: {len(config_df)} settings")
    print(f"  - BLACKLIST_NAMES: {len(blacklist_df)} entries")

    # Extract API keys from CONFIG sheet
    api_keys = {}
    for _, row in config_df.iterrows():
        key = row.get("key", "")
        value = row.get("value", "")
        if "api.key" in key:
            # Map config keys to expected format
            if "skiptrace" in key:
                api_keys["BD_SKIPTRACE_KEY"] = value
            elif "address" in key:
                api_keys["BD_ADDRESS_KEY"] = value
            elif "property" in key:
                api_keys["BD_PROPERTY_KEY"] = value
            elif "phone" in key:
                api_keys["BD_PHONE_KEY"] = value

    # Check for environment variable overrides
    for key in [
        "BD_SKIPTRACE_KEY",
        "BD_ADDRESS_KEY",
        "BD_PROPERTY_KEY",
        "BD_PHONE_KEY",
    ]:
        env_value = os.getenv(key)
        if env_value:
            api_keys[key] = env_value

    if dry_run:
        # Calculate cost estimates
        record_count = len(input_df)
        skip_trace_cost = record_count * 0.07 if stage_config.get("skip_trace") else 0
        phone_verify_cost = (
            record_count * 2 * 0.007 if stage_config.get("phone_verify") else 0
        )
        dnc_cost = record_count * 2 * 0.002 if stage_config.get("dnc") else 0
        tcpa_cost = record_count * 2 * 0.002 if stage_config.get("tcpa") else 0
        total_cost = skip_trace_cost + phone_verify_cost + dnc_cost + tcpa_cost

        print(f"\n{'='*40}")
        print("DRY RUN - Cost Estimate")
        print(f"{'='*40}")
        print(f"Records to process: {record_count}")
        if stage_config.get("skip_trace"):
            print(f"Skip-trace: ${skip_trace_cost:.2f}")
        if stage_config.get("phone_verify"):
            print(f"Phone verification: ${phone_verify_cost:.2f}")
        if stage_config.get("dnc"):
            print(f"DNC screening: ${dnc_cost:.2f}")
        if stage_config.get("tcpa"):
            print(f"TCPA screening: ${tcpa_cost:.2f}")
        print(f"{'='*40}")
        print(f"TOTAL ESTIMATED COST: ${total_cost:.2f}")
        print(f"{'='*40}\n")
        return None

    # Initialize sync client
    client = BatchDataSyncClient(api_keys)

    # Run enrichment pipeline
    print(f"\nRunning enrichment pipeline with stages: {stage_config}")
    result_df = client.run_enrichment_pipeline(input_df, stage_config)

    # Apply Ecorp-to-Batchdata name matching
    # NOTE: ecorp_file is REQUIRED - BD_OWNER_NAME_FULL fallback has been removed
    if apply_name_matching is not None:
        print("\nComputing Ecorp-to-Batchdata name matching...")
        ecorp_complete_df = None
        if ecorp_file:
            ecorp_path = Path(ecorp_file)
            if ecorp_path.exists():
                ecorp_complete_df = pd.read_excel(ecorp_path)
                print("  Using full Ecorp Complete for 22-field matching")
            else:
                print(f"  WARNING: Ecorp file not found: {ecorp_file}")
                print(
                    "  Name matching will set ECORP_TO_BATCH_MATCH_% to 'N/A' for all records"
                )
        else:
            print("  WARNING: No Ecorp_Complete file provided")
            print(
                "  Name matching will set ECORP_TO_BATCH_MATCH_% to 'N/A' for all records"
            )
        result_df = apply_name_matching(result_df, ecorp_complete_df)
        print("  Added ECORP_TO_BATCH_MATCH_% and MISSING_1-8_FULL_NAME columns")
    else:
        print("\nWarning: name_matching module not available, skipping name matching")

    # Validate output against canonical template before saving
    print("\nValidating output schema against template...")
    try:
        validate_output_against_template(
            result_df, BATCHDATA_COMPLETE_TEMPLATE, strict=True
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"⚠️ Schema validation error: {e}")
        print("  Proceeding with save despite mismatch (set strict=False to suppress)")

    # Save results
    print(f"\nSaving results to: {expected_output}")
    with pd.ExcelWriter(expected_output, engine="openpyxl") as writer:
        config_df.to_excel(writer, sheet_name="CONFIG", index=False)
        result_df.to_excel(writer, sheet_name="OUTPUT_MASTER", index=False)
        blacklist_df.to_excel(writer, sheet_name="BLACKLIST_NAMES", index=False)

    print(f"✓ Created BatchData Complete: {expected_output}")
    print(
        f"  - OUTPUT_MASTER: {len(result_df)} records x {len(result_df.columns)} columns"
    )

    return expected_output


def _run_async_enrichment(
    upload_file: Path,
    expected_output: Path,
    dry_run: bool,
    dedupe: bool,
    consolidate_families: bool,
    filter_entities: bool,
) -> Optional[Path]:
    """Run legacy async BatchData enrichment (may have 404 issues).

    Internal function for backward compatibility.
    """
    # Create a temporary results directory for the pipeline
    output_path = expected_output.parent
    timestamp = expected_output.stem.split("_")[-1]
    temp_results_dir = output_path / f"temp_results_{timestamp}"
    temp_results_dir.mkdir(exist_ok=True)

    try:
        # Run the BatchData pipeline
        # Note: The pipeline will create its own output files in results/
        # We'll need to move/rename them after completion

        print("\nStarting BatchData pipeline...")
        run_pipeline(
            input_path=str(upload_file),
            dry_run=dry_run,
            template_output=True,  # Use template format
            dedupe=dedupe,
            consolidate_families=consolidate_families,
            filter_entities=filter_entities,
        )

        if dry_run:
            print("\n✓ Dry run completed - no files created")
            return None

        # The pipeline creates output in results/ directory
        # Look for the most recent batchdata_complete file
        results_dir = Path("Batchdata/results")
        if results_dir.exists():
            complete_files = sorted(
                results_dir.glob("*complete*.xlsx"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if complete_files:
                # Move the most recent file to our standardized location
                source_file = complete_files[0]
                shutil.move(str(source_file), str(expected_output))
                print(f"\n✓ Created BatchData Complete: {expected_output}")
                return expected_output
            else:
                print(f"\nWarning: No complete file found in {results_dir}")
                return None
        else:
            print(f"\nWarning: Results directory not found: {results_dir}")
            return None

    except Exception as e:
        print(f"\nError during BatchData enrichment: {e}")
        raise
    finally:
        # Clean up temp directory
        if temp_results_dir.exists():
            shutil.rmtree(temp_results_dir, ignore_errors=True)


def create_template_config(
    source_input_path: str = "Batchdata/tests/batchdata_local_input.xlsx",
    output_path: str = "Batchdata/template_config.xlsx",
) -> Path:
    """Create template config file from existing batchdata_local_input.xlsx.

    Extracts CONFIG and BLACKLIST_NAMES sheets, creates empty INPUT_MASTER sheet.

    Args:
        source_input_path: Path to existing batchdata_local_input.xlsx
        output_path: Path for new template file

    Returns:
        Path to created template file

    Raises:
        FileNotFoundError: If source file doesn't exist
        ValueError: If required sheets missing
    """
    source_file = Path(source_input_path)

    if not source_file.exists():
        raise FileNotFoundError(f"Source file not found: {source_input_path}")

    print(f"Creating template config from {source_file.name}...")

    # Load sheets
    sheets = pd.read_excel(source_file, sheet_name=None)

    required_sheets = ["CONFIG", "BLACKLIST_NAMES", "INPUT_MASTER"]
    for sheet in required_sheets:
        if sheet not in sheets:
            raise ValueError(f"Required sheet '{sheet}' not found in source")

    config_df = sheets["CONFIG"]
    blacklist_df = sheets["BLACKLIST_NAMES"]
    input_master_df = sheets["INPUT_MASTER"]

    # Create empty INPUT_MASTER with same structure (just headers)
    empty_input = pd.DataFrame(columns=input_master_df.columns)

    # Write template file
    output_file = Path(output_path)
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        config_df.to_excel(writer, sheet_name="CONFIG", index=False)
        empty_input.to_excel(writer, sheet_name="INPUT_MASTER", index=False)
        blacklist_df.to_excel(writer, sheet_name="BLACKLIST_NAMES", index=False)

    print(f"✓ Created template: {output_file}")
    print(f"  - CONFIG: {len(config_df)} settings")
    print("  - INPUT_MASTER: Empty (template structure)")
    print(f"  - BLACKLIST_NAMES: {len(blacklist_df)} entries")

    return output_file
