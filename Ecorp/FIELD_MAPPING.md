# Ecorp Field Mapping Documentation

## Overview

The Ecorp Complete file contains **93 columns (A-CO)** that combine MCAO property data with Arizona Corporation Commission (ACC) entity information.

**File Pattern**: `M.YY_Ecorp_Complete_{timestamp}.xlsx`

**Total Column Breakdown**:
- 3 Upload columns (A-C): Address and ownership from MCAO
- 1 Index column (D): Sequential record number
- 1 Owner type column (E): Classified owner type
- 88 ACC entity columns (F-CO): Entity details, principals, and URL

---

## Upload Columns (A-C, E) - 4 Fields

These columns are extracted from MCAO_Complete files.

| Column | Field Name | Source | Population Logic | Data Type | Example |
|--------|------------|--------|------------------|-----------|---------|
| **A** | FULL_ADDRESS | MCAO_Complete Column A | Direct copy | Text | "123 MAIN ST, PHOENIX, AZ 85001" |
| **B** | COUNTY | MCAO_Complete Column B | Direct copy | Text | "MARICOPA" |
| **C** | Owner_Ownership | MCAO_Complete Column E | Direct copy | Text | "SMITH PROPERTIES LLC" |
| **E** | OWNER_TYPE | Classified from Owner_Ownership | `classify_owner_type(Owner_Ownership)`<br/>Returns "BUSINESS" or "INDIVIDUAL" based on keyword matching | Text | "BUSINESS" |

**OWNER_TYPE Classification Logic**:
- Scans Owner_Ownership for 74+ entity keywords (LLC, CORP, INC, TRUST, SCHOOL, etc.)
- Returns "BUSINESS" if entity keywords found
- Returns "INDIVIDUAL" for simple 2-4 word names without business keywords
- See `src/adhs_etl/ecorp.py:classify_owner_type()` for full logic

---

## Index Column (D) - 1 Field

| Column | Field Name | Source | Population Logic | Data Type | Example |
|--------|------------|--------|------------------|-----------|---------|
| **D** | ECORP_INDEX_# | Generated | Sequential record number:<br/>`idx + 1` where idx is the row index | Integer | 1, 2, 3, 4... |

**Purpose**: Unique identifier for each record in the Ecorp Complete file, facilitates record tracking and referencing.

---

## ACC Entity Core Columns (F-P) - 11 Fields

These columns contain basic entity information scraped from the Arizona Corporation Commission website.

| Column | Field Name | Source | Population Logic | Data Type | Example |
|--------|------------|--------|------------------|-----------|---------|
| **F** | Search Name | Owner_Ownership value used for search | Copy of Owner_Ownership (Column C) | Text | "SMITH PROPERTIES LLC" |
| **G** | Type | Classification result | `classify_name_type(Owner_Ownership)`<br/>Returns "Entity" or "Individual(s)" | Text | "Entity" |
| **H** | Entity Name(s) | ACC entity search result | Entity name from ACC search results table<br/>Blank if not found | Text | "SMITH PROPERTIES, LLC" |
| **I** | Entity ID(s) | ACC entity ID | Entity ID/File Number from ACC<br/>Blank if not found | Text | "L12345678" |
| **J** | Entity Type | ACC detail page | Scraped from "Entity Type:" field<br/>Blank if not found | Text | "LLC" |
| **K** | Status | ACC detail page | Scraped from "Entity Status:" field<br/>Blank if not found | Text | "Active" |
| **L** | Formation Date | ACC detail page | Scraped from "Formation Date:" field<br/>Blank if not found | Date/Text | "01/15/2020" |
| **M** | Business Type | ACC detail page | Scraped from "Business Type:" field<br/>Blank if not found | Text | "Domestic" |
| **N** | Domicile State | ACC detail page | Scraped from "Domicile State:" field<br/>Blank if not found | Text | "Arizona" |
| **O** | County | ACC detail page | Scraped from "County:" field for entity<br/>Different from Column B (property county) | Text | "MARICOPA" |
| **P** | Comments | Error tracking | Populated only if lookup error occurs<br/>Otherwise blank | Text | "Lookup error: timeout" |

**Population Conditions**:
- **BUSINESS owners**: Full ACC lookup performed, fields populated from search results
- **INDIVIDUAL owners**: ACC lookup skipped, all entity fields left blank
- **Blank owners**: All entity fields left blank
- **Not found**: Returns blank record with all fields empty

---

## Statutory Agent Columns (Q-AB) - 12 Fields

Up to 3 statutory agents extracted from ACC "Statutory Agent Information" section.

| Column | Field Name | Source | Population Logic | Data Type |
|--------|------------|--------|------------------|-----------|
| **Q** | StatutoryAgent1_Name | ACC detail page | Regex extraction from "Statutory Agent Information" section | Text |
| **R** | StatutoryAgent1_Address | ACC detail page | Regex extraction from agent address field | Text |
| **S** | StatutoryAgent1_Phone | ACC detail page | Reserved for phone if available | Text |
| **T** | StatutoryAgent1_Mail | ACC detail page | Reserved for email if available | Text |
| **U-X** | StatutoryAgent2_[Name/Address/Phone/Mail] | ACC detail page | Same as Agent1 | Text |
| **Y-AB** | StatutoryAgent3_[Name/Address/Phone/Mail] | ACC detail page | Same as Agent1 | Text |

**Extraction Logic**:
- Uses regex patterns to find "Name:" and "Address:" in Statutory Agent section
- Cleans up whitespace and formatting
- Phone and Mail fields currently not extracted (reserved for future)
- Maximum 3 agents supported
- See `src/adhs_etl/ecorp.py:get_statutory_agent_info()` for implementation

---

## Manager Columns (AC-AV) - 20 Fields

Up to 5 managers/managing members extracted from ACC Principal Information table.

| Column | Field Name | Source | Population Logic | Data Type |
|--------|------------|--------|------------------|-----------|
| **AC-AF** | Manager1_[Name/Address/Phone/Mail] | ACC principal table | Rows with title containing "MANAGER" (but not "MEMBER") | Text |
| **AG-AJ** | Manager2_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager1 | Text |
| **AK-AN** | Manager3_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager1 | Text |
| **AO-AR** | Manager4_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager1 | Text |
| **AS-AV** | Manager5_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager1 | Text |

**Extraction Logic**:
- Parses HTML table with id `grid_principalList`
- Filters by title field containing "MANAGER" (excluding "MANAGER/MEMBER")
- Extracts Name (col 1), Address (col 3) from table
- Phone/Mail extracted if present in additional columns
- Maximum 5 managers
- See `src/adhs_etl/ecorp.py:extract_principal_info()` for implementation

---

## Manager/Member Columns (AW-BP) - 20 Fields

Up to 5 principals with dual "Manager/Member" role.

| Column | Field Name | Source | Population Logic | Data Type |
|--------|------------|--------|------------------|-----------|
| **AW-AZ** | Manager/Member1_[Name/Address/Phone/Mail] | ACC principal table | Rows with title containing both "MANAGER" and "MEMBER" | Text |
| **BA-BD** | Manager/Member2_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager/Member1 | Text |
| **BE-BH** | Manager/Member3_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager/Member1 | Text |
| **BI-BL** | Manager/Member4_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager/Member1 | Text |
| **BM-BP** | Manager/Member5_[Name/Address/Phone/Mail] | ACC principal table | Same as Manager/Member1 | Text |

**Extraction Logic**:
- Same table source as Managers
- Filters for titles containing BOTH "MANAGER" AND "MEMBER"
- Maximum 5 manager/members

---

## Member Columns (BQ-CJ) - 20 Fields

Up to 5 members extracted from ACC Principal Information table.

| Column | Field Name | Source | Population Logic | Data Type |
|--------|------------|--------|------------------|-----------|
| **BQ-BT** | Member1_[Name/Address/Phone/Mail] | ACC principal table | Rows with title containing "MEMBER" (but not "MANAGER") | Text |
| **BU-BX** | Member2_[Name/Address/Phone/Mail] | ACC principal table | Same as Member1 | Text |
| **BY-CB** | Member3_[Name/Address/Phone/Mail] | ACC principal table | Same as Member1 | Text |
| **CC-CF** | Member4_[Name/Address/Phone/Mail] | ACC principal table | Same as Member1 | Text |
| **CG-CJ** | Member5_[Name/Address/Phone/Mail] | ACC principal table | Same as Member1 | Text |

**Extraction Logic**:
- Same table source as Managers
- Filters for titles containing "MEMBER" (excluding "MANAGER/MEMBER")
- Maximum 5 members

---

## Individual Name Columns (CK-CN) - 4 Fields

For INDIVIDUAL owner types, parsed names in "FIRSTNAME LASTNAME" format.

| Column | Field Name | Source | Population Logic | Data Type | Example |
|--------|------------|--------|------------------|-----------|---------|
| **CK** | IndividualName1 | Owner_Ownership parsed | `parse_individual_names()` output[0] | Text | "TIMOTHY MCCORMICK" |
| **CL** | IndividualName2 | Owner_Ownership parsed | `parse_individual_names()` output[1] | Text | "ROBIN MCCORMICK" |
| **CM** | IndividualName3 | Owner_Ownership parsed | `parse_individual_names()` output[2] | Text | |
| **CN** | IndividualName4 | Owner_Ownership parsed | `parse_individual_names()` output[3] | Text | |

**Population Conditions**:
- **BUSINESS owners**: All 4 fields left blank
- **INDIVIDUAL owners**: Fields populated from parsed Owner_Ownership
- **Blank owners**: All 4 fields left blank

**Parsing Logic** (`parse_individual_names()`):
- Handles patterns like "LASTNAME FIRSTNAME/FIRSTNAME2" → ["FIRSTNAME LASTNAME", "FIRSTNAME2 LASTNAME"]
- Handles "LASTNAME1 FIRSTNAME1/LASTNAME2 FIRSTNAME2" → separate full names
- Removes suffixes: TR, TRUST, TRUSTEE, ET AL, JT TEN, etc.
- Reorders from "LASTNAME FIRSTNAME MIDDLE" to "FIRSTNAME MIDDLE LASTNAME"
- Returns up to 4 individual names
- See `src/adhs_etl/ecorp.py:parse_individual_names()` for full implementation

**Examples**:
- Input: "MCCORMICK TIMOTHY/ROBIN" → ["TIMOTHY MCCORMICK", "ROBIN MCCORMICK"]
- Input: "SOTO JEREMY/SIPES CAROLYN" → ["JEREMY SOTO", "CAROLYN SIPES"]
- Input: "GREEN JEROME V" → ["JEROME V GREEN"]
- Input: "BARATTI JAMES J/DEBORAH F TR" → ["JAMES J BARATTI", "DEBORAH F BARATTI"]

---

## URL Column (CO) - 1 Field

| Column | Field Name | Source | Population Logic | Data Type | Example |
|--------|------------|--------|------------------|-----------|---------|
| **CO** | ECORP_URL | ACC search detail URL | Captured from `href` attribute when opening entity detail page<br/>Blank if entity not found | URL | "https://ecorp.azcc.gov/EntitySearch/Details?entityNumber=L12345678" |

**Purpose**: Direct link to the ACC entity detail page for manual verification and additional research.

**Population Conditions**:
- **BUSINESS with ACC match**: Full URL to entity detail page
- **BUSINESS not found**: Blank
- **INDIVIDUAL owners**: Blank (ACC lookup skipped)
- **Blank owners**: Blank

---

## Data Flow Summary

```
MCAO_Complete (84+ columns)
    ↓
Extract 4 columns → Ecorp Upload
    ↓
For each record:
    1. Classify OWNER_TYPE (BUSINESS/INDIVIDUAL)
    2. Generate ECORP_INDEX_# (sequential)
    3. If BUSINESS → ACC lookup via Selenium
       - Search by Owner_Ownership name
       - Parse entity details from result page
       - Extract principals from table
       - Capture detail page URL
    4. If INDIVIDUAL → Parse name into 1-4 individual names
    5. Combine all 93 columns
    ↓
Ecorp Complete (93 columns)
```

---

## Implementation Details

**Code Location**: `src/adhs_etl/ecorp.py`

**Key Functions**:
- `classify_owner_type()` - Determines BUSINESS vs INDIVIDUAL
- `classify_name_type()` - Determines Entity vs Individual(s)
- `parse_individual_names()` - Parses concatenated individual names
- `search_entities()` - Performs ACC web scraping
- `get_statutory_agent_info()` - Extracts statutory agent data
- `extract_principal_info()` - Extracts manager/member data from table
- `get_blank_acc_record()` - Returns empty 88-field ACC record
- `generate_ecorp_upload()` - Creates 4-column Upload file
- `generate_ecorp_complete()` - Enriches Upload with ACC data to create 93-column Complete file

**Performance Features**:
- In-memory caching to avoid duplicate ACC lookups
- Progress checkpointing every 50 records
- Graceful interrupt handling (Ctrl+C saves progress)
- Estimated rate: ~4 seconds per BUSINESS record
- INDIVIDUAL records process instantly (no lookup)

---

## Column Order Verification

To verify output matches template:
1. Read both files with pandas
2. Compare column names: `df.columns.tolist()`
3. Verify count: `len(df.columns)` should equal 93
4. Check order matches template exactly (A-CO)

---

## Usage Example

```python
from src.adhs_etl.ecorp import generate_ecorp_upload, generate_ecorp_complete
from pathlib import Path

# Step 1: Generate Upload file
month = "1.25"
mcao_file = Path("MCAO/Complete/1.25_MCAO_Complete_{timestamp}.xlsx")
upload_path = generate_ecorp_upload(month, mcao_file)

# Step 2: Enrich with ACC data
success = generate_ecorp_complete(month, upload_path, headless=True)
# Output: Ecorp/Complete/1.25_Ecorp_Complete_{timestamp}.xlsx (93 columns)
```

---

## Notes

- All ACC fields remain blank for INDIVIDUAL owner types (no lookup performed)
- All ACC fields remain blank if Owner_Ownership is blank
- Comments field (P) only populated on lookup errors
- Phone and Mail fields for principals/agents reserved for future extraction
- Maximum limits: 3 statutory agents, 5 managers, 5 manager/members, 5 members, 4 individual names
- Column positions critical - maintain exact order A-CO to match template
