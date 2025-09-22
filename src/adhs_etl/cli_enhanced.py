"""Enhanced CLI for ADHS ETL pipeline with full analysis capabilities."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from rich.console import Console
from rich.logging import RichHandler

from .config import Settings
from .transform_enhanced import (
    EnhancedFieldMapper, 
    ProviderGrouper,
    process_month_data,
    create_reformat_output,
    create_all_to_date_output,
    log_memory_usage,
    clear_memory
)
from .analysis import (
    ProviderAnalyzer,
    create_analysis_summary_sheet,
    create_blanks_count_sheet
)
from .mca_api import MCAPGeocoder

app = typer.Typer()
console = Console()


def setup_logging(level: str = "INFO") -> None:
    """Configure logging with rich handler."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def get_previous_month_data(all_months_dir: Path, current_month: int, current_year: int) -> pd.DataFrame:
    """Get data from the previous month."""
    import pandas as pd
    
    # Calculate previous month
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    # Look for previous month folder
    if prev_month >= 10:
        prev_folder_name = f"Raw {prev_month}.{prev_year % 100}"
    else:
        prev_folder_name = f"Raw {prev_month}.{prev_year % 100}"
    
    prev_folder = all_months_dir / prev_folder_name
    
    if prev_folder.exists():
        # Process previous month data
        field_mapper = EnhancedFieldMapper(
            Path("field_map.yml"),
            Path("field_map.TODO.yml")
        )
        provider_grouper = ProviderGrouper()
        
        return process_month_data(
            prev_folder,
            field_mapper,
            provider_grouper,
            prev_month,
            prev_year
        )
    
    return pd.DataFrame()


def get_all_historical_data(all_to_date_dir: Path) -> pd.DataFrame:
    """Get all historical data from the most recent All to Date file."""
    import pandas as pd
    
    # Find most recent All to Date file
    all_to_date_files = list(all_to_date_dir.glob("Reformat All to Date *.xlsx"))
    
    if all_to_date_files:
        latest_file = max(all_to_date_files, key=lambda p: p.stat().st_mtime)
        return pd.read_excel(latest_file)
    
    return pd.DataFrame()


@app.command()
def run(
    month: str = typer.Option(
        ...,
        "--month",
        "-m",
        help="Month to process (format: MM.YY or M.YY)",
    ),
    raw_dir: Optional[Path] = typer.Option(
        None,
        "--raw-dir",
        "-r",
        help="Raw data directory (default: Raw-New-Month)",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory (default: current directory)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run without writing files",
    ),
    batch_size: int = typer.Option(
        1000,
        "--batch-size",
        "-b",
        help="Batch size for processing large datasets",
    ),
    low_memory: bool = typer.Option(
        False,
        "--low-memory",
        help="Enable low memory mode with aggressive garbage collection",
    ),
) -> None:
    """Run the enhanced ADHS ETL pipeline with full analysis."""
    import pandas as pd
    
    # Convert month format from M.YY to YYYY-MM
    parts = month.split('.')
    month_num = int(parts[0])
    year_num = 2000 + int(parts[1])
    formatted_month = f"{year_num}-{month_num:02d}"
    
    settings = Settings(month=formatted_month)
    if raw_dir:
        settings.raw_dir = raw_dir
    else:
        settings.raw_dir = Path("Raw-New-Month")
    
    if output_dir:
        settings.output_dir = output_dir
    else:
        settings.output_dir = Path(".")
    
    settings.dry_run = dry_run
    
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    
    # Parse month/year
    try:
        parts = month.split('.')
        month_num = int(parts[0])
        year_num = 2000 + int(parts[1])
    except Exception:
        logger.error(f"Invalid month format: {month}. Use MM.YY or M.YY")
        raise typer.Exit(code=1)
    
    logger.info(f"Starting enhanced ADHS ETL pipeline for month: {month_num}/{year_num}")
    if dry_run:
        logger.info("[DRY RUN MODE] No files will be written")
    if low_memory:
        logger.info("[LOW MEMORY MODE] Using aggressive memory management")
    
    log_memory_usage("at start of ETL pipeline")
    
    # Initialize components
    field_mapper = EnhancedFieldMapper(settings.field_map_path, settings.field_map_todo_path)
    provider_grouper = ProviderGrouper(settings.fuzzy_threshold)
    analyzer = ProviderAnalyzer()
    geocoder = MCAPGeocoder(settings.mcao_api_key, settings.mcao_api_url)
    
    # Process current month data with batch size
    current_month_df = process_month_data(
        settings.raw_dir,
        field_mapper,
        provider_grouper,
        month_num,
        year_num,
        batch_size
    )
    
    if low_memory:
        clear_memory()
        log_memory_usage("after processing current month data")
    
    if current_month_df.empty:
        logger.error("No data processed for current month")
        raise typer.Exit(code=1)
    
    logger.info(f"Processed {len(current_month_df)} records for current month")
    
    # Save unknown columns
    field_mapper.save_unknown_columns(dry_run=settings.dry_run)
    
    # Create output directories (relative to current working directory)
    reformat_dir = Path("Reformat")
    all_to_date_dir = Path("All-to-Date")
    analysis_dir = Path("Analysis")
    
    if not dry_run:
        # Create output directories with proper permissions
        for directory in [reformat_dir, all_to_date_dir, analysis_dir]:
            directory.mkdir(exist_ok=True)
            # Ensure directories are visible and accessible
            try:
                import os
                os.chmod(directory, 0o755)
            except Exception as e:
                logger.warning(f"Could not set directory permissions for {directory}: {e}")
    
    # 1. Create Reformat output
    if not dry_run:
        reformat_path = create_reformat_output(
            current_month_df,
            month_num,
            year_num,
            reformat_dir
        )
        logger.info(f"Created Reformat file: {reformat_path}")
    
    # 2. Create All to Date output
    if not dry_run:
        all_to_date_path = create_all_to_date_output(
            current_month_df,
            month_num,
            year_num,
            all_to_date_dir,
            batch_size
        )
        logger.info(f"Created All to Date file: {all_to_date_path}")
        
        if low_memory:
            clear_memory()
            log_memory_usage("after creating All to Date file")
    
    # 3. Get previous month data for analysis
    all_months_dir = Path("ALL-MONTHS")
    previous_month_df = get_previous_month_data(all_months_dir, month_num, year_num)
    
    # 4. Get all historical data
    all_historical_df = get_all_historical_data(all_to_date_dir)
    
    # 5. Perform analysis
    logger.info("Performing provider analysis...")
    
    # Analyze changes
    analysis_df = analyzer.analyze_month_changes(
        current_month_df,
        previous_month_df,
        all_historical_df
    )
    
    # Ensure CAPACITY is formatted as integers (no decimals)
    if 'CAPACITY' in analysis_df.columns:
        analysis_df['CAPACITY'] = pd.to_numeric(analysis_df['CAPACITY'], errors='coerce')
        # Convert to integers where not null, then to string
        mask = analysis_df['CAPACITY'].notna() & (analysis_df['CAPACITY'] != 0)
        analysis_df.loc[mask, 'CAPACITY'] = analysis_df.loc[mask, 'CAPACITY'].astype(int).astype(str)
        # Set null/0 values to empty string
        analysis_df.loc[~mask, 'CAPACITY'] = ''

    # Add provider group information
    analysis_df = analyzer.calculate_provider_groups(analysis_df)

    # Add monthly counts and movements
    if not all_historical_df.empty:
        months_data = analyzer.create_monthly_counts(all_historical_df, month_num, year_num)
        analysis_df = analyzer.create_movement_columns(analysis_df, months_data)

    # Add summary columns AFTER provider groups are calculated (needs Column M and N)
    analysis_df = analyzer.create_summary_columns(analysis_df)

    # Calculate enhanced tracking fields (EH:EY columns)
    analysis_df = analyzer.calculate_enhanced_tracking_fields(analysis_df, previous_month_df)

    # Ensure all columns from v300Track_this.xlsx as defined in v300Track_this.md are present
    analysis_df = analyzer.ensure_all_analysis_columns(analysis_df, month_num, year_num)

    # Ensure CAPACITY is formatted as integers (no decimals) - MOVED AFTER ensure_all_analysis_columns
    if 'CAPACITY' in analysis_df.columns:
        analysis_df['CAPACITY'] = pd.to_numeric(analysis_df['CAPACITY'], errors='coerce')
        # Convert to integers where not null, then to string
        mask = analysis_df['CAPACITY'].notna() & (analysis_df['CAPACITY'] != 0)
        analysis_df.loc[mask, 'CAPACITY'] = analysis_df.loc[mask, 'CAPACITY'].astype(int).astype(str)
        # Set null/0 values to empty string
        analysis_df.loc[~mask, 'CAPACITY'] = ''

    # Fix MONTH and YEAR columns to only show the processing month/year
    analysis_df['MONTH'] = month_num
    analysis_df['YEAR'] = year_num
    
    # 6. Add MCAO property data for seller leads
    logger.info("Fetching property data for seller leads...")
    
    seller_leads_df = analysis_df[
        analysis_df['LEAD TYPE'].isin(['SELLER LEAD', 'SELLER/SURVEY LEAD'])
    ]
    
    # MCAO columns are already initialized by ensure_all_analysis_columns
    # No need to reinitialize here
    
    # Batch process property data for seller leads to reduce API calls
    api_batch_size = max(5, batch_size // 100)  # Scale API batch size based on processing batch size
    seller_indices = seller_leads_df.index.tolist()
    
    for i in range(0, len(seller_indices), api_batch_size):
        batch_indices = seller_indices[i:i+api_batch_size]
        logger.info(f"Processing MCAO batch {i//api_batch_size + 1}/{(len(seller_indices) + api_batch_size - 1)//api_batch_size}")
        
        for idx in batch_indices:
            row = analysis_df.loc[idx]
            address = row['ADDRESS']
            city = row['CITY']
            zip_code = row['ZIP']
            
            try:
                property_data = geocoder.get_property_info(address, city, zip_code)
                
                if property_data:
                    # Update the analysis dataframe using loc for better performance
                    analysis_df.loc[idx, 'APN'] = property_data.get('apn', 'N/A')
                    analysis_df.loc[idx, "BR'S"] = property_data.get('bedrooms', 'N/A')
                    analysis_df.loc[idx, "BA'S"] = property_data.get('bathrooms', 'N/A')
                    analysis_df.loc[idx, 'STORIES'] = property_data.get('stories', 'N/A')
                    analysis_df.loc[idx, 'OWNER NAME'] = property_data.get('owner_name', 'N/A')
                    analysis_df.loc[idx, 'OWNER MAILING'] = property_data.get('owner_mailing', 'N/A')
                    analysis_df.loc[idx, 'PURCHASE PRICE'] = property_data.get('purchase_price', 'N/A')
                    analysis_df.loc[idx, 'PURCHASE DATE'] = property_data.get('purchase_date', 'N/A')
            except Exception as e:
                logger.warning(f"Failed to get property data for {address}: {e}")
                continue
    
    # 7. Create analysis output file
    if month_num >= 10:
        analysis_filename = f"{month_num}.{year_num % 100} Analysis.xlsx"
    else:
        analysis_filename = f"{month_num}.{year_num % 100} Analysis.xlsx"
    
    analysis_path = analysis_dir / analysis_filename
    
    if not dry_run:
        # Create summary sheet - pass both Analysis and Reformat data for v300 compliance
        summary_df = create_analysis_summary_sheet(analysis_df, current_month_df)
        
        # Create blanks count sheet - pass month and year for v300 compliance
        blanks_df = create_blanks_count_sheet(current_month_df, month_num, year_num)
        
        # Optimize Analysis dataframe before writing - FIXED: Clean 'N/A' while preserving v300 column structure
        logger.info("Optimizing Analysis dataframe for faster writing...")
        analysis_df_optimized = analysis_df.copy()

        # Replace 'N/A' strings - FIXED: Use empty strings instead of pd.NA to prevent column dropping
        for col in analysis_df_optimized.columns:
            if analysis_df_optimized[col].dtype == 'object':
                analysis_df_optimized[col] = analysis_df_optimized[col].replace('N/A', '')
                # Don't replace empty strings - they're already correct

        # Validate column count for v300Track_this.xlsx 1:1 alignment
        expected_columns = 155  # v300Track_this.xlsx has columns A through EY (155 columns)
        actual_columns = len(analysis_df_optimized.columns)

        logger.info(f"Column validation: {actual_columns} columns (expected: {expected_columns})")
        logger.info(f"First 5 columns: {list(analysis_df_optimized.columns[:5])}")
        logger.info(f"Last 5 columns: {list(analysis_df_optimized.columns[-5:])}")

        if actual_columns != expected_columns:
            logger.error(f"❌ COLUMN COUNT MISMATCH: Expected {expected_columns} columns, got {actual_columns}")
            logger.error(f"❌ NOT CONSISTENT WITH v300Track_this.xlsx - BLOCKING OUTPUT")
            logger.error(f"❌ NO FILES WILL BE WRITTEN UNTIL COLUMN STRUCTURE MATCHES v300")
            return  # Block processing completely - don't write any files
        else:
            logger.info(f"✅ Column count validated: {actual_columns} columns match v300Track_this.xlsx")

        # Write all sheets to Excel using xlsxwriter for better performance
        try:
            # Try xlsxwriter first (5-10x faster for large files)
            engine = 'xlsxwriter'
            engine_kwargs = {
                'options': {
                    'strings_to_urls': False,  # Don't convert strings to URLs
                    'nan_inf_to_errors': True,  # Handle NaN/Inf properly
                    'strings_to_formulas': False,  # Don't interpret strings as formulas
                    'constant_memory': False  # FIXED: Disable to prevent column dropping for v300 compliance
                }
            }

            logger.info(f"Writing Excel file using {engine} engine for better performance...")

            with pd.ExcelWriter(analysis_path, engine=engine, engine_kwargs=engine_kwargs) as writer:
                # Sheet 1: Summary
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Sheet 2: Blanks Count
                blanks_df.to_excel(writer, sheet_name='Blanks Count', index=False)

                # Sheet 3: Analysis (optimized)
                analysis_df_optimized.to_excel(writer, sheet_name='Analysis', index=False)

                logger.info(f"Successfully wrote Excel file with {engine} engine")

        except ImportError:
            # Fallback to openpyxl if xlsxwriter not available
            logger.warning("xlsxwriter not available, falling back to openpyxl (slower)")

            with pd.ExcelWriter(analysis_path, engine='openpyxl') as writer:
                # Sheet 1: Summary
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Sheet 2: Blanks Count
                blanks_df.to_excel(writer, sheet_name='Blanks Count', index=False)

                # Sheet 3: Analysis (optimized)
                analysis_df_optimized.to_excel(writer, sheet_name='Analysis', index=False)

                # Skip column formatting for now to speed up writing
                logger.info("Wrote Excel file with openpyxl (formatting skipped for performance)")
        
        # Ensure file is visible and accessible
        import os
        import subprocess
        try:
            # Set file permissions to be readable/writable by owner and readable by others
            os.chmod(analysis_path, 0o644)
            # Also ensure the directory is accessible
            os.chmod(analysis_dir, 0o755)
            logger.info(f"Set file permissions for {analysis_path}")
            
            # Remove any extended attributes that might make the file hidden
            try:
                # Remove quarantine and other extended attributes on macOS
                subprocess.run(['xattr', '-c', str(analysis_path)], check=False, capture_output=True)
                logger.info(f"Cleared extended attributes for {analysis_path}")
            except Exception:
                pass  # Not critical if this fails
                
        except Exception as e:
            logger.warning(f"Could not set permissions for {analysis_path}: {e}")
        
        logger.info(f"Created Analysis file: {analysis_path}")
        logger.info(f"  - {len(summary_df)} summary metrics")
        logger.info(f"  - {len(blanks_df)} provider types tracked")
        logger.info(f"  - {len(analysis_df)} providers analyzed")
        logger.info(f"  - {len(seller_leads_df)} seller leads identified")
    
    log_memory_usage("at end of ETL pipeline")
    logger.info("Enhanced ETL pipeline completed successfully!")


@app.command()
def validate(
    field_map: Path = typer.Option(
        Path("field_map.yml"),
        "--field-map",
        "-f",
        help="Path to field mapping YAML file",
    ),
) -> None:
    """Validate field mapping configuration."""
    logger = logging.getLogger(__name__)
    setup_logging()
    
    if not field_map.exists():
        logger.error(f"Field map not found: {field_map}")
        raise typer.Exit(code=1)
    
    try:
        import yaml
        with open(field_map, "r") as f:
            mapping = yaml.safe_load(f)
        
        if not isinstance(mapping, dict):
            logger.error("Field map must be a dictionary")
            raise typer.Exit(code=1)
        
        logger.info(f"Field map validated: {len(mapping)} mappings found")
        
        # Show required fields
        required_fields = ['PROVIDER', 'ADDRESS', 'CITY', 'ZIP', 'FULL_ADDRESS', 'CAPACITY', 'LONGITUDE', 'LATITUDE', 'COUNTY']
        for field in required_fields:
            mappings = [k for k, v in mapping.items() if v == field]
            logger.info(f"  {field}: {len(mappings)} mappings")
        
    except Exception as e:
        logger.error(f"Error validating field map: {e}")
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the enhanced ADHS ETL CLI."""
    app()


if __name__ == "__main__":
    main()