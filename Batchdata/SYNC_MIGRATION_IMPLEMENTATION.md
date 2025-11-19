# BatchData V1 API Implementation Guide

**Document Version**: 1.0 (Clean V1 Implementation)
**Created**: 2025-01-17
**Status**: Active Implementation
**API Version**: V1 (Wallet Credits Compatible)

---

## Executive Summary

This guide documents the BatchData V1 API integration for the ADHS ETL pipeline. The V1 API is the correct endpoint for wallet credit accounts and supports both synchronous and asynchronous processing patterns.

### Complete V1 Endpoint List

#### Property Skip-Trace
- **Sync**: `POST https://api.batchdata.com/api/v1/property/skip-trace`
- **Async**: `POST https://api.batchdata.com/api/v1/property/skip-trace/async`

#### Phone Operations
- **Verification Sync**: `POST https://api.batchdata.com/api/v1/phone/verification`
- **Verification Async**: `POST https://api.batchdata.com/api/v1/phone/verification/async`
- **DNC Sync**: `POST https://api.batchdata.com/api/v1/phone/dnc`
- **DNC Async**: `POST https://api.batchdata.com/api/v1/phone/dnc/async`
- **TCPA Sync**: `POST https://api.batchdata.com/api/v1/phone/tcpa`
- **TCPA Async**: `POST https://api.batchdata.com/api/v1/phone/tcpa/async`

#### Address Operations
- **Address Verify**: `POST https://api.batchdata.com/api/v1/address/verify`

#### Property Data
- **Property Search**: `POST https://api.batchdata.com/api/v1/property/search/async`
- **Property Lookup**: `POST https://api.batchdata.com/api/v1/property/lookup/async`

#### Job Management
- **Job Status**: `GET https://api.batchdata.com/api/v1/jobs/{job_id}`
- **Job Download**: `GET https://api.batchdata.com/api/v1/jobs/{job_id}/download`

**Note**: For complete API reference with request/response formats, see `V1_API_REFERENCE.md`

---

## Current Configuration

### API Settings
```yaml
Base URL: https://api.batchdata.com/api/v1
Authentication: Bearer token (API Key)
Content-Type: application/json (sync) or multipart/form-data (async CSV)
Max Batch Size: 100 records (recommended: 50)
```

### Environment Variables
```bash
BD_SKIPTRACE_KEY=your-api-key-here  # Skip-trace service
BD_PHONE_KEY=your-api-key-here      # Phone verification (optional)
BD_ADDRESS_KEY=your-api-key-here    # Address validation (optional)
BD_PROPERTY_KEY=your-api-key-here   # Property data (optional)
```

---

## Implementation Architecture

### File Structure
```
Batchdata/
├── src/
│   ├── batchdata.py          # Async client (CSV upload + polling)
│   ├── batchdata_sync.py     # Sync client (JSON request/response)
│   ├── transform.py          # Ecorp → BatchData transformation
│   └── io.py                 # File I/O utilities
├── template_config.xlsx      # Template configuration
├── tests/
│   └── batchdata_local_input.xlsx  # Test configuration
└── Upload/                    # Input files for processing
```

### Integration Points
```
src/adhs_etl/
└── batchdata_bridge.py       # Bridge between ADHS ETL and BatchData
```

---

## API Request/Response Formats

### Sync Request (JSON)
```json
{
  "requests": [
    {
      "requestId": "ecorp_12345_1_abc123",
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
  ]
}
```

### Sync Response (JSON)
```json
{
  "status": {
    "code": 200,
    "text": "OK"
  },
  "result": {
    "data": [
      {
        "input": {
          "requestId": "ecorp_12345_1_abc123"
        },
        "persons": [
          {
            "name": {
              "first": "John",
              "last": "Doe"
            },
            "phones": [
              {
                "number": "555-123-4567",
                "type": "mobile",
                "carrier": "Verizon",
                "dnc": false,
                "tcpa": false,
                "confidence": 0.95
              }
            ],
            "emails": [
              {
                "email": "john.doe@example.com",
                "tested": true
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Async Request (CSV Upload)
```
POST /api/v1/property/skip-trace/async
Content-Type: multipart/form-data

Form fields:
- file: CSV file with columns (record_id, first_name, last_name, address, city, state, zip)
```

### Async Response (Job ID)
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

---

## Processing Workflows

### Sync Workflow (Recommended for <100 records)
```mermaid
graph LR
    A[Ecorp Complete] --> B[Transform to BatchData Format]
    B --> C[Chunk into 50-record batches]
    C --> D[POST to /property/skip-trace]
    D --> E[Parse JSON Response]
    E --> F[Convert to Wide Format]
    F --> G[BatchData Complete]
```

### Async Workflow (For large batches)
```mermaid
graph LR
    A[Ecorp Complete] --> B[Transform to CSV]
    B --> C[Upload to /property/skip-trace/async]
    C --> D[Receive Job ID]
    D --> E[Poll /jobs/{job_id}]
    E --> F{Status?}
    F -->|Processing| E
    F -->|Complete| G[Download Results]
    G --> H[Parse CSV]
    H --> I[BatchData Complete]
```

---

## Data Transformation

### Ecorp → BatchData Mapping
| Ecorp Field | BatchData Field | Notes |
|-------------|-----------------|-------|
| Entity Name | owner_name_full | Full entity name |
| Principal Name | target_first_name, target_last_name | Split name |
| Business Address | address_line1 | Street address |
| City | city | City name |
| Domicile State | state | State abbreviation (fallback) |
| Zip | zip | 5-digit ZIP |
| ECORP_INDEX_# | ecorp_index | For deduplication |

### State Field Resolution
Priority order for state field:
1. Parsed from address string
2. Domicile State column (fallback)
3. State column (if exists)
4. Empty string (last resort)

---

## Cost Optimization

### Smart Indexing with ECORP_INDEX_#
Reduce API costs by 30-40% through intelligent deduplication:

```python
# Group records by ECORP_INDEX_# + person identity
unique_persons = df.groupby(['ecorp_index', 'owner_name_full', 'address']).first()

# Process only unique persons
api_results = process_skip_trace(unique_persons)

# Copy results back to all original records
final_results = merge_results_to_duplicates(api_results, original_df)
```

### Cost Structure
| Service | Cost per Item | Typical Volume |
|---------|--------------|----------------|
| Skip-trace | $0.07 | 1× records |
| Phone verify | $0.007 | 2× records (avg 2 phones/person) |
| Phone DNC | $0.002 | 2× records |
| Phone TCPA | $0.002 | 2× records |

**Example**: 100 unique persons = $7.00 (skip-trace only)

---

## Testing & Validation

### Quick Test Script
Create `test_v1_skiptrace.py`:
```python
#!/usr/bin/env python3
import os
import requests
import json

# Configuration
API_KEY = os.getenv('BD_SKIPTRACE_KEY')
BASE_URL = "https://api.batchdata.com/api/v1"

def test_sync_endpoint():
    """Test V1 sync skip-trace endpoint"""
    url = f"{BASE_URL}/property/skip-trace"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "requests": [{
            "requestId": "test_001",
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
        }]
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("✅ V1 Sync endpoint working!")
        print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {response.text}")

    return response.status_code == 200

if __name__ == "__main__":
    if not API_KEY:
        print("Error: BD_SKIPTRACE_KEY environment variable not set")
        exit(1)

    test_sync_endpoint()
```

### Integration Test
```bash
# Test with real Ecorp data
cd Batchdata
python3 src/run.py \
    --input tests/batchdata_local_input.xlsx \
    --dry-run \
    --use-sync
```

### Validation Checklist
- [ ] API base URL is `https://api.batchdata.com/api/v1`
- [ ] Sync endpoint returns 200 status
- [ ] Async endpoint returns job ID
- [ ] State field populated in output
- [ ] Phone numbers in wide format (phone_1, phone_2, etc.)
- [ ] Record count preserved (input count = output count)
- [ ] record_id maintained through processing

---

## Troubleshooting

### Common Issues and Solutions

#### 404 Not Found Error
**Cause**: Wrong API version in configuration
**Solution**:
1. Check CONFIG sheet in input file
2. Verify `api.base_url` = `https://api.batchdata.com/api/v1`
3. Update if necessary

#### Empty State Fields
**Cause**: State not parsed from address, no fallback
**Solution**:
1. Check if Ecorp data has "Domicile State" column
2. Verify transform.py uses fallback logic
3. Add state normalization if needed

#### Authentication Failed
**Cause**: Missing or invalid API key
**Solution**:
1. Check environment variable: `echo $BD_SKIPTRACE_KEY`
2. Verify key has wallet credits
3. Test with curl:
```bash
curl -H "Authorization: Bearer $BD_SKIPTRACE_KEY" \
     https://api.batchdata.com/api/v1/property/skip-trace
```

#### Batch Size Error
**Cause**: Too many records in single request
**Solution**:
1. Limit to 100 records per request
2. Recommended: 50 records for optimal performance
3. Implement automatic chunking

---

## Current Status (2025-01-17)

### ✅ Completed
- Fixed API base URLs in all config files (V2 → V1)
- Updated template_config.xlsx
- Updated batchdata_local_input.xlsx
- Updated recent upload files
- Documented V1 API endpoints and formats

### 🔧 In Progress
- Testing V1 endpoints with real data
- Verifying state field population
- Implementing smart indexing for cost optimization

### 📋 Next Steps
1. Run test_v1_skiptrace.py to verify API access
2. Process month 10.24 with V1 endpoints
3. Implement interactive stage selection
4. Add comprehensive error handling
5. Create production deployment guide

---

## Quick Start Commands

```bash
# Set up environment
export BD_SKIPTRACE_KEY="your-api-key"

# Test V1 API
python3 Batchdata/test_v1_skiptrace.py

# Process with sync client (recommended)
cd Batchdata
python3 src/run.py --input tests/batchdata_local_input.xlsx --use-sync

# Process with async client (legacy)
python3 src/run.py --input tests/batchdata_local_input.xlsx

# Run from main ETL pipeline
cd /path/to/project
poetry run python scripts/process_months_local.py
```

---

## API Documentation References

- BatchData API Docs: See `Batchdata/BATCHDATA_API_DOCUMENTATION.md`
- V1 Endpoints confirmed by BatchData Support (2025-01-17)
- Wallet credits compatible with both sync and async patterns

---

## Contact & Support

For issues or questions:
1. Check this documentation first
2. Review error messages and logs
3. Test with minimal example
4. Contact BatchData support if API-related
5. File issue in project repository if integration-related

---

**Last Updated**: 2025-01-17
**Maintained By**: ADHS ETL Pipeline Team
**Document Status**: Active - V1 Implementation