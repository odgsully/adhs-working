"""
run.py - CLI entrypoint for BatchData pipeline
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

from .io import (
    load_workbook_sheets, load_config_dict, load_blacklist_set,
    ensure_results_dir, save_intermediate_csv, save_intermediate_xlsx, write_final_excel,
    get_timestamped_path, get_template_filename, write_template_excel,
    save_api_result
)
from .transform import (
    transform_ecorp_to_batchdata, explode_phones_to_long, aggregate_top_phones, 
    deduplicate_batchdata_records, consolidate_entity_families, filter_entity_only_records,
    validate_input_fields, optimize_for_api
)
from .normalize import apply_blacklist_filter
from .batchdata import create_client_from_env


def load_input_data(input_path: str):
    """Load and validate input Excel file.
    
    Args:
        input_path: Path to input Excel file
        
    Returns:
        Tuple of (config_dict, input_df, blacklist_set)
    """
    print(f"Loading input file: {input_path}")
    
    sheets = load_workbook_sheets(input_path)
    required_sheets = ['CONFIG', 'INPUT_MASTER', 'BLACKLIST_NAMES']
    
    for sheet in required_sheets:
        if sheet not in sheets:
            raise ValueError(f"Required sheet '{sheet}' not found in {input_path}")
    
    config = load_config_dict(sheets['CONFIG'])
    input_df = sheets['INPUT_MASTER']
    blacklist = load_blacklist_set(sheets['BLACKLIST_NAMES'])
    
    print(f"Loaded {len(input_df)} records from INPUT_MASTER")
    print(f"Configuration: {len(config)} settings")
    print(f"Blacklist: {len(blacklist)} entries")
    
    return config, input_df, blacklist


def load_ecorp_data(ecorp_path: str):
    """Load eCorp data file and transform to BatchData format.
    
    Args:
        ecorp_path: Path to eCorp Excel file
        
    Returns:
        Transformed DataFrame in BatchData format
    """
    print(f"Loading eCorp data: {ecorp_path}")
    ecorp_df = pd.read_excel(ecorp_path)
    
    print(f"Loaded {len(ecorp_df)} eCorp records")
    print("Transforming to BatchData format...")
    
    batchdata_df = transform_ecorp_to_batchdata(ecorp_df)
    print(f"Transformed to {len(batchdata_df)} BatchData records")
    
    return batchdata_df


def estimate_and_confirm_costs(client, record_count: int, config: dict, dry_run: bool = False):
    """Estimate costs and get user confirmation.
    
    Args:
        client: BatchData client
        record_count: Number of records to process
        config: Configuration dictionary
        dry_run: If True, only show estimate without prompting
        
    Returns:
        True if user confirms, False otherwise
    """
    costs = client.estimate_cost(record_count, config)
    
    print("\n=== COST ESTIMATE ===")
    for service, cost in costs.items():
        if service != 'total' and cost > 0:
            print(f"{service}: ${cost:.2f}")
    print(f"TOTAL ESTIMATED COST: ${costs['total']:.2f}")
    print("======================")
    
    if dry_run:
        print("DRY RUN MODE - No charges will be incurred")
        return True
    
    while True:
        confirm = input("Continue with processing? (y/n): ").lower().strip()
        if confirm in ['y', 'yes']:
            return True
        elif confirm in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def run_pipeline(input_path: str, ecorp_path: str = None, dry_run: bool = False, template_output: bool = False, dedupe: bool = False, consolidate_families: bool = False, filter_entities: bool = False):
    """Run the complete BatchData pipeline.
    
    Args:
        input_path: Path to input Excel with CONFIG, INPUT_MASTER, BLACKLIST_NAMES
        ecorp_path: Optional path to eCorp data (if not provided, uses INPUT_MASTER)
        dry_run: If True, estimate costs but don't process
        template_output: If True, output in template format with M.YY naming
        dedupe: If True, remove duplicate records to reduce API costs
        consolidate_families: If True, consolidate principals across entity families
        filter_entities: If True, remove entity-only records with no individual names
    """
    # Load environment variables from project root
    load_dotenv(Path(__file__).parent.parent.parent / '.env')
    
    # Ensure results directory exists
    results_dir = ensure_results_dir("results")
    timestamp = datetime.now().strftime("%m.%d.%I-%M-%S")
    
    try:
        # Load configuration and input data
        config, input_df, blacklist = load_input_data(input_path)
        
        # Determine data source
        if ecorp_path:
            # Transform eCorp data to BatchData format
            working_df = load_ecorp_data(ecorp_path)
        else:
            # Use INPUT_MASTER directly
            working_df = input_df.copy()
            print(f"Using {len(working_df)} records from INPUT_MASTER")
        
        # Apply blacklist filter
        print("Applying blacklist filter...")
        pre_filter_count = len(working_df)
        working_df = apply_blacklist_filter(working_df, blacklist)
        post_filter_count = len(working_df)
        print(f"Blacklist filter removed {pre_filter_count - post_filter_count} records")
        
        if working_df.empty:
            print("No records remaining after blacklist filter. Exiting.")
            return
        
        # Validate and optimize input fields for better API results
        print("\nValidating input data quality...")
        working_df = validate_input_fields(working_df)
        
        print("\nOptimizing fields for API...")
        working_df = optimize_for_api(working_df)
        
        # Apply deduplication if requested
        if dedupe:
            print("Applying deduplication to reduce API costs...")
            working_df = deduplicate_batchdata_records(working_df)
            
            if working_df.empty:
                print("No records remaining after deduplication. Exiting.")
                return
        
        # Apply entity family consolidation if requested
        if consolidate_families:
            if not dedupe:
                print("Warning: --consolidate-families works best with --dedupe enabled")
            print("Applying entity family consolidation...")
            working_df = consolidate_entity_families(working_df)
            
            if working_df.empty:
                print("No records remaining after consolidation. Exiting.")
                return
        
        # Apply entity-only filter if requested
        if filter_entities:
            print("Applying entity-only record filter...")
            working_df = filter_entity_only_records(working_df, filter_enabled=True)
            
            if working_df.empty:
                print("No records remaining after entity filter. Exiting.")
                return
        
        # Save filtered input
        suffix_parts = ["filtered_input", timestamp]
        if dedupe:
            suffix_parts.append("dedupe")
        if consolidate_families:
            suffix_parts.append("families")
        if filter_entities:
            suffix_parts.append("no_entities")
        filename_suffix = "_".join(suffix_parts)
        
        filtered_input_path = save_api_result(working_df, results_dir, 'input', filename_suffix, 'xlsx')
        print(f"Saved filtered input: {filtered_input_path}")
        
        # Create API client
        print("Initializing BatchData client...")
        client = create_client_from_env()
        
        # Estimate costs and get confirmation
        if not estimate_and_confirm_costs(client, len(working_df), config, dry_run):
            print("Processing cancelled by user")
            return
        
        if dry_run:
            print("Dry run complete - no processing performed")
            return
        
        # Run skip-trace pipeline
        print("\n=== STARTING BATCHDATA PIPELINE ===")
        final_results, intermediates = client.run_skip_trace_pipeline(
            working_df, results_dir, config
        )
        
        # Save raw skip-trace results with ALL fields preserved
        raw_results_path = save_api_result(final_results, results_dir, 'skiptrace', f"skiptrace_complete_{timestamp}", 'xlsx')
        print(f"Saved raw skip-trace results: {raw_results_path}")
        
        # Process phone results if available
        if not final_results.empty:
            print("Processing phone results...")
            
            # Explode phones to long format
            phones_long = explode_phones_to_long(final_results)
            
            if not phones_long.empty:
                # Apply scrubs based on intermediate results
                verification_df = None
                dnc_df = None
                tcpa_df = None
                
                # Find scrub results in intermediates
                for idx, df in enumerate(intermediates):
                    if 'is_active' in df.columns:
                        verification_df = df
                    elif 'on_dnc' in df.columns:
                        dnc_df = df  
                    elif 'is_litigator' in df.columns:
                        tcpa_df = df
                
                # Apply scrubs
                from .transform import apply_phone_scrubs
                phones_scrubbed = apply_phone_scrubs(phones_long, verification_df, dnc_df, tcpa_df)
                
                # Save scrubbed phones in phone_scrub subfolder
                scrubbed_phones_path = save_api_result(
                    phones_scrubbed, results_dir, 'phone_scrub', f"phones_scrubbed_{timestamp}", 'xlsx'
                )
                print(f"Saved scrubbed phones: {scrubbed_phones_path}")
                
                # Aggregate back to wide format
                phones_wide = aggregate_top_phones(phones_scrubbed, top_n=10)
                
                # Merge with original data - preserve ALL fields from both DataFrames
                # Use outer merge to keep all data, then prefer skip-trace results
                final_df = pd.merge(working_df, phones_wide, on='record_id', how='left', suffixes=('', '_phones'))
                
                # Also merge the full skip-trace results to preserve all API fields
                if not final_results.empty:
                    # Ensure we keep ALL fields from API response
                    final_df = pd.merge(final_df, final_results, on='record_id', how='left', suffixes=('', '_api'))
            else:
                final_df = working_df
        else:
            print("No results from skip-trace")
            final_df = working_df
        
        # Write final Excel output - conditional logic for template format
        if template_output:
            # NEW: Template output with M.YY naming
            month_year = datetime.now().strftime("%m.%y")
            final_excel_path = get_template_filename(results_dir, month_year)
            write_template_excel(final_df, final_excel_path, config, blacklist)
            print(f"\n=== PIPELINE COMPLETE (Template Format) ===")
        else:
            # EXISTING: Standard output format (unchanged)
            final_excel_path = get_timestamped_path(results_dir, "batchdata_complete", "xlsx")
            write_final_excel(final_df, final_excel_path, "Final_Contacts")
            print(f"\n=== PIPELINE COMPLETE ===")
        
        print(f"Final results: {final_excel_path}")
        print(f"Records processed: {len(working_df)}")
        print(f"Final records: {len(final_df)}")
        print(f"All outputs saved to: {results_dir}")
        
    except Exception as e:
        print(f"Pipeline error: {e}")
        
        # Save error log
        error_log_path = get_timestamped_path(results_dir, "error_log", "txt")
        with open(error_log_path, 'w') as f:
            f.write(f"Pipeline Error: {datetime.now()}\n")
            f.write(f"Input: {input_path}\n")
            f.write(f"eCorp: {ecorp_path}\n")
            f.write(f"Error: {str(e)}\n")
        
        print(f"Error details saved: {error_log_path}")
        raise


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="BatchData Bulk Skip-Trace Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use template with INPUT_MASTER data
  python -m src.run --input batchdata_local_input.xlsx
  
  # Transform eCorp data and process
  python -m src.run --input template.xlsx --ecorp ecorp_complete.xlsx
  
  # Dry run to estimate costs only
  python -m src.run --input template.xlsx --dry-run
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input Excel file with CONFIG, INPUT_MASTER, BLACKLIST_NAMES sheets'
    )
    
    parser.add_argument(
        '--ecorp',
        help='Path to eCorp Excel file to transform (optional)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Estimate costs without processing'
    )
    
    parser.add_argument(
        '--template-output',
        action='store_true',
        help='Output in template_batchdata_upload.xlsx format with M.YY naming'
    )
    
    parser.add_argument(
        '--dedupe',
        action='store_true',
        help='Remove duplicate records to reduce API costs'
    )
    
    parser.add_argument(
        '--consolidate-families',
        action='store_true',
        help='Consolidate principals across related entity families (requires --dedupe)'
    )
    
    parser.add_argument(
        '--filter-entities',
        action='store_true',
        help='Remove entity-only records with no individual names to save API costs'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    if args.ecorp and not os.path.exists(args.ecorp):
        print(f"Error: eCorp file not found: {args.ecorp}")
        sys.exit(1)
    
    # Run pipeline
    try:
        run_pipeline(args.input, args.ecorp, args.dry_run, args.template_output, args.dedupe, args.consolidate_families, args.filter_entities)
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()