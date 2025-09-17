# BatchData Bulk Pipeline

A Python package for processing bulk skip-trace operations using BatchData APIs. This pipeline transforms eCorp entity data into BatchData format and processes it through various API endpoints including skip-trace, phone verification, DNC checking, and TCPA compliance.

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

2. Copy environment template:
```bash
cp .env.example .env
```

3. Configure your BatchData API keys in `.env`:
```bash
BD_SKIPTRACE_KEY=your_skiptrace_api_key_here
BD_ADDRESS_KEY=your_address_verify_api_key_here
BD_PROPERTY_KEY=your_property_api_key_here
BD_PHONE_KEY=your_phone_verification_api_key_here
```

## Usage

### Basic Usage

Process a template file with INPUT_MASTER data:
```bash
python -m src.run --input batchdata_local_input.xlsx
```

### Transform eCorp Data

Transform and process eCorp data:
```bash
python -m src.run --input template.xlsx --ecorp ../8.25\ ecorp\ complete.xlsx
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

## API Endpoints

The pipeline supports these BatchData endpoints:

- **property-skip-trace-async**: Core skip-trace functionality
- **phone-verification-async**: Phone number verification
- **phone-dnc-async**: Do-Not-Call checking
- **phone-tcpa-async**: TCPA litigation checking
- **address-verify**: Address standardization (optional)
- **property-search-async**: Property search (optional)
- **property-lookup-async**: Property lookup (optional)

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