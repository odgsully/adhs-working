# ADHS-ETL Pipeline Index

## Core Entry Points
- **CLI**: `src/adhs_etl/cli.py:7` → redirects to `cli_enhanced.py`
- **Enhanced CLI**: `src/adhs_etl/cli_enhanced.py:57` → main command handler
- **Poetry Script**: Defined in `pyproject.toml:18`

## Configuration & Settings
- **Settings Class**: `src/adhs_etl/config.py:8` → Pydantic-based configuration
- **Environment Variables**: `.env` file support via pydantic-settings

## Data Transformation Pipeline

### Field Mapping
- **Base Mapper**: `src/adhs_etl/transform.py:31` → FieldMapper class
- **Enhanced Mapper**: `src/adhs_etl/transform_enhanced.py:49` → EnhancedFieldMapper
- **Field Map YAML**: `src/adhs_etl/field_map.yml` → column mappings
- **TODO Tracking**: `src/adhs_etl/field_map.TODO.yml` → unknown columns

### Provider Grouping
- **Grouper Class**: `src/adhs_etl/transform_enhanced.py:77` → ProviderGrouper
- **Address Matching**: Exact match on first 20 chars
- **Name Matching**: Fuzzy match at 85% threshold using rapidfuzz

### Analysis Engine
- **Analyzer**: `src/adhs_etl/analysis.py:77` → ProviderAnalyzer class
- **Lead Detection**: `src/adhs_etl/analysis.py:228` → identify_leads method
- **Summary Generation**: `src/adhs_etl/analysis.py:283` → create_summary method

## Data Processing Functions
- **Main Runner**: `src/adhs_etl/runner.py:208` → run_etl_pipeline
- **Process Month**: `src/adhs_etl/runner.py:23` → process_month_data
- **Output Generation**: `src/adhs_etl/runner.py:127` → generate_outputs

## API Integration
- **MCAO Geocoder**: `src/adhs_etl/mca_api.py:11` → MCAPGeocoder (stub)
- **Property Data**: Planned integration for APN, owner info, etc.

## Batch Processing Scripts
- **Interactive**: `scripts/batch_process_months.py` → user-guided processing
- **Automated**: `scripts/batch_auto.py` → unattended batch runs
- **Fast Batch**: `scripts/fast_batch.py` → optimized for speed

## Testing Infrastructure
- **Config Tests**: `src/tests/test_config.py`
- **Transform Tests**: `src/tests/test_transform.py`
- **Analysis Tests**: `src/tests/test_analysis.py`
- **Runner Tests**: `src/tests/test_runner.py`
- **Fixtures**: `src/tests/fixtures/` → sample data files

## Output File Handlers
- **Reformat Files**: `runner.py:127` → standardized monthly data
- **All-to-Date Files**: `runner.py:156` → cumulative historical data
- **Analysis Files**: `runner.py:184` → business intelligence output

## Key Data Models

### Input Files (by Provider Type)
- ASSISTED_LIVING_HOME.xlsx
- NURSING_HOME.xlsx
- BEHAVIORAL_HEALTH_OUTPATIENT_CLINIC.xlsx
- ADULT_BEHAVIORAL_HEALTH_HOME.xlsx
- BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY.xlsx
- ADULT_CARE_HOME.xlsx
- ADULT_DAY_HEALTH_CARE.xlsx
- HOME_AND_COMMUNITY_BASED_SERVICE.xlsx
- CHILD_DEVELOPMENT_HOME.xlsx
- CHILD_WELFARE_RESIDENTIAL_GROUP_CARE_FACILITY.xlsx
- SUBSTANCE_ABUSE_TREATMENT_TRANSITIONAL_FACILITY.xlsx

### Standard Output Columns
1. MONTH
2. YEAR
3. PROVIDER TYPE
4. PROVIDER
5. ADDRESS
6. CITY
7. ZIP
8. CAPACITY
9. LONGITUDE
10. LATITUDE
11. PROVIDER GROUP INDEX #

### Analysis Output (77 columns)
- Provider info (cols 1-11)
- MCAO data (cols 12-21) - placeholder
- Historical tracking (cols 22-37)
- Change analysis (cols 38-77)

## Utility Functions
- **File Utils**: `src/adhs_etl/utils/file_utils.py`
- **Month Parsing**: `cli_enhanced.py:18` → parse_month function
- **Logger Setup**: Throughout modules using Python logging

## Configuration Files
- **Poetry**: `pyproject.toml` → dependencies & scripts
- **Pre-commit**: `.pre-commit-config.yaml` → code quality hooks
- **Ruff**: `pyproject.toml:33` → linting configuration
- **Black**: `pyproject.toml:44` → formatting configuration

## Data Flow Summary
1. **Input**: Excel files from Raw-New-Month/ or ALL-MONTHS/Raw M.YY/
2. **Transform**: Field mapping → uppercase → provider grouping
3. **Analyze**: Historical comparison → lead identification
4. **Output**: Three Excel files (Reformat, All-to-Date, Analysis)

## Command Examples
```bash
# Process single month
poetry run adhs-etl run --month 1.25 --raw-dir ./Raw-New-Month

# Dry run mode
poetry run adhs-etl run --month 1.25 --dry-run

# Batch processing
poetry run python scripts/batch_process_months.py
```