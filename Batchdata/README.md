# BatchData Pipeline - Optional Post-Processing Enrichment

## Overview

This is an **OPTIONAL** post-processing pipeline that enriches Arizona Corporation Commission (ACC) entity data with additional contact information using BatchData skip-trace APIs.

**Important**: This is optional enrichment that runs AFTER the main ADHS ETL pipeline. The primary ACC entity lookup is handled by `src/adhs_etl/ecorp.py` as part of the main pipeline. This BatchData pipeline is located at `/Batchdata/` at the project root level.

## Features

- **Data Transformation**: Convert eCorp format to BatchData INPUT_MASTER format
- **Principal Explosion**: Transform entity records with multiple principals into individual records
- **Blacklist Filtering**: Filter out registered agents and other blacklisted entities
- **Async Processing**: Submit batches to async API endpoints with polling
- **Phone Scrubbing**: Verify, DNC check, and TCPA compliance for phone numbers
- **Cost Estimation**: Preview costs before processing
- **Error Handling**: Robust error handling with retry logic

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure BatchData API keys in project root `.env`:
```bash
# See root .env.sample for complete configuration template
# Add these keys to your root .env file:

BD_PROPERTY_KEY=your_property_and_skiptrace_api_key_here
BD_ADDRESS_KEY=your_address_verify_api_key_here
BD_PHONE_KEY=your_phone_verification_api_key_here
```

**Note**: BatchData uses the centralized `.env` file at the project root, not a local Batchdata/.env file.

## API Key Permissions

Each API key requires specific permissions enabled in the BatchData dashboard. Create 3 keys:

### Permission Categories

| API Key | Category | Required Permissions |
|---------|----------|----------------------|
| `BD_PROPERTY_KEY` | **Property & Skip-trace** | `property-skip-trace`, `property-skip-trace-async`, `property-lookup-all-attributes`, `property-search`, `property-search-async`, `property-lookup-async` |
| `BD_ADDRESS_KEY` | **Address** | `address-geocode`, `address-reverse-geocode`, `address-verify`, `address-autocomplete` |
| `BD_PHONE_KEY` | **Phone** | `phone-dnc`, `phone-tcpa`, `phone-verification`, `phone-verification-async`, `phone-dnc-async`, `phone-tcpa-async` |

### Dashboard Setup Steps

1. **Log into BatchData Dashboard** at https://app.batchdata.com
2. **Create 3 API keys** (one per category)
3. **Enable permissions** for each key:
   - **Property Key**: Enable all 6 Property permissions (skip-trace + lookup/search)
   - **Address Key**: Enable all 4 Address permissions
   - **Phone Key**: Enable all 6 Phone permissions
4. **Fund each key's wallet** with appropriate credits

### Permission Details

#### Property Permissions (BD_PROPERTY_KEY)
- `property-skip-trace` / `property-skip-trace-async` - Contact discovery (phones, emails) - **$0.07/record**
- `property-lookup-all-attributes` / `property-lookup-async` - Detailed property data
- `property-search` / `property-search-async` - Search properties by criteria

#### Address Permissions (BD_ADDRESS_KEY)
- `address-geocode` - Convert addresses to coordinates
- `address-reverse-geocode` - Convert coordinates to addresses
- `address-verify` - Standardize and validate addresses
- `address-autocomplete` - Address suggestion API

#### Phone Permissions (BD_PHONE_KEY)
- `phone-verification` / `phone-verification-async` - Validate phone numbers, check line type - **$0.007/phone**
- `phone-dnc` / `phone-dnc-async` - Do-Not-Call registry compliance - **$0.002/phone**
- `phone-tcpa` / `phone-tcpa-async` - TCPA litigation risk screening - **$0.002/phone**

## Usage

### Basic Usage

Process a template file with INPUT_MASTER data:
```bash
python -m src.run --input batchdata_local_input.xlsx
```

### Transform eCorp Data

Transform and process eCorp Complete files from the main pipeline:
```bash
python -m src.run --input template.xlsx --ecorp "../Ecorp/Complete/M.YY_Ecorp_Complete_{timestamp}.xlsx"
```

### Dry Run (Cost Estimation)

Estimate costs without processing:
```bash
python -m src.run --input batchdata_local_input.xlsx --dry-run
```

## Input File Format

The input Excel file must contain these sheets:

### CONFIG Sheet
Configuration options (key-value pairs):
- `workflow.enable_phone_verification`: TRUE/FALSE
- `workflow.enable_phone_dnc`: TRUE/FALSE  
- `workflow.enable_phone_tcpa`: TRUE/FALSE
- `batch.size`: Number of records per batch (e.g., 5000)
- `batch.poll_seconds`: Polling interval (e.g., 15)

### INPUT_MASTER Sheet  
Required columns:
- `record_id`: Unique identifier
- `source_entity_name`: Entity name
- `source_entity_id`: Entity ID
- `target_first_name`: Contact first name
- `target_last_name`: Contact last name
- `owner_name_full`: Full contact name
- `address_line1`: Street address
- `city`: City
- `state`: State (2-letter code)
- `zip`: ZIP code

### BLACKLIST_NAMES Sheet
Names to filter out (e.g., registered agents):
- `blacklist_name`: Name to exclude

## Output Files

All outputs are saved to the `results/` directory with timestamps:

- `input/filtered_input_YYYYMMDD_HHMMSS.xlsx`: Input after blacklist filtering
- `skiptrace/skiptrace_results_YYYYMMDD_HHMMSS.xlsx`: Raw skip-trace results  
- `phone_scrub/phones_scrubbed_YYYYMMDD_HHMMSS.xlsx`: Phone numbers after scrubbing
- `final_contacts_YYYYMMDD_HHMMSS.xlsx`: Final aggregated results

**Note**: API inputs are saved as CSV (required by BatchData APIs), while processed outputs use XLSX format.

## API Endpoints (V1)

The pipeline uses BatchData V1 API endpoints:

### Skip-Trace
- **Sync**: `POST /api/v1/property/skip-trace`
- **Async**: `POST /api/v1/property/skip-trace/async` (Core functionality)

### Phone Operations
- **Verification**: `POST /api/v1/phone/verification/async`
- **DNC Check**: `POST /api/v1/phone/dnc/async`
- **TCPA Check**: `POST /api/v1/phone/tcpa/async`

### Address & Property (Optional)
- **Address Verify**: `POST /api/v1/address/verify`
- **Property Search**: `POST /api/v1/property/search/async`
- **Property Lookup**: `POST /api/v1/property/lookup/async`

**Note**: See `V1_API_REFERENCE.md` for complete API documentation

## Cost Structure

Estimated costs per record:
- Skip-trace: $0.07
- Phone verification: $0.007 per phone
- DNC check: $0.002 per phone  
- TCPA check: $0.002 per phone

## Error Handling

- Network errors: Exponential backoff with retries
- Job failures: Logged to `results/_failed_jobs.csv`
- API errors: Detailed error logging
- Timeouts: Configurable polling with max attempts

## Development

### Running Tests

Create test data:
```bash
python create_test_input.py
```

Test with small dataset:
```bash
python -m src.run --input batchdata_local_input.xlsx --dry-run
```

### Module Structure

- `src/io.py`: Excel/CSV I/O operations
- `src/normalize.py`: Data cleaning and normalization
- `src/transform.py`: Data format transformations
- `src/batchdata.py`: API client and async operations
- `src/run.py`: CLI interface and pipeline orchestration

## Troubleshooting

1. **Import Errors**: Ensure `PYTHONPATH` includes the `src` directory
2. **API Key Errors**: Verify all required keys are set in `.env`
3. **File Not Found**: Check input file paths and working directory
4. **Network Errors**: Check internet connection and API endpoints
5. **Memory Issues**: Reduce `batch.size` in CONFIG for large datasets

## License

This project is proprietary software for BatchData pipeline processing.