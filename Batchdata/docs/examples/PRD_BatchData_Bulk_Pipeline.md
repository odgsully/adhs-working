# PRD — BatchData Bulk Skip-Trace Pipeline (Local Run)
**Date:** 2025-08-18

## Objective
Build a deterministic local script that ingests one workbook (`template_batchdata_upload.xlsx`), generates BatchData async jobs to return **phones/emails**, and optionally scrubs phones via **verification, DNC, TCPA**. Outputs are merged back to a single results table keyed by `BD_RECORD_ID`.

## Scope
- Inputs: `INPUT_MASTER` sheet (one row per person+address or address-only).
- Optional upstream helpers: `/api/v1/address/verify`, `/api/v1/property/search/async`, `/api/v1/property/lookup/async`.
- Core: `/api/v1/property/skip-trace/async`.
- Optional downstream scrubs: `/api/v1/phone/verification/async`, `/api/v1/phone/dnc/async`, `/api/v1/phone/tcpa/async`.

## Non-Goals
- No web scraping. No synchronous endpoints needed.
- No persistence beyond local CSV/Parquet + Excel output.

## Configuration
Read `CONFIG` sheet (key-value). Environment variables for API tokens (in project root `.env` file):
- `BD_SKIPTRACE_KEY`, `BD_ADDRESS_KEY`, `BD_PROPERTY_KEY`, `BD_PHONE_KEY`.

## Input Contract (INPUT_MASTER) - 16 columns
Columns (minimum subset bold):
**BD_RECORD_ID**, BD_SOURCE_TYPE, BD_ENTITY_NAME, BD_SOURCE_ENTITY_ID, BD_TITLE_ROLE, **BD_ADDRESS**, **BD_CITY**, **BD_STATE**, **BD_ZIP**, BD_COUNTY, BD_APN, BD_MAILING_LINE1, BD_MAILING_CITY, BD_MAILING_STATE, BD_MAILING_ZIP, BD_NOTES.

**REMOVED (Nov 2025)**: BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL, BD_ADDRESS_2

Rules:
- Explode upstream corporate filings so each person/address is its own row.
- Filter using `BLACKLIST_NAMES` sheet for registered agent filtering.
- API uses address-only for skip-trace lookups; names returned in API response.

## Outputs
- `results/skiptrace/skiptrace_complete_{timestamp}.xlsx` (processed skip-trace results)
- `results/phone_scrub/phones_scrubbed_{timestamp}.xlsx` (after verification/DNC/TCPA)
- `results/final_contacts_{timestamp}.xlsx` (joined, wide format; one row per `BD_RECORD_ID` with up to 10 phones flattened)

**Note**: Raw API inputs/outputs may use CSV format as required by BatchData APIs, but processed results use XLSX.

## Endpoints (V1 API)
- Skip Trace (async): `POST /api/v1/property/skip-trace/async`
- Address Verify (opt): `POST /api/v1/address/verify`
- Property Search (opt): `POST /api/v1/property/search/async`
- Property Lookup (opt): `POST /api/v1/property/lookup/async`
- Phone Verification (opt): `POST /api/v1/phone/verification/async`
- Phone DNC (opt): `POST /api/v1/phone/dnc/async`
- Phone TCPA (opt): `POST /api/v1/phone/tcpa/async`

## Processing Flow
1. Load Excel → read `CONFIG`, `INPUT_MASTER`, `BLACKLIST_NAMES`.
2. Normalize names (split first/last, drop suffixes), standardize state (2-letter).
3. (If enabled) Address-verify → update address fields on working dataframe.
4. (If enabled) Property search/lookup — when APN/owner_name is present or address is partial; fill owner/mailing fields.
5. Build skip-trace payloads (CSV batches of `batch.size`), call async; poll using `batch.poll_seconds` until complete.
6. Parse results → explode phones to long form: columns `BD_RECORD_ID, phone, type, confidence, carrier`.
7. (If enabled) Run phone verification/DNC/TCPA async in sequence, merging flags onto the phone table.
8. Keep phones where `is_active==true` AND `line_type=='mobile'` AND not on DNC AND not litigators.
9. Aggregate back to one row per `BD_RECORD_ID` with up to 10 ranked phones → write final Excel.

## Error Handling & Retries
- Network: exponential backoff (0.5, 1, 2, 4… up to 5 tries).
- API 4xx: log and skip row; mark `error_message`.
- Job timeouts: cancel and re-queue file once; after two failures, write to `results/_failed_jobs.csv`.

## Rate/Spend Guardrails
- Batch sizes capped by `batch.size`.
- Estimate spend: 7¢ × rows + optional scrubs (0.7¢ + 0.2¢ + 0.2¢ per phone).
- Write a preview `COST_ESTIMATE.md` before first submit.

## Acceptance Criteria
- Given a mixed workbook, pipeline produces a `final_contacts_*.xlsx` with ≥98% row preservation and correct joins by `BD_RECORD_ID`.
- Phone table contains only **unique** E.164 mobiles post-scrub.
- All intermediate artifacts and logs saved under `results/` with timestamps.

## Folder Structure (suggested)
```
/pipeline
  /src
    io.py            # Excel/CSV read-write
    normalize.py     # name/address normalization
    batchdata.py     # client for async endpoints + polling
    transform.py     # explode/aggregate phones
    run.py           # CLI entrypoint
  /results
  batchdata_local_input.xlsx
  .env.example
```
