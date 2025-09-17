# ADHS ETL Pipeline

Python ETL pipeline for processing Arizona Department of Health Services (ADHS) provider data.

## Features

- Processes raw ADHS Excel workbooks
- Field mapping with automatic unknown column detection
- Fuzzy matching for provider deduplication
- MCAO geocoding integration (stub)
- Dry-run mode for testing
- Comprehensive test coverage (≥80%)

## Installation

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

## Usage

### Basic ETL Run

```bash
poetry run adhs-etl run --month 2025-05 --raw-dir ./raw
```

### Dry Run Mode

```bash
poetry run adhs-etl run --month 2025-05 --raw-dir ./raw --dry-run
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