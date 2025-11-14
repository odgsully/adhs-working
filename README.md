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

### Primary Method: Interactive Month Processor

The main entry point for processing ADHS data is the interactive script:

```bash
python scripts/process_months_local.py
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

Copy `.env.example` to `.env` and configure:

```bash
MCAO_API_KEY=your-api-key
FUZZY_THRESHOLD=80.0
LOG_LEVEL=INFO
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

The pipeline generates multiple output types:

- **Reformat**: Standardized provider data with MONTH, YEAR, ADDRESS, COORDINATES, etc.
- **All-to-Date**: Cumulative data across all processed months
- **Analysis**: Full business analysis with Summary, Blanks Count, and lost license detection
- **APN Upload**: MARICOPA-only records extracted for parcel number lookup
- **APN Complete**: APN Upload enriched with Assessor Parcel Numbers
- **MCAO Upload**: Filtered APNs ready for property data enrichment
- **MCAO Complete**: Full property data with 84 fields from Maricopa County Assessor
- **Ecorp Upload**: Filtered MCAO data prepared for ACC entity lookup (4 columns)
- **Ecorp Complete**: Full entity details with principals and registration data (26 columns)

## Optional: BatchData Enrichment

For additional contact discovery via skip-trace APIs, see the BatchData pipeline in `/Batchdata/`. This optional post-processing step can enrich Ecorp Complete files with:
- Phone number discovery
- Email discovery
- DNC/TCPA compliance filtering
- Phone verification

See `/Batchdata/README.md` for setup and usage instructions.

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