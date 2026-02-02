# ADHS ETL Pipeline

Python ETL pipeline for processing Arizona Department of Health Services (ADHS) provider data.

## Features

- Processes raw ADHS Excel workbooks from monthly snapshots
- Interactive menu for selecting date ranges to process
- Field mapping with automatic unknown column detection
- Provider deduplication using fuzzy matching
- MCAO geocoding integration for location data
- APN (Assessor Parcel Number) lookup for Maricopa County properties
- Ecorp (ACC) entity lookup integration for ownership research
- Generates three output types: Reformat, All-to-Date, and Analysis files
- Comprehensive test coverage (≥80%)

## Installation

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Chrome browser required for Ecorp processing
# Install Chrome from: https://www.google.com/chrome/

# Install dependencies
poetry install

# Install APN lookup dependencies
pip3 install usaddress
```

## Usage

### Automated Data Acquisition (Recommended)

The pipeline includes automatic monitoring and downloading of AZDHS provider data:

```bash
# One-time setup
./scripts/setup_azdhs_monitor.sh

# Check for new month data
poetry run python scripts/azdhs_monitor.py --check-only

# Download specific month
poetry run python scripts/azdhs_monitor.py --month 1.26 --force

# Auto-check + download + notify (runs daily via scheduler)
poetry run python scripts/azdhs_monitor.py --notify
```

**Features:**
- Monitors https://www.azdhs.gov/licensing/index.php#databases daily
- Auto-downloads all 12 provider types when new month appears
- Sends Slack + Gmail notifications
- Saves to `ALL-MONTHS/Raw M.YY/` directory
- Optional Supabase sync

**Scheduling Options:**
- macOS: LaunchAgent runs daily at 6 AM (`scripts/com.azdhs.monitor.plist`)
- CI/CD: GitHub Actions workflow (`.github/workflows/azdhs-monitor.yml`)

### Primary Method: Interactive Month Processor

The main entry point for processing ADHS data is the interactive script:

```bash
poetry run python scripts/process_months_local.py
```

This will:
1. Scan the `ALL-MONTHS/` directory for available data
2. Present an interactive menu to select start and end months
3. Process the selected range sequentially
4. Generate outputs in `Reformat/`, `All-to-Date/`, and `Analysis/` directories

### Alternative: CLI Interface

For single-month processing or automation:

```bash
poetry run adhs-etl run --month 1.25 --raw-dir ./ALL-MONTHS/Raw\ 1.25
```

### Dry Run Mode

```bash
poetry run adhs-etl run --month 1.25 --raw-dir ./ALL-MONTHS/Raw\ 1.25 --dry-run
```

### Validate Field Mapping

```bash
poetry run adhs-etl validate --field-map field_map.yml
```

## Configuration

### Environment Variables

Copy `.env.sample` to `.env` and configure:

```bash
# Main ETL Configuration
MCAO_API_KEY=your-api-key
FUZZY_THRESHOLD=80.0
LOG_LEVEL=INFO

# BatchData API Keys (Optional - Stage 5 enrichment)
BD_SKIPTRACE_KEY=your-batchdata-key
BD_ADDRESS_KEY=your-batchdata-key
BD_PROPERTY_KEY=your-batchdata-key
BD_PHONE_KEY=your-batchdata-key
```

### Field Mapping

Edit `field_map.yml` to configure column mappings:

```yaml
"Provider Name": "name"
"Provider Address": "address"
"License Number": "license_number"
```

Unknown columns are automatically added to `field_map.TODO.yml`.

## Output Files

The pipeline generates multiple output types with standardized naming: `M.YY_{Stage}_{timestamp}.xlsx`

Where:
- `M.YY` is the month code (e.g., `1.25` for January 2025)
- `{Stage}` is the processing stage (Reformat, Analysis, APN_Upload, etc.)
- `{timestamp}` is `MM.DD.HH-MM-SS` format (12-hour, no AM/PM)

### Core Pipeline Outputs

- **Reformat**: `M.YY_Reformat_{timestamp}.xlsx`
  - Standardized provider data with MONTH, YEAR, ADDRESS, COORDINATES, etc.

- **All-to-Date**: `M.YY_Reformat_All_to_Date_{timestamp}.xlsx`
  - Cumulative data across all processed months

- **Analysis**: `M.YY_Analysis_{timestamp}.xlsx`
  - Full business analysis with Summary, Blanks Count, and lost license detection
  - **v300 Template Compliance**: Must match `v300Track_this.xlsx` exactly (155 columns)
  - Column naming uses underscores (`PROVIDER_TYPE`, `9.24_COUNT`, `10.24_TO_PREV`)
  - See `v300Track_this.md` for complete field definitions

### Optional Enrichment Stages

- **APN Upload**: `M.YY_APN_Upload_{timestamp}.xlsx`
  - MARICOPA-only records extracted for parcel number lookup

- **APN Complete**: `M.YY_APN_Complete_{timestamp}.xlsx`
  - APN Upload enriched with Assessor Parcel Numbers

- **MCAO Upload**: `M.YY_MCAO_Upload_{timestamp}.xlsx`
  - Filtered APNs ready for property data enrichment

- **MCAO Complete**: `M.YY_MCAO_Complete_{timestamp}.xlsx`
  - Full property data with 84 fields from Maricopa County Assessor

- **Ecorp Upload**: `M.YY_Ecorp_Upload_{timestamp}.xlsx`
  - Filtered MCAO data prepared for ACC entity lookup (4 columns)

- **Ecorp Complete**: `M.YY_Ecorp_Complete_{timestamp}.xlsx`
  - Full entity details with principals and registration data (93 columns)
  - Includes ECORP_INDEX_# (sequential record number) and ECORP_URL (ACC entity detail page)

- **BatchData Upload**: `M.YY_BatchData_Upload_{timestamp}.xlsx`
  - Ecorp Complete data prepared for contact discovery APIs

- **BatchData Complete**: `M.YY_BatchData_Complete_{timestamp}.xlsx`
  - Enriched with phone numbers, emails, DNC/TCPA compliance, phone verification

### Backward Compatibility

During the transition period, the pipeline creates both:
- New format: `1.25_Reformat_01.15.03-45-30.xlsx`
- Legacy format: `1.25 Reformat.xlsx` (for compatibility)

## Individual Stage Commands

### ETL-Integrated Commands

The main processing script handles the full pipeline:

```bash
# Interactive menu (recommended)
poetry run python scripts/process_months_local.py

# Single month via CLI
poetry run adhs-etl run --month 1.25 --raw-dir ./ALL-MONTHS/Raw\ 1.25
```

### Standalone Stage Commands

Each enrichment stage can also be run independently for testing or reprocessing:

#### APN Lookup (Standalone)

```bash
# Process a single APN Upload file
python3 APN/apn_lookup.py -i APN/Upload/1.25_APN_Upload_{timestamp}.xlsx --rate 5.0
```

#### MCAO Enrichment (Standalone)

```bash
# Test MCAO API integration
poetry run python scripts/test_mcao_standalone.py
```

#### Ecorp Entity Lookup (Standalone)

```bash
# Run Ecorp processing on MCAO Complete file
poetry run python scripts/test_ecorp_standalone.py
```

#### BatchData Enrichment (Standalone)

```bash
# Using the local test input (includes CONFIG, INPUT_MASTER, BLACKLIST_NAMES)
cd Batchdata
python3 src/run.py --input tests/batchdata_local_input.xlsx --dry-run

# Using ETL-generated Upload file
python3 src/run.py --input Upload/1.25_BatchData_Upload_{timestamp}.xlsx --template-output --dedupe --consolidate-families --filter-entities
```

**Note**: For BatchData standalone usage, the input file must contain three sheets:
- `CONFIG`: API keys and settings
- `INPUT_MASTER`: Records to process
- `BLACKLIST_NAMES`: Names to filter out

See `Batchdata/tests/batchdata_local_input.xlsx` for the complete structure.

## Development

### Running Tests

```bash
poetry run pytest
```

### With Coverage

```bash
poetry run pytest --cov=adhs_etl --cov-fail-under=80
```

### Linting

```bash
poetry run ruff check src/
poetry run black src/
```

## License

MIT