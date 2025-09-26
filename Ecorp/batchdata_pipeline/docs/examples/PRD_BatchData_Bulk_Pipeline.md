# PRD — BatchData Bulk Skip-Trace Pipeline (Local Run)
**Date:** 2025-08-18

## Objective
Build a deterministic local script that ingests one workbook (`template_batchdata_upload.xlsx`), generates BatchData async jobs to return **phones/emails**, and optionally scrubs phones via **verification, DNC, TCPA**. Outputs are merged back to a single results table keyed by `record_id`.

## Scope
- Inputs: `INPUT_MASTER` sheet (one row per person+address or address-only).
- Optional upstream helpers: `address-verify`, `property-search-async`, `property-lookup-async`.
- Core: `property-skip-trace-async`.
- Optional downstream scrubs: `phone-verification-async`, `phone-dnc-async`, `phone-tcpa-async`.

## Non-Goals
- No web scraping. No synchronous endpoints needed.
- No persistence beyond local CSV/Parquet + Excel output.

## Configuration
Read `CONFIG` sheet (key-value). Environment variables for API tokens:
- `BD_SKIPTRACE_KEY`, `BD_ADDRESS_KEY`, `BD_PROPERTY_KEY`, `BD_PHONE_KEY`.

## Input Contract (INPUT_MASTER)
Columns (minimum subset bold):  
**record_id**, source_type, source_entity_name, source_entity_id, title_role, target_first_name, target_last_name, owner_name_full, **address_line1**, address_line2, **city**, **state**, **zip**, county, apn, mailing_line1, mailing_city, mailing_state, mailing_zip, notes.

Rules:
- Explode upstream corporate filings so each person/address is its own row.
- Drop rows where `owner_name_full` matches entries in `BLACKLIST_NAMES`.
- If both name and address exist, pass both to skip-trace. Otherwise address-only is allowed.

## Outputs
- `results/skiptrace/skiptrace_complete_{timestamp}.xlsx` (processed skip-trace results)
- `results/phone_scrub/phones_scrubbed_{timestamp}.xlsx` (after verification/DNC/TCPA)
- `results/final_contacts_{timestamp}.xlsx` (joined, wide format; one row per `record_id` with up to 10 phones flattened)

**Note**: Raw API inputs/outputs may use CSV format as required by BatchData APIs, but processed results use XLSX.

## Endpoints
- Skip Trace (async): Property → `property-skip-trace-async`
- Address Verify (opt): Address → `address-verify`
- Property Search (opt): Property → `property-search-async`
- Property Lookup (opt): Property → `property-lookup-async`
- Phone Verification (opt): Phone → `phone-verification-async`
- Phone DNC (opt): Phone → `phone-dnc-async`
- Phone TCPA (opt): Phone → `phone-tcpa-async`

## Processing Flow
1. Load Excel → read `CONFIG`, `INPUT_MASTER`, `BLACKLIST_NAMES`.
2. Normalize names (split first/last, drop suffixes), standardize state (2-letter).
3. (If enabled) Address-verify → update address fields on working dataframe.
4. (If enabled) Property search/lookup — when APN/owner_name is present or address is partial; fill owner/mailing fields.
5. Build skip-trace payloads (CSV batches of `batch.size`), call async; poll using `batch.poll_seconds` until complete.
6. Parse results → explode phones to long form: columns `record_id, phone, type, confidence, carrier`.
7. (If enabled) Run phone verification/DNC/TCPA async in sequence, merging flags onto the phone table.
8. Keep phones where `is_active==true` AND `line_type=='mobile'` AND not on DNC AND not litigators.
9. Aggregate back to one row per `record_id` with up to 10 ranked phones → write final Excel.

## Error Handling & Retries
- Network: exponential backoff (0.5, 1, 2, 4… up to 5 tries).
- API 4xx: log and skip row; mark `error_message`.
- Job timeouts: cancel and re-queue file once; after two failures, write to `results/_failed_jobs.csv`.

## Rate/Spend Guardrails
- Batch sizes capped by `batch.size`.
- Estimate spend: 7¢ × rows + optional scrubs (0.7¢ + 0.2¢ + 0.2¢ per phone).
- Write a preview `COST_ESTIMATE.md` before first submit.

## Acceptance Criteria
- Given a mixed workbook, pipeline produces a `final_contacts_*.xlsx` with ≥98% row preservation and correct joins by `record_id`.
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
