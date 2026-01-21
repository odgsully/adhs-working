# Ecorp Step Necessity Analysis

**Date:** 2026-01-12
**Context:** Evaluating whether Ecorp step is necessary given BatchData Complete gets all names/numbers for a Property Address

---

## Necessity Rating: 5/10

---

## Why NOT Higher (What BatchData Covers)

- BatchData performs **address-based skip-trace** - finds ALL persons associated with a property address
- Returns up to 10 phone numbers + 10 emails per address regardless of Ecorp
- BatchData doesn't need names upfront - just the address from MCAO_Complete
- Cost-effective for volume contact discovery

---

## Why NOT Lower (What Ecorp Uniquely Provides)

| Ecorp Value | Importance |
|-------------|------------|
| **Principal identification** | Know WHO you're calling (Manager vs Member vs Agent) |
| **Name matching** | `ECORP_TO_BATCH_MATCH_%` confirms BatchData found the *right* people |
| **Entity verification** | Active/Inactive status from official ACC source |
| **Statutory Agent** | Legal contact point for service of process |
| **Corporate family grouping** | Groups entities by shared management (85%+ principal overlap) |

---

## The Core Trade-off

| With Ecorp | Without Ecorp |
|------------|---------------|
| You know you're calling the LLC Manager at 602-555-1234 | You're calling *someone* at that address at 602-555-1234 |
| Role context (Manager, Member, Statutory Agent) | No role information |
| Entity status verified (Active/Inactive) | Unknown business status |
| Name matching confirms correct contacts | No verification of who BatchData found |

---

## Situational Rating Adjustments

### When Ecorp Drops to 3/10
- You just need *any* contact at a property
- Volume over precision
- Old Ecorp site is offline anyway (needs migration to new AZ Business Connect)
- Speed/cost is priority over accuracy

### When Ecorp Rises to 8/10
- You need verified decision-makers
- Legal compliance matters (service of process)
- You're filtering by entity status (inactive = skip)
- Corporate family analysis is important
- Calling context matters ("Hi, are you the manager of XYZ LLC?")

---

## Pipeline Flow Reference

```
MCAO_Complete (84 cols)
    ↓
[OPTIONAL] Ecorp_Upload → Ecorp_Complete (93 cols)
    ↓
BatchData_Upload (16-33 cols depending on Ecorp)
    ↓
BatchData_Complete (169 cols with contact data)
```

**With Ecorp:** BatchData gets 17 Ecorp passthrough columns + principal names for matching
**Without Ecorp:** BatchData gets address only from MCAO, no name matching possible

---

## Bottom Line

If your use case is **"dial for dollars at licensed facility addresses"** → Skip Ecorp

If your use case is **"reach verified business owners with role context"** → Keep Ecorp

---

## Current Status Note

As of January 2026, the old `ecorp.azcc.gov` site is offline (301 redirect). The new Arizona Business Connect platform is live but the scraper needs URL and CSS selector updates to function. This technical debt affects the practical availability of Ecorp data regardless of its theoretical value.
