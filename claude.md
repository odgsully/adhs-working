# Claude‑Code operating rules for **adhs‑etl**

1. **Branch hygiene** — No direct commits to `main`; open a PR, request review.
2. **Config & secrets** — Always access through `from adhs_etl.config import Settings`.
   *Never* import `os.environ` directly inside business logic.
3. **Primary entry point** — Interactive month processor for batch processing:
   ```bash
   poetry run python scripts/process_months_local.py
   ```
   * Provides interactive menu for selecting month ranges
   * Processes from `ALL-MONTHS/Raw M.YY/` directories
   * Generates outputs in `Reformat/`, `All-to-Date/`, and `Analysis/`
4. **Alternative CLI** — For single months or automation:
   ```bash
   poetry run adhs-etl run --month 1.25 --raw-dir ./ALL-MONTHS/Raw\ 1.25 --dry-run
   ```
   * `--dry-run` must be honoured in all write operations
   * Month format is `M.YY` or `MM.YY` (e.g., `1.25` for January 2025)
5. **Unknown columns workflow** — The first time an unseen header appears, add it (with null mapping) to `field_map.TODO.yml`, log a `WARNING`, and keep the run going.
6. **Testing & lint** — `pytest -q` + `pytest-cov` for coverage; `ruff` & `black` via `pre‑commit`.  
   * Keep tests in `src/tests/`; aim for ≥ 80 % coverage.
7. **Commit messages** — Conventional Commits (`feat:`, `fix:`, `chore:` …).  
8. **File naming** — Python in `snake_case.py`, Markdown in `kebab-case.md`.  
9. **Large artefacts** — Place any file > 5 MB in `/data`, git‑ignored; DVC if history needed.  
10. **Folder structure** — Updated to use hyphens:
   * `Raw-New-Month/` — Input files for current month processing
   * `ALL-MONTHS/` — Historical data organized by month folders
   * `Reformat/` — `M.YY_Reformat_{timestamp}.xlsx` output files
   * `All-to-Date/` — `M.YY_Reformat_All_to_Date_{timestamp}.xlsx` cumulative files
   * `Analysis/` — `M.YY_Analysis_{timestamp}.xlsx` files with full business analysis
   * `APN/Upload/` — `M.YY_APN_Upload_{timestamp}.xlsx` MARICOPA-only extracts for parcel lookup
   * `APN/Complete/` — `M.YY_APN_Complete_{timestamp}.xlsx` enriched with Assessor Parcel Numbers
   * `MCAO/Upload/` — `M.YY_MCAO_Upload_{timestamp}.xlsx` filtered APNs for property data enrichment
   * `MCAO/Complete/` — `M.YY_MCAO_Complete_{timestamp}.xlsx` full property data (84 columns) from Maricopa County Assessor
   * `Ecorp/Upload/` — `M.YY_Ecorp_Upload_{timestamp}.xlsx` files for ACC entity lookup
   * `Ecorp/Complete/` — `M.YY_Ecorp_Complete_{timestamp}.xlsx` with full entity data
   * `Batchdata/Upload/` — `M.YY_BatchData_Upload_{timestamp}.xlsx` prepared for contact discovery APIs
   * `Batchdata/Complete/` — `M.YY_BatchData_Complete_{timestamp}.xlsx` enriched with phone/email data
11. **Output Files** — Pipeline generates multiple types with standardized naming `M.YY_{Stage}_{timestamp}.xlsx`:
    * **Naming format**: `{timestamp}` is `MM.DD.HH-MM-SS` (12-hour, no AM/PM). Example: `1.25_Reformat_01.15.03-45-30.xlsx`
    * **Reformat**: Standardized data with MONTH, YEAR, PROVIDER_TYPE, PROVIDER, ADDRESS, CITY, ZIP, FULL_ADDRESS, CAPACITY, LONGITUDE, LATITUDE, COUNTY, PROVIDER_GROUP_INDEX_#
    * **All-to-Date**: Cumulative data across all months processed
    * **Analysis**: Full business analysis with 3 sheets (Summary, Blanks Count, Analysis) including lost license detection, MCAO property data, and extended tracking per v300Track_this.md
    * **APN Processing** (optional): For MARICOPA records, generates Upload and Complete files with Assessor Parcel Numbers
    * **MCAO Processing** (optional): Enriches APN data with 84 property fields from Maricopa County Assessor API
    * **Ecorp Upload**: 4 columns (FULL_ADDRESS, COUNTY, Owner_Ownership, OWNER_TYPE) extracted from MCAO_Complete
    * **Ecorp Complete**: 93 columns (4 Upload + 89 entity fields) - Generated via `src/adhs_etl/ecorp.py`
      - ECORP_INDEX_# — Sequential record number (1, 2, 3...)
      - ECORP_URL — ACC entity detail page URL from ecorp.azcc.gov
      - Full entity details, principals, statutory agents, and registration data
    * **BatchData Enrichment** (optional, 5th stage): Contact discovery via `src/adhs_etl/batchdata_bridge.py` for skip-trace, phone/email enrichment, and DNC/TCPA compliance
    * **Backward compatibility**: During transition, both new format (underscores + timestamp) and legacy format (spaces, no timestamp) are created
