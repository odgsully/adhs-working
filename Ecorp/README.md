# Ecorp Pipeline

Arizona Corporation Commission (ACC) entity lookup and enrichment pipeline for ADHS provider ownership data.

## Overview

The Ecorp pipeline enriches MCAO property data with Arizona Corporation Commission entity information to discover business ownership details, principals, statutory agents, and contact information.

### Input

MCAO_Complete files from the MCAO enrichment stage:
- Location: `MCAO/Complete/`
- Pattern: `M.YY_MCAO_Complete_{timestamp}.xlsx`
- Contains: 84 columns of property data including Owner_Ownership field

### Output

**Ecorp Upload** (intermediate):
- Location: `Ecorp/Upload/`
- Pattern: `M.YY_Ecorp_Upload_{timestamp}.xlsx`
- Columns: 4 (FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE)
- Purpose: Filtered extract ready for ACC enrichment

**Ecorp Complete** (final):
- Location: `Ecorp/Complete/`
- Pattern: `M.YY_Ecorp_Complete_{timestamp}.xlsx`
- Columns: **93** (Upload + Index + ACC Entity + URL)
- Purpose: Comprehensive ownership and entity data

## Pipeline Stages

### Stage 1: Upload Generation

Extracts ownership data from MCAO_Complete:

```
MCAO_Complete (84+ cols) → Ecorp Upload (4 cols)
```

**Extracted Columns**:
- Column A: FULL_ADDRESS (from MCAO col A)
- Column B: COUNTY (from MCAO col B)
- Column C: Owner_Ownership (from MCAO col E)
- Column D: OWNER_TYPE (classified as BUSINESS or INDIVIDUAL)

**Classification Logic**:
- Scans Owner_Ownership for business keywords (LLC, CORP, INC, TRUST, etc.)
- Returns "BUSINESS" if entity keywords found
- Returns "INDIVIDUAL" for simple personal names

### Stage 2: ACC Enrichment

Enriches Upload with ACC entity data:

```
Ecorp Upload (4 cols) → Ecorp Complete (93 cols)
```

**For BUSINESS Owners**:
1. Search ACC database by Owner_Ownership name
2. Parse entity details from search results
3. Extract principals from entity detail page
4. Capture statutory agent information
5. Save entity detail page URL

**For INDIVIDUAL Owners**:
1. Skip ACC lookup (not businesses)
2. Parse Owner_Ownership into individual names
3. Populate IndividualName1-4 fields

**For Blank Owners**:
- All ACC fields left blank

### Output Structure (93 Columns)

**Upload Columns (A-C, E)** - 4 fields
- FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE

**Index Column (D)** - 1 field
- **ECORP_INDEX_#** - Sequential record number (1, 2, 3...)

**ACC Entity Columns (F-P)** - 11 fields
- ECORP_SEARCH_NAME, ECORP_TYPE, ECORP_NAME_S, ECORP_ENTITY_ID_S, ECORP_ENTITY_TYPE, ECORP_STATUS, ECORP_FORMATION_DATE, ECORP_BUSINESS_TYPE, ECORP_STATE, ECORP_COUNTY, ECORP_COMMENTS

**Statutory Agent Columns (Q-AB)** - 12 fields
- StatutoryAgent1-3: Name, Address, Phone, Mail (4 fields × 3 agents)

**Manager Columns (AC-AV)** - 20 fields
- Manager1-5: Name, Address, Phone, Mail (4 fields × 5 managers)

**Manager/Member Columns (AW-BP)** - 20 fields
- Manager/Member1-5: Name, Address, Phone, Mail (4 fields × 5)

**Member Columns (BQ-CJ)** - 20 fields
- Member1-5: Name, Address, Phone, Mail (4 fields × 5 members)

**Individual Name Columns (CK-CN)** - 4 fields
- IndividualName1-4 (for non-business owners)

**URL Column (CO)** - 1 field
- **ECORP_URL** - ACC entity detail page URL from ecorp.azcc.gov

See [FIELD_MAPPING.md](FIELD_MAPPING.md) for comprehensive field documentation.

## Usage

### Interactive Processing (Recommended)

```bash
python scripts/test_ecorp_standalone.py
```

This launches an interactive menu where you can:
- Select month(s) to process
- Choose processing mode (full, upload-only, sample, test, dry-run)
- Configure browser mode (headless or visible)

### Command Line Processing

**Process specific month:**
```bash
python scripts/test_ecorp_standalone.py --month 1.25
```

**Upload only (skip ACC lookup):**
```bash
python scripts/test_ecorp_standalone.py --month 1.25 --upload-only
```

**Visible browser (for debugging):**
```bash
python scripts/test_ecorp_standalone.py --month 1.25 --no-headless
```

**Dry run (preview without processing):**
```bash
python scripts/test_ecorp_standalone.py --month 1.25 --dry-run
```

### Python API

```python
from src.adhs_etl.ecorp import generate_ecorp_upload, generate_ecorp_complete
from pathlib import Path

# Step 1: Generate Upload
month = "1.25"
mcao_file = Path("MCAO/Complete/1.25_MCAO_Complete_{timestamp}.xlsx")
upload_path = generate_ecorp_upload(month, mcao_file)

# Step 2: Enrich with ACC data
if upload_path:
    success = generate_ecorp_complete(month, upload_path, headless=True)
```

## Performance

**Processing Speed**:
- BUSINESS records: ~4 seconds each (ACC lookup required)
- INDIVIDUAL records: Instant (no lookup)
- Average file with 1,000 owners: ~60-70 minutes

**Optimization Features**:
- In-memory caching (avoids duplicate ACC lookups)
- Progress checkpointing every 50 records
- Resume capability after interruption
- Headless browser mode for background processing

**Interruption Handling**:
- Press Ctrl+C to interrupt processing
- Progress automatically saved to `.checkpoint_{month}.pkl`
- Rerun same command to resume from last checkpoint

## Requirements

### Dependencies

```bash
# Chrome browser (required for Selenium)
# Download from: https://www.google.com/chrome/

# Python packages (installed via poetry)
poetry install

# Key packages:
# - selenium
# - beautifulsoup4
# - pandas
# - webdriver-manager
```

### Configuration

No special configuration required. The pipeline uses:
- Chrome WebDriver (auto-installed via webdriver-manager)
- ACC public website (no API key required)

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│ MCAO_Complete (84+ columns)                         │
│ - Property data with Owner_Ownership                │
└────────────────┬────────────────────────────────────┘
                 │
                 ├─ Extract 4 columns
                 ↓
┌─────────────────────────────────────────────────────┐
│ Ecorp Upload (4 columns)                            │
│ - FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE │
└────────────────┬────────────────────────────────────┘
                 │
                 ├─ For each record:
                 │  ├─ Generate ECORP_INDEX_# (sequential)
                 │  ├─ If BUSINESS → ACC web scraping
                 │  ├─ If INDIVIDUAL → Parse names
                 │  └─ If Blank → Skip lookup
                 ↓
┌─────────────────────────────────────────────────────┐
│ Ecorp Complete (93 columns)                         │
│ - Upload + Index + ACC Entity + Principals + URL    │
└─────────────────────────────────────────────────────┘
```

## Key Features

### Owner Type Classification

Automatically classifies owners as BUSINESS or INDIVIDUAL based on:
- 74+ business entity keywords (LLC, CORP, INC, TRUST, SCHOOL, etc.)
- Name patterns (2-4 word personal names)
- See `src/adhs_etl/ecorp.py:classify_owner_type()` for logic

### Individual Name Parsing

For INDIVIDUAL owners, parses complex name formats:
- "MCCORMICK TIMOTHY/ROBIN" → ["TIMOTHY MCCORMICK", "ROBIN MCCORMICK"]
- "SOTO JEREMY/SIPES CAROLYN" → ["JEREMY SOTO", "CAROLYN SIPES"]
- "GREEN JEROME V" → ["JEROME V GREEN"]
- Handles suffixes: TR, TRUST, TRUSTEE, ET AL, etc.
- Reorders: "LASTNAME FIRSTNAME" → "FIRSTNAME LASTNAME"
- Up to 4 individual names per record

### Sequential Indexing

**ECORP_INDEX_#** provides:
- Unique identifier for each record
- Simple sequential numbering (1, 2, 3...)
- Facilitates record tracking and cross-referencing

### URL Capture

**ECORP_URL** enables:
- Direct access to ACC entity detail page
- Manual verification of scraped data
- Additional research and due diligence
- Format: `https://ecorp.azcc.gov/EntitySearch/Details?entityNumber=L12345678`

## Troubleshooting

### Chrome Driver Issues

If Selenium fails to start:
```bash
# Update Chrome to latest version
# Restart terminal
# Clear webdriver cache
rm -rf ~/.wdm
```

### Checkpoint Recovery

If processing is interrupted:
```bash
# Check for checkpoint file
ls -lh Ecorp/.checkpoint_*.pkl

# Resume by running same command again
python scripts/test_ecorp_standalone.py --month 1.25
```

### Blank Results

If all ACC fields are blank:
- Check if Owner_Ownership contains business entity keywords
- Verify OWNER_TYPE is "BUSINESS" (not "INDIVIDUAL")
- Try visible browser mode to see what's happening: `--no-headless`
- Check ACC website availability: https://ecorp.azcc.gov/EntitySearch/Index

### Slow Performance

To speed up processing:
- Use headless mode (default)
- Process during off-peak hours
- Check internet connection speed
- Consider sample mode for testing: `-s` flag

## Next Steps

After Ecorp processing, data can flow to:
- **BatchData Pipeline**: `/Batchdata/` for phone/email enrichment via skip-trace APIs
- **CRM/Dialer Systems**: Using v300 dialer template format
- **Business Intelligence**: Analysis of ownership patterns and entity structures

## Documentation

- [FIELD_MAPPING.md](FIELD_MAPPING.md) - Comprehensive 93-column field documentation
- [../README.md](../README.md) - Overall ADHS ETL pipeline overview
- [../CLAUDE.md](../CLAUDE.md) - Development and operating guidelines
- `src/adhs_etl/ecorp.py` - Source code with inline documentation

## Support

For issues or questions:
1. Check documentation in this directory
2. Review source code comments in `src/adhs_etl/ecorp.py`
3. Test with sample mode first: `python scripts/test_ecorp_standalone.py` → choose 's' mode
4. Enable visible browser for debugging: `--no-headless`
