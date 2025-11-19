You are acting as an engineer to implement a local BatchData bulk pipeline, we want a new output from the information from ecorp complete.xlsx to match the template of template_batchdata_upload.xlsx INPUT_MASTER sheet for all records to perform the API calls. READ documents to reference are available in /Users/garrettsullivan/Desktop/agent_ecorp/batchdata_local_pack.

DELIVERABLES
1) Python package under /pipeline with modules:
   - src/io.py (Excel <-> DataFrame, CSV writers, timestamped paths)
   - src/normalize.py (name split, RA blacklist filter, state normalization)
   - src/batchdata.py (HTTP client; async upload, polling, download; endpoints: address-verify, property-search-async, property-lookup-async, property-skip-trace-async, phone-verification-async, phone-dnc-async, phone-tcpa-async)
   - src/transform.py (explode phones to long; apply scrubs; aggregate top-10 phones by confidence)
   - src/run.py (CLI: python -m src.run --input batchdata_local_input.xlsx)
2) Read / write exactly the columns defined in the Excel template’s INPUT_MASTER and EXPECTED_FIELDS.
3) Environment variables (in project root .env file): BD_SKIPTRACE_KEY, BD_ADDRESS_KEY, BD_PROPERTY_KEY, BD_PHONE_KEY.
4) Write outputs under /results as described in the PRD.

IMPLEMENTATION NOTES
- Use requests for HTTP, pandas for ETL, python-dotenv to load .env.
- CSV uploads: use multipart/form-data; generate temp CSVs for batches of size from CONFIG['batch.size'].
- Poll GET /jobs/{id} until status==completed; then GET /jobs/{id}/download to fetch results.
- Robust join key is `record_id`. Preserve row order via a stable index.
- Scrubs: retain only phones with (is_active==True AND line_type=='mobile') and not on DNC and not litigators.
- Normalize phone output to E.164 (+1XXXXXXXXXX). Deduplicate by (record_id, phone).

ACCEPTANCE TEST
- Create a small test Excel (3 rows) and run full pipeline with all toggles TRUE using mocked responses. Verify output shapes and columns.
- Provide a dry-run mode that prints estimated cost before submitting.

DO NOT:
- Hardcode API keys.
- Use synchronous endpoints.
- Change column names.
