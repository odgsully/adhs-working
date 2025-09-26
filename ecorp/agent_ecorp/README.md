
# ACC Entity Lookup & Contact Discovery Pipeline

This project provides a complete two-stage pipeline for:
1. **Stage 1**: Automating Arizona Corporation Commission (ACC) entity lookups via web scraping
2. **Stage 2**: Enriching entity data with contact information through BatchData skip-trace APIs

## Quick Overview

```
Input: Company Names → ACC Lookup → Entity Details → Skip-Trace → Contact Discovery → Verified Phone Numbers
```

- **Start**: Excel file with company names (`M.YY_Ecorp_Upload *.xlsx`)
- **Stage 1 Output**: Complete entity details with principals (`M.YY_Ecorp_Complete *.xlsx`)  
- **Stage 2 Output**: Verified mobile phone numbers for each principal (`final_contacts_*.xlsx`)

## Features

### Stage 1: ACC Entity Lookup
- Automated web scraping of [Arizona Corporation Commission Entity Search](https://ecorp.azcc.gov/EntitySearch/Index)
- Extracts 22 data fields including:
  - Entity Name, ID, Type, Status
  - Formation Date, Business Type
  - Statutory Agent & Address
  - Up to 3 Principal Officers with details
- Handles multiple search results and no-result scenarios
- Browser automation via Selenium

### Stage 2: BatchData Contact Discovery
- Transforms entity data into individual contact records
- Discovers phone numbers and emails via skip-trace APIs
- Performs compliance filtering:
  - Phone verification (active/valid)
  - Do-Not-Call (DNC) registry check
  - TCPA litigation database check
- Outputs up to 10 verified mobile numbers per person

## Installation

1. Clone this repository
2. Install Stage 1 dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Stage 2 dependencies:
   ```bash
   cd pipeline
   pip install -r requirements.txt
   ```

4. Configure BatchData API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Usage

### Stage 1: ACC Entity Lookup

Basic usage:
```bash
python main.py --input "M.YY_Ecorp_Upload *.xlsx" --output "M.YY_Ecorp_Complete *.xlsx"
```

Debug mode (visible browser):
```bash
python main.py --input "input.xlsx" --output "output.xlsx" --no-headless
```

### Stage 2: BatchData Processing

Transform and process eCorp data:
```bash
cd pipeline
python -m src.run --input template.xlsx --ecorp "../M.YY_Ecorp_Complete *.xlsx"
```

Process pre-formatted data:
```bash
python -m src.run --input batchdata_local_input.xlsx
```

Dry run (cost estimation only):
```bash
python -m src.run --input batchdata_local_input.xlsx --dry-run
```

## Input/Output Files

### Stage 1
- **Input**: Excel with `Owner_Ownership` column containing company names
- **Output**: Excel with 22 columns of entity details and principal information

### Stage 2
- **Input**: Stage 1 output or any Excel with entity/principal data
- **Output**: `pipeline/results/final_contacts_[timestamp].xlsx` with verified phone numbers

## Cost Structure

- **Stage 1**: Free (web scraping)
- **Stage 2**: BatchData API costs
  - Skip-trace: $0.07 per record
  - Phone verification: $0.007 per phone
  - DNC check: $0.002 per phone
  - TCPA check: $0.002 per phone
  - **Typical total**: $0.08-0.10 per input record

## Project Structure

```
agent_ecorp/
├── main.py                      # Stage 1: ACC lookup script
├── M.YY_Ecorp_Upload *.xlsx     # Sample Stage 1 input
├── M.YY_Ecorp_Complete *.xlsx   # Sample Stage 1 output
├── pipeline/                     # Stage 2: BatchData processing
│   ├── src/                     # Pipeline source code
│   └── results/                 # Output directory
└── CLAUDE.md                    # Detailed documentation
```

## Requirements

- Python 3.7+
- Chrome browser (for Selenium)
- BatchData API keys (for Stage 2)

## Documentation

See [CLAUDE.md](CLAUDE.md) for comprehensive documentation including:
- Detailed workflow descriptions
- API endpoint specifications
- Configuration options
- Troubleshooting guide
- Performance metrics

## License

Proprietary software for ACC entity lookup and BatchData processing.
