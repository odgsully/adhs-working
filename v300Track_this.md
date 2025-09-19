# v300Track Analysis Sheet - Complete Field Definitions

## Version Overview
**v300Track** represents a major enhancement with:
- Extended historical tracking (Q:EE for monthly data spanning longer periods)
- Full address consolidation in Column G
- County data addition in Column K
- Enhanced tracking fields now starting at Column EH

---

## Core Identification Fields (Columns A-P)

### Column A: SOLO PROVIDER TYPE PROVIDER [Y, #]
**Source**: Calculated from current month's Reformat data
**Logic**:
```
IF all addresses in PROVIDER GROUP INDEX # have same PROVIDER TYPE
  THEN "Y"  // Regardless of address count
ELSE
  COUNT(distinct PROVIDER TYPE for this PROVIDER GROUP INDEX #)
```
**Example**: "Y" = all addresses have same provider type (could be 1 or many addresses), "3" = group has 3 different provider types

### Column B: PROVIDER TYPE
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

### Column G: FULL ADDRESS
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
**Note**: Shifted one column right due to FULL_ADDRESS addition

### Column I: LONGITUDE
**Source**: Direct from Reformat file
**Note**: Shifted one column right due to FULL_ADDRESS addition

### Column J: LATITUDE
**Source**: Direct from Reformat file
**Note**: Shifted one column right due to FULL_ADDRESS addition

### Column K: COUNTY
**Source**: Direct from Raw file
**Values**: County names (e.g., "MARICOPA", "PIMA", "COCONINO")
**Purpose**: Enables county-level analysis and regional tracking
**Note**: This shifts PROVIDER GROUP INDEX # to Column L

### Column L: PROVIDER GROUP INDEX #
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
5. Merger: lowest index number wins
6. Split: original keeps index, new gets next available
```

### Column M: PROVIDER GROUP (DBA CONCAT)
**Source**: Calculated from all records sharing same PROVIDER GROUP INDEX #
**Logic**:
```
FOR each PROVIDER GROUP INDEX #:
  LIST all other providers with same index
  FORMAT as: "PROVIDER NAME (FULL ADDRESS), PROVIDER NAME (FULL ADDRESS)"
  EXCLUDE self from list
  SORT alphabetically by provider name
```
**Exact Format Examples**:
- "VISIT-N-CARE/ ALDO (7123 N 77TH DRIVE, GLENDALE, AZ 85303)"
- "VISIT-N-CARE /  MAHALO (7373 W MONTEBELLO AVE, PHOENIX, AZ 85033), VISIT-N-CARE/ ALDO (7123 N 77TH DRIVE, GLENDALE, AZ 85303)"
- "ZION COMPASSION CARE, LLC/ MT CALVARY (424 S ROSEMONT, MESA, AZ 85206), ZION COMPASSION CARE, LLC/ MT TABOR (4752 E DRAGOON AVE, TUCSON, AZ 85710)"

**Format Pattern**: `PROVIDER NAME (FULL ADDRESS), PROVIDER NAME (FULL ADDRESS)`
**Note**: Uses FULL_ADDRESS for complete location matching

### Column N: PROVIDER GROUP, ADDRESS COUNT
**Source**: Calculated COUNT(DISTINCT FULL ADDRESS for this PROVIDER GROUP INDEX #)
**Note**: Now uses FULL ADDRESS (Column G) instead of ADDRESS (Column D)

### Column O: THIS MONTH STATUS
**Source**: Calculated by comparing current month to previous month
**Logic**:
```
IF no record in previous month AND Column A = "Y"
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

### Column P: LEAD TYPE
**Source**: Derived from THIS MONTH STATUS



### Columns Q-BD: [Month.Year] COUNT
**Coverage**: Extended historical range spanning 40+ months
**Logic**:
```
FOR each month column:
  IF provider+type+FULL ADDRESS exists in that month's Reformat file
    THEN 1
  ELSE 0
```
**Span**: Now covers 40+ months of historical data
**Example Columns**:
- Q: "1.22 COUNT"
- R: "2.22 COUNT"
- ...continuing through...
- BD: "12.25 COUNT"



### Columns BE-CQ: [Month.Year] TO PREV
**Coverage**: Matches extended count range
**Logic**:
```
Current month COUNT - Previous month COUNT
Results:
  1 = Added this month
  0 = No change
  -1 = Lost this month
```
**Span**: Covers same 40+ month range as COUNT section


### Columns CR-EE: [Month.Year] SUMMARY
**Coverage**: Matches extended count range
**Logic**:
```
IF TO PREV = 1: "Added in [Month.Year]"
ELSE IF TO PREV = -1: "Lost in [Month.Year]"
ELSE IF COUNT = 1: "Active"
ELSE: "Inactive"
```
**Purpose**: Human-readable status for each historical month


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
IF FULL ADDRESS is NULL: score -= 25  // Changed from ADDRESS
IF COUNTY is NULL: score -= 5         // New check
IF PROVIDER GROUP INDEX # is NULL: score -= 10
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
**Row Count**: 32 rows (including blank separator rows)

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

#### Section 3: Lead Generation Metrics (Rows 17-18)
**Row 17: Seller Leads**
- **Source**: `COUNTIF(Column P = "Exit Lead - Full" OR "Exit Lead - Partial")`
- **Logic**: Providers marked as potential acquisition targets
- **Purpose**: M&A opportunity pipeline

**Row 18: Survey Leads**
- **Source**: `COUNTIF(Column P CONTAINS "Survey")`
- **Logic**: Providers flagged for survey outreach
- **Purpose**: Research and feedback targets

**Row 19: [BLANK SEPARATOR ROW]**

#### Section 4: Provider Type Breakdown (Rows 20-32)
**Row 20: Total Record Count (TRC)**
- **Source**: `COUNT(all records)` from Analysis sheet
- **Logic**: Total number of all provider records
- **Purpose**: Overall database size

**Rows 21-32: [PROVIDER_TYPE] (TRC)**
- **Source**: `COUNTIF(Column B = [specific provider type])` from Analysis sheet
- **Complete List**:
  - Row 21: ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME (TRC)
  - Row 22: ASSISTED_LIVING_CENTER (TRC)
  - Row 23: ASSISTED_LIVING_HOME (TRC)
  - Row 24: BEHAVIORAL_HEALTH_INPATIENT (TRC)
  - Row 25: BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY (TRC)
  - Row 26: CC_CENTERS (TRC)
  - Row 27: CC_GROUP_HOMES (TRC)
  - Row 28: DEVELOPMENTALLY_DISABLED_GROUP_HOME (TRC)
  - Row 29: HOSPITAL_REPORT (TRC)
  - Row 30: NURSING_HOME (TRC)
  - Row 31: NURSING_SUPPORTED_GROUP_HOMES (TRC)
  - Row 32: OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT (TRC)
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
B17: =COUNTIFS(Analysis!P:P,"Exit Lead - Full")+COUNTIFS(Analysis!P:P,"Exit Lead - Partial")
B18: =COUNTIF(Analysis!P:P,"*Survey*")

// Total Record Count
B20: =COUNTA(Analysis!B:B)-1  // Subtract header row

// Provider type counts
B21: =COUNTIF(Analysis!B:B,"ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME")
B22: =COUNTIF(Analysis!B:B,"ASSISTED_LIVING_CENTER")
B23: =COUNTIF(Analysis!B:B,"ASSISTED_LIVING_HOME")
B24: =COUNTIF(Analysis!B:B,"BEHAVIORAL_HEALTH_INPATIENT")
B25: =COUNTIF(Analysis!B:B,"BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY")
B26: =COUNTIF(Analysis!B:B,"CC_CENTERS")
B27: =COUNTIF(Analysis!B:B,"CC_GROUP_HOMES")
B28: =COUNTIF(Analysis!B:B,"DEVELOPMENTALLY_DISABLED_GROUP_HOME")
B29: =COUNTIF(Analysis!B:B,"HOSPITAL_REPORT")
B30: =COUNTIF(Analysis!B:B,"NURSING_HOME")
B31: =COUNTIF(Analysis!B:B,"NURSING_SUPPORTED_GROUP_HOMES")
B32: =COUNTIF(Analysis!B:B,"OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT")
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
1. **FULL ADDRESS** (Column G) - Complete address string for better matching
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

1. **FULL ADDRESS** must be consistently formatted across all months
2. **COUNTY** data must be backfilled for historical records
3. Extended columns (Q-EE) require historical data loading
4. Column references in formulas must be updated for new positions
5. Enhanced tracking fields (EH-EY) require initial calculation for all records

---

*Version: v300Track*
*Last Updated: Analysis for extended historical tracking and regional insights*
*09.18.25*
