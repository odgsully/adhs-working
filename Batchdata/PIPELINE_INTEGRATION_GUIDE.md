# BatchData API Integration Guide for ADHS ETL Pipeline

**Created:** 2025-11-17
**Purpose:** Complete guide for integrating BatchData APIs into our ADHS ETL pipeline

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Endpoints](#api-endpoints)
3. [Authentication](#authentication)
4. [Pipeline Integration](#pipeline-integration)
5. [Troubleshooting](#troubleshooting)
6. [Cost Management](#cost-management)
7. [Testing](#testing)

---

## Quick Start

### Prerequisites

```bash
# Required environment variables in .env
BD_SKIPTRACE_KEY=your-skip-trace-api-key
BD_ADDRESS_KEY=your-address-api-key (optional)
BD_PROPERTY_KEY=your-property-api-key (optional)
BD_PHONE_KEY=your-phone-api-key
```

### Pipeline Flow

```
Ecorp Complete (93 columns)
    ↓
transform_ecorp_to_batchdata()
    ↓
BatchData Upload (INPUT_MASTER sheet with required columns)
    ↓
BatchData API Processing
    ↓
BatchData Complete (enriched with phone/email/DNC/TCPA data)
```

---

## API Endpoints

### Base URL Structure

**IMPORTANT:** BatchData V1 API is the correct version for wallet credit accounts:

```
✅ CORRECT: https://api.batchdata.com/api/v1
❌ WRONG:   https://api.batchdata.com (missing version)
❌ WRONG:   https://api.batchdata.com/v1 (missing /api prefix)
```

### API Version Information

- **V1** (RECOMMENDED for wallet credits): `https://api.batchdata.com/api/v1`
  - Full support for all features
  - Compatible with wallet credit billing
  - Supports both sync and async patterns
  - Stable and production-ready

**Note**: V2 and V3 exist but V1 is the recommended version for wallet credit accounts.

### Skip-Trace API (Primary)

#### Async Endpoint (Recommended for batches)

```
POST https://api.batchdata.com/api/v1/property/skip-trace/async
```

**Features:**
- Processes large batches without timeout
- Returns job ID immediately
- Poll for completion or use webhook
- Each property with results = 1 billable request

**Request Format:**
```json
{
  "requests": [
    {
      "requestId": "unique_123",
      "propertyAddress": {
        "street": "123 Main St",
        "city": "Phoenix",
        "state": "AZ",
        "zip": "85001"
      },
      "name": {
        "first": "John",
        "last": "Doe"
      }
    }
  ],
  "options": {
    "webhookUrl": "https://your-webhook.com/callback"
  }
}
```

**Response:**
```json
{
  "status": {
    "code": 200,
    "text": "OK"
  },
  "result": {
    "jobId": "job_abc123def456"
  }
}
```

#### Sync Endpoint (For small batches < 100 properties)

```
POST https://api.batchdata.com/api/v1/property/skip-trace
```

**Use when:**
- Processing < 100 properties
- Need immediate results (no polling)
- Interactive queries

### Phone Verification APIs

#### Phone Verification
```
Sync:  POST https://api.batchdata.com/api/v1/phone/verification
Async: POST https://api.batchdata.com/api/v1/phone/verification/async
Cost: $0.007/phone
```

#### Phone DNC Status
```
Sync:  POST https://api.batchdata.com/api/v1/phone/dnc
Async: POST https://api.batchdata.com/api/v1/phone/dnc/async
Cost: $0.002/phone
```

#### Phone TCPA Status
```
Sync:  POST https://api.batchdata.com/api/v1/phone/tcpa
Async: POST https://api.batchdata.com/api/v1/phone/tcpa/async
Cost: $0.002/phone
```

### Address Verification (Optional)

```
POST https://api.batchdata.com/api/v1/address/verify
```

---

## Authentication

### API Key Headers

```http
Authorization: Bearer YOUR_API_KEY_HERE
Content-Type: application/json
Accept: application/json
```

### API Key Types

| Service | ENV Variable | Purpose |
|---------|--------------|---------|
| Skip-Trace | `BD_SKIPTRACE_KEY` | Property owner contact lookup |
| Phone Verification | `BD_PHONE_KEY` | Phone validation/DNC/TCPA |
| Address Verification | `BD_ADDRESS_KEY` | Address validation (optional) |
| Property Search | `BD_PROPERTY_KEY` | Property data lookup (optional) |

### Key Management

```python
# In config
from adhs_etl.config import Settings

settings = Settings()
api_keys = {
    'BD_SKIPTRACE_KEY': settings.bd_skiptrace_key,
    'BD_PHONE_KEY': settings.bd_phone_key,
    # ... etc
}
```

---

## Pipeline Integration

### Stage 5: BatchData Enrichment

#### Input Requirements

The `INPUT_MASTER` sheet must have these **16 columns** (API uses ADDRESS ONLY for skip-trace):

**Required:**
- `BD_RECORD_ID` - Unique identifier
- `BD_SOURCE_TYPE` - Always "Entity"
- `BD_ENTITY_NAME` - Entity name from Ecorp
- `BD_SOURCE_ENTITY_ID` - Entity ID from Ecorp
- `BD_TITLE_ROLE` - Principal's role (Manager, Member, etc.)
- `BD_ADDRESS` - Street address
- `BD_CITY` - City name
- `BD_STATE` - 2-letter state code
- `BD_ZIP` - 5-digit ZIP code
- `BD_COUNTY` - County name
- `BD_APN` - Assessor Parcel Number
- `BD_MAILING_LINE1`, `BD_MAILING_CITY`, `BD_MAILING_STATE`, `BD_MAILING_ZIP` - Mailing address
- `BD_NOTES` - Processing notes

**REMOVED (November 2025):**
- BD_TARGET_FIRST_NAME, BD_TARGET_LAST_NAME, BD_OWNER_NAME_FULL, BD_ADDRESS_2
- API uses address-only for lookups; names returned in API response

#### Transformation Process

```python
# In batchdata_bridge.py
from src.adhs_etl.batchdata_bridge import (
    create_batchdata_upload,
    run_batchdata_enrichment
)

# Step 1: Create Upload file from Ecorp Complete
upload_path = create_batchdata_upload(
    ecorp_complete_path="Ecorp/Complete/10.24_Ecorp_Complete_11.17.09-48-02.xlsx",
    month_code="10.24",
    timestamp="11.17.09-48-02"
)

# Step 2: Run enrichment
complete_path = run_batchdata_enrichment(
    upload_path=str(upload_path),
    month_code="10.24",
    timestamp="11.17.09-48-02",
    dry_run=False,
    dedupe=True,
    consolidate_families=True,
    filter_entities=True
)
```

#### Output Structure

**BatchData Complete** includes:

- All input columns
- `phones[0-9].number` - Phone numbers in E.164 format
- `phones[0-9].type` - mobile/landline/voip
- `phones[0-9].score` - Quality score (0-100)
- `phones[0-9].is_active` - Phone verification status
- `phones[0-9].on_dnc` - Do-Not-Call registry status
- `phones[0-9].is_litigator` - TCPA litigator flag
- `emails[0-9].address` - Email addresses
- `emails[0-9].type` - Email type

---

## Troubleshooting

### Common Issues

#### 1. 404 Not Found Error

**Error:**
```
404 Client Error: Not Found for url: https://api.batchdata.com/property-skip-trace-async
```

**Cause:** Missing `/api/v1` prefix in URL or using hyphens instead of slashes

**Solution:**
```python
# ❌ WRONG
base_url = "https://api.batchdata.com"
endpoint = "property-skip-trace-async"  # Wrong: hyphens
url = f"{base_url}/{endpoint}"  # Missing /api/v1!

# ✅ CORRECT
base_url = "https://api.batchdata.com/api/v1"
endpoint = "property/skip-trace/async"  # Note: forward slashes, not hyphens
url = f"{base_url}/{endpoint}"
```

**Fixed in:** `Batchdata/src/batchdata.py:18`

#### 2. Authentication Errors

**Error:**
```
401 Unauthorized
```

**Causes:**
- Invalid API key
- Expired API key
- Wrong service key for endpoint

**Solution:**
```bash
# Verify keys in .env
echo $BD_SKIPTRACE_KEY
echo $BD_PHONE_KEY

# Test with curl
curl -X POST https://api.batchdata.com/api/v1/property/skip-trace \
  -H "Authorization: Bearer YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"requests":[{"requestId":"test","propertyAddress":{"street":"123 Main St","city":"Phoenix","state":"AZ","zip":"85001"}}]}'
```

#### 3. Data Quality Issues

**Error:**
```
Missing fields: BD_ADDRESS, BD_CITY, BD_STATE
```

**Solution:**
The `transform_ecorp_to_batchdata()` function should handle this, but verify:

```python
# Check transformed data
df = transform_ecorp_to_batchdata(ecorp_df)
print(df.columns.tolist())
print(df[['BD_ADDRESS', 'BD_CITY', 'BD_STATE', 'BD_ZIP']].head())
```

#### 4. Webhook Issues (Async)

**Problem:** No webhook responses received

**Solutions:**
1. Use ngrok for local testing:
   ```bash
   ngrok http 8000
   # Use ngrok URL as webhookUrl
   ```

2. Verify webhook endpoint accepts POST requests
3. Check webhook logs for incoming requests
4. Use synchronous endpoint for testing

#### 5. Rate Limiting

**Error:**
```
429 Too Many Requests
```

**Solution:**
- Reduce batch size
- Add delays between requests
- Use async endpoints for large batches
- Contact BatchData support to increase limits

---

## Cost Management

### Pricing Structure

| Service | Cost per Record | Notes |
|---------|-----------------|-------|
| Skip-Trace | $0.07 | Per property with results |
| Phone Verification | $0.007 | Per phone number |
| Phone DNC | $0.002 | Per phone number |
| Phone TCPA | $0.002 | Per phone number |

### Cost Optimization Strategies

#### 1. Deduplication

```python
# Enabled by default in run_batchdata_enrichment
dedupe=True  # Removes duplicate persons within batch
```

**Savings:** Typically 10-30% reduction

#### 2. Family Consolidation

```python
# Consolidate principals across related entities
consolidate_families=True
```

**Savings:** 5-15% for entity-heavy datasets

#### 3. Entity Filtering

```python
# Remove entity-only records (no individuals)
filter_entities=True
```

**Savings:** 20%+ for corporate-heavy datasets

#### 4. Batch Processing

- Process monthly, not daily
- Combine multiple months before enrichment
- Skip records already enriched

### Cost Estimation

```python
# Automatic cost estimate before processing
=== COST ESTIMATE ===
skip_trace: $0.28 (4 records × $0.07)
phone_verification: $0.06 (8 phones × $0.007)
phone_dnc: $0.02 (8 phones × $0.002)
phone_tcpa: $0.02 (8 phones × $0.002)
TOTAL ESTIMATED COST: $0.37
======================
```

---

## Testing

### Dry Run Mode

```python
# Test without API calls
run_batchdata_enrichment(
    upload_path="test.xlsx",
    month_code="10.24",
    dry_run=True  # No API calls, no charges
)
```

### Sample Test Input

```python
# Create test file with minimal data
test_df = pd.DataFrame([
    {
        'BD_RECORD_ID': 'test_001',
        'BD_SOURCE_TYPE': 'Entity',
        'BD_ENTITY_NAME': 'TEST ENTITY LLC',
        'BD_SOURCE_ENTITY_ID': 'L12345678',
        'BD_TITLE_ROLE': 'Manager',
        'BD_ADDRESS': '123 Main St',
        'BD_CITY': 'Phoenix',
        'BD_STATE': 'AZ',
        'BD_ZIP': '85001',
        'BD_COUNTY': 'MARICOPA'
    }
])
```

### Integration Test

```bash
# Run complete pipeline on test data
cd Batchdata
python3 src/run.py --input tests/batchdata_local_input.xlsx --dry-run
```

---

## API Response Examples

### Skip-Trace Success Response

```json
{
  "record_id": "ecorp_123456_1_abc123",
  "property": {
    "address": {
      "street": "123 MAIN ST",
      "city": "PHOENIX",
      "state": "AZ",
      "zip": "85001"
    }
  },
  "persons": [
    {
      "name": {
        "first": "JOHN",
        "last": "DOE",
        "full": "JOHN DOE"
      },
      "phones": [
        {
          "number": "+16025551234",
          "type": "mobile",
          "score": 95,
          "is_active": true,
          "is_reachable": true,
          "on_dnc": false,
          "is_litigator": false
        }
      ],
      "emails": [
        {
          "address": "john.doe@example.com",
          "type": "personal"
        }
      ]
    }
  ]
}
```

### Error Response

```json
{
  "error": {
    "code": "INVALID_ADDRESS",
    "message": "Address could not be validated",
    "details": {
      "field": "propertyAddress.street",
      "value": "Invalid St"
    }
  }
}
```

---

## Rate Limits

### Default Limits (V1 API)

- **Synchronous endpoints:** 10 requests/second
- **Asynchronous endpoints:** 100 requests/minute
- **Concurrent async jobs:** 5 active jobs

### Handling Rate Limits

```python
import time
from requests.exceptions import HTTPError

def make_request_with_retry(func, max_retries=3):
    """Retry requests with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** attempt
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

---

## Additional Resources

### Documentation Links

- **Official API Docs:** https://developer.batchdata.com/docs/batchdata
- **Data Dictionary:** View field definitions and types
- **Support:** support@batchdata.com
- **Sales:** sales@batchdata.com

### Pipeline Documentation

- `Batchdata/README.md` - BatchData module overview
- `Batchdata/docs/BATCHDATA.md` - Detailed implementation guide
- `BATCHDATA_API_DOCUMENTATION.md` - Complete scraped API docs (auto-generated)

### Code References

- `src/adhs_etl/batchdata_bridge.py` - Integration layer
- `Batchdata/src/batchdata.py` - API client
- `Batchdata/src/transform.py` - Data transformation
- `Batchdata/src/run.py` - Pipeline orchestration

---

## Changelog

### 2025-11-17
- Fixed 404 error: Updated to V1 API endpoints
- Fixed endpoint format: `property/skip-trace/async` (not `property-skip-trace-async`)
- Fixed phone endpoints: Use forward slashes, not hyphens
- Created comprehensive V1 API reference guide

### 2025-01-17
- Updated all documentation to V1 API
- Confirmed V1 is correct for wallet credit accounts
- Fixed all phone endpoint paths to use slashes

---

## Quick Reference Card

```bash
# Environment Setup
export BD_SKIPTRACE_KEY="your-key"
export BD_PHONE_KEY="your-key"

# Base URL (V1 - for wallet credits)
https://api.batchdata.com/api/v1

# Key Endpoints
POST /property/skip-trace/async    # Skip-trace (async)
POST /property/skip-trace           # Skip-trace (sync)
POST /phone/verification            # Phone validation
POST /phone/dnc                     # DNC check
POST /phone/tcpa                    # TCPA check

# Pipeline Commands
poetry run python scripts/process_months_local.py  # Full pipeline
cd Batchdata && python3 src/run.py --dry-run      # Test BatchData

# Cost Estimates
Skip-trace: $0.07/property
Phone verify: $0.007/phone
DNC/TCPA: $0.002/phone each
```

---

**End of Guide** | Questions? → support@batchdata.com
