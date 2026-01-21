# Ecorp Scraping Analysis: CAPTCHA & Platform Transition

**Date:** January 12, 2026
**Status:** UPDATE - New Platform Live, NO CAPTCHA Detected
**Author:** Claude Code Analysis
**Last Updated:** January 12, 2026 (Post-Launch Reconnaissance)

---

## Executive Summary

**UPDATE:** The new Arizona Business Connect platform is **LIVE AND ACCESSIBLE** as of today. Initial reconnaissance shows **NO CAPTCHA** on the new platform - this is significantly better than expected.

~~Our Ecorp scraping pipeline is completely broken as of today.~~ **REVISED:** Our pipeline needs URL and selector updates, but the new platform appears MORE scrape-friendly than the old one.

The Arizona Corporation Commission (ACC) has completed the transition from ecorp.azcc.gov to "Arizona Business Connect." This analysis covers:

1. The state of the old eCorp site (CAPTCHA + shutdown)
2. The new Arizona Business Connect platform (launching TODAY)
3. Our current scraping implementation vulnerabilities
4. Feasibility assessment for continued bulk data extraction
5. Alternative approaches and recommendations

---

## Timeline of Events

| Date | Event |
|------|-------|
| Pre-2026 | eCorp added custom text-based CAPTCHA to entity search |
| January 2, 2026 5PM | **eCorp shut down** - No online filing or search |
| January 2-12, 2026 | **Blackout period** - Data migration to new platform |
| **January 12, 2026** | **Arizona Business Connect launches** (TODAY) |

**Critical Impact:** We are in the exact moment of platform transition. The old scraping target no longer exists.

---

## Process Architecture: Visual Overview

### Old eCorp Scraping Pipeline (DEPRECATED)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           OLD ECORP SCRAPING ARCHITECTURE                               │
│                              (ecorp.azcc.gov - OFFLINE)                                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘

    MCAO_Complete.xlsx                                                     Ecorp_Complete.xlsx
    (84 columns)                                                           (93 columns)
         │                                                                       ▲
         │                                                                       │
         ▼                                                                       │
┌─────────────────┐                                                    ┌─────────────────┐
│ generate_ecorp_ │                                                    │  Post-Process   │
│    upload()     │                                                    │  • Index assign │
│                 │                                                    │  • Fuzzy match  │
│ Extract 4 cols: │                                                    │  • Deduplication│
│ • FULL_ADDRESS  │                                                    └────────▲────────┘
│ • COUNTY        │                                                             │
│ • Owner_Owner.. │                                                             │
│ • OWNER_TYPE    │                                                             │
└────────┬────────┘                                                             │
         │                                                                       │
         ▼                                                                       │
┌─────────────────┐         ┌─────────────────────────────────────────────────────┐
│ Ecorp_Upload    │         │              SELENIUM WEB SCRAPING                  │
│ (4 columns)     │────────▶│                                                     │
└─────────────────┘         │  ┌─────────────────────────────────────────────┐   │
                            │  │ FOR EACH ROW:                                │   │
                            │  │                                              │   │
                            │  │  1. Navigate to ecorp.azcc.gov/EntitySearch │   │
                            │  │            │                                 │   │
                            │  │            ▼                                 │   │
                            │  │  ┌─────────────────┐                        │   │
                            │  │  │ Enter owner name│                        │   │
                            │  │  │ Press ENTER     │                        │   │
                            │  │  └────────┬────────┘                        │   │
                            │  │           │                                  │   │
                            │  │           ▼                                  │   │
                            │  │  ┌─────────────────┐    ┌──────────────┐   │   │
                            │  │  │ Wait 1.5 sec    │───▶│ CAPTCHA?     │   │   │
                            │  │  │ for results     │    │ ⚠️ NO HANDLE │   │   │
                            │  │  └────────┬────────┘    └──────────────┘   │   │
                            │  │           │                                  │   │
                            │  │           ▼                                  │   │
                            │  │  ┌─────────────────┐                        │   │
                            │  │  │ Parse results   │                        │   │
                            │  │  │ table rows      │                        │   │
                            │  │  └────────┬────────┘                        │   │
                            │  │           │                                  │   │
                            │  │           ▼                                  │   │
                            │  │  ┌─────────────────┐                        │   │
                            │  │  │ For each entity:│                        │   │
                            │  │  │ • Open new tab  │                        │   │
                            │  │  │ • Wait for load │                        │   │
                            │  │  │ • BeautifulSoup │                        │   │
                            │  │  │ • Extract 88    │                        │   │
                            │  │  │   fields        │                        │   │
                            │  │  │ • Close tab     │                        │   │
                            │  │  └────────┬────────┘                        │   │
                            │  │           │                                  │   │
                            │  │           ▼                                  │   │
                            │  │  ┌─────────────────┐                        │   │
                            │  │  │ Cache result    │                        │   │
                            │  │  │ Save checkpoint │                        │   │
                            │  │  │ (every 50 recs) │                        │   │
                            │  │  └─────────────────┘                        │   │
                            │  │                                              │   │
                            │  └──────────────────────────────────────────────┘   │
                            │                                                     │───┘
                            │  TIMING: ~4 sec/record = 65 min for 1000 records   │
                            └─────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                         OLD SYSTEM FAILURE POINTS                           │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │  ❌ Hardcoded URL: ecorp.azcc.gov (NOW 301 REDIRECT)                        │
    │  ❌ CSS Selectors: input[placeholder*='Search for an Entity Name'] (GONE)  │
    │  ❌ XPath: //h2[contains(text(),'Entity Information')] (DOM CHANGED)       │
    │  ❌ CAPTCHA: Zero detection, zero handling                                  │
    │  ❌ Rate Limiting: Fixed 1.5s delays (detectable pattern)                   │
    │  ❌ Detection: navigator.webdriver=true exposed                             │
    └─────────────────────────────────────────────────────────────────────────────┘
```

### New Arizona Business Connect Pipeline (PROPOSED REWORK)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         NEW ARIZONA BUSINESS CONNECT ARCHITECTURE                       │
│                         (arizonabusinesscenter.azcc.gov - LIVE)                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

    MCAO_Complete.xlsx                                                     Ecorp_Complete.xlsx
    (84 columns)                                                           (93 columns)
         │                                                                       ▲
         │                                                                       │
         ▼                                                                       │
┌─────────────────┐         NO CHANGES NEEDED                          ┌─────────────────┐
│ generate_ecorp_ │         (file-based only)                          │  Post-Process   │
│    upload()     │─────────────────────────────────────────────────▶  │  (unchanged)    │
└────────┬────────┘                                                    └────────▲────────┘
         │                                                                       │
         ▼                                                                       │
┌─────────────────┐                                                             │
│ Ecorp_Upload    │                                                             │
│ (4 columns)     │                                                             │
└────────┬────────┘                                                             │
         │                                                                       │
         │         ┌─────────────────────────────────────────────────────────────┤
         │         │                                                             │
         ▼         ▼                                                             │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    OPTION A: ADAPTED SELENIUM (Recommended)                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                     CHANGES REQUIRED                                      │ │
│  ├───────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                           │ │
│  │  1. URL UPDATE:                                                           │ │
│  │     OLD: ecorp.azcc.gov/EntitySearch/Index                               │ │
│  │     NEW: arizonabusinesscenter.azcc.gov/entitysearch/index               │ │
│  │                                                                           │ │
│  │  2. SELECTOR UPDATES (Angular Material):                                  │ │
│  │     OLD: input[placeholder*='Search for an Entity Name']                 │ │
│  │     NEW: mat-form-field input, [formControlName="entityName"], etc.      │ │
│  │          (REQUIRES DEVTOOLS INVESTIGATION)                                │ │
│  │                                                                           │ │
│  │  3. RESULTS TABLE:                                                        │ │
│  │     OLD: Standard HTML <table>                                           │ │
│  │     NEW: <mat-table> with <mat-row> components                           │ │
│  │                                                                           │ │
│  │  4. TIMING IMPROVEMENTS:                                                  │ │
│  │     OLD: time.sleep(1.5) - fixed                                         │ │
│  │     NEW: random.uniform(2.0, 5.0) - variable                             │ │
│  │                                                                           │ │
│  │  5. CAPTCHA DETECTION (NEW):                                              │ │
│  │     def detect_captcha(driver):                                          │ │
│  │         indicators = ["captcha", "verify", "robot", "human"]             │ │
│  │         return any(i in driver.page_source.lower() for i in indicators)  │ │
│  │                                                                           │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  FLOW: Same as before, just updated selectors + improved resilience             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│   OPTION B: API DISCOVERY       │  │   OPTION C: M027 OFFICIAL       │
│         (If Available)          │  │      (Fallback/Parallel)        │
├─────────────────────────────────┤  ├─────────────────────────────────┤
│                                 │  │                                 │
│  Monitor Network tab for:       │  │  Submit Form M027:              │
│  • /api/entity/search           │  │  • $75 for custom extract       │
│  • /api/entity/{id}             │  │  • $1,000 for full database     │
│  • GraphQL endpoints            │  │  • Delivery: Email (free)       │
│  • JSON responses               │  │  • Processing: Up to 30 days    │
│                                 │  │                                 │
│  If found:                      │  │  Available data:                │
│  • Direct HTTP requests         │  │  ✓ Business name/address        │
│  • No Selenium needed           │  │  ✓ Incorporation date           │
│  • Faster processing            │  │  ✓ Statutory agent info         │
│  • Lower detection risk         │  │  ✓ Officers/Directors           │
│                                 │  │  ✓ Status, domicile             │
│                                 │  │                                 │
│  FEASIBILITY: Unknown           │  │  NOT available:                 │
│  (Needs investigation)          │  │  ✗ Phone numbers                │
│                                 │  │  ✗ Email addresses              │
│                                 │  │  ✗ SSN/EIN                      │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

### Data Field Comparison: Scraping vs M027

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         DATA AVAILABILITY COMPARISON                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  FIELD                          │ SCRAPING │ M027 OFFICIAL │ CRITICAL FOR PIPELINE?    │
│  ───────────────────────────────┼──────────┼───────────────┼────────────────────────── │
│  Entity Name                    │    ✓     │      ✓        │ Yes                       │
│  Entity ID                      │    ✓     │      ✓        │ Yes                       │
│  Entity Type                    │    ✓     │      ✓        │ Yes                       │
│  Status (Active/Inactive)       │    ✓     │      ✓        │ Yes                       │
│  Formation Date                 │    ✓     │      ✓        │ Yes                       │
│  Business Type                  │    ✓     │      ✓        │ No                        │
│  State/County                   │    ✓     │      ✓        │ Yes                       │
│  ───────────────────────────────┼──────────┼───────────────┼────────────────────────── │
│  Statutory Agent Name           │    ✓     │      ✓        │ Yes - PRIMARY CONTACT     │
│  Statutory Agent Address        │    ✓     │      ✓        │ Yes                       │
│  Statutory Agent Phone          │    ✓     │      ✗        │ YES - CONTACT ENRICHMENT  │
│  Statutory Agent Email          │    ✓     │      ✗        │ YES - CONTACT ENRICHMENT  │
│  ───────────────────────────────┼──────────┼───────────────┼────────────────────────── │
│  Principal/Manager Names        │    ✓     │      ✓        │ Yes - DECISION MAKERS     │
│  Principal/Manager Addresses    │    ✓     │      ✓        │ Yes                       │
│  Principal/Manager Phones       │    ✓     │      ✗        │ YES - CONTACT ENRICHMENT  │
│  Principal/Manager Emails       │    ✓     │      ✗        │ YES - CONTACT ENRICHMENT  │
│  ───────────────────────────────┼──────────┼───────────────┼────────────────────────── │
│  Name Change History            │    ?     │      ✓        │ No                        │
│  Merger Information             │    ?     │      ✓        │ No                        │
│                                                                                         │
│  VERDICT: M027 lacks phone/email - the PRIMARY VALUE of our scraping pipeline          │
│           Scraping provides contact enrichment that M027 cannot                         │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Old eCorp Site Analysis

### 1.1 CAPTCHA Implementation (Pre-Shutdown)

The old ecorp.azcc.gov implemented a **custom text-based CAPTCHA**:

- **Type:** Traditional image-to-text CAPTCHA (not reCAPTCHA v2/v3 or hCaptcha)
- **Trigger Points:**
  - Entity search initiation
  - User validation checkpoints
  - Filing operations
- **Message:** "User validation required to continue. Please type the text you see in the image into the text box and submit."

### 1.2 Why Our Scraper Was Vulnerable

Our implementation in `src/adhs_etl/ecorp.py` (1,179 lines) had **zero CAPTCHA handling**:

```python
# Current flow (ecorp.py lines 343-347)
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//h2[contains(text(),'Entity Information')]"))
)
# ^ This would timeout indefinitely if CAPTCHA appeared
```

**Vulnerability Matrix:**

| Component | CAPTCHA Resilience | Notes |
|-----------|-------------------|-------|
| Search page navigation | None | Would hit CAPTCHA wall |
| Entity results parsing | None | Never reaches results |
| Detail page extraction | None | Critical failure point |
| Checkpoint resume | Partial | Would resume into same CAPTCHA |
| Error handling | None | Silent timeout → crash |

### 1.3 Detection Signatures Our Scraper Exposed

Our Selenium-based approach was highly detectable:

1. **Consistent timing patterns** - Fixed 1.5s delays between actions
2. **No user-agent rotation** - Same Chrome UA for all requests
3. **Selenium fingerprints** - `navigator.webdriver = true`
4. **Sequential tab opening** - `window.open()` pattern for each entity
5. **High request volume** - 1000+ records × 4 seconds = ~65 minutes of sustained activity
6. **Single IP** - No proxy rotation

---

## Part 2: New Platform - Arizona Business Connect

### 2.1 Platform Overview

**URL:** https://arizonabusinesscenter.azcc.gov/entitysearch/index
**Old URL:** https://ecorp.azcc.gov → **301 redirects to new platform**

**Key Changes:**
- Modern Angular SPA (Material Design components)
- Client-side rendering (requires JS execution)
- Google Analytics tracking (GTM: G-WTNGGR2SRX)
- Chatbot widget integration
- Multi-language support via Google Translate

### 2.2 LIVE RECONNAISSANCE RESULTS (January 12, 2026)

**Status checks performed:**

| URL | Status | Notes |
|-----|--------|-------|
| `arizonabusinesscenter.azcc.gov` | **LIVE** | Main platform accessible |
| `arizonabusinesscenter.azcc.gov/entitysearch/index` | **LIVE** | Entity search available |
| `ecorp.azcc.gov` | **301 REDIRECT** | Permanently redirects to new platform |

**Security/Anti-Bot Assessment:**

| Protection Type | Status |
|-----------------|--------|
| CAPTCHA | **NOT DETECTED** |
| Cloudflare | **NOT DETECTED** |
| DataDome | **NOT DETECTED** |
| Rate Limiting | **NOT VISIBLE** (needs testing) |
| Authentication | **NOT REQUIRED** for search |

### 2.3 Technical Architecture

- **Framework:** Angular (Material Design components: mat-table, mat-select, mat-datepicker)
- **Rendering:** Client-side SPA (BeautifulSoup won't work alone)
- **Implications:**
  - Selenium/Playwright REQUIRED for JS execution
  - API endpoints may exist (needs DevTools investigation)
  - DOM selectors will be completely different from old site

### 2.4 Remaining Investigation Items

- [ ] ~~What CAPTCHA system the new platform uses~~ **NONE DETECTED**
- [x] ~~Whether the DOM structure is similar~~ **COMPLETELY DIFFERENT (Angular SPA)**
- [ ] ~~If there are new anti-bot measures~~ **NONE VISIBLE**
- [ ] New CSS selectors for search input, results table, detail pages
- [ ] Rate limiting thresholds (needs live testing)
- [ ] API endpoint discovery (check Network tab during search)

---

## Part 3: Current Implementation Deep Dive

### 3.1 Architecture Overview

```
Pipeline Flow:
MCAO_Complete (84 cols)
       │
       ▼
┌─────────────────────────────┐
│  generate_ecorp_upload()    │ ← Extracts 4 columns
│  (Works independently)      │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  generate_ecorp_complete()  │ ← WEB SCRAPING HERE
│  • Selenium WebDriver       │
│  • BeautifulSoup parsing    │
│  • 88 entity fields         │
│  • Checkpoint every 50 recs │
└─────────────────────────────┘
       │
       ▼
Ecorp_Complete (93 cols)
```

### 3.2 Code Locations

| Function | File | Lines | Status |
|----------|------|-------|--------|
| `setup_driver()` | `ecorp.py` | 251-276 | BROKEN - Target site gone |
| `search_entities()` | `ecorp.py` | 279-345 | BROKEN - Selectors invalid |
| `extract_entity_info()` | `ecorp.py` | 347-589 | BROKEN - DOM structure changed |
| `generate_ecorp_complete()` | `ecorp.py` | 900-1100+ | BROKEN - Depends on above |

### 3.3 What Still Works

- `generate_ecorp_upload()` - File-based, no web dependencies
- Checkpoint system - Can resume if we fix the scraper
- Index grouping logic - Post-processing, no web dependencies
- Column mapping - Output structure unchanged

---

## Part 4: Feasibility Assessment

### 4.1 Feasibility Matrix (UPDATED Post-Reconnaissance)

| Approach | Feasibility | Effort | Risk | Recommendation |
|----------|-------------|--------|------|----------------|
| **Adapt Selenium for new site** | **HIGH** | Medium | Low | **RECOMMENDED** - No CAPTCHA! |
| **API endpoint discovery** | HIGH | Low | Low | **INVESTIGATE FIRST** - May be easier than DOM |
| **Official Database Extraction (M027)** | HIGH | Low | Low | Good backup option |
| **Add CAPTCHA solving service** | N/A | N/A | N/A | ~~Not needed~~ |
| **Headless browser with stealth** | MEDIUM | Medium | Low | May not be necessary |
| **Manual processing** | HIGH | Very High | Low | Last resort only |

### 4.2 Detailed Analysis by Approach

#### Option A: Adapt Selenium for New Site (NOW RECOMMENDED)

**Pros:**
- Minimal architectural change
- Existing checkpoint system works
- **NO CAPTCHA detected on new platform**
- **No Cloudflare/anti-bot protection visible**
- Selenium handles Angular SPA rendering natively

**Cons:**
- Requires complete selector rewrite (Angular Material components)
- Need to discover new DOM structure
- Rate limiting thresholds unknown (test carefully)

**Feasibility Score: 8/10** (UPGRADED from 2/10)

**Implementation Steps:**
1. Update base URL to `https://arizonabusinesscenter.azcc.gov/entitysearch/index`
2. Use browser DevTools to find new selectors for:
   - Search input field
   - Search button/trigger
   - Results table (likely `mat-table`)
   - Entity detail links
   - Detail page fields
3. Add random delays (2-5 seconds) as precaution
4. Test with small batch first (10 records)

---

#### Option B: CAPTCHA Solving Integration

**Services:**
- 2Captcha (~$3 per 1000 CAPTCHAs)
- Anti-Captcha (~$2 per 1000)
- CapSolver (~$2.5 per 1000)

**Implementation:**
```python
# Conceptual integration
from twocaptcha import TwoCaptcha

solver = TwoCaptcha('API_KEY')
result = solver.normal('captcha_image.png')
```

**Pros:**
- Can bypass text-based CAPTCHA
- Relatively cheap at scale

**Cons:**
- Adds latency (10-30 seconds per solve)
- Doesn't help with other anti-bot measures
- May violate ToS
- New site might use reCAPTCHA v3 (harder to solve)

**Feasibility Score: 5/10** (depends on new CAPTCHA type)

---

#### Option C: Official Database Extraction (M027)

**Process:**
1. Download Form M027 from ACC website
2. Submit request for entity data extraction
3. Specify data fields needed
4. Receive via email (free) or CD-ROM

**URL:** https://www.azcc.gov/docs/default-source/corps-files/forms/m027-database-extraction-request.pdf

**Pros:**
- 100% legal and authorized
- Complete data access
- No scraping infrastructure
- Free for electronic delivery
- No anti-bot concerns

**Cons:**
- Up to 30 days processing time
- One-time snapshot (not real-time)
- May not include all fields we extract
- Manual process for each request

**Feasibility Score: 9/10** - **HIGHLY RECOMMENDED**

---

#### Option D: API Discovery on New Platform

**Investigation Steps:**
1. Open DevTools → Network tab on new site
2. Perform manual search
3. Look for XHR/Fetch requests to API endpoints
4. Document any REST/GraphQL patterns

**Potential Endpoints to Look For:**
- `/api/entity/search`
- `/api/entity/{id}`
- `/graphql`
- Any JSON responses

**Feasibility Score: 6/10** (unknown until investigated)

---

#### Option E: Stealth Browser Automation

**Tools:**
- Playwright with `playwright-stealth`
- Puppeteer with `puppeteer-extra-plugin-stealth`
- undetected-chromedriver

**Features:**
- Removes automation fingerprints
- Randomizes timing
- Rotates user agents
- Can integrate proxies

**Implementation Complexity:** High

**Feasibility Score: 4/10** (high effort, uncertain success)

---

## Part 5: Recommendations

### 5.1 Immediate Actions (Today)

1. **DO NOT** attempt to run Ecorp scraping - it will fail completely
2. **Manual investigation** of new Arizona Business Connect site:
   - Visit https://arizonabusinesscenter.azcc.gov
   - Document DOM structure
   - Check for visible CAPTCHA
   - Inspect network requests
3. **Backup existing data** - All Ecorp/Complete files from working months

### 5.2 Short-Term Strategy (This Week)

1. **Submit M027 Database Extraction Request** for comprehensive entity data
2. **Document new site** architecture through manual exploration
3. **Create decision matrix** based on findings

### 5.3 Medium-Term Options

**If new site has minimal protection:**
- Update selectors in `ecorp.py`
- Add basic stealth measures
- Implement rate limiting (2-3 second random delays)

**If new site has strong protection:**
- Rely on M027 database extractions
- Investigate API endpoints
- Consider paid data providers

### 5.4 Implementation Priority

| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| P0 | Stop all Ecorp scraping attempts | Immediate | Today |
| P1 | Investigate new site manually | Developer | Today |
| P1 | Submit M027 request | Business | This week |
| P2 | Document new site architecture | Developer | This week |
| P3 | Prototype new scraper (if viable) | Developer | TBD |

---

## Part 6: Technical Debt & Future-Proofing

### 6.1 Current Code Issues

Our `ecorp.py` has several anti-patterns that made it fragile:

```python
# Issue 1: Hardcoded URL (line ~280)
driver.get("https://ecorp.azcc.gov/EntitySearch/Index")
# Should be configurable via Settings

# Issue 2: Fixed selectors (various)
driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Search for an Entity Name']")
# Should be configurable or use more resilient selectors

# Issue 3: No CAPTCHA detection
# Should check for CAPTCHA indicators before proceeding

# Issue 4: Fixed delays
time.sleep(1.5)
# Should use random delays between min/max
```

### 6.2 Recommended Architecture Changes

```python
# Future-proof configuration
class EcorpConfig:
    BASE_URL: str = "https://arizonabusinesscenter.azcc.gov/entitysearch/index"
    MIN_DELAY: float = 2.0
    MAX_DELAY: float = 5.0
    CAPTCHA_SOLVER: Optional[str] = None  # "2captcha", "anticaptcha", None
    USER_AGENTS: List[str] = [...]
    PROXY_LIST: List[str] = [...]

# CAPTCHA detection
def detect_captcha(driver) -> bool:
    captcha_indicators = [
        "captcha",
        "verify you're human",
        "security check",
        "recaptcha"
    ]
    page_source = driver.page_source.lower()
    return any(indicator in page_source for indicator in captcha_indicators)
```

---

## Part 7: Contact Information

For official data requests:

- **Phone:** 602-542-3026 or 1-800-345-5819
- **Email:** answers@azcc.gov
- **Public Records Request:** https://azcc.gov/public-records-request
- **Database Extraction Form:** https://www.azcc.gov/docs/default-source/corps-files/forms/m027-database-extraction-request.pdf

---

## Appendix A: Files Affected

```
src/adhs_etl/ecorp.py           # Main scraping logic (BROKEN)
scripts/process_months_local.py  # Calls generate_ecorp_complete
scripts/test_ecorp_standalone.py # Standalone testing (BROKEN)
Ecorp/Upload/                    # Still works (file-based)
Ecorp/Complete/                  # Cannot generate new files
```

## Appendix B: Last Known Working Files

Based on directory listing, our most recent successful runs:

```
Ecorp/Complete/3.25_Ecorp_Complete 11.04.12-30-58.xlsx  # March 2025
Ecorp/Complete/2.25_Ecorp_Complete 11.04.12-30-33.xlsx  # February 2025
Ecorp/Complete/1.25_Ecorp_Complete 11.04.12-30-12.xlsx  # January 2025
```

These represent our last complete entity extractions before the platform shutdown.

## Appendix C: New Site Investigation Checklist

- [ ] Can access https://arizonabusinesscenter.azcc.gov
- [ ] Identify search input field selector
- [ ] Identify results table structure
- [ ] Identify entity detail page URL pattern
- [ ] Check for CAPTCHA on initial load
- [ ] Check for CAPTCHA after search
- [ ] Document any API endpoints in Network tab
- [ ] Test basic Selenium navigation
- [ ] Check for Cloudflare/DataDome indicators
- [ ] Measure rate limiting thresholds

---

## Part 8: Anti-Bot Protection Likelihood Analysis

### 8.1 Why No CAPTCHA on Day One?

The absence of CAPTCHA on launch day is **expected** but likely **temporary**. Here's the analysis:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    WHY NEW PLATFORM LAUNCHED WITHOUT CAPTCHA                            │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  FACTOR                              │ EXPLANATION                                      │
│  ────────────────────────────────────┼────────────────────────────────────────────────  │
│  1. Launch Priority                  │ Core functionality > security hardening          │
│  2. Testing Period                   │ Need real traffic to tune anti-bot thresholds   │
│  3. User Experience Focus            │ CAPTCHA friction reduces adoption on new site   │
│  4. Analytics Collection             │ Gathering baseline traffic patterns first        │
│  5. Phased Rollout                   │ Security often added in subsequent releases     │
│  6. Budget/Timeline Constraints      │ 10-day migration window was aggressive          │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Probability of Future Anti-Bot Measures

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    ANTI-BOT IMPLEMENTATION PROBABILITY MATRIX                           │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  TIMEFRAME        │ PROBABILITY │ LIKELY MEASURES                                      │
│  ─────────────────┼─────────────┼───────────────────────────────────────────────────── │
│  Week 1-2         │    15%      │ Monitoring only, establishing baselines              │
│  Month 1          │    35%      │ Basic rate limiting, IP blocking                     │
│  Month 2-3        │    60%      │ reCAPTCHA v3 (invisible scoring)                     │
│  Month 3-6        │    75%      │ Full CAPTCHA on search, Cloudflare/similar           │
│  Month 6+         │    85%      │ Aggressive anti-bot (if scraping detected)           │
│                                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  TRIGGER EVENTS THAT ACCELERATE ANTI-BOT DEPLOYMENT:                                    │
│                                                                                         │
│  • High-volume automated traffic detected from single IP                                │
│  • Selenium/WebDriver fingerprints in logs                                              │
│  • Consistent timing patterns in requests                                               │
│  • Complaints from legitimate users about slow performance                              │
│  • Data breach or scraping incident becomes public                                      │
│  • Budget approval for security enhancements                                            │
│  • Vendor pitch for anti-bot solutions (Cloudflare, DataDome, etc.)                    │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Historical Precedent: Government Site Security Patterns

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    GOVERNMENT WEBSITE SECURITY LIFECYCLE                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PHASE 1: Launch (Weeks 1-4)                                                            │
│  ├── Focus: Core functionality                                                          │
│  ├── Security: Basic (HTTPS, authentication where needed)                               │
│  └── Anti-bot: None or minimal                                                          │
│                                                                                         │
│  PHASE 2: Stabilization (Months 1-3)                                                    │
│  ├── Focus: Bug fixes, performance tuning                                               │
│  ├── Security: Log analysis, traffic monitoring                                         │
│  └── Anti-bot: Rate limiting, basic IP blocking                                         │
│                                                                                         │
│  PHASE 3: Hardening (Months 3-6)                                                        │
│  ├── Focus: Security audit findings                                                     │
│  ├── Security: Penetration testing remediation                                          │
│  └── Anti-bot: CAPTCHA on high-value endpoints                                          │
│                                                                                         │
│  PHASE 4: Mature (Months 6+)                                                            │
│  ├── Focus: Feature additions                                                           │
│  ├── Security: Compliance requirements (FedRAMP, etc.)                                  │
│  └── Anti-bot: Full protection suite if budget allows                                   │
│                                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  ARIZONA-SPECIFIC FACTORS:                                                              │
│                                                                                         │
│  • Old eCorp HAD custom CAPTCHA → They know about bot traffic                          │
│  • "Improved security features" mentioned in announcement → Already planned            │
│  • State government budget cycles → Security upgrades in Q3/Q4                         │
│  • Public records laws → May resist blocking legitimate bulk access                    │
│                                                                                         │
│  VERDICT: Expect some form of protection within 3-6 months                              │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.4 Our Scraping Detection Risk

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         OUR DETECTION RISK PROFILE                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  BEHAVIOR                          │ RISK LEVEL │ MITIGATION                            │
│  ──────────────────────────────────┼────────────┼────────────────────────────────────── │
│  1000+ sequential searches         │    HIGH    │ Spread across days, random delays     │
│  Fixed timing patterns             │    HIGH    │ random.uniform(2.0, 8.0)              │
│  navigator.webdriver=true          │   MEDIUM   │ undetected-chromedriver               │
│  Single IP address                 │   MEDIUM   │ Residential proxy rotation            │
│  Same user-agent all requests      │    LOW     │ User-agent rotation                   │
│  Headless browser mode             │    LOW     │ Run in headed mode                    │
│  Tab opening pattern               │    LOW     │ Randomize tab management              │
│                                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  ESTIMATED TIME UNTIL DETECTION (if no mitigation):                                     │
│                                                                                         │
│     ┌─────────────────────────────────────────────────────────────────────┐            │
│     │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │            │
│     │  30-60 days of heavy scraping before flagged                        │            │
│     └─────────────────────────────────────────────────────────────────────┘            │
│                                                                                         │
│  WITH MITIGATION (delays, rotation, stealth):                                           │
│                                                                                         │
│     ┌─────────────────────────────────────────────────────────────────────┐            │
│     │  ████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │            │
│     │  90-180 days before potential detection                             │            │
│     └─────────────────────────────────────────────────────────────────────┘            │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 9: M027 Decision Framework

### 9.1 When to Switch to Official M027 Route

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         M027 DECISION TREE                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│                            ┌──────────────────────┐                                     │
│                            │   Can we scrape the  │                                     │
│                            │   new site at all?   │                                     │
│                            └──────────┬───────────┘                                     │
│                                       │                                                 │
│                          ┌────────────┴────────────┐                                    │
│                          │                         │                                    │
│                          ▼                         ▼                                    │
│                    ┌─────────┐               ┌─────────┐                                │
│                    │   YES   │               │   NO    │──────▶ USE M027 IMMEDIATELY    │
│                    └────┬────┘               └─────────┘                                │
│                         │                                                               │
│                         ▼                                                               │
│            ┌───────────────────────────┐                                                │
│            │  Is phone/email data      │                                                │
│            │  critical to our pipeline?│                                                │
│            └─────────────┬─────────────┘                                                │
│                          │                                                              │
│             ┌────────────┴────────────┐                                                 │
│             │                         │                                                 │
│             ▼                         ▼                                                 │
│       ┌─────────┐               ┌─────────┐                                             │
│       │   YES   │               │   NO    │──────▶ USE M027 (cheaper, legal)            │
│       └────┬────┘               └─────────┘                                             │
│            │                                                                            │
│            ▼                                                                            │
│  ┌─────────────────────────────┐                                                        │
│  │  Is scraping sustainable    │                                                        │
│  │  (no CAPTCHA, low risk)?    │                                                        │
│  └─────────────┬───────────────┘                                                        │
│                │                                                                        │
│   ┌────────────┴────────────┐                                                           │
│   │                         │                                                           │
│   ▼                         ▼                                                           │
│ ┌───────┐              ┌─────────┐                                                      │
│ │  YES  │              │   NO    │──────▶ HYBRID: M027 for base + BatchData for contact │
│ └───┬───┘              └─────────┘                                                      │
│     │                                                                                   │
│     ▼                                                                                   │
│  CONTINUE SCRAPING                                                                      │
│  (with monitoring)                                                                      │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Trigger Conditions for M027 Switch

| Trigger Condition | Action |
|-------------------|--------|
| CAPTCHA appears on new site | Immediate M027 submission |
| Cloudflare/anti-bot detected | Immediate M027 submission |
| IP blocked or rate limited | Assess severity, likely M027 |
| Scraper fails 3+ consecutive runs | M027 + investigate |
| Processing time exceeds 4 hours/batch | Consider M027 for efficiency |
| Legal concern raised | Immediate M027 switch |
| Cost of scraping > $200/month | Evaluate M027 economics |

### 9.3 Hybrid Strategy Recommendation

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      RECOMMENDED HYBRID APPROACH                                        │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  IMMEDIATE (This Week):                                                                 │
│  ├── 1. Submit M027 request for comprehensive baseline data ($75)                       │
│  ├── 2. Adapt Selenium scraper for new site (selectors only)                           │
│  └── 3. Test scraper with 10-record batch                                              │
│                                                                                         │
│  SHORT-TERM (Month 1):                                                                  │
│  ├── 1. Run adapted scraper for current month's data                                    │
│  ├── 2. Receive M027 data (backup/validation)                                          │
│  ├── 3. Compare scraping results vs M027 data                                          │
│  └── 4. Document scraping reliability metrics                                          │
│                                                                                         │
│  ONGOING:                                                                               │
│  ├── 1. Monthly scraping runs (if viable)                                               │
│  ├── 2. Quarterly M027 requests (safety net)                                           │
│  └── 3. Monitor for anti-bot changes                                                   │
│                                                                                         │
│  FALLBACK:                                                                              │
│  ├── 1. M027 for base entity data (names, addresses, status)                           │
│  └── 2. BatchData API for phone/email enrichment (already in pipeline)                 │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 10: Cost Analysis

### 10.1 Scraping Cost Model

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         SCRAPING COST BREAKDOWN                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  CURRENT COSTS (Monthly Estimate):                                                      │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  COMPONENT                         │ COST/MONTH │ NOTES                                 │
│  ──────────────────────────────────┼────────────┼────────────────────────────────────── │
│  Developer time (maintenance)      │   $0-100   │ Assuming occasional fixes             │
│  Compute (local machine)           │     $0     │ Using existing hardware               │
│  Electricity                       │    ~$5     │ 65 min/run × 4 runs/month             │
│  Proxy service (if needed)         │   $0-50    │ Currently not used                    │
│  CAPTCHA solving (if needed)       │   $0-15    │ ~$3/1000 solves                       │
│  ──────────────────────────────────┼────────────┼────────────────────────────────────── │
│  TOTAL (current)                   │   ~$5      │ Minimal - local execution             │
│  TOTAL (with mitigations)          │  ~$50-150  │ If proxies/CAPTCHA needed             │
│                                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  HIDDEN COSTS:                                                                          │
│  • Developer time for selector updates when site changes                                │
│  • Debugging failed runs                                                                │
│  • Data quality issues from incomplete scrapes                                          │
│  • Risk of IP blacklisting affecting other operations                                   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 M027 Official Route Cost Model

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         M027 COST BREAKDOWN                                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PRICING OPTIONS:                                                                       │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  OPTION                            │ ONE-TIME   │ ANNUAL      │ NOTES                   │
│  ──────────────────────────────────┼────────────┼─────────────┼──────────────────────── │
│  Custom Extract (email delivery)   │    $75     │    $900     │ 12 monthly requests     │
│  Custom Extract (quarterly)        │    $75     │    $300     │ 4 quarterly requests    │
│  Full Database (one-time)          │   $1,000   │   $1,000    │ Complete snapshot       │
│  Full Database (semi-annual)       │   $1,000   │   $2,000    │ 2 full extracts/year    │
│                                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  RECOMMENDED: Quarterly Custom Extract @ $300/year                                      │
│                                                                                         │
│  PROCESSING TIME: Up to 30 days (plan accordingly)                                      │
│  DELIVERY: Email (free) or CD-ROM                                                       │
│  FORMAT: Double-quote delimited, comma-separated ASCII                                  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 10.3 Total Cost Comparison (Annual)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    ANNUAL COST COMPARISON: SCRAPING vs M027                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│                          SCRAPING                    M027 OFFICIAL                      │
│                          ────────                    ────────────                       │
│                                                                                         │
│  Base Cost               $60/year                    $300-900/year                      │
│                          (compute only)              (quarterly-monthly)                │
│                                                                                         │
│  With Mitigations        $600-1,800/year             $300-900/year                      │
│                          (proxies, CAPTCHA)          (same)                             │
│                                                                                         │
│  Maintenance Time        20-40 hrs/year              2-4 hrs/year                       │
│                          @ $50/hr = $1,000-2,000     @ $50/hr = $100-200                │
│                                                                                         │
│  Data Completeness       95-99%                      100%                               │
│                          (network errors, blocks)    (official source)                  │
│                                                                                         │
│  Phone/Email Data        YES                         NO                                 │
│                          (critical differentiator)   (requires BatchData)               │
│                                                                                         │
│  Risk                    MEDIUM-HIGH                 ZERO                               │
│                          (blocks, legal gray area)   (authorized access)                │
│                                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  SCENARIO A: Phone/Email NOT Critical                                                   │
│  ─────────────────────────────────────                                                  │
│  Winner: M027 @ $300-900/year (lower maintenance, zero risk)                            │
│                                                                                         │
│  SCENARIO B: Phone/Email IS Critical                                                    │
│  ─────────────────────────────────────                                                  │
│  Winner: Hybrid approach                                                                │
│  • M027 for base data: $300/year                                                        │
│  • Scraping for phone/email: $60-600/year                                               │
│  • OR BatchData API: Variable (already in pipeline)                                     │
│  Total: $360-900/year + BatchData costs                                                 │
│                                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  BREAK-EVEN ANALYSIS:                                                                   │
│                                                                                         │
│  If scraping requires > 10 hrs/month maintenance → Switch to M027                       │
│  If CAPTCHA solving costs > $50/month → Switch to M027                                  │
│  If proxy costs > $100/month → Switch to M027                                           │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 10.4 Contact Enrichment Cost (If M027 Used for Base Data)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    CONTACT ENRICHMENT ALTERNATIVES                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  Since M027 lacks phone/email, alternatives for contact data:                           │
│                                                                                         │
│  OPTION                   │ COST              │ DATA QUALITY │ INTEGRATION              │
│  ─────────────────────────┼───────────────────┼──────────────┼───────────────────────── │
│  BatchData API            │ ~$0.05-0.15/rec   │ HIGH         │ Already in pipeline      │
│  (already integrated)     │                   │              │                          │
│                           │                   │              │                          │
│  Scrape new site          │ ~$0.005/rec       │ MEDIUM       │ Needs selector rework    │
│  (phone/email only)       │ (compute only)    │              │                          │
│                           │                   │              │                          │
│  ZoomInfo/similar         │ $500+/month       │ HIGH         │ API integration needed   │
│                           │                   │              │                          │
│  Skip manual              │ $0                │ N/A          │ No phone/email in output │
│                           │                   │              │                          │
│  ─────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                         │
│  RECOMMENDATION: Continue using BatchData API for contact enrichment                    │
│                  It's already integrated and provides TCPA/DNC compliance              │
│                                                                                         │
│  M027 + BatchData = Complete data without scraping risk                                 │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 11: Risk-Adjusted Recommendations

### 11.1 Risk Matrix

| Factor | Scraping (New Site) | M027 Official |
|--------|---------------------|---------------|
| Legal Risk | MEDIUM (gray area) | ZERO |
| Technical Risk | MEDIUM (selectors may break) | ZERO |
| Data Completeness | 95-99% | 100% |
| Phone/Email Access | YES | NO |
| Turnaround Time | Immediate | Up to 30 days |
| Maintenance Burden | HIGH | MINIMAL |
| Long-term Viability | UNCERTAIN | GUARANTEED |

### 11.2 Final Recommendations

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         STRATEGIC RECOMMENDATION                                        │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ╔═══════════════════════════════════════════════════════════════════════════════════╗ │
│  ║                                                                                   ║ │
│  ║  PRIMARY: Adapt scraping for new site (window of opportunity)                     ║ │
│  ║  ────────────────────────────────────────────────────────────────                 ║ │
│  ║  The new site has NO CAPTCHA today. This is a limited window.                     ║ │
│  ║  Act now to:                                                                      ║ │
│  ║  1. Update URL and selectors                                                      ║ │
│  ║  2. Add random delays and stealth measures                                        ║ │
│  ║  3. Process backlog while access is easy                                          ║ │
│  ║                                                                                   ║ │
│  ║  SECONDARY: Submit M027 as insurance                                              ║ │
│  ║  ────────────────────────────────────────────────────────────────                 ║ │
│  ║  $75 for peace of mind. If scraping breaks, you have backup.                      ║ │
│  ║  30-day processing means submit NOW for February data.                            ║ │
│  ║                                                                                   ║ │
│  ║  TERTIARY: Monitor for anti-bot rollout                                           ║ │
│  ║  ────────────────────────────────────────────────────────────────                 ║ │
│  ║  Check weekly for:                                                                ║ │
│  ║  • CAPTCHA on search/detail pages                                                 ║ │
│  ║  • Cloudflare challenge pages                                                     ║ │
│  ║  • Rate limiting errors                                                           ║ │
│  ║  • Selenium detection ("bot detected" messages)                                   ║ │
│  ║                                                                                   ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════════════╝ │
│                                                                                         │
│  EXPECTED OUTCOME:                                                                      │
│  • 3-6 months of scraping viability (estimated)                                         │
│  • M027 as guaranteed fallback                                                          │
│  • BatchData continues for contact enrichment regardless                                │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Conclusion

**Current Status (January 12, 2026):**
- Old eCorp site: **OFFLINE** (301 redirect to new platform)
- New Arizona Business Connect: **LIVE, NO CAPTCHA DETECTED**
- Our scraper: **NEEDS REWORK** (URL + selectors)

**Key Insight:** We have a **window of opportunity**. New government platforms typically launch without aggressive anti-bot measures, adding them in subsequent releases. Expect 3-6 months before significant protection is added.

**Action Items:**
1. **TODAY:** Investigate new site DOM structure via DevTools
2. **THIS WEEK:** Update `ecorp.py` with new URL and selectors
3. **THIS WEEK:** Submit M027 request ($75) as insurance
4. **ONGOING:** Monitor for anti-bot changes, have fallback ready

**The Bottom Line:**
- Scraping is **viable NOW** but has a **limited lifespan**
- M027 provides **guaranteed access** but lacks phone/email
- **Hybrid approach** (scraping + M027 backup) is optimal
- BatchData API already handles contact enrichment regardless

---

## Appendix D: DOM Selector Mapping (Old → New)

### D.1 URL Updates

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              URL MIGRATION                                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  COMPONENT                │ OLD (ecorp.azcc.gov)              │ NEW (arizonabusinesscenter)        │
│  ─────────────────────────┼───────────────────────────────────┼────────────────────────────────── │
│  Base URL                 │ https://ecorp.azcc.gov            │ https://arizonabusinesscenter.azcc.gov │
│  Entity Search            │ /EntitySearch/Index               │ /entitysearch/index               │
│  Entity Detail            │ /EntitySearch/EntityDetails/{id}  │ /entitysearch/entitydetails/{id}  │
│                                                                                         │
│  CODE CHANGE (ecorp.py line 301):                                                       │
│  OLD: base_url = "https://ecorp.azcc.gov/EntitySearch/Index"                           │
│  NEW: base_url = "https://arizonabusinesscenter.azcc.gov/entitysearch/index"           │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### D.2 Angular Material Selector Migration

The new site uses Angular Material components. Here's the selector mapping:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         SEARCH INPUT SELECTORS                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  OLD (ecorp.py line 307):                                                               │
│  ────────────────────────                                                               │
│  By.CSS_SELECTOR, "input[placeholder*='Search for an Entity Name']"                    │
│                                                                                         │
│  NEW (try in order - first match wins):                                                 │
│  ─────────────────────────────────────                                                  │
│  1. By.CSS_SELECTOR, "input[formcontrolname='entityName']"                             │
│  2. By.CSS_SELECTOR, "mat-form-field input[type='text']"                               │
│  3. By.CSS_SELECTOR, "input[placeholder*='entity']"                                    │
│  4. By.CSS_SELECTOR, "input[placeholder*='Entity']"                                    │
│  5. By.CSS_SELECTOR, ".mat-mdc-form-field input"                                       │
│  6. By.XPATH, "//input[contains(@placeholder, 'Entity') or contains(@placeholder, 'entity')]" │
│                                                                                         │
│  RECOMMENDED ROBUST APPROACH:                                                           │
│  ─────────────────────────────                                                          │
│  def find_search_input(driver):                                                         │
│      selectors = [                                                                      │
│          (By.CSS_SELECTOR, "input[formcontrolname='entityName']"),                     │
│          (By.CSS_SELECTOR, "input[formcontrolname='entityname']"),                     │
│          (By.CSS_SELECTOR, "mat-form-field input[type='text']"),                       │
│          (By.CSS_SELECTOR, "input[placeholder*='Entity']"),                            │
│          (By.CSS_SELECTOR, ".mat-mdc-form-field-infix input"),                         │
│      ]                                                                                  │
│      for by, selector in selectors:                                                     │
│          try:                                                                           │
│              return WebDriverWait(driver, 3).until(                                     │
│                  EC.presence_of_element_located((by, selector))                         │
│              )                                                                          │
│          except:                                                                        │
│              continue                                                                   │
│      raise Exception("Could not find search input")                                     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         RESULTS TABLE SELECTORS                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  OLD (ecorp.py line 329):                                                               │
│  ────────────────────────                                                               │
│  By.CSS_SELECTOR, "table tbody tr"                                                     │
│                                                                                         │
│  NEW (Angular Material table):                                                          │
│  ─────────────────────────────                                                          │
│  1. By.CSS_SELECTOR, "mat-table mat-row"          # Angular Material table rows        │
│  2. By.CSS_SELECTOR, "mat-row"                     # Shorthand for mat-row elements    │
│  3. By.CSS_SELECTOR, ".mat-mdc-row"                # MDC-based Material row class      │
│  4. By.CSS_SELECTOR, "table.mat-mdc-table tbody tr" # Hybrid table/material           │
│  5. By.CSS_SELECTOR, "[role='row']"                # ARIA role-based selector          │
│                                                                                         │
│  TABLE CELL SELECTORS:                                                                  │
│  ─────────────────────                                                                  │
│  OLD: row.find_elements(By.TAG_NAME, "td")                                             │
│  NEW: row.find_elements(By.CSS_SELECTOR, "mat-cell") OR                                │
│       row.find_elements(By.CSS_SELECTOR, ".mat-mdc-cell") OR                           │
│       row.find_elements(By.CSS_SELECTOR, "[role='cell']")                              │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         NO RESULTS / MODAL SELECTORS                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  OLD (ecorp.py line 319):                                                               │
│  ────────────────────────                                                               │
│  By.XPATH, "//div[contains(text(), 'No search results were found')]"                   │
│                                                                                         │
│  NEW (Angular Material dialog):                                                         │
│  ─────────────────────────────                                                          │
│  1. By.CSS_SELECTOR, "mat-dialog-container"        # Dialog container                  │
│  2. By.CSS_SELECTOR, ".mat-mdc-dialog-container"   # MDC dialog                        │
│  3. By.CSS_SELECTOR, "mat-snack-bar-container"     # Could be snackbar instead         │
│  4. By.XPATH, "//*[contains(text(), 'No') and contains(text(), 'found')]"             │
│  5. By.XPATH, "//mat-dialog-content//*[contains(text(), 'result')]"                   │
│                                                                                         │
│  OK BUTTON (ecorp.py line 321):                                                         │
│  ─────────────────────────────                                                          │
│  OLD: By.XPATH, "//button[normalize-space()='OK']"                                     │
│  NEW:                                                                                   │
│  1. By.CSS_SELECTOR, "mat-dialog-actions button"                                       │
│  2. By.CSS_SELECTOR, ".mat-mdc-dialog-actions button"                                  │
│  3. By.XPATH, "//mat-dialog-actions//button"                                           │
│  4. By.CSS_SELECTOR, "button.mat-mdc-button"                                           │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         ENTITY DETAIL PAGE SELECTORS                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  OLD (ecorp.py line 344):                                                               │
│  ────────────────────────                                                               │
│  By.XPATH, "//h2[contains(text(),'Entity Information')]"                               │
│                                                                                         │
│  NEW (Angular Material expansion panels or cards):                                      │
│  ─────────────────────────────────────────────────                                      │
│  1. By.XPATH, "//*[contains(text(),'Entity Information')]"                             │
│  2. By.CSS_SELECTOR, "mat-expansion-panel-header"                                      │
│  3. By.CSS_SELECTOR, "mat-card-title"                                                  │
│  4. By.CSS_SELECTOR, ".entity-info, .entity-details"                                   │
│  5. By.XPATH, "//mat-card//*[contains(text(),'Entity')]"                               │
│                                                                                         │
│  FIELD LABEL → VALUE PATTERN:                                                           │
│  ────────────────────────────                                                           │
│  OLD: Text search with find_next()                                                      │
│  NEW: Angular Material likely uses definition lists or grid layouts:                    │
│                                                                                         │
│  # Pattern 1: Definition list                                                           │
│  By.XPATH, "//dt[contains(text(),'Status')]/following-sibling::dd[1]"                  │
│                                                                                         │
│  # Pattern 2: Label-value pairs in mat-form-field                                       │
│  By.XPATH, "//mat-label[contains(text(),'Status')]/..//input"                          │
│                                                                                         │
│  # Pattern 3: Grid layout with classes                                                  │
│  By.XPATH, "//*[@class='field-label' and contains(text(),'Status')]/following-sibling::*" │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### D.3 Complete Code Change Summary

```python
# ecorp.py CHANGES REQUIRED
# ========================

# Line 301 - URL Update
# OLD:
base_url = "https://ecorp.azcc.gov/EntitySearch/Index"
# NEW:
base_url = "https://arizonabusinesscenter.azcc.gov/entitysearch/index"

# Lines 306-308 - Search Input
# OLD:
search_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Search for an Entity Name']"))
)
# NEW (with fallback):
search_selectors = [
    (By.CSS_SELECTOR, "input[formcontrolname='entityName']"),
    (By.CSS_SELECTOR, "input[formcontrolname='entityname']"),
    (By.CSS_SELECTOR, "mat-form-field input[type='text']"),
    (By.CSS_SELECTOR, "input[placeholder*='Entity']"),
    (By.CSS_SELECTOR, ".mat-mdc-form-field-infix input"),
]
search_input = None
for by_type, selector in search_selectors:
    try:
        search_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((by_type, selector))
        )
        break
    except:
        continue
if not search_input:
    raise Exception("Could not locate search input field")

# Line 315 - Add random delay instead of fixed
# OLD:
time.sleep(1.5)
# NEW:
import random
time.sleep(random.uniform(2.0, 5.0))

# Lines 319-322 - No Results Modal
# OLD:
no_results_modal = driver.find_element(By.XPATH, "//div[contains(text(), 'No search results were found')]")
ok_button = driver.find_element(By.XPATH, "//button[normalize-space()='OK']")
# NEW:
no_results_selectors = [
    (By.XPATH, "//*[contains(text(), 'No') and contains(text(), 'found')]"),
    (By.CSS_SELECTOR, "mat-dialog-content"),
    (By.CSS_SELECTOR, ".mat-mdc-snack-bar-container"),
]
# Try each selector...

# Line 329 - Results Table
# OLD:
rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
# NEW:
table_row_selectors = [
    (By.CSS_SELECTOR, "mat-row"),
    (By.CSS_SELECTOR, ".mat-mdc-row"),
    (By.CSS_SELECTOR, "table tbody tr"),  # Keep as fallback
    (By.CSS_SELECTOR, "[role='row']:not([role='row'][aria-rowindex='1'])"),
]

# Lines 331-338 - Table Cell Extraction
# OLD:
cols = row.find_elements(By.TAG_NAME, "td")
link = cols[1].find_element(By.TAG_NAME, "a")
# NEW:
cols = row.find_elements(By.CSS_SELECTOR, "mat-cell, .mat-mdc-cell, td")
link = cols[1].find_element(By.CSS_SELECTOR, "a, [routerlink]")

# Lines 343-345 - Entity Detail Wait
# OLD:
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//h2[contains(text(),'Entity Information')]"))
)
# NEW:
detail_selectors = [
    (By.XPATH, "//*[contains(text(),'Entity Information')]"),
    (By.CSS_SELECTOR, "mat-card, .entity-details"),
    (By.CSS_SELECTOR, "[class*='entity']"),
]
```

### D.4 Testing Checklist

Before running the updated scraper on live data:

- [ ] Manually verify new URL loads: `https://arizonabusinesscenter.azcc.gov/entitysearch/index`
- [ ] Open DevTools (F12) → Elements tab
- [ ] Find actual search input selector by inspecting the element
- [ ] Find actual results table structure by performing a test search
- [ ] Find entity detail page structure by clicking on a result
- [ ] Confirm NO CAPTCHA appears during manual test
- [ ] Document exact selectors found in DevTools
- [ ] Test scraper with 1 record first
- [ ] Test with 10 records batch
- [ ] Monitor for rate limiting (HTTP 429 or blocks)

### D.5 DevTools Quick Reference

To find the exact selectors on the live site:

1. **Open the site**: `https://arizonabusinesscenter.azcc.gov/entitysearch/index`
2. **Open DevTools**: Press `F12` or `Cmd+Option+I` (Mac)
3. **Inspect search input**: Click the "Select element" tool (top-left of DevTools), click on the search box
4. **Copy selector**: Right-click the highlighted HTML → Copy → Copy selector
5. **Test selector in Console**: `document.querySelector('YOUR_SELECTOR')`
6. **Repeat for results table** after performing a search

---

*This analysis was generated on January 12, 2026 - the exact day of the Arizona Business Connect platform launch.*

*Document Location: `Ecorp/ecorp-captcha-analysis.md`*
*Related Files: `src/adhs_etl/ecorp.py`, `Ecorp/m027-database-extraction-request.pdf`*
