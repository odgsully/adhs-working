# Analysis of Duplicate Records - Combined Column C & Column G

**Source File:** `Analysis/11.24_Analysis_12.01.03-47-23.xlsx`
**Total Records:** 10,280
**Analysis Date:** 2025-12-02
**Version:** v300Track Compliance Review

---

## Executive Summary

This document provides a comprehensive analysis of duplicate records across two critical columns:
- **Column C (PROVIDER):** 1,630 duplicate records across 440 unique providers
- **Column G (FULL_ADDRESS):** 398 duplicate records across 185 unique addresses
- **Intersection (Both C & G duplicated):** 63 records requiring priority review

---

# SECTION 0: Data Pipeline & Record Origin

## Source of Truth

**Primary Data Source:** Arizona Department of Health Services (ADHS)
- Monthly license roster downloads containing all active healthcare facility licenses in Arizona
- Each download represents a point-in-time snapshot of licensed providers
- Location: `ALL-MONTHS/Raw M.YY/` directories (e.g., `Raw 11.24/`, `Raw 10.24/`)

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA PIPELINE FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  RAW ADHS    │───▶│   REFORMAT   │───▶│  ALL-TO-DATE │───▶│ ANALYSIS  │ │
│  │  Downloads   │    │   M.YY       │    │    M.YY      │    │   M.YY    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│                                                                             │
│  Location:           Location:           Location:           Location:     │
│  ALL-MONTHS/         Reformat/           All-to-Date/        Analysis/     │
│  Raw M.YY/                                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Raw ADHS Download
- **Input:** Excel files downloaded from ADHS portal
- **Content:** Active licenses for the month
- **Fields:** Facility name, address, license type, capacity, coordinates, etc.
- **Processing:** None - raw data preserved as-is

### Stage 2: Reformat
- **Script:** `scripts/process_months_local.py` → `src/adhs_etl/pipeline.py`
- **Output:** `M.YY_Reformat_{timestamp}.xlsx`
- **Transformations:**
  - Field mapping via `field_map.yml`
  - Standardized column names (PROVIDER, PROVIDER_TYPE, ADDRESS, CITY, ZIP, etc.)
  - FULL_ADDRESS concatenation: `{ADDRESS}, {CITY}, AZ {ZIP}`
  - PROVIDER_GROUP_INDEX_# assignment (fuzzy matching 85%+ or 20+ char match)
- **Record count:** Only records from current month's ADHS download

### Stage 3: All-to-Date
- **Output:** `M.YY_Reformat_All_to_Date_{timestamp}.xlsx`
- **Content:** Cumulative union of all Reformat files from 9.24 onwards
- **Purpose:** Historical reference, not used for Analysis generation

### Stage 4: Analysis
- **Script:** `src/adhs_etl/analysis.py`
- **Output:** `M.YY_Analysis_{timestamp}.xlsx`
- **Content:** 155 columns per v300Track_this.md specification
- **Record population logic:** See below

## Record Qualification Criteria

### How a Record ENTERS the Analysis File

A record is added to Analysis when it appears in **ANY** month's Reformat file:

| Scenario | Action | THIS_MONTH_STATUS |
|----------|--------|-------------------|
| New in current month, never seen before | ADD record | `NEW PROVIDER TYPE, NEW ADDRESS` |
| New in current month, address existed with different provider | ADD record | `NEW PROVIDER TYPE, EXISTING ADDRESS` |
| New in current month, provider existed at different address | ADD record | `EXISTING PROVIDER TYPE, NEW ADDRESS` |
| Exists in current month, existed last month | KEEP record | `EXISTING PROVIDER TYPE, EXISTING ADDRESS` |
| Missing 1-4 months, now returned | KEEP record | `REINSTATED PROVIDER TYPE, EXISTING ADDRESS` |

### How a Record is Marked LOST (but retained)

| Scenario | Action | THIS_MONTH_STATUS | M.YY_COUNT |
|----------|--------|-------------------|------------|
| Was in last month, not in current month, no other addresses | KEEP + mark LOST | `LOST PROVIDER TYPE, LOST ADDRESS (0 remain)` | 0 |
| Was in last month, not in current month, other addresses exist | KEEP + mark LOST | `LOST PROVIDER TYPE, LOST ADDRESS (1+ remain)` | 0 |
| Address exists, but this provider type dropped | KEEP + mark LOST | `LOST PROVIDER TYPE, EXISTING ADDRESS` | 0 |

### Composite Primary Key

Records are uniquely identified by:
```
PROVIDER + PROVIDER_TYPE + FULL_ADDRESS
```

**Important:** The same physical location can have multiple records if:
- Different PROVIDER names operate there (multi-tenant building)
- Same PROVIDER has different PROVIDER_TYPE licenses (e.g., Nursing Home + Outpatient)

## Deduplication Rules

### When Duplicates Exist in Source Data

Currently **NO automatic deduplication** is performed. If ADHS source contains duplicates:
- Both records flow through to Reformat
- Both records appear in Analysis
- Both receive the same M.YY_COUNT value
- Manual intervention required to resolve

### Identified True Duplicates Requiring Manual Review

| Provider | Address | Occurrences | Issue |
|----------|---------|-------------|-------|
| ST MICHAELS ASSOCIATION FOR SPECIAL EDUCATION | 1 MILE NORTH OF HWY 264, MUSTANG ROAD | 3x | Source data error |
| MAYO CLINIC HOSPITAL | 5777 EAST MAYO BOULEVARD, PHOENIX | 2x | Capacity field variance |
| D.V.U.S.D.#97 - NORTERRA CANYON | 2200 WEST MAYA WAY, PHOENIX | 2x | Capacity mismatch (45 vs 59) |
| *(20 additional cases)* | | | |

## Field Mapping Reference

| Analysis Column | Source Field | Transformation |
|-----------------|--------------|----------------|
| PROVIDER_TYPE | License Type | Mapped via field_map.yml |
| PROVIDER | Facility Name / DBA | Uppercase, trimmed |
| ADDRESS | Street Address | Uppercase, trimmed |
| CITY | City | Uppercase, trimmed |
| ZIP | ZIP Code | 5-digit format |
| FULL_ADDRESS | Derived | `{ADDRESS}, {CITY}, AZ {ZIP}` |
| CAPACITY | Licensed Capacity | Integer or null |
| LONGITUDE | Longitude | Float |
| LATITUDE | Latitude | Float |
| COUNTY | County | Uppercase |
| PROVIDER_GROUP_INDEX_# | Derived | Fuzzy match grouping |

## Month-to-Month Tracking Logic

```
FOR each record in previous Analysis file:
  IF record's (PROVIDER + PROVIDER_TYPE + FULL_ADDRESS) exists in current Reformat:
    STATUS = "EXISTING..."
    COUNT = number of locations for this PROVIDER+TYPE in current Reformat
  ELSE:
    STATUS = "LOST..."
    COUNT = 0

FOR each record in current Reformat:
  IF record NOT in previous Analysis:
    ADD to Analysis
    STATUS = "NEW..."
    COUNT = number of locations for this PROVIDER+TYPE
```

---

# SECTION 1: Column C - PROVIDER Duplicates

## Category Breakdown by Percentage

| Category | Records | % |
|----------|---------|---|
| Other Healthcare | 696 | 42.7% |
| Banner Health System | 217 | 13.3% |
| Behavioral/Mental Health | 166 | 10.2% |
| Home Care/Assisted Living | 147 | 9.0% |
| Community Health/Clinics | 110 | 6.7% |
| Childcare/Learning Centers | 98 | 6.0% |
| Specialty/Outpatient Services | 72 | 4.4% |
| Urgent Care/Retail Clinics | 58 | 3.6% |
| HonorHealth System | 34 | 2.1% |
| Phoenix Children's Hospital | 17 | 1.0% |
| Dignity Health System | 15 | 0.9% |

---

## Edge Case Classification - Column C

| Edge Case Type | Count | % of 1,630 | Assessment |
|----------------|-------|------------|------------|
| Legitimate multi-location chains | 1,607 | 98.6% | Valid duplicates |
| True duplicates (same provider + same address) | 23 | 1.4% | Data quality issue |
| Naming inconsistency (same entity, different name) | 1 | <0.1% | Needs standardization |

### True Duplicates Identified (23 cases)

These provider-address combinations appear multiple times and represent actual data quality issues:

- ACACIA HEALTH CENTER at 4555 EAST MAYO BLVD, PHOENIX
- ALTA MESA HEALTH AND REHABILITATION at 5848 EAST UNIVERSITY DRIVE, MESA
- MAYO CLINIC HOSPITAL at 5777 EAST MAYO BOULEVARD, PHOENIX
- ST MICHAELS ASSOCIATION FOR SPECIAL EDUCATION (3x duplicate)
- D.V.U.S.D.#97 - NORTERRA CANYON (capacity mismatch: 45 vs 59)
- *(and 18 additional cases)*

### Naming Inconsistency (1 case)

- **Address:** 2187 NORTH VICKEY STREET, FLAGSTAFF, AZ 86004
  - Listed as: "THE GUIDANCE CENTER, INC"
  - Also as: "GUIDANCE CENTER, INC., THE"

---

# SECTION 2: Column G - FULL_ADDRESS Duplicates

## Overview Statistics

| Metric | Value |
|--------|-------|
| Total unique addresses | 10,065 |
| Addresses appearing only once | 9,880 (98.16%) |
| Addresses with duplicates | 185 (1.84%) |
| Total records at duplicate addresses | 398 (3.87%) |

## Frequency Distribution

| Times Address Appears | Addresses | Total Records |
|----------------------|-----------|---------------|
| 5 times | 2 | 10 |
| 4 times | 3 | 12 |
| 3 times | 16 | 48 |
| 2 times | 164 | 328 |

## Edge Case Classification - Column G

| Edge Case Type | Records | % of 398 | Assessment |
|----------------|---------|----------|------------|
| Legitimate multi-provider locations | 357 | 89.7% | Valid - hospital campuses, CCRCs, schools |
| True duplicates (same provider+address) | 41 | 10.3% | Data quality issue |
| Address normalization issues | 32 | 8.0% | Fixable - WEST vs W, BLVD vs BOULEVARD |

### Top Duplicate Addresses

1. **100 WEST CHIEF MANUELITO BLVD, CHINLE, AZ 86503** (5x) - Chinle Valley School campus
2. **2460 PARKVIEW LOOP, YUMA, AZ 85364** (5x) - Yuma Regional Medical Center departments
3. **2187 NORTH VICKEY STREET, FLAGSTAFF, AZ 86004** (4x) - The Guidance Center multi-service
4. **1200 WEST MOHAVE ROAD, PARKER, AZ 85344** (4x) - La Paz Regional Hospital
5. **4951 SOUTH WHITE MOUNTAIN ROAD, BUILDING A, SHOW LOW, AZ 85901** (4x) - Summit Healthcare

### Address Normalization Issues (16 pairs, 32 records)

| Variation Type | Example | Records Affected |
|---------------|---------|------------------|
| Direction (WEST/W) | 100 WEST vs 100 W CHIEF MANUELITO BLVD | 8 |
| Direction (EAST/E) | 3003 EAST vs 3003 E MCDOWELL ROAD | 2 |
| Street (BOULEVARD/BLVD) | RANCHO VISTOSO BOULEVARD vs BLVD | 12 |
| Street (AVENUE/AVE) | VIRGINIA AVENUE vs AVE | 8 |
| Street (ROAD/RD) | THOMAS ROAD vs RD | 2 |

---

# SECTION 3: Combined Analysis - C & G Intersection

## Intersection Overview

**63 records** (0.61% of dataset) where BOTH:
- The PROVIDER (Column C) appears more than once
- AND the FULL_ADDRESS (Column G) appears more than once

This represents the **highest priority subset** for data quality review.

## Intersection Classification

| Category | Records | % of 63 | Priority |
|----------|---------|---------|----------|
| TRUE DUPLICATES (same provider + same address, multiple times) | 47 | 74.6% | CRITICAL |
| NAMING INCONSISTENCY (provider variants at shared addresses) | 16 | 25.4% | HIGH |

### TRUE DUPLICATES - 47 Records (23 Unique Pairs)

These are exact duplicates - same provider name AND same address appearing 2-3 times:

| Provider | Address | Count | Issue |
|----------|---------|-------|-------|
| ST MICHAELS ASSOCIATION FOR SPECIAL EDUCATION | 1 MILE NORTH OF HWY 264, MUSTANG ROAD, SAINT MICHAELS | 3x | Triple duplicate |
| MAYO CLINIC HOSPITAL | 5777 EAST MAYO BOULEVARD, PHOENIX | 2x | Capacity field variance |
| ACACIA HEALTH CENTER | 4555 EAST MAYO BLVD, PHOENIX | 2x | True duplicate |
| ALTA MESA HEALTH AND REHABILITATION | 5848 EAST UNIVERSITY DRIVE, MESA | 2x | True duplicate |
| SHEA POST ACUTE REHABILITATION CENTER | 11150 NORTH 92ND STREET, SCOTTSDALE | 2x | True duplicate |
| *(18 additional pairs)* | | | |

### NAMING INCONSISTENCY - 16 Records

| Address | Provider Variants | Issue |
|---------|------------------|-------|
| 2187 NORTH VICKEY STREET, FLAGSTAFF | "THE GUIDANCE CENTER, INC", "GUIDANCE CENTER, INC., THE", "THE GUIDANCE CENTER" | 4 name variants |
| 755 EAST MCDOWELL ROAD, PHOENIX | "BANNER PHYSICAL THERAPY AND REHABILITATION", "BANNER - UNIVERSITY MEDICINE INSTITUTES 755" | Unclear if same entity |
| 100 EAST 5TH STREET, DOUGLAS | "COPPER QUEEN COMMUNITY HOSPITAL-DOUGLAS RHC", "COPPER QUEEN COMM HOSPITAL-DOUGLAS EMERGENCY DEPT", "COPPER QUEEN COMMUNITY HOSPITAL - DOUGLAS PHYSICAL" | 3 department names |

---

# SECTION 4: Comprehensive Edge Case Taxonomy

## All Edge Cases with Percentage Breakdowns

| # | Edge Case Type | Records | % of Total | Risk Level | Impact on M.YY Tracking |
|---|---------------|---------|------------|------------|------------------------|
| 1 | **Address normalization (WEST/W, BLVD/BOULEVARD)** | 119 | 1.2% | MEDIUM | May cause false NEW/LOST classifications |
| 2 | **Provider name "THE" prefix/suffix variations** | 356 | 3.5% | MEDIUM | Prevents proper PROVIDER_GROUP_INDEX_# grouping |
| 3 | **Provider name spelling differences** | ~470 | 4.6% | MEDIUM-HIGH | Large systems fragmented across records |
| 4 | **Multi-service locations (same address, different types)** | 134 | 1.3% | LOW | Each type counted separately - by design |
| 5 | **Healthcare system variations (BANNER 115 variants)** | 316 | 3.1% | MEDIUM | Corporate relationships unclear |
| 6 | **Capacity discrepancies (same provider+address)** | 4 | 0.04% | LOW | Data entry errors or facility changes |
| 7 | **Missing critical data fields** | 2 | 0.02% | LOW | Excellent completeness (99.98%) |
| 8 | **PROVIDER_GROUP_INDEX_# inconsistency** | 366 groups | 3.6% | HIGH | DBA_Concat and ADDRESS_COUNT affected |
| 9 | **True duplicates (exact match)** | 9 | 0.09% | LOW | Manual deduplication needed |
| 10 | **Month-to-month tracking anomalies** | ~120 | 1.2% | MEDIUM | Address/name changes cause false status |

### Edge Case Detail: BANNER Health System

BANNER represents the most complex naming challenge:
- **115 unique provider name variations**
- **316 total records** (3.1% of dataset)
- **169 different PROVIDER_GROUP_INDEX_# values** (should be ~115 or fewer)
- **Key variants:**
  - BANNER URGENT CARE (43 locations)
  - BANNER PHYSICAL THERAPY (32 locations)
  - BANNER PHYSICAL THERAPY AND REHABILITATION (31 locations)
  - BANNER HEALTH CLINIC (30 locations)
  - BANNER IMAGING (22 locations)
  - BANNER CHILDREN'S SPECIALISTS (20 locations)

---

# SECTION 5: Record Qualification & M.YY_COUNT Logic

## What Qualifies a Record for Analysis?

A record appears in the Analysis file if it meets ANY of these criteria:
1. **Currently active** - EXISTS in the current month's Reformat file
2. **Historically active** - EXISTED in any tracked month (9.24 onwards)
3. **Lost but tracked** - Was active previously, now has COUNT=0 for historical continuity

### Record Qualification Summary

| Qualification | Records | % |
|--------------|---------|---|
| Active in 11.24 (COUNT > 0) | 10,093 | 98.2% |
| Lost/Inactive (COUNT = 0) | 187 | 1.8% |
| **Total Qualified** | **10,280** | **100%** |

## Primary Key Definition

The **composite primary key** for unique record identification is:

```
PROVIDER + PROVIDER_TYPE + FULL_ADDRESS
```

| Key Combination | Unique Records | Duplicates | Validity |
|----------------|----------------|------------|----------|
| PROVIDER only | 9,090 | 1,190 | INVALID |
| FULL_ADDRESS only | 10,065 | 215 | INVALID |
| PROVIDER + FULL_ADDRESS | 10,254 | 26 | CLOSE |
| **PROVIDER + PROVIDER_TYPE + FULL_ADDRESS** | **10,273** | **7** | **BEST** |

---

## M.YY_COUNT Logic Analysis

### Documentation vs. Implementation

**Per v300Track_this.md (lines 177-189), the expected logic is:**
```
FOR each month column:
  IF provider+type+FULL_ADDRESS exists in that month's Reformat file
    THEN 1
  ELSE 0
```

**Actual Implementation Discovered:**
```
FOR each record in Analysis file:
  COUNT = Number of FULL_ADDRESS records in M.YY Reformat file
          WHERE PROVIDER matches AND PROVIDER_TYPE matches
```

### Key Difference

| Aspect | Expected (Binary) | Actual (Count) |
|--------|-------------------|----------------|
| Value range | 0 or 1 | 0 to 42 |
| Meaning | "Does this location exist?" | "How many locations does this provider have?" |
| Multi-location providers | Each location = 1 | All locations share same count |

### 11.24_COUNT Distribution

| COUNT Value | Records | % | Interpretation |
|-------------|---------|---|----------------|
| 0 | 187 | 1.82% | Lost providers (not in Reformat) |
| 1 | 8,629 | 83.94% | Single-location providers |
| 2-5 | 845 | 8.22% | Small multi-location providers |
| 6-15 | 329 | 3.20% | Medium chains |
| 16-42 | 290 | 2.82% | Large systems (BANNER = 42) |

### Logic Alignment Issue

The current COUNT implementation provides **enterprise-level visibility** (how big is this provider?) rather than **location-level tracking** (does THIS specific address exist this month?).

**Impact:**
- Cannot track individual location presence/absence using COUNT alone
- Must rely on THIS_MONTH_STATUS for location-specific tracking
- SUMMARY columns inherit this aggregated count

---

# SECTION 6: Geographic Distribution

## By County

| County | Duplicate Records | % |
|--------|-------------------|---|
| MARICOPA | 1,049 | 64.4% |
| PIMA | 239 | 14.7% |
| PINAL | 90 | 5.5% |
| YAVAPAI | 62 | 3.8% |
| YUMA | 43 | 2.6% |
| MOHAVE | 42 | 2.6% |
| COCONINO | 24 | 1.5% |
| COCHISE | 23 | 1.4% |
| GILA | 18 | 1.1% |
| APACHE | 9 | 0.6% |
| NAVAJO | 7 | 0.4% |
| GRAHAM | 7 | 0.4% |
| SANTA CRUZ | 7 | 0.4% |
| LA PAZ | 4 | 0.2% |
| GREENLEE | 2 | 0.1% |

## By City (Top 15)

| City | Count | % |
|------|-------|---|
| PHOENIX | 323 | 19.8% |
| TUCSON | 225 | 13.8% |
| MESA | 130 | 8.0% |
| GILBERT | 88 | 5.4% |
| GLENDALE | 85 | 5.2% |
| SCOTTSDALE | 76 | 4.7% |
| CHANDLER | 74 | 4.5% |
| TEMPE | 45 | 2.8% |
| LAVEEN | 39 | 2.4% |
| YUMA | 36 | 2.2% |
| PEORIA | 36 | 2.2% |
| CASA GRANDE | 35 | 2.1% |
| GOODYEAR | 31 | 1.9% |
| SURPRISE | 26 | 1.6% |
| PRESCOTT | 24 | 1.5% |

---

# SECTION 7: By Provider Type (Facility Classification)

| Facility Type | Count | % |
|---------------|-------|---|
| OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT | 919 | 56.4% |
| BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY | 295 | 18.1% |
| CC_CENTERS | 143 | 8.8% |
| ASSISTED_LIVING_HOME | 108 | 6.6% |
| DEVELOPMENTALLY_DISABLED_GROUP_HOME | 82 | 5.0% |
| Other types | <2% each | 5.1% |

---

# SECTION 8: Duplication Frequency Distribution

| Locations per Provider | Providers | Records | % of Total |
|------------------------|-----------|---------|------------|
| 2 locations | 262 | 524 | 32.1% |
| 3 locations | 66 | 198 | 12.1% |
| 4 locations | 37 | 148 | 9.1% |
| 5-9 locations | ~50 | 288 | 17.7% |
| 10+ locations | 27 | 416 | 25.5% |

## Top Multi-Location Providers

| Provider | Locations | Cities |
|----------|-----------|--------|
| BANNER URGENT CARE | 43 | 16 |
| BANNER PHYSICAL THERAPY | 32 | 13 |
| BANNER PHYSICAL THERAPY AND REHABILITATION | 31 | 15 |
| BANNER HEALTH CLINIC | 30 | 13 |
| KINDERCARE LEARNING CENTER | 23 | 11 |
| BANNER IMAGING | 22 | 11 |
| TUTOR TIME CHILD CARE/ LEARNING CENTERS | 22 | 11 |
| BANNER CHILDREN'S SPECIALISTS | 20 | - |
| THE CORE INSTITUTE | 16 | 7 |
| OPTIMA MEDICAL | 15 | 14 |
| HONORHEALTH CANCER CARE | 15 | 9 |
| HONORHEALTH OUTPATIENT THERAPY SERVICES | 15 | 7 |

---

# SECTION 9: Critical Findings & Bugs Identified

## Data Quality Wins

| Metric | Value | Assessment |
|--------|-------|------------|
| Data completeness | 99.98% | EXCELLENT |
| Duplicate-free rate | 99.91% | EXCELLENT |
| Month-to-month tracking | 99.1% | EXCELLENT |
| Historical integrity | 100% | EXCELLENT (no gaps) |

## Critical Bugs in analysis.py

### Bug #1: PROVIDER_GROUP,_ADDRESS_COUNT Incorrect
- **Location:** `src/adhs_etl/analysis.py` line 227
- **Issue:** Counts unique ADDRESSes, not total group members
- **Impact:** 156+ groups affected
- **Current:** `'address_count': len(group_df['ADDRESS'].unique())`
- **Should be:** `'address_count': len(group_df)`

### Bug #2: DBA_Concat Excludes Self
- **Location:** `src/adhs_etl/analysis.py` lines 236-240
- **Issue:** Each record shows only OTHER providers in group
- **Impact:** All multi-member groups show N-1 instead of N

### Bug #3: SOLO Marker Incorrect
- **Location:** `src/adhs_etl/analysis.py` lines 246-252
- **Issue:** 3,031 records marked 'Y' but actually in groups
- **Impact:** SOLO_PROVIDER_TYPE_PROVIDER_[Y,#] unreliable

### Bug #4: M.YY_COUNT Logic Mismatch
- **Issue:** Counts total provider locations, not binary presence
- **Impact:** Cannot track individual location existence from COUNT alone

---

# SECTION 10: Recommendations

## Immediate Actions (Critical)

1. **Deduplicate 23 true duplicate pairs** (47 records) - Keep one record per unique provider-address-type combination
2. **Resolve ST MICHAELS ASSOCIATION triple duplicate** - Investigate source data
3. **Fix PROVIDER_GROUP,_ADDRESS_COUNT bug** - Update analysis.py line 227

## Short-Term Actions (High Priority)

4. **Implement address normalization** - Standardize before duplicate detection:
   - WEST → W, EAST → E, NORTH → N, SOUTH → S
   - BOULEVARD → BLVD, AVENUE → AVE, STREET → ST, ROAD → RD
5. **Standardize provider naming** - Remove "THE" variations, standardize punctuation
6. **Clarify M.YY_COUNT logic** - Document actual behavior or modify to match spec
7. **Review 4 capacity discrepancy cases** - Determine correct values

## Long-Term Strategic Actions

8. **Add PARENT_ORGANIZATION field** - Link BANNER variants to single parent
9. **Implement provider master ID** - Persistent identity across name changes
10. **Create dual COUNT series** - Location-level binary + Enterprise-level count
11. **Add CHAIN_FLAG column** - Distinguish multi-location providers from unique facilities

---

# SECTION 11: Alignment Ranking

## Criteria Evaluated

| Criterion | Weight | Score (1-10) | Weighted |
|-----------|--------|--------------|----------|
| **Data completeness** | 15% | 10 | 1.50 |
| **Duplicate detection accuracy** | 15% | 7 | 1.05 |
| **M.YY_COUNT logic alignment with v300** | 20% | 4 | 0.80 |
| **PROVIDER_GROUP_INDEX_# consistency** | 15% | 6 | 0.90 |
| **Month-to-month tracking accuracy** | 15% | 8 | 1.20 |
| **Address normalization** | 10% | 5 | 0.50 |
| **Provider name standardization** | 10% | 5 | 0.50 |

## Detailed Scoring Rationale

### Data Completeness: 10/10
- 99.98% of records have all critical fields populated
- Only 2 records missing FULL_ADDRESS/ZIP
- Exceptional data quality

### Duplicate Detection Accuracy: 7/10
- 98.6% of PROVIDER duplicates correctly identified as legitimate chains
- 89.7% of ADDRESS duplicates correctly identified as multi-service locations
- Lost 3 points for 23 true duplicates not flagged for removal

### M.YY_COUNT Logic Alignment: 4/10
- Documentation says binary (0/1) for location existence
- Implementation returns total provider location count (0-42)
- Major deviation from v300Track_this.md specification
- Functional but not as documented

### PROVIDER_GROUP_INDEX_# Consistency: 6/10
- 84.2% of groups are solo providers (correctly identified)
- 366 suspicious groups (3.6%) with inconsistent grouping
- ADDRESS_COUNT bug affects 156+ groups
- DBA_Concat excludes self (unclear if intentional)

### Month-to-Month Tracking: 8/10
- 99.1% continuity between months
- Status transitions (NEW, EXISTING, LOST, REINSTATED) working correctly
- Lost 2 points for address normalization issues causing ~1.2% false classifications

### Address Normalization: 5/10
- No standardization implemented
- 119 records (1.2%) affected by WEST/W, BLVD/BOULEVARD variations
- Same physical location gets different FULL_ADDRESS values month-to-month

### Provider Name Standardization: 5/10
- No standardization for "THE" prefix/suffix
- 356 providers (3.5%) affected
- BANNER has 115 variants for what may be fewer distinct entities

---

## FINAL ALIGNMENT SCORE

# 6.5 / 10

### Interpretation

| Score Range | Assessment |
|-------------|------------|
| 9-10 | Production Ready - Fully aligned |
| 7-8 | Good - Minor adjustments needed |
| **5-6** | **Fair - Significant gaps require attention** |
| 3-4 | Poor - Major rework required |
| 1-2 | Critical - Fundamental issues |

### Current State Summary

The Analysis pipeline produces **high-quality, highly complete data** (99.98% completeness, 99.91% duplicate-free). However, there are **significant alignment gaps** between documentation and implementation:

1. **M.YY_COUNT does not match spec** - This is the largest deviation. The spec says binary (0/1), implementation returns total counts (0-42).

2. **Grouping logic has bugs** - ADDRESS_COUNT, DBA_Concat, and SOLO markers have calculation errors affecting hundreds of groups.

3. **No normalization layer** - Address and provider name variations cause tracking inconsistencies across months.

### Path to 8+/10

1. Fix the 4 identified bugs in analysis.py
2. Implement address normalization preprocessing
3. Clarify and document actual M.YY_COUNT behavior (or modify to match spec)
4. Add provider name standardization rules

### Path to 9+/10

5. Add PARENT_ORGANIZATION field for enterprise tracking
6. Implement provider master ID for persistent identity
7. Create validation layer to catch future inconsistencies
8. Add automated duplicate detection with flagging

---

# SECTION 12: Implementation Plan

## Sample Size Limitation

**Current Analysis Based On:**
- **3 months only:** 9.24, 10.24, 11.24
- **10,280 records** in latest Analysis file
- **Limited visibility** into seasonal patterns, long-term provider behavior, edge cases

**Recommendation:** Expand validation to full historical range (9.24 → present) before implementing fixes to ensure:
- Edge cases aren't artifacts of small sample
- Patterns hold across 12+ months of data
- Seasonal variations are accounted for

---

## Phase 0: Expanded Validation (Before Any Code Changes)

### 0.1 Full Historical Analysis
**Objective:** Validate findings across larger dataset before implementing fixes

| Task | Description | Deliverable |
|------|-------------|-------------|
| Process all available months | Run pipeline on 9.24 through most recent month | All M.YY_Reformat files |
| Generate comprehensive Analysis | Build Analysis with full 40-month history | Full historical Analysis file |
| Re-run duplicate analysis | Validate C & G duplicate patterns hold | Updated edge case percentages |
| Track provider lifecycle | Identify providers that appear/disappear/return | Provider lifecycle report |

**Success Criteria:**
- [ ] Edge case percentages within ±2% of current findings
- [ ] No new edge case categories discovered
- [ ] M.YY_COUNT logic confirmed across all months

### 0.2 Baseline Metrics Capture
**Objective:** Establish measurable baseline before changes

| Metric | Current Value | Target |
|--------|---------------|--------|
| Data completeness | 99.98% | Maintain |
| True duplicate rate | 0.09% | <0.05% |
| Address normalization issues | 1.2% | <0.1% |
| Provider name variations | 3.5% | <1.0% |
| PROVIDER_GROUP_INDEX_# accuracy | 96.4% | >99% |
| M.YY_COUNT spec alignment | 4/10 | 9/10 |

---

## Phase 1: Critical Bug Fixes (Conservative, Low-Risk)

### 1.1 Fix PROVIDER_GROUP,_ADDRESS_COUNT Bug
**File:** `src/adhs_etl/analysis.py` line 227
**Risk:** LOW - Calculation fix, no data model change

```python
# CURRENT (broken)
'address_count': len(group_df['ADDRESS'].unique())

# FIXED
'address_count': len(group_df)  # Count all members in group
```

**Validation:**
- [ ] Run on 11.24 data
- [ ] Verify 156 affected groups now show correct counts
- [ ] Compare before/after for 10 sample groups

### 1.2 Clarify DBA_Concat Design Decision
**Question:** Should DBA_Concat include self or exclude self?

| Option | Behavior | Pros | Cons |
|--------|----------|------|------|
| **A: Exclude self (current)** | Each record sees N-1 others | Less redundant | Inconsistent within groups |
| **B: Include self** | Each record sees all N | Consistent | More verbose |

**Recommendation:** Keep current behavior BUT document it explicitly in v300Track_this.md

### 1.3 Fix SOLO Marker Logic
**File:** `src/adhs_etl/analysis.py` lines 246-252
**Risk:** MEDIUM - Affects 3,031 records

```python
# CURRENT (checks providers at same ADDRESS)
providers_at_address = df[df['ADDRESS'] == row['ADDRESS']]['PROVIDER'].unique()

# FIXED (checks actual group membership)
group_size = group_info[row['PROVIDER_GROUP_INDEX_#']]['member_count']
solo = 'Y' if group_size == 1 else str(group_size)
```

**Validation:**
- [ ] Verify previously incorrect "Y" markers now show correct count
- [ ] Spot-check 20 multi-member groups

---

## Phase 2: Normalization Layer (Medium-Risk, High-Impact)

### 2.1 Address Normalization
**Objective:** Standardize address formats BEFORE duplicate detection and tracking

**Implementation Location:** `src/adhs_etl/pipeline.py` (Reformat stage)

```python
def normalize_address(address: str) -> str:
    """Standardize address abbreviations for consistent matching."""
    if not address:
        return address

    address = address.upper().strip()

    # Direction normalization
    replacements = {
        r'\bNORTH\b': 'N', r'\bSOUTH\b': 'S',
        r'\bEAST\b': 'E', r'\bWEST\b': 'W',
        r'\bNORTHEAST\b': 'NE', r'\bNORTHWEST\b': 'NW',
        r'\bSOUTHEAST\b': 'SE', r'\bSOUTHWEST\b': 'SW',

        # Street type normalization
        r'\bBOULEVARD\b': 'BLVD', r'\bAVENUE\b': 'AVE',
        r'\bSTREET\b': 'ST', r'\bROAD\b': 'RD',
        r'\bDRIVE\b': 'DR', r'\bLANE\b': 'LN',
        r'\bCOURT\b': 'CT', r'\bPLACE\b': 'PL',
        r'\bCIRCLE\b': 'CIR', r'\bPARKWAY\b': 'PKWY',
    }

    for pattern, replacement in replacements.items():
        address = re.sub(pattern, replacement, address)

    return address
```

**Rollout Strategy:**
1. Apply to NEW data first (12.24+)
2. Generate comparison report: normalized vs original
3. If <0.5% unexpected changes, backfill historical data
4. Update FULL_ADDRESS in all Reformat files

**Validation:**
- [ ] 119 currently affected records now match correctly
- [ ] No false positives (different locations incorrectly merged)

### 2.2 Provider Name Normalization
**Objective:** Standardize "THE" prefix/suffix and common variations

```python
def normalize_provider_name(name: str) -> str:
    """Standardize provider names for consistent grouping."""
    if not name:
        return name

    name = name.upper().strip()

    # Remove leading "THE "
    name = re.sub(r'^THE\s+', '', name)

    # Remove trailing ", THE" or " THE"
    name = re.sub(r',?\s*THE$', '', name)

    # Standardize punctuation
    name = re.sub(r'\s+', ' ', name)  # Multiple spaces → single
    name = re.sub(r'\s*,\s*', ', ', name)  # Normalize comma spacing

    return name.strip()
```

**Conservative Approach:**
- Store BOTH original and normalized names
- Use normalized for grouping/matching
- Display original in outputs
- Add `PROVIDER_NORMALIZED` column

---

## Phase 3: M.YY_COUNT Logic Clarification (Decision Required)

### Decision Point: Binary vs Count

**Current Implementation:** Returns total provider locations (0-42)
**v300 Specification:** Binary presence indicator (0 or 1)

| Option | Description | Impact |
|--------|-------------|--------|
| **A: Update documentation** | Change v300Track_this.md to match actual behavior | Minimal code change |
| **B: Fix code to match spec** | Modify analysis.py to return binary 0/1 | Breaking change, historical reprocessing |
| **C: Add both columns** | Keep current + add binary presence column | Most flexible, more columns |

**Recommendation:** Option C (Add Both)
- Add `M.YY_PRESENT` columns (binary 0/1) alongside existing `M.YY_COUNT`
- Provides location-level tracking (spec intent) AND enterprise-level visibility (current behavior)
- Non-breaking change

### Implementation (if Option C chosen)

```python
# In analysis.py, for each month:
df[f'{month}_COUNT'] = ...  # Keep existing (total locations)
df[f'{month}_PRESENT'] = df[f'{month}_COUNT'].apply(lambda x: 1 if x > 0 else 0)
```

**Column growth:** 40 additional columns (one per month)
**Alternative:** Single `MONTHS_PRESENT` column with comma-separated list of months

---

## Phase 4: Deduplication Strategy (High-Risk, Careful Execution)

### 4.1 Identify True Duplicates (No Code Change)
**Manual Review Required**

| Provider | Address | Action | Rationale |
|----------|---------|--------|-----------|
| ST MICHAELS ASSOCIATION... | 1 MILE NORTH OF HWY 264... | Keep 1, remove 2 | Source data error |
| MAYO CLINIC HOSPITAL | 5777 EAST MAYO BOULEVARD | Keep record with CAPACITY | Data completeness |
| D.V.U.S.D.#97 - NORTERRA CANYON | 2200 WEST MAYA WAY | Keep higher capacity (59) | Likely updated value |

### 4.2 Automated Duplicate Detection (Future)
**Add to pipeline - flag but don't auto-remove**

```python
def flag_potential_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Add DUPLICATE_FLAG column for manual review."""
    # Group by composite key
    key_counts = df.groupby(['PROVIDER', 'PROVIDER_TYPE', 'FULL_ADDRESS']).size()
    duplicates = key_counts[key_counts > 1].index

    df['DUPLICATE_FLAG'] = df.apply(
        lambda row: 'REVIEW' if (row['PROVIDER'], row['PROVIDER_TYPE'], row['FULL_ADDRESS']) in duplicates else '',
        axis=1
    )
    return df
```

---

## Phase 5: Validation & Testing Framework

### 5.1 Automated Validation Suite
**Create `tests/test_analysis_quality.py`**

```python
def test_no_true_duplicates():
    """Composite key should be unique."""
    df = load_analysis()
    key = df.groupby(['PROVIDER', 'PROVIDER_TYPE', 'FULL_ADDRESS']).size()
    duplicates = key[key > 1]
    assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate keys"

def test_address_normalization():
    """No WEST/W variations should exist."""
    df = load_analysis()
    west_full = df[df['FULL_ADDRESS'].str.contains(r'\bWEST\b', na=False)]
    w_abbrev = df[df['FULL_ADDRESS'].str.contains(r'\bW\b', na=False)]
    # Check for overlapping addresses (same location, different format)
    # ... validation logic

def test_group_count_accuracy():
    """PROVIDER_GROUP,_ADDRESS_COUNT should match actual group size."""
    df = load_analysis()
    for group_id in df['PROVIDER_GROUP_INDEX_#'].unique():
        group_df = df[df['PROVIDER_GROUP_INDEX_#'] == group_id]
        reported_count = group_df['PROVIDER_GROUP,_ADDRESS_COUNT'].iloc[0]
        actual_count = len(group_df)
        assert reported_count == actual_count, f"Group {group_id}: {reported_count} != {actual_count}"
```

### 5.2 Monthly Health Check Report
**Add to pipeline output**

| Check | Status | Details |
|-------|--------|---------|
| Composite key uniqueness | PASS/FAIL | X duplicates found |
| Address normalization | PASS/FAIL | X unnormalized addresses |
| Provider name normalization | PASS/FAIL | X "THE" variations |
| GROUP_INDEX accuracy | PASS/FAIL | X groups miscounted |
| M.YY_COUNT logic | PASS/FAIL | X unexpected values |

---

## Implementation Timeline (Conservative)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION TIMELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 0: Expanded Validation                                               │
│  ├── 0.1 Process all historical months                                      │
│  ├── 0.2 Validate edge case percentages                                     │
│  └── 0.3 Capture baseline metrics                                           │
│                                                                             │
│  PHASE 1: Critical Bug Fixes                                                │
│  ├── 1.1 Fix ADDRESS_COUNT bug                                              │
│  ├── 1.2 Document DBA_Concat design decision                                │
│  └── 1.3 Fix SOLO marker logic                                              │
│                                                                             │
│  PHASE 2: Normalization Layer                                               │
│  ├── 2.1 Implement address normalization                                    │
│  ├── 2.2 Implement provider name normalization                              │
│  └── 2.3 Backfill historical data (if validated)                            │
│                                                                             │
│  PHASE 3: M.YY_COUNT Clarification                                          │
│  ├── 3.1 Make decision (doc update vs code fix vs add columns)              │
│  └── 3.2 Implement chosen approach                                          │
│                                                                             │
│  PHASE 4: Deduplication                                                     │
│  ├── 4.1 Manual review of 23 true duplicates                                │
│  └── 4.2 Add automated duplicate flagging                                   │
│                                                                             │
│  PHASE 5: Validation Framework                                              │
│  ├── 5.1 Create automated test suite                                        │
│  └── 5.2 Add monthly health check report                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Risk Mitigation

### Rollback Strategy
- **Before each phase:** Create backup of current Analysis files
- **Version control:** Tag git commits at each phase completion
- **Parallel runs:** Generate both old and new outputs during transition

### Conservative Principles
1. **Validate before changing** - Run expanded analysis on full history first
2. **Flag, don't delete** - Add DUPLICATE_FLAG rather than auto-removing
3. **Preserve originals** - Store both original and normalized values
4. **Incremental rollout** - Apply to new data first, backfill only after validation
5. **Automated testing** - No deployment without passing test suite

---

## Success Metrics (Post-Implementation)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Alignment Score | 6.5/10 | 8.5+/10 | Re-run scoring rubric |
| True Duplicates | 23 | 0 | Automated test |
| Address Variations | 119 records | 0 | Automated test |
| Provider Name Variations | 356 records | <50 | Automated test |
| GROUP_INDEX Accuracy | 96.4% | 99%+ | Automated test |
| Month-to-Month Tracking | 99.1% | 99.5%+ | Status transition validation |

---

## Open Questions for Stakeholder Input

1. **M.YY_COUNT Logic:** Binary (0/1) per spec, or keep current counts (0-42)? Or both?
2. **DBA_Concat Design:** Include self in list or exclude?
3. **Normalization Aggressiveness:** Normalize in-place or preserve originals?
4. **Historical Backfill:** Reprocess all months with new logic, or apply forward-only?
5. **Duplicate Resolution:** Who decides which record to keep when true duplicates found?

---

*Document Version: 2.1*
*Analysis Date: 2025-12-02*
*v300Track Compliance Review Complete*
*Implementation Plan Added: 2025-12-04*
