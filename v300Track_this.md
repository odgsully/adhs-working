# v300Track Analysis Sheet - Complete Field Definitions

> **TEMPLATE REFERENCE**: This documentation defines the official column naming and structure for `v300Track_this.xlsx`. All Analysis output files MUST match this template exactly.

## Column Naming Convention

**IMPORTANT**: All column names use **underscores** (`_`) instead of spaces for v300 compliance:
- `PROVIDER_TYPE` (not `PROVIDER TYPE`)
- `PROVIDER_GROUP_INDEX_#` (not `PROVIDER GROUP INDEX #`)
- `THIS_MONTH_STATUS` (not `THIS MONTH STATUS`)
- `9.24_COUNT` (not `9.24 COUNT`)
- `10.24_TO_PREV` (not `10.24 TO PREV`)
- `9.24_SUMMARY` (not `9.24 SUMMARY`)

This ensures:
1. Consistent column parsing across the codebase
2. Excel formula compatibility
3. Reliable data matching between months

---

## Project Overview and Goal

**Objective**: Have a simple clean functioning database with exceptional mapping & attention to detail. I have a monthly recurring number of datasets to download. The goal is to have a singular script that gives Reformatting capabilities and Analysis with perfect data execution.

**Data Source**: References a local folder called 'ALL-MONTHS', located: `/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-restore-28-Jul-2025 copy/ALL-MONTHS`. These separate excel files are a straight raw download from Arizona Department of Health Services where it lists active licenses each month.

**Business Value**: There is a lot of value to be able to see who is no longer licensed as it could be a Lead opportunity for an owner looking to sell the location which is beneficial for me as a investor. Then lead opportunities in surveying the steady licensees for my research business. Both great lead generation and we need to create great and sound analysis to differentiate & diagnose where every provider is on a individual and PROVIDER_GROUP_INDEX_# basis.

**Ultimate Goal**: Besides documentation output files, this is a large part of the ultimate goal to populate the 'M.YY Analysis.xlsx' output file with perfect accuracy.

## Core Identification Fields (Columns A-P)

### Column A: SOLO_PROVIDER_TYPE_PROVIDER_[Y,#]
**Source**: Calculated from current month's Reformat data
**Logic**:
```
IF all addresses in PROVIDER_GROUP_INDEX_# have same PROVIDER_TYPE
  THEN "Y"  // Regardless of address count
ELSE
  COUNT(distinct PROVIDER_TYPE for this PROVIDER_GROUP_INDEX_#)
```
**Example**: "Y" = all addresses have same provider type (could be 1 or many addresses), "3" = group has 3 different provider types

### Column B: PROVIDER_TYPE
**Source**: Direct from Reformat file, originally from Raw files
**Values**: DEVELOPMENTALLY_DISABLED_GROUP_HOME, ASSISTED_LIVING_CENTER, etc.

### Column C: PROVIDER
**Source**: Direct from Reformat file
**Example**: "ARIZONA MENTOR/ WILMOT NORTH"

### Column D: ADDRESS
**Source**: Direct from Reformat file
**Format**: Street address only
**Note**: This is now just the street portion; full address moved to Column G

### Column E: CITY
**Source**: Direct from Reformat file

### Column F: ZIP
**Source**: Direct from Reformat file
**Format**: 5-digit ZIP code

### Column G: FULL_ADDRESS
**Source**: Concatenated from ADDRESS, CITY, STATE, ZIP
**Logic**:
```
CONCATENATE(Column D, ", ", Column E, ", AZ ", Column F)
```
**Exact Format Examples**:
- "6926 EAST CALLE BELLATRIX, TUCSON, AZ 85710"
- "7373 W MONTEBELLO AVE, PHOENIX, AZ 85033"
- "1501 N PIEDMONT DRIVE, SCOTTSDALE, AZ 85251"
- "424 S ROSEMONT, MESA, AZ 85206"

**Format Pattern**: `[STREET ADDRESS], [CITY], AZ [5-DIGIT ZIP]`
**Purpose**: Enables complete address matching and geocoding

### Column H: CAPACITY
**Source**: Direct from Reformat file


### Column I: LONGITUDE
**Source**: Direct from Reformat file

### Column J: LATITUDE
**Source**: Direct from Reformat file


### Column K: COUNTY
**Source**: Direct from Reformat file
**Values**: County names (e.g., "MARICOPA", "PIMA", "COCONINO")
**Purpose**: Enables county-level analysis and regional tracking

### Column L: PROVIDER_GROUP_INDEX_#
**Source**: Calculated during Reformat process
**Note**: Positioned after COUNTY field
**Logic**:
```
Groups assigned unique index based on:
1. Provider name matching:
   - 85%+ fuzzy match (Levenshtein distance) OR
   - 20+ consecutive matching characters
2. Sequential numbering starting from 1
3. Solo providers get unique index
4. Group members share same index number
```

### Column M: PROVIDER_GROUP_(DBA_CONCAT)
**Source**: Calculated from all records sharing same PROVIDER_GROUP_INDEX_#
**Logic**:
```
FOR each PROVIDER_GROUP_INDEX_#:
  LIST all other providers with same index
  FORMAT as: "PROVIDER_NAME (FULL_ADDRESS), PROVIDER_NAME (FULL_ADDRESS)"
  EXCLUDE self from list
  SORT alphabetically by provider name
```
**Exact Format Examples**:
- "VISIT-N-CARE/ ALDO (7123 N 77TH DRIVE, GLENDALE, AZ 85303)"
- "VISIT-N-CARE /  MAHALO (7373 W MONTEBELLO AVE, PHOENIX, AZ 85033), VISIT-N-CARE/ ALDO (7123 N 77TH DRIVE, GLENDALE, AZ 85303)"
- "ZION COMPASSION CARE, LLC/ MT CALVARY (424 S ROSEMONT, MESA, AZ 85206), ZION COMPASSION CARE, LLC/ MT TABOR (4752 E DRAGOON AVE, TUCSON, AZ 85710)"

**Format Pattern**: `PROVIDER_NAME (FULL_ADDRESS), PROVIDER_NAME (FULL_ADDRESS)`
**Note**: Uses FULL_ADDRESS for complete location matching

### Column N: PROVIDER_GROUP, ADDRESS_COUNT
**Source**: Calculated COUNT(DISTINCT FULL ADDRESS for this PROVIDER_GROUP_INDEX_#)
**Note**: Now uses FULL_ADDRESS (Column G) instead of ADDRESS (Column D)

### Column O: THIS_MONTH_STATUS
**Source**: Calculated by comparing current month to previous month
**Logic**:
```
IF no record in previous months AND Column A = "Y"
  THEN "NEW PROVIDER TYPE, NEW ADDRESS"

ELSE IF provider+type exists in previous month at same FULL_ADDRESS
  THEN "EXISTING PROVIDER TYPE, EXISTING ADDRESS"

ELSE IF provider+type exists but FULL_ADDRESS changed
  THEN check:
    IF previous addresses = 0: "EXISTING PROVIDER TYPE, NEW ADDRESS"
    ELSE: "Provider Relocated" or expansion logic

ELSE IF provider+FULL_ADDRESS exists but type is new
  THEN "NEW PROVIDER TYPE, EXISTING ADDRESS"

ELSE IF provider+type+FULL_ADDRESS missing last 1-4 months but existed within 4-month window
  THEN "REINSTATED PROVIDER TYPE, EXISTING ADDRESS"

ELSE IF provider+type+FULL_ADDRESS existed last month but not this month
  THEN check remaining addresses:
    IF no addresses remain: "LOST PROVIDER TYPE, LOST ADDRESS (0 remain)"
    IF other addresses remain: "LOST PROVIDER TYPE, LOST ADDRESS (1+ remain)"
    IF same address but lost type: "LOST PROVIDER TYPE, EXISTING ADDRESS"
```

### Column P: LEAD_TYPE
**Source**: Derived from THIS_MONTH_STATUS
**Logic**:
```
'NEW PROVIDER TYPE, NEW ADDRESS' = 'Survey Lead'
'NEW PROVIDER TYPE, EXISTING ADDRESS' = 'Survey Lead'
'EXISTING PROVIDER TYPE, NEW ADDRESS' = 'Survey Lead'
'EXISTING PROVIDER TYPE, EXISTING ADDRESS' = 'Survey Lead'
'LOST PROVIDER TYPE, EXISTING ADDRESS' = 'Seller/Survey Lead'
'LOST PROVIDER TYPE, LOST ADDRESS (0 remain)' = 'Seller Lead'
'LOST PROVIDER TYPE, LOST ADDRESS (1+ remain)' = 'Seller Lead'
'REINSTATED PROVIDER TYPE, EXISTING ADDRESS' = 'Survey Lead'
```
**Note**: All statuses map to a lead type - no blanks allowed. Existing steady providers are Survey Leads for ongoing research opportunities.



### Columns Q-BD: M.YY_COUNT
**Coverage**: Extended historical range spanning 40+ months
**Logic**:
```
FOR each month column:
  COUNT the number of FULL_ADDRESS records for the corresponding PROVIDER
  in the M.YY Reformat file

  IF provider+type+FULL_ADDRESS exists in that month's Reformat file
    THEN 1
  ELSE 0
```
**Note**: This is a COUNT of the number of FULL ADDRESS records for the corresponding PROVIDER record in each M.YY Reformat file. For processing a single month M.YY Analysis, copy values from the previous month's workbook for all previous months.
**Span**: Now covers 40+ months of historical data
**Example Columns**:
- Q: "9.24_COUNT"
- R: "10.24_COUNT"
- ...continuing through...
- BD: "12.27_COUNT"



### Columns BE-CQ: M.YY TO PREV
**Coverage**: Matches extended count range
**Logic**:
```
Comparing the subject month COUNT to the previous month COUNT in Q-BD columns

Current month COUNT - Previous month COUNT
Results:
  'Decreased' = Count went down
  'Increased' = Count went up
  'No movement' = Count stayed the same
```
**Span**: Covers same 40+ month range as COUNT section


### Columns CR-EE: [Month.Year]_SUMMARY
**Coverage**: Matches extended count range (9.24_SUMMARY through 12.27_SUMMARY)
**Logic**:
```
Simple concatenation of Column N and Column M:
[Column N: PROVIDER_GROUP,_ADDRESS_COUNT], [Column M: PROVIDER_GROUP_(DBA_Concat)]
```
**Example**: "7, SAGUARO FOUNDATION COMMUNITY LIVING PROGRAM (2783 S MARY AVENUE), SAGUARO FOUNDATION..."
**Purpose**: Consolidated group information showing address count and all related providers
**Note**: Values are carried forward from previous M.YY Analysis files when processing historical data


### Column EF: MONTH
**Source**: Current processing month
**Note**: Positioned after extended historical columns

### Column EG: YEAR
**Source**: Current processing year
**Note**: Positioned after MONTH field



### Column EH: PREVIOUS_MONTH_STATUS
**Source**: THIS_MONTH_STATUS from previous month's analysis
**Logic**:
```
LOOKUP(THIS_MONTH_STATUS WHERE
  PROVIDER = current.PROVIDER AND
  PROVIDER_TYPE = current.PROVIDER_TYPE AND
  FULL_ADDRESS = current.FULL_ADDRESS AND
  MONTH = current.MONTH - 1)

IF lookup returns NULL or no previous month found:
  RETURN "No Prev Month Found"
```

### Column EI: STATUS_CONFIDENCE
**Source**: Calculated based on data completeness
**Enhanced Logic for v300**:
```
score = 100
IF PROVIDER is NULL: score -= 30
IF FULL_ADDRESS is NULL: score -= 25  // Changed from ADDRESS
IF COUNTY is NULL: score -= 5         // New check
IF PROVIDER_GROUP_INDEX_# is NULL: score -= 10
IF previous month data missing: score -= 20

IF score >= 80: "High"
ELSE IF score >= 50: "Medium"
ELSE: "Low"
```

### Column EJ: PROVIDER_TYPES_GAINED
**Source**: Comparison of provider types between current and previous month
**Logic**:
```
IF previous month data missing:
  RETURN "No Prev Month Found"

FOR this PROVIDER at this FULL_ADDRESS:
  current_types = LIST(PROVIDER_TYPE this month by address)
  previous_types = LIST(PROVIDER_TYPE last month by address)
  gained_types = current_types - previous_types

  GROUP gained_types by PROVIDER_TYPE:
    FOR each unique provider_type:
      count = COUNT(addresses with this gained type)
      format as: "[count]; [PROVIDER_TYPE]"

RETURN formatted list as comma-separated string
Example: "1; ASSISTED_LIVING_CENTER, 2; BEHAVIORAL_HEALTH_INPATIENT"
```
**Format Pattern**: `[ADDRESS_COUNT]; [PROVIDER_TYPE], [ADDRESS_COUNT]; [PROVIDER_TYPE]`
**Note**: Count represents number of addresses/locations, not provider type count

### Column EK: PROVIDER_TYPES_LOST
**Source**: Comparison of provider types between current and previous month
**Logic**:
```
IF previous month data missing:
  RETURN "No Prev Month Found"

FOR this PROVIDER at this FULL_ADDRESS:
  previous_types = LIST(PROVIDER_TYPE last month by address)
  current_types = LIST(PROVIDER_TYPE this month by address)
  lost_types = previous_types - current_types

  GROUP lost_types by PROVIDER_TYPE:
    FOR each unique provider_type:
      count = COUNT(addresses that lost this type)
      format as: "[count]; [PROVIDER_TYPE]"

RETURN formatted list as comma-separated string
Example: "1; NURSING_HOME, 2; CC_CENTERS"
```
**Format Pattern**: `[ADDRESS_COUNT]; [PROVIDER_TYPE], [ADDRESS_COUNT]; [PROVIDER_TYPE]`
**Note**: Count represents number of addresses/locations, not provider type count

### Column EL: NET_TYPE_CHANGE
**Logic**:
```
IF PROVIDER_TYPES_GAINED = "No Prev Month Found" OR
   PROVIDER_TYPES_LOST = "No Prev Month Found":
  RETURN "No Prev Month Found"
ELSE:
  SUM(address counts from PROVIDER_TYPES_GAINED) -
  SUM(address counts from PROVIDER_TYPES_LOST)
```

### Column EM: MONTHS_SINCE_LOST
**Source**: Calculated from THIS_MONTH_STATUS history
**Logic**:
```
IF previous month data missing:
  RETURN "No Prev Month Found"

IF THIS_MONTH_STATUS contains "LOST"
  THEN 0  // Reset counter
ELSE IF PREVIOUS_MONTH_STATUS contains "LOST"
  THEN previous.MONTHS_SINCE_LOST + 1  // Increment
ELSE
  THEN NULL  // Not applicable
```
**Enhanced for v300**: Can now track up to 40+ months of lost status

### Column EN: REINSTATED_FLAG
**Enhanced Logic**:
```
IF previous month data missing:
  RETURN "No Prev Month Found"

IF current month COUNT >= 1 AND
   previous month COUNT = 0 AND
   ANY(historical COUNT in past 40 months) >= 1  // Extended from 12
  THEN "Y"
ELSE "N"
```

### Column EO: REINSTATED_DATE
**Source**: Current date when reinstatement is detected plus last active month
**Logic**:
```
IF REINSTATED_FLAG = "Y"
  THEN CONCATENATE(
    current.MONTH, "/", current.YEAR,
    " ; Last Active Month license: ",
    LAST_ACTIVE_MONTH (formatted as M/YYYY)
  )
  Example: "5/2025 ; Last Active Month license: 2/2025"
ELSE
  THEN NULL
```
**Format Pattern**: `M/YYYY ; Last Active Month license: M/YYYY`

### Column EP: DATA_QUALITY_SCORE
**Enhanced Logic**:
```
required_fields = [PROVIDER, TYPE, FULL ADDRESS, COUNTY, ZIP, INDEX]
optional_fields = [CAPACITY, LONGITUDE, LATITUDE]

score = 0
FOR each required_field present: score += 15  // 6 fields × 15 = 90
FOR each optional_field present: score += 3.33  // 3 fields × 3.33 = 10
score = ROUND(score)  // Ensures total = 100
```

### Column EQ: MANUAL_REVIEW_FLAG
**Enhanced Logic**:
```
IF STATUS_CONFIDENCE = "Low" OR
   DATA_QUALITY_SCORE < 70 OR
   (REINSTATED_FLAG = "Y" AND MONTHS_SINCE_LOST > 12)
  THEN "Y"
ELSE "N"
```

### Column ER: REVIEW_NOTES
**Purpose**: Manual input field for analyst notes

### Column ES: LAST_ACTIVE_MONTH
**Enhanced**: Now searches through extended 40+ month history


### Column ET: REGIONAL_MARKET
**Source**: Derived from COUNTY
**Logic**:
```
IF COUNTY IN ("MARICOPA", "PINAL"): "Phoenix Metro"
ELSE IF COUNTY IN ("PIMA"): "Tucson Metro"
ELSE IF COUNTY IN ("COCONINO", "YAVAPAI"): "Northern AZ"
ELSE: "Rural/Other"
```

### Column EU: HISTORICAL_STABILITY_SCORE
**Source**: Calculated from 40+ month history
**Logic**:
```
active_months = COUNT(months with COUNT >= 1)
total_months = COUNT(all tracked months)
consecutive_active = MAX(consecutive months active)

IF total_months = 0:
  score = NULL
ELSE:
  active_ratio = (active_months / total_months) × 50
  consistency_ratio = MIN(consecutive_active / total_months, 1) × 50
  score = active_ratio + consistency_ratio
```
**Range**: 0-100, NULL if no history

### Column EV: EXPANSION_VELOCITY
**Source**: Rate of address additions over time (as percentage)
**Logic**:
```
addresses_6mo_ago = COUNT(addresses 6 months ago)
addresses_now = COUNT(current addresses)

IF addresses_6mo_ago = 0 AND addresses_now > 0:
  velocity = 100  // 100% growth from zero
ELSE IF addresses_6mo_ago = 0:
  velocity = 0  // No growth from zero
ELSE:
  velocity = ((addresses_now - addresses_6mo_ago) / addresses_6mo_ago) × 100
```
**Units**: Always returns percentage

### Column EW: CONTRACTION_RISK
**Source**: Pattern analysis of recent changes
**Logic**:
```
recent_losses = COUNT(negative TO PREV in last 6 months)
IF recent_losses >= 3: "High"
ELSE IF recent_losses >= 1: "Medium"
ELSE: "Low"
```

### Column EX: MULTI_CITY_OPERATOR
**Source**: Analysis across all records for PROVIDER_GROUP_INDEX_#
**Logic**:
```
unique_cities = COUNT(DISTINCT CITY for this PROVIDER_GROUP_INDEX_#)
IF unique_cities > 1: "Y"
ELSE: "N"
```
**Purpose**: Identifies providers operating across multiple cities

### Column EY: RELOCATION_FLAG
**Source**: Comparison of addresses between current and previous month for same provider
**Logic**:
```
IF previous month data missing:
  RETURN "No Prev Month Found"

FOR this PROVIDER and PROVIDER_TYPE:
  current_addresses = LIST(DISTINCT FULL_ADDRESS this month)
  previous_addresses = LIST(DISTINCT FULL_ADDRESS last month)

  lost_addresses = previous_addresses - current_addresses
  new_addresses = current_addresses - previous_addresses

  IF COUNT(lost_addresses) = 1 AND COUNT(new_addresses) = 1 AND
     COUNT(current_addresses) = COUNT(previous_addresses) AND
     same CITY for both addresses
    THEN "Y"  // Provider relocated within same city
  ELSE "N"
```
**Purpose**: Identifies relocations where a provider closes exactly one location and opens exactly one new location in the same city
**Lead Implication**: High-value leads as relocations often indicate ownership changes or financial restructuring

---

## Summary Sheet Documentation

### Purpose
Provides high-level metrics and status distribution for quick executive overview and monthly reporting.

### Structure
**Format**: 2 columns (Metric, Count)
**Row Count**: 33 rows (including blank separator rows)

### Field Definitions

#### Section 1: Aggregate Counts (Rows 2-6)
**Row 2: Total ADDRESS**
- **Source**: `COUNT(DISTINCT FULL_ADDRESS)` from Analysis sheet
- **Logic**: Counts all unique full addresses in current month
- **Purpose**: Total facility locations tracked

**Row 3: Total PROVIDER**
- **Source**: `COUNT(DISTINCT PROVIDER)` from Analysis sheet
- **Logic**: Counts all unique provider names
- **Purpose**: Total provider entities in system

**Row 4: Total PROVIDER GROUP**
- **Source**: `COUNT(DISTINCT PROVIDER_GROUP_INDEX_#)` from Analysis sheet
- **Logic**: Counts unique group indices
- **Purpose**: Total provider groups (including solo providers)

**Row 5: Total Blanks**
- **Source**: Links to BlanksCount sheet
- **Logic**: `SUM(all blank counts across provider types)`
- **Purpose**: Data quality indicator

**Row 6: Total SOLO PROVIDER TYPE PROVIDER**
- **Source**: `COUNTIF(Column A = "Y")` from Analysis sheet
- **Logic**: Counts records where SOLO_PROVIDER_TYPE_PROVIDER_[Y,#] = "Y"
- **Purpose**: Number of independent solo providers

**Row 7: [BLANK SEPARATOR ROW]**

#### Section 2: Status Distribution (Rows 8-14)
**Row 8: New PROVIDER TYPE, New ADDRESS**
- **Source**: `COUNTIF(Column O = "New PROVIDER TYPE, New ADDRESS")` from Analysis sheet
- **Logic**: Count of this specific status in THIS_MONTH_STATUS
- **Purpose**: Track new market entrants

**Row 9: New PROVIDER TYPE, Existing ADDRESS**
- **Source**: `COUNTIF(Column O = "New PROVIDER TYPE, Existing ADDRESS")`
- **Logic**: Count of providers adding services at existing locations
- **Purpose**: Service expansion tracking

**Row 10: Existing PROVIDER TYPE, New ADDRESS**
- **Source**: `COUNTIF(Column O = "Existing PROVIDER TYPE, New ADDRESS")`
- **Logic**: Count of geographic expansions
- **Purpose**: Location growth tracking

**Row 11: Existing PROVIDER TYPE, Existing ADDRESS**
- **Source**: `COUNTIF(Column O = "Existing PROVIDER TYPE, Existing ADDRESS")`
- **Logic**: Count of unchanged/stable providers
- **Purpose**: Baseline stability metric

**Row 12: Lost PROVIDER TYPE, Existing ADDRESS**
- **Source**: `COUNTIF(Column O = "Lost PROVIDER TYPE, Existing ADDRESS")`
- **Logic**: Count of service reductions at continuing locations
- **Purpose**: Service contraction tracking

**Row 13: Lost PROVIDER TYPE, Lost ADDRESS (0 remain)**
- **Source**: `COUNTIF(Column O = "Lost PROVIDER TYPE, Lost ADDRESS (0 remain)")`
- **Logic**: Count of complete provider exits
- **Purpose**: Market exit tracking

**Row 14: Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)**
- **Source**: `COUNTIF(Column O = "Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)")`
- **Logic**: Count of partial location closures
- **Purpose**: Partial contraction tracking

**Row 15: Reinstated PROVIDER TYPE, Existing ADDRESS**
- **Source**: `COUNTIF(Column O = "Reinstated PROVIDER TYPE, Existing ADDRESS")`
- **Logic**: Count of providers returning after 1-4 month gap
- **Purpose**: Track intermittent providers and reinstatement patterns

**Row 16: [BLANK SEPARATOR ROW]**

#### Section 3: Lead Generation Metrics (Rows 17-19)
**Row 17: Total Seller/Survey Lead**
- **Source**: `COUNTIF(Column P:P, "*") - COUNTIF(Column P:P, "")` from Analysis sheet
- **Logic**: Total count of all records with any lead type assigned
- **Purpose**: Overall lead pipeline size

**Row 18: Total Seller Lead**
- **Source**: `COUNTIF(Column P = "Seller Lead") + COUNTIF(Column P = "Seller/Survey Lead")` from Analysis sheet
- **Logic**: Providers marked as potential acquisition targets (includes mixed leads)
- **Purpose**: M&A opportunity pipeline

**Row 19: Total Survey Lead**
- **Source**: `COUNTIF(Column P = "Survey Lead") + COUNTIF(Column P = "Seller/Survey Lead")` from Analysis sheet
- **Logic**: Providers flagged for survey outreach (includes mixed leads)
- **Purpose**: Research and feedback targets

**Row 20: [BLANK SEPARATOR ROW]**

#### Section 4: Provider Type Breakdown (Rows 21-33)
**Row 21: Total Record Count (TRC)**
- **Source**: `COUNT(all records)` from Analysis sheet
- **Logic**: Total number of all provider records
- **Purpose**: Overall database size

**Rows 22-33: [PROVIDER_TYPE] (TRC)**
- **Source**: `COUNTIF(Column B = [specific provider type])` from Analysis sheet
- **Complete List**:
  - Row 22: ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME (TRC)
  - Row 23: ASSISTED_LIVING_CENTER (TRC)
  - Row 24: ASSISTED_LIVING_HOME (TRC)
  - Row 25: BEHAVIORAL_HEALTH_INPATIENT (TRC)
  - Row 26: BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY (TRC)
  - Row 27: CC_CENTERS (TRC)
  - Row 28: CC_GROUP_HOMES (TRC)
  - Row 29: DEVELOPMENTALLY_DISABLED_GROUP_HOME (TRC)
  - Row 30: HOSPITAL_REPORT (TRC)
  - Row 31: NURSING_HOME (TRC)
  - Row 32: NURSING_SUPPORTED_GROUP_HOMES (TRC)
  - Row 33: OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT (TRC)
- **Logic**: Total Record Count for each provider type
- **Purpose**: Distribution by service category

### Calculation Formulas
```excel
// Example formulas for Summary sheet with correct row numbers
B2: =COUNTUNIQUE(Analysis!G:G)  // Total ADDRESS
B3: =COUNTUNIQUE(Analysis!C:C)  // Total PROVIDER
B4: =COUNTUNIQUE(Analysis!K:K)  // Total PROVIDER GROUP
B5: =SUM(BlanksCount!B2:L13)    // Total Blanks
B6: =COUNTIF(Analysis!A:A,"Y")  // Total SOLO

// Status counts
B8: =COUNTIF(Analysis!O:O,"New PROVIDER TYPE, New ADDRESS")
B9: =COUNTIF(Analysis!O:O,"New PROVIDER TYPE, Existing ADDRESS")
B10: =COUNTIF(Analysis!O:O,"Existing PROVIDER TYPE, New ADDRESS")
B11: =COUNTIF(Analysis!O:O,"Existing PROVIDER TYPE, Existing ADDRESS")
B12: =COUNTIF(Analysis!O:O,"Lost PROVIDER TYPE, Existing ADDRESS")
B13: =COUNTIF(Analysis!O:O,"Lost PROVIDER TYPE, Lost ADDRESS (0 remain)")
B14: =COUNTIF(Analysis!O:O,"Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)")
B15: =COUNTIF(Analysis!O:O,"Reinstated PROVIDER TYPE, Existing ADDRESS")

// Lead counts
B17: =COUNTIF(Analysis!P:P,"*")-COUNTIF(Analysis!P:P,"")  // Total Seller/Survey Lead
B18: =COUNTIF(Analysis!P:P,"Seller Lead")+COUNTIF(Analysis!P:P,"Seller/Survey Lead")  // Total Seller Lead
B19: =COUNTIF(Analysis!P:P,"Survey Lead")+COUNTIF(Analysis!P:P,"Seller/Survey Lead")  // Total Survey Lead

// Total Record Count
B21: =COUNTA(Analysis!B:B)-1  // Subtract header row

// Provider type counts
B22: =COUNTIF(Analysis!B:B,"ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME")
B23: =COUNTIF(Analysis!B:B,"ASSISTED_LIVING_CENTER")
B24: =COUNTIF(Analysis!B:B,"ASSISTED_LIVING_HOME")
B25: =COUNTIF(Analysis!B:B,"BEHAVIORAL_HEALTH_INPATIENT")
B26: =COUNTIF(Analysis!B:B,"BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY")
B27: =COUNTIF(Analysis!B:B,"CC_CENTERS")
B28: =COUNTIF(Analysis!B:B,"CC_GROUP_HOMES")
B29: =COUNTIF(Analysis!B:B,"DEVELOPMENTALLY_DISABLED_GROUP_HOME")
B30: =COUNTIF(Analysis!B:B,"HOSPITAL_REPORT")
B31: =COUNTIF(Analysis!B:B,"NURSING_HOME")
B32: =COUNTIF(Analysis!B:B,"NURSING_SUPPORTED_GROUP_HOMES")
B33: =COUNTIF(Analysis!B:B,"OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT")
```

---

## BlanksCount Sheet Documentation

### Purpose
Tracks missing data (blanks/nulls) by provider type to identify data quality issues and inform cleanup efforts.

### Structure
**Format**: Matrix with provider types as rows and data fields as columns
**Dimensions**: 12 rows × 11 columns

### Column Definitions

**Column A: Provider Type (Unnamed: 0)**
- **Values**: List of all provider types
- **Examples**:
  - ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME
  - ASSISTED_LIVING_CENTER
  - ASSISTED_LIVING_HOME
  - BEHAVIORAL_HEALTH_INPATIENT
  - BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY
  - CC_CENTERS
  - CC_GROUP_HOMES
  - DEVELOPMENTALLY_DISABLED_GROUP_HOME
  - HOSPITAL_REPORT
  - NURSING_HOME
  - OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT
  - SUPERVISORY_CARE_FACILITY

**Columns B-K: Field Blank Counts**
- **Column B: MONTH** - Count of blank MONTH values for this provider type
- **Column C: YEAR** - Count of blank YEAR values
- **Column D: PROVIDER** - Count of blank PROVIDER names
- **Column E: ADDRESS** - Count of blank ADDRESS values
- **Column F: CITY** - Count of blank CITY values
- **Column G: ZIP** - Count of blank ZIP codes
- **Column H: CAPACITY** - Count of blank CAPACITY values
- **Column I: LONGITUDE** - Count of blank LONGITUDE values
- **Column J: LATITUDE** - Count of blank LATITUDE values
- **Column K: PROVIDER GROUP INDEX #** - Count of blank group indices

### Calculation Logic
For each cell in the matrix:
```excel
// Formula pattern for each cell
=[Provider Type Row, Field Column] =
  COUNTIFS(
    Analysis!B:B, [Provider Type],
    Analysis![Field Column]:[Field Column], ""
  )

// Example: Blanks for ASSISTED_LIVING_CENTER ADDRESS field
=COUNTIFS(Analysis!B:B,"ASSISTED_LIVING_CENTER", Analysis!D:D,"")
```

### Data Quality Metrics Derived

**Critical Fields** (should have zero blanks):
- PROVIDER (Column D)
- ADDRESS (Column E)
- PROVIDER_GROUP_INDEX_# (Column K)

**Important Fields** (minimal blanks acceptable):
- CITY (Column F)
- ZIP (Column G)
- MONTH (Column B)
- YEAR (Column C)

**Optional Fields** (blanks acceptable but not ideal):
- CAPACITY (Column H)
- LONGITUDE (Column I)
- LATITUDE (Column J)

### Usage for Quality Control

1. **Monthly Quality Check**:
   - Run after each monthly data load
   - Flag provider types with >10% blanks in critical fields
   - Prioritize cleanup based on blank counts

2. **Provider Type Issues**:
   - Identify provider types with systematic data issues
   - Target specific types for data enhancement efforts

3. **Field Completeness Score**:
   ```
   Completeness % = (1 - (Blank Count / Total Records)) × 100
   ```

4. **Quality Threshold Alerts**:
   - RED: >20% blanks in critical fields
   - YELLOW: 10-20% blanks in critical fields
   - GREEN: <10% blanks in all fields

---

## Summary of v300 Enhancements

### Major v300 Enhancements:
1. **FULL_ADDRESS** (Column G) - Complete address string for better matching
2. **COUNTY** (Column K) - Regional analysis capability
3. **Extended History**  40+ months vs. ~15 months
4. **Column Shift** - Enhanced fields now in columns EH-EY (18 tracking fields)
5. **New Analytics** - Regional markets, stability scoring, expansion velocity

### Data Quality Improvements:
- Full address matching reduces false positives
- County data enables regional pattern detection
- Extended history allows long-term trend analysis
- Stability scoring identifies reliable providers

### Business Intelligence Gains:
- Regional market identification
- Multi-county operator tracking
- Expansion/contraction velocity metrics
- Enhanced risk assessment

---

## Critical Implementation Notes

1. **FULL_ADDRESS** must be consistently formatted across all months
2. **COUNTY** data must be backfilled for historical records
3. Extended columns (Q-EE) require historical data loading
4. Column references in formulas must be updated for new positions
5. Enhanced tracking fields (EH-EY) require initial calculation for all records

---

## Column Structure Reference (155 columns)

| Range | Columns | Content | Naming Pattern |
|-------|---------|---------|----------------|
| A-P | 16 | Core identification fields | `PROVIDER_TYPE`, `THIS_MONTH_STATUS`, etc. |
| Q-BD | 40 | Monthly COUNT fields | `9.24_COUNT` through `12.27_COUNT` |
| BE-CQ | 39 | Monthly TO PREV fields | `10.24_TO_PREV` through `12.27_TO_PREV` |
| CR-EE | 40 | Monthly SUMMARY fields | `9.24_SUMMARY` through `12.27_SUMMARY` |
| EF-EG | 2 | Metadata | `MONTH`, `YEAR` |
| EH-EY | 18 | Enhanced tracking fields | `PREVIOUS_MONTH_STATUS` through `RELOCATION_FLAG` |

### Lead Type Values (Title Case)
Per v300 spec, lead types use Title Case:
- `Survey Lead`
- `Seller Lead`
- `Seller/Survey Lead`

### SUMMARY Column Format
SUMMARY columns concatenate only columns M and N:
```
{PROVIDER_GROUP,_ADDRESS_COUNT}, {PROVIDER_GROUP_(DBA_Concat)}
```
Example: `"7, SAGUARO FOUNDATION COMMUNITY LIVING PROGRAM (2783 S MARY AVENUE)"`

---

*Version: v300Track*
*Last Updated: Analysis for extended historical tracking and regional insights*
*11.25.25*
