# BatchData Complete Template - Field Descriptions

This document describes all **169 columns** in the BatchData Complete output file and explains in plain English exactly where each field's data comes from.

**File Pattern**: `M.YY_BatchData_Complete_{timestamp}.xlsx`

**Note**: As of November 2025, name input fields (BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL, BD_ADDRESS_2) have been removed. The BatchData API uses ADDRESS ONLY for skip-trace lookups. Names are returned in the API response (BD_PHONE_X_FIRST/LAST, BD_EMAIL_X_FIRST/LAST).

---

## Sheet Overview

| Sheet | Purpose | Columns |
|-------|---------|---------|
| CONFIG | Pipeline configuration settings | 15 key-value pairs |
| INPUT_MASTER | Records to process via skip-trace API | 16 BD_* input columns |
| BLACKLIST_NAMES | Names to exclude from processing | 1 column |
| OUTPUT_MASTER | Enriched results with phones/emails | 169 columns |

---

## CONFIG Sheet

The CONFIG sheet contains pipeline configuration as key-value pairs. These settings control API behavior and processing options.

| Key | Type | Description |
|-----|------|-------------|
| `api.endpoint` | String | BatchData API base URL |
| `api.token` | String | API authentication token (40 characters) |
| `workflow.enable_skip_trace` | Boolean | Enable property skip-trace for contact discovery |
| `workflow.enable_phone_verify` | Boolean | Enable phone verification stage |
| `workflow.enable_dnc` | Boolean | Enable Do-Not-Call registry check |
| `workflow.enable_tcpa` | Boolean | Enable TCPA litigator screening |
| `batch.size` | Integer | Records per API request (max 5000) |
| `batch.retry_count` | Integer | Number of retries on API failure |
| `batch.timeout_seconds` | Integer | API request timeout |
| `defaults.include_tcpa_phones` | Boolean | Include TCPA-flagged phones in output |
| `defaults.confidence_threshold` | Float | Minimum confidence score to include |
| `output.format` | String | Output format (xlsx/csv) |
| `output.include_metadata` | Boolean | Include API metadata columns |
| `pipeline.version` | String | Pipeline version identifier |
| `pipeline.dry_run` | Boolean | If true, skip actual API calls |

**Where it comes from**: Parsed by `io.py:load_config_dict()` from the CONFIG sheet.

---

## INPUT_MASTER Sheet

The INPUT_MASTER sheet contains records to process through the BatchData skip-trace API. These **16 columns** are populated by `transform.py:ecorp_to_batchdata_records()` from Ecorp_Complete data.

**Note**: API uses ADDRESS ONLY for lookups. Name fields (BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL) and BD_ADDRESS_2 have been **REMOVED**.

| Column | Field | Type | Description |
|--------|-------|------|-------------|
| A | BD_RECORD_ID | String | Unique record identifier (format: `ecorp_{entity_id}_{index}_{uuid8}`) |
| B | BD_SOURCE_TYPE | String | Always "Entity" for Ecorp-derived records |
| C | BD_ENTITY_NAME | String | Registered entity name from ACC |
| D | BD_SOURCE_ENTITY_ID | String | ACC file number (e.g., L12345678) |
| E | BD_TITLE_ROLE | String | Principal's role (Manager, Member, Statutory Agent, etc.) |
| F | BD_ADDRESS | String | Street address line 1 |
| G | BD_CITY | String | City name |
| H | BD_STATE | String | 2-letter state abbreviation |
| I | BD_ZIP | String | 5-digit ZIP code |
| J | BD_COUNTY | String | County name |
| K | BD_APN | String | Assessor Parcel Number (if available) |
| L | BD_MAILING_LINE1 | String | Mailing address line 1 |
| M | BD_MAILING_CITY | String | Mailing city |
| N | BD_MAILING_STATE | String | Mailing state |
| O | BD_MAILING_ZIP | String | Mailing ZIP |
| P | BD_NOTES | String | Processing notes and derivation info |

**Removed columns**: BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL, BD_ADDRESS_2

---

## BLACKLIST_NAMES Sheet

The BLACKLIST_NAMES sheet contains names to exclude from processing (professional service companies, registered agents, etc.).

### Column: blacklist_name

**Where it comes from**: Loaded by `io.py:load_blacklist_set()` into uppercase set for fast lookup.

**What it contains**: Names of professional service companies that should be filtered out (e.g., "CORPORATION SERVICE COMPANY", "CT CORPORATION SYSTEM").

**How it's used**: Before creating BatchData records, `transform.py:prepare_ecorp_for_batchdata()` checks statutory agent names against this blacklist.

**Example entries**:
- `CORPORATION SERVICE COMPANY`
- `CT CORPORATION SYSTEM`
- `REGISTERED AGENTS INC`
- `NATIONAL REGISTERED AGENTS`

---

## OUTPUT_MASTER Sheet - Column Summary by Section

| Section | Columns | Count | Description |
|---------|---------|-------|-------------|
| ECORP Passthrough | 1-17 | 17 | Copied from Ecorp_Complete for context |
| BD Input | 18-33 | 16 | Transformed from Ecorp data for API (4 name columns removed) |
| BD Phone Blocks | 34-113 | 80 | Skip-trace phone results (10 phones x 8 fields) |
| BD Email Blocks | 114-153 | 40 | Skip-trace email results (10 emails x 4 fields) |
| BD Metadata | 154-161 | 8 | API and pipeline tracking fields |
| Name Matching | 162-169 | 8 | Ecorp-to-Batchdata name verification |

**Total: 169 columns**

---

## Section 1: ECORP Passthrough Columns (1-17)

These columns are copied directly from Ecorp_Complete to maintain context and traceability.

### Column 1: FULL_ADDRESS

**Where it comes from**: Copied from Ecorp_Complete Column A (originally from MCAO_Complete).

**What it contains**: Complete property street address.

**Example**: `123 MAIN ST, PHOENIX, AZ 85001`

---

### Column 2: COUNTY

**Where it comes from**: Copied from Ecorp_Complete Column B.

**What it contains**: Property county (always MARICOPA for this pipeline).

**Example**: `MARICOPA`

---

### Column 3: Owner_Ownership

**Where it comes from**: Copied from Ecorp_Complete Column C (originally from MCAO property records).

**What it contains**: Raw owner name from county property records.

**Example**: `ACME INVESTMENTS LLC` or `SMITH JOHN/MARY`

---

### Column 4: ECORP_INDEX_#

**Where it comes from**: Copied from Ecorp_Complete Column D.

**What it contains**: Grouping index linking records with shared principals (85% person overlap threshold).

**Example**: `1`, `2`, `15`

---

### Column 5: OWNER_TYPE

**Where it comes from**: Copied from Ecorp_Complete Column E.

**What it contains**: Classification of owner - either `BUSINESS` or `INDIVIDUAL`.

**Example**: `BUSINESS`

---

### Column 6: ECORP_SEARCH_NAME

**Where it comes from**: Copied from Ecorp_Complete Column F.

**What it contains**: Exact text used to search ACC website.

**Example**: `SMITH PROPERTIES LLC`

---

### Column 7: ECORP_TYPE

**Where it comes from**: Copied from Ecorp_Complete Column G.

**What it contains**: Classification for ACC lookup - `Entity` or `Individual(s)`.

**Example**: `Entity`

---

### Column 8: ECORP_NAME_S

**Where it comes from**: Copied from Ecorp_Complete Column H.

**What it contains**: Official registered entity name from ACC records.

**Example**: `SMITH PROPERTIES, L.L.C.`

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 9: ECORP_ENTITY_ID_S

**Where it comes from**: Copied from Ecorp_Complete Column I.

**What it contains**: Arizona Corporation Commission file number.

**Example**: `L12345678`

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 10: ECORP_ENTITY_TYPE

**Where it comes from**: Copied from Ecorp_Complete Column J.

**What it contains**: Legal structure (e.g., `L.L.C. - Domestic`, `Corporation - Domestic`).

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 11: ECORP_STATUS

**Where it comes from**: Copied from Ecorp_Complete Column K.

**What it contains**: Entity registration status (e.g., `Good Standing`, `Active`, `Dissolved`).

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 12: ECORP_FORMATION_DATE

**Where it comes from**: Copied from Ecorp_Complete Column L.

**What it contains**: Date entity was formed/registered with ACC.

**Example**: `01/15/2020`

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 13: ECORP_BUSINESS_TYPE

**Where it comes from**: Copied from Ecorp_Complete Column M.

**What it contains**: Domestic or Foreign classification.

**Example**: `Domestic`

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 14: ECORP_STATE

**Where it comes from**: Copied from Ecorp_Complete Column N.

**What it contains**: Domicile state of the entity.

**Example**: `Arizona`, `Delaware`, `Nevada`

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 15: ECORP_COUNTY

**Where it comes from**: Copied from Ecorp_Complete Column O.

**What it contains**: County from entity registration (may differ from property county).

**Example**: `MARICOPA`, `PIMA`

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

### Column 16: ECORP_COMMENTS

**Where it comes from**: Copied from Ecorp_Complete Column P.

**What it contains**: Error messages or processing notes from ACC lookup.

**Example**: `Lookup error: timeout`

**When blank**: Lookup was successful.

---

### Column 17: ECORP_URL

**Where it comes from**: Copied from Ecorp_Complete Column CO.

**What it contains**: Direct link to ACC entity detail page.

**Example**: `https://ecorp.azcc.gov/EntitySearch/Details?entityNumber=L12345678`

**When blank**: No ACC results found or INDIVIDUAL owner type.

---

## Section 2: BD Input Columns (18-33)

These **16 columns** are populated by `transform.py:ecorp_to_batchdata_records()` and represent the data sent to the BatchData skip-trace API.

**Note**: BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL, and BD_ADDRESS_2 have been **REMOVED**. The API uses address-only for skip-trace lookups.

### Column 18: BD_RECORD_ID

**Where it comes from**: Generated by `transform.py` using format `ecorp_{entity_id}_{principal_index}_{uuid8}`.

**What it contains**: Unique identifier linking input to output.

**Example**: `ecorp_L12345678_1_a1b2c3d4`

---

### Column 19: BD_SOURCE_TYPE

**Where it comes from**: Set to "Entity" by `transform.py:ecorp_to_batchdata_records()`.

**What it contains**: Always `Entity` for Ecorp-derived records.

---

### Column 20: BD_ENTITY_NAME

**Where it comes from**: Copied from ECORP_NAME_S.

**What it contains**: Registered entity name.

**Example**: `SMITH PROPERTIES, L.L.C.`

---

### Column 21: BD_SOURCE_ENTITY_ID

**Where it comes from**: Copied from ECORP_ENTITY_ID_S.

**What it contains**: ACC file number.

**Example**: `L12345678`

---

### Column 22: BD_TITLE_ROLE

**Where it comes from**: Extracted from principal table by `transform.py:extract_title_role()`.

**What it contains**: Principal's role in the entity.

**Examples**: `Manager`, `Member`, `Manager/Member`, `Statutory Agent`, `Individual`

---

### Column 23: BD_ADDRESS

**Where it comes from**: Parsed from principal address by `transform.py:parse_address()`.

**What it contains**: Street address line 1.

**Example**: `123 N CENTRAL AVE`

---

### Column 24: BD_CITY

**Where it comes from**: Parsed from principal address.

**What it contains**: City name.

**Example**: `Phoenix`

---

### Column 25: BD_STATE

**Where it comes from**: Parsed from address, normalized by `normalize.py:normalize_state()`.

**What it contains**: 2-letter state abbreviation.

**Example**: `AZ`

---

### Column 26: BD_ZIP

**Where it comes from**: Parsed from address, normalized by `normalize.py:normalize_zip_code()`.

**What it contains**: 5-digit ZIP code.

**Example**: `85004`

---

### Column 27: BD_COUNTY

**Where it comes from**: From ECORP_COUNTY or fallback to COUNTY field.

**What it contains**: County name.

**Example**: `MARICOPA`

---

### Column 28: BD_APN

**Where it comes from**: Not available from Ecorp data.

**What it contains**: Assessor Parcel Number (typically blank).

---

### Columns 29-32: BD_MAILING_*

**Where it comes from**: Could be populated if mailing address differs from property address.

**What it contains**: Mailing address components (LINE1, CITY, STATE, ZIP).

**When blank**: No separate mailing address available.

---

### Column 33: BD_NOTES

**Where it comes from**: Generated by `transform.py:ecorp_to_batchdata_records()`.

**What it contains**: Processing notes, derivation info.

**Example**: `Derived from eCorp search: SMITH PROPERTIES LLC`

---

## Section 3: BD Phone Block Columns (34-113)

These 80 columns store skip-trace phone results. There are 10 phone blocks, each with 8 fields.

### Block Structure (X = 1-10)

Each phone block contains:

| Column Pattern | Type | Description |
|----------------|------|-------------|
| BD_PHONE_X | String | Phone number (E.164 format preferred) |
| BD_PHONE_X_FIRST | String | First name of person associated with this phone |
| BD_PHONE_X_LAST | String | Last name of person associated with this phone |
| BD_PHONE_X_TYPE | String | Line type: `mobile`, `landline`, `voip` |
| BD_PHONE_X_CARRIER | String | Phone carrier name |
| BD_PHONE_X_DNC | Boolean | Do-Not-Call registry flag |
| BD_PHONE_X_TCPA | Boolean | TCPA litigator flag |
| BD_PHONE_X_CONFIDENCE | Float | Match confidence score (0.0-1.0) |

### Phone 1 Fields (Columns 34-41)

#### Column 38: BD_PHONE_1

**Where it comes from**: Skip-trace API response `person.phones[0].number` via `batchdata_sync.py:_parse_sync_response_to_schema()`.

**What it contains**: Phone number, preferably in E.164 format (+1XXXXXXXXXX).

**Example**: `+15551234567` or `555-123-4567`

**When blank**: No phone found for this record or skip-trace returned no results.

---

#### Column 39: BD_PHONE_1_FIRST

**Where it comes from**: Skip-trace API response `person.name.first` for the person who owns this phone.

**What it contains**: First name of the person associated with this phone number.

**Example**: `John`

**Why this matters**: Multiple persons may be returned per property. This field links each phone to its owner, enabling personalized outreach.

**When blank**: API did not return a name, or no phone found.

---

#### Column 40: BD_PHONE_1_LAST

**Where it comes from**: Skip-trace API response `person.name.last` for the person who owns this phone.

**What it contains**: Last name of the person associated with this phone number.

**Example**: `Smith`

**When blank**: API did not return a name, or no phone found.

---

#### Column 41: BD_PHONE_1_TYPE

**Where it comes from**: Skip-trace API response `person.phones[0].type`.

**What it contains**: Line type classification.

**Values**: `mobile`, `landline`, `voip`

**Why this matters**: Mobile phones are preferred for SMS/text campaigns. Landlines require voice calls only.

**When blank**: Type not available or no phone found.

---

#### Column 42: BD_PHONE_1_CARRIER

**Where it comes from**: Skip-trace API response `person.phones[0].carrier`.

**What it contains**: Phone carrier name.

**Example**: `Verizon`, `AT&T`, `T-Mobile`

**When blank**: Carrier not available or no phone found.

---

#### Column 43: BD_PHONE_1_DNC

**Where it comes from**: Skip-trace API response `person.phones[0].dnc` or DNC scrub stage.

**What it contains**: Boolean indicating if phone is on National Do-Not-Call registry.

**Values**: `TRUE` (on DNC list, do not call), `FALSE` (safe to call)

**Why this matters**: Calling DNC-listed numbers can result in significant fines.

---

#### Column 44: BD_PHONE_1_TCPA

**Where it comes from**: Skip-trace API response `person.phones[0].tcpa` or TCPA scrub stage.

**What it contains**: Boolean indicating if phone is associated with known TCPA litigators.

**Values**: `TRUE` (litigator risk), `FALSE` (no known risk)

**Why this matters**: TCPA litigators may sue for unsolicited calls/texts.

---

#### Column 45: BD_PHONE_1_CONFIDENCE

**Where it comes from**: Skip-trace API response `person.phones[0].score` or `person.phones[0].confidence`.

**What it contains**: Match confidence score from 0.0 (low) to 1.0 (high).

**Example**: `0.95`

**Why this matters**: Higher confidence phones are more likely to be accurate and current.

---

### Phones 2-10 (Columns 46-117)

Follow the same 8-field pattern as Phone 1:
- **Columns 46-53**: BD_PHONE_2_* fields
- **Columns 54-61**: BD_PHONE_3_* fields
- **Columns 62-69**: BD_PHONE_4_* fields
- **Columns 70-77**: BD_PHONE_5_* fields
- **Columns 78-85**: BD_PHONE_6_* fields
- **Columns 86-93**: BD_PHONE_7_* fields
- **Columns 94-101**: BD_PHONE_8_* fields
- **Columns 102-109**: BD_PHONE_9_* fields
- **Columns 110-117**: BD_PHONE_10_* fields

**Name denormalization**: If one person has multiple phones (e.g., John Smith has 3 phones), BD_PHONE_1_FIRST through BD_PHONE_3_FIRST will all contain "John", and BD_PHONE_1_LAST through BD_PHONE_3_LAST will all contain "Smith".

---

## Section 4: BD Email Block Columns (114-153)

These 40 columns store skip-trace email results. There are 10 email blocks, each with 4 fields.

### Block Structure (X = 1-10)

Each email block contains:

| Column Pattern | Type | Description |
|----------------|------|-------------|
| BD_EMAIL_X | String | Email address |
| BD_EMAIL_X_FIRST | String | First name of person associated with this email |
| BD_EMAIL_X_LAST | String | Last name of person associated with this email |
| BD_EMAIL_X_TESTED | Boolean | Email validation status |

### Email 1 Fields (Columns 118-121)

#### Column 118: BD_EMAIL_1

**Where it comes from**: Skip-trace API response `person.emails[0].address` via `batchdata_sync.py:_parse_sync_response_to_schema()`.

**What it contains**: Email address.

**Example**: `john.smith@example.com`

**When blank**: No email found for this record.

---

#### Column 119: BD_EMAIL_1_FIRST

**Where it comes from**: Skip-trace API response `person.name.first` for the person who owns this email.

**What it contains**: First name of the person associated with this email.

**Example**: `John`

**When blank**: API did not return a name, or no email found.

---

#### Column 120: BD_EMAIL_1_LAST

**Where it comes from**: Skip-trace API response `person.name.last` for the person who owns this email.

**What it contains**: Last name of the person associated with this email.

**Example**: `Smith`

**When blank**: API did not return a name, or no email found.

---

#### Column 121: BD_EMAIL_1_TESTED

**Where it comes from**: Skip-trace API response `person.emails[0].tested`.

**What it contains**: Boolean indicating if email has been validated/tested.

**Values**: `TRUE` (email tested/verified), `FALSE` (not tested)

**When blank**: Testing status not available.

---

### Emails 2-10 (Columns 122-157)

Follow the same 4-field pattern as Email 1:
- **Columns 122-125**: BD_EMAIL_2_* fields
- **Columns 126-129**: BD_EMAIL_3_* fields
- **Columns 130-133**: BD_EMAIL_4_* fields
- **Columns 134-137**: BD_EMAIL_5_* fields
- **Columns 138-141**: BD_EMAIL_6_* fields
- **Columns 142-145**: BD_EMAIL_7_* fields
- **Columns 146-149**: BD_EMAIL_8_* fields
- **Columns 150-153**: BD_EMAIL_9_* fields
- **Columns 154-157**: BD_EMAIL_10_* fields

---

## Section 5: BD Metadata Columns (154-161)

These 8 columns track API status and pipeline processing.

### Column 158: BD_API_STATUS

**Where it comes from**: Set by `batchdata_sync.py:_parse_sync_response_to_schema()`.

**What it contains**: API response status.

**Values**:
- `success` - API returned results
- `no_match` - No contact data found for this record
- `invalid_response` - API returned error or invalid format

---

### Column 159: BD_API_RESPONSE_TIME

**Where it comes from**: Captured by `batchdata_sync.py` during API call.

**What it contains**: Timestamp when API response was received.

**Example**: `2025-01-15 14:30:45`

---

### Column 160: BD_PERSONS_FOUND

**Where it comes from**: Count of `persons[]` array in API response.

**What it contains**: Number of distinct persons returned by skip-trace.

**Example**: `2` (e.g., husband and wife)

---

### Column 161: BD_PHONES_FOUND

**Where it comes from**: Sum of phones across all persons in API response.

**What it contains**: Total phones discovered before filtering to top 10.

**Example**: `5`

---

### Column 162: BD_EMAILS_FOUND

**Where it comes from**: Sum of emails across all persons in API response.

**What it contains**: Total emails discovered before filtering to top 10.

**Example**: `3`

---

### Column 163: BD_PIPELINE_VERSION

**Where it comes from**: Set from CONFIG `pipeline.version` value.

**What it contains**: Version identifier for the processing pipeline.

**Example**: `2.1.0`

---

### Column 164: BD_PIPELINE_TIMESTAMP

**Where it comes from**: Generated at processing time.

**What it contains**: ISO timestamp when pipeline processed this record.

**Example**: `2025-01-15T14:30:45`

---

### Column 165: BD_STAGES_APPLIED

**Where it comes from**: Built during pipeline execution.

**What it contains**: Comma-separated list of stages applied to this record.

**Example**: `skip_trace,phone_verify,dnc,tcpa`

---

## Population Logic Summary

### Skip-Trace Enrichment Flow

1. **Input**: Record sent to BatchData Skip-Trace API with address and optional name
2. **API Response**: Returns array of `persons`, each with `name`, `phones[]`, and `emails[]`
3. **Flattening**: All phones collected across persons into BD_PHONE_1 through BD_PHONE_10
4. **Name Association**: Each phone/email gets its owner's first/last name (denormalized)
5. **Optional Scrubs**: DNC and TCPA checks update corresponding flags
6. **Output**: Complete record written to OUTPUT_MASTER

### When Fields Are Blank

- **No API results**: BD_PHONE_*, BD_EMAIL_* columns remain empty
- **Missing person name**: BD_PHONE_X_FIRST, BD_PHONE_X_LAST remain empty
- **Fewer than 10 contacts**: Later slots (BD_PHONE_5+, BD_EMAIL_5+) remain empty
- **Invalid address**: API may return `no_match` status

### Name Denormalization Logic

When one person has multiple phones:
```
Person: John Smith
  - Phone A: 555-1111
  - Phone B: 555-2222
  - Phone C: 555-3333

Results in:
  BD_PHONE_1 = 555-1111, BD_PHONE_1_FIRST = John, BD_PHONE_1_LAST = Smith
  BD_PHONE_2 = 555-2222, BD_PHONE_2_FIRST = John, BD_PHONE_2_LAST = Smith
  BD_PHONE_3 = 555-3333, BD_PHONE_3_FIRST = John, BD_PHONE_3_LAST = Smith
```

When multiple persons have phones:
```
Person 1: John Smith - Phones: 555-1111, 555-2222
Person 2: Jane Smith - Phones: 555-3333

Results in:
  BD_PHONE_1 = 555-1111, BD_PHONE_1_FIRST = John, BD_PHONE_1_LAST = Smith
  BD_PHONE_2 = 555-2222, BD_PHONE_2_FIRST = John, BD_PHONE_2_LAST = Smith
  BD_PHONE_3 = 555-3333, BD_PHONE_3_FIRST = Jane, BD_PHONE_3_LAST = Smith
```

---

## Code Reference

All field population logic is implemented in these files:

**File**: `Batchdata/src/batchdata_sync.py`

| Function | Purpose |
|----------|---------|
| `_parse_sync_response_to_schema()` | Converts API response to wide-format DataFrame |
| `skip_trace_sync()` | Executes skip-trace API call |
| `phone_verification_sync()` | Validates phone numbers |
| `dnc_check_sync()` | Checks DNC registry |
| `tcpa_check_sync()` | Screens TCPA litigators |

**File**: `Batchdata/src/transform.py`

| Function | Purpose |
|----------|---------|
| `ecorp_to_batchdata_records()` | Transforms Ecorp row to BatchData records |
| `prepare_ecorp_for_batchdata()` | Preprocesses Ecorp data structure |
| `parse_address()` | Parses address into components |
| `transform_ecorp_to_batchdata()` | Full DataFrame transformation |

**File**: `Batchdata/src/io.py`

| Function | Purpose |
|----------|---------|
| `load_config_dict()` | Parses CONFIG sheet to dictionary |
| `load_blacklist_set()` | Loads BLACKLIST_NAMES to set |
| `write_template_excel()` | Writes multi-sheet output file |

**File**: `Batchdata/src/normalize.py`

| Function | Purpose |
|----------|---------|
| `split_full_name()` | Parses full name to first/last |
| `normalize_state()` | Converts state names to abbreviations |
| `normalize_zip_code()` | Standardizes ZIP codes |
| `normalize_phone_e164()` | Formats phones to E.164 |

---

## Usage Example

```python
from src.adhs_etl.batchdata_bridge import (
    create_batchdata_upload,
    run_batchdata_enrichment
)

# Step 1: Create Upload from Ecorp Complete
month = "1.25"
ecorp_file = "Ecorp/Complete/1.25_Ecorp_Complete_01.15.03-45-30.xlsx"
upload_path = create_batchdata_upload(ecorp_file, month)

# Step 2: Run enrichment pipeline
complete_path = run_batchdata_enrichment(
    upload_path,
    month,
    stage_config={
        'skip_trace': True,
        'phone_verify': True,
        'dnc': True,
        'tcpa': True
    }
)
# Output: Batchdata/Complete/1.25_BatchData_Complete_01.15.03-45-30.xlsx
```

---

## Notes

- **Maximum contacts**: 10 phones and 10 emails per record
- **Phone format**: E.164 preferred (+1XXXXXXXXXX), but API may return other formats
- **Name fields**: BD_PHONE_X_FIRST/LAST and BD_EMAIL_X_FIRST/LAST capture person association
- **Compliance flags**: DNC and TCPA flags help ensure calling regulation compliance
- **Confidence scores**: Range 0.0 (low) to 1.0 (high) - higher is more reliable
- **API costs**: ~$0.07 per skip-trace record + optional scrub fees
- **Processing rate**: Varies by batch size and API response time

---

## Section 6: Name Matching Columns (162-169)

These 8 columns verify that contacts from BatchData correspond to principals from Ecorp records.

### Column 166: ECORP_TO_BATCH_MATCH_%

**Where it comes from**: Calculated by `name_matching.py:calculate_match_percentage()`.

**What it contains**: Percentage of Ecorp principal names found in BatchData results using 85% fuzzy matching threshold.

**Values**:
- `0` to `100` - Percentage of Ecorp names matched in BatchData results
- `100+` - All Ecorp names matched AND BatchData returned additional names not in Ecorp

**Formula**: `(Ecorp names matched at 85%+ confidence) / (Total Ecorp principal names) × 100`

**Example**:
- Ecorp has: John Smith, Jane Smith, Bob Jones (3 names)
- BatchData returns: John Smith, Jane Smith (2 names)
- Result: `67` (2/3 × 100 = 67%)

**Why this matters**: Helps verify that BatchData contacts are associated with the correct entity principals, not random people at the property address.

---

### Columns 167-173: MISSING_1-8_FULL_NAME

**Where it comes from**: Populated by `name_matching.py:apply_name_matching()`.

**What it contains**: Ecorp principal names NOT found in BatchData results (up to 8 names).

**When populated**: Whenever `ECORP_TO_BATCH_MATCH_%` < 100

**When blank**:
- `ECORP_TO_BATCH_MATCH_%` = 100 (all names matched)
- `ECORP_TO_BATCH_MATCH_%` = 100+ (all names matched, extras found)

**Example**:
```
ECORP principals: John Smith, Jane Smith, Bob Jones
BatchData results: John Smith, Jane Smith

ECORP_TO_BATCH_MATCH_% = 67
MISSING_1_FULL_NAME = Bob Jones
MISSING_2_FULL_NAME = (blank)
...
MISSING_8_FULL_NAME = (blank)
```

**Why this matters**: Identifies which principals need manual contact lookup since BatchData didn't return their information.

---

### Name Matching Algorithm

1. **Extract Ecorp Names**: Collect all 22 principal name fields from Ecorp_Complete:
   - StatutoryAgent1-3_Name (3 fields)
   - Manager1-5_Name (5 fields)
   - Member1-5_Name (5 fields)
   - Manager/Member1-5_Name (5 fields)
   - IndividualName1-4 (4 fields)

2. **Extract BatchData Names**: Collect all person names from API results:
   - BD_PHONE_1-10_FIRST + BD_PHONE_1-10_LAST
   - BD_EMAIL_1-10_FIRST + BD_EMAIL_1-10_LAST

3. **Fuzzy Match**: Compare each Ecorp name against BatchData names using `rapidfuzz.token_sort_ratio()`:
   - Threshold: 85% similarity
   - Case insensitive
   - Order invariant ("John Smith" matches "Smith John")

4. **Calculate Percentage**: `matched_count / total_ecorp_names × 100`

5. **Store Missing**: First 8 unmatched Ecorp names go into MISSING_1-8_FULL_NAME

---

### Code Reference

**File**: `Batchdata/src/name_matching.py`

| Function | Purpose |
|----------|---------|
| `fuzzy_name_match()` | Compare two names with 85% threshold |
| `extract_ecorp_names_from_complete()` | Get all 22 principal names from Ecorp row |
| `extract_batch_names()` | Get all person names from BatchData row |
| `calculate_match_percentage()` | Compute match % and missing names |
| `apply_name_matching()` | Main integration function for DataFrame |

**Integration**: Called by `batchdata_bridge.py:_run_sync_enrichment()` after API enrichment completes.
