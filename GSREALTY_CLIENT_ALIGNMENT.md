# gsrealty-client Alignment Assessment

## Overview

This document assesses the alignment between **adhs-working** (Python ETL pipeline) and **gsrealty-client** (Next.js web application) for potential integration.

## Codebase Comparison

| Factor | adhs-working | gsrealty-client |
|--------|-------------|-----------------|
| Runtime | Python 3.11 | Node.js/Next.js |
| Package Mgr | Poetry | npm/Turborepo |
| Interface | CLI/scripts | Web UI |
| Data | Excel/batch processing | Supabase/real-time |
| MCAO/APN | Yes - batch | Yes - web-based |

## Common Ground

- Both handle Maricopa County property data
- Both integrate with MCAO (Maricopa County Assessor's Office)
- Both perform APN (Assessor Parcel Number) lookups
- Same domain expertise (Arizona real estate data)

## Barriers to Direct Integration

- Completely different tech stacks
- Python scripts cannot "plug in" as a React page natively
- Would need to either:
  - Call Python as subprocess from API routes
  - Expose Python as separate microservice
  - Port logic to TypeScript

## Alignment Score: 5/10

Strong domain overlap and complementary functionality, but the tech stack mismatch means it cannot simply "plug in" as a menu page. Integration requires architectural decisions.

---

## Integration Options (Ranked by Pragmatism)

### Option 1: Shared Supabase Database (Easiest)

Both codebases already interact with Supabase. Have adhs-working write its ETL outputs directly to Supabase tables instead of (or in addition to) Excel files. gsrealty-client then reads from those tables and displays the data in a new menu page.

**Pros:**
- No code porting required
- Just add a Supabase output stage to the Python pipeline
- Minimal changes to either codebase

**Cons:**
- One-way data flow (Python writes, Next.js reads)
- Cannot trigger ETL from web UI

### Option 2: Python Microservice (Most Flexible)

Wrap adhs-working in a lightweight FastAPI server. gsrealty-client's API routes call the Python service endpoints.

```
gsrealty-client (Next.js) → /api/etl/run → FastAPI → adhs-working pipeline
```

**Pros:**
- Keeps Python logic intact
- Trigger ETL jobs from web UI
- Clean separation of concerns

**Cons:**
- Separate deployment/process to manage
- Network latency between services

### Option 3: Subprocess Calls (Quick & Dirty)

From Next.js API routes, spawn Python scripts directly via `child_process`.

**Pros:**
- Single deployment
- Direct access to Python scripts

**Cons:**
- Messy coupling of deployments
- Must manage Python on Node server
- Error handling is complex

### Option 4: Background Job Queue (Best for Heavy ETL)

Use Redis + Bull (Node) or Celery (Python) to queue long-running ETL jobs. The web UI submits jobs, Python workers process them, results land in Supabase.

**Pros:**
- Best for jobs that take minutes/hours
- Proper async handling
- Scalable

**Cons:**
- Most complex to set up
- Additional infrastructure (Redis)

---

## Recommendation

**Start with Option 1** (shared Supabase):
1. Add tables for ADHS provider data to Supabase
2. Modify the Python pipeline to write ETL outputs there
3. Build a read-only page in gsrealty-client to display the data

**Later, add Option 2** (FastAPI wrapper) if you need to trigger ETL from the UI.

This approach gets integration working fast without major refactoring to either codebase.

---

## gsrealty-client Location

```
/Users/garrettsullivan/Desktop/AUTOMATE/Vibe Code/Wabbit/clients/sullivan_realestate/Actual/apps/gsrealty-client/
```

## Related Files

- gsrealty-client MCAO lookup: `apps/gsrealty-client/scripts/apn_lookup.py`
- adhs-working MCAO integration: `scripts/test_mcao_*.py`
- adhs-working APN lookup: `APN/apn_lookup.py`
