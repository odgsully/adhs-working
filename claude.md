# Claude‑Code operating rules for **adhs‑etl**

1. **Branch hygiene** — No direct commits to `main`; open a PR, request review.  
2. **Config & secrets** — Always access through `from adhs_etl.config import Settings`.  
   *Never* import `os.environ` directly inside business logic.  
3. **CLI entry point** — Use the Poetry script alias:  
   ```bash
   poetry run adhs-etl run --month 1.25 --raw-dir ./Raw-New-Month --dry-run
   ```  
   * `--dry-run` must be honoured in all write operations.*  
   * Month format is `M.YY` or `MM.YY` (e.g., `1.25` for January 2025)  
4. **Unknown columns workflow** — The first time an unseen header appears, add it (with null mapping) to `field_map.TODO.yml`, log a `WARNING`, and keep the run going.  
5. **Testing & lint** — `pytest -q` + `pytest-cov` for coverage; `ruff` & `black` via `pre‑commit`.  
   * Keep tests in `src/tests/`; aim for ≥ 80 % coverage.
6. **Commit messages** — Conventional Commits (`feat:`, `fix:`, `chore:` …).  
7. **File naming** — Python in `snake_case.py`, Markdown in `kebab-case.md`.  
8. **Large artefacts** — Place any file > 5 MB in `/data`, git‑ignored; DVC if history needed.  
9. **Folder structure** — Updated to use hyphens:
   * `Raw-New-Month/` — Input files for current month processing
   * `ALL-MONTHS/` — Historical data organized by month folders
   * `Reformat/` — M.YY Reformat.xlsx output files
   * `All-to-Date/` — Reformat All to Date M.YY.xlsx cumulative files
   * `Analysis/` — M.YY Analysis.xlsx files with full business analysis
10. **Output Files** — Pipeline generates three types:
    * **Reformat**: Standardized data with MONTH, YEAR, PROVIDER TYPE, PROVIDER, ADDRESS, CITY, ZIP, CAPACITY, LONGITUDE, LATITUDE, PROVIDER GROUP INDEX #
    * **All-to-Date**: Cumulative data across all months processed
    * **Analysis**: Full business analysis with 3 sheets (Summary, Blanks Count, Analysis) including lost license detection and MCAO property data
