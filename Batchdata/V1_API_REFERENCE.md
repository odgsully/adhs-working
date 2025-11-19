# BatchData V1 API Reference

**Version**: 1.0
**Last Updated**: 2025-01-17
**Status**: Official V1 API Documentation

---

## Base URL

```
https://api.batchdata.com/api/v1
```

**Authentication**: Bearer token in Authorization header
**Format**: `Authorization: Bearer YOUR_API_KEY`

---

## Complete V1 Endpoint List

### Property Skip-Trace Operations

| Method | Endpoint | Type | Description | Cost |
|--------|----------|------|-------------|------|
| POST | `/api/v1/property/skip-trace` | Sync | Immediate skip-trace results | $0.07/record |
| POST | `/api/v1/property/skip-trace/async` | Async | Batch skip-trace with job ID | $0.07/record |

### Phone Operations

| Method | Endpoint | Type | Description | Cost |
|--------|----------|------|-------------|------|
| POST | `/api/v1/phone/verification` | Sync | Verify phone numbers | $0.007/phone |
| POST | `/api/v1/phone/verification/async` | Async | Batch phone verification | $0.007/phone |
| POST | `/api/v1/phone/dnc` | Sync | Check DNC status | $0.002/phone |
| POST | `/api/v1/phone/dnc/async` | Async | Batch DNC check | $0.002/phone |
| POST | `/api/v1/phone/tcpa` | Sync | Check TCPA litigator status | $0.002/phone |
| POST | `/api/v1/phone/tcpa/async` | Async | Batch TCPA check | $0.002/phone |

### Address Operations

| Method | Endpoint | Type | Description | Cost |
|--------|----------|------|-------------|------|
| POST | `/api/v1/address/verify` | Sync | Verify and normalize addresses | $0.01/address |

### Property Data Operations

| Method | Endpoint | Type | Description | Cost |
|--------|----------|------|-------------|------|
| POST | `/api/v1/property/search/async` | Async | Search property records | Variable |
| POST | `/api/v1/property/lookup/async` | Async | Lookup property details | Variable |

### Job Management

| Method | Endpoint | Type | Description | Cost |
|--------|----------|------|-------------|------|
| GET | `/api/v1/jobs/{job_id}` | Sync | Check job status | Free |
| GET | `/api/v1/jobs/{job_id}/download` | Sync | Download job results | Free |

---

## Request/Response Formats

### Property Skip-Trace (Sync)

**Endpoint**: `POST /api/v1/property/skip-trace`

**Request:**
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
  ]
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
    "data": [
      {
        "input": {
          "requestId": "unique_123"
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

### Property Skip-Trace (Async)

**Endpoint**: `POST /api/v1/property/skip-trace/async`

**Request:**
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

### Phone Verification (Async)

**Endpoint**: `POST /api/v1/phone/verification/async`

**Request:**
```json
{
  "requests": [
    "2024561111"
  ],
  "options": {
    "webhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf",
    "errorWebhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf"
  }
}
```

**Response:**
```json
{
  "status": {
    "text": "Forbidden",
    "message": "Insufficient balance or invalid token permission",
    "code": 403
  }
}
```

### Phone DNC Check (Async)

**Endpoint**: `POST /api/v1/phone/dnc/async`

**Request:**
```json
{
  "requests": [
    "2024561111"
  ],
  "options": {
    "webhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf",
    "errorWebhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf"
  }
}
```

**Response:**
```json
{
  "status": {
    "text": "Forbidden",
    "message": "Insufficient balance or invalid token permission",
    "code": 403
  }
}
```

### Phone TCPA Check (Async)

**Endpoint**: `POST /api/v1/phone/tcpa/async`

**Request:**
```json
{
  "requests": [
    "6027828092"
  ],
  "options": {
    "webhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf",
    "errorWebhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf"
  }
}
```

**Response:**
```json
{
  "status": {
    "text": "Forbidden",
    "message": "Insufficient balance or invalid token permission",
    "code": 403
  }
}
```

### Address Verification

**Endpoint**: `POST /api/v1/address/verify`

**Request:**
```json
{
  "requests": [
    {
      "street": "2800 N 24th St",
      "city": "Phoenix",
      "state": "Arizona",
      "zip": "85008",
      "requestId": ""
    }
  ]
}
```

**Response Example:**
```json
{
  "status": {
    "text": "Forbidden",
    "message": "Insufficient balance or invalid token permission",
    "code": 403
  }
}
```

### Property Search (Async)

**Endpoint**: `POST /api/v1/property/search/async`

**Request:**
```json
{
  "searchCriteria": {
    "query": "Phoenix, AZ",
    "completeness": {
      "street": "41028 N Congressional Dr",
      "city": "Phoenix",
      "state": "AZ",
      "zip": "85086"
    }
  },
  "options": {
    "quickList": true,
    "skip": 0,
    "take": 100,
    "webhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf",
    "errorWebhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf"
  }
}
```

### Property Lookup (Async)

**Endpoint**: `POST /api/v1/property/lookup/async`

**Request:**
```json
{
  "requests": [
    {
      "address": {
        "street": "101 Portsmouth Cir",
        "city": "Victoria",
        "state": "TX",
        "zip": "77904-2301"
      }
    }
  ],
  "options": {
    "webhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf",
    "errorWebhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ca-9c91645659bf"
  }
}
```

---

## Webhook Requirements for Async Endpoints

All async endpoints require webhook configuration in the `options` object:

```json
{
  "options": {
    "webhookUrl": "https://your-webhook.com/success",
    "errorWebhookUrl": "https://your-webhook.com/error"
  }
}
```

**Important Notes:**
- `webhookUrl` is REQUIRED for async endpoints
- `errorWebhookUrl` is optional but recommended
- Webhook must be publicly accessible
- Webhook should return 200 status to acknowledge receipt
- Results are delivered as POST request to webhook

---

## Job Management

### Check Job Status

**Endpoint**: `GET /api/v1/jobs/{job_id}`

**Response:**
```json
{
  "status": {
    "code": 200,
    "text": "OK"
  },
  "result": {
    "jobId": "job_abc123def456",
    "status": "completed",
    "progress": 100,
    "recordsProcessed": 500,
    "recordsMatched": 473,
    "completedAt": "2025-01-17T12:34:56Z"
  }
}
```

### Download Job Results

**Endpoint**: `GET /api/v1/jobs/{job_id}/download`

Returns the complete results in the format specified when job was created (JSON or CSV).

---

## Error Responses

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request format or missing required fields |
| 401 | Unauthorized | Invalid or missing API key |
| 403 | Forbidden | Insufficient balance or invalid token permission |
| 404 | Not Found | Endpoint not found (check URL format) |
| 405 | Method Not Allowed | Wrong HTTP method |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
  "status": {
    "code": 403,
    "text": "Forbidden",
    "message": "Insufficient balance or invalid token permission",
    "data": []
  }
}
```

---

## Rate Limits

| Endpoint Type | Rate Limit | Batch Size |
|---------------|------------|------------|
| Sync endpoints | 100 req/min | Max 100 records/request |
| Async endpoints | 10 req/min | Max 10,000 records/request |
| Job status | 60 req/min | N/A |

**Best Practices:**
- Use async endpoints for batches > 100 records
- Implement exponential backoff on 429 errors
- Cache job results to avoid repeated downloads
- Use webhooks instead of polling for async jobs

---

## Cost Summary

### Skip-Trace Services
- Property Skip-Trace: **$0.07** per record with results

### Phone Services
- Phone Verification: **$0.007** per phone number
- Phone DNC Check: **$0.002** per phone number
- Phone TCPA Check: **$0.002** per phone number

### Address Services
- Address Verification: **$0.01** per address

### Property Data
- Property Search: Variable based on results
- Property Lookup: Variable based on results

**Billing Notes:**
- Only charged for records with results
- No charge for job management endpoints
- Wallet credits deducted immediately
- Failed requests not charged

---

## Testing Endpoints

### Test Script

```python
#!/usr/bin/env python3
import os
import requests

API_KEY = os.getenv('BD_SKIPTRACE_KEY')
BASE_URL = "https://api.batchdata.com/api/v1"

def test_sync_endpoint():
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
            }
        }]
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_sync_endpoint()
```

### cURL Examples

**Property Skip-Trace (Sync):**
```bash
curl -X POST "https://api.batchdata.com/api/v1/property/skip-trace" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"requests":[{"requestId":"test","propertyAddress":{"street":"123 Main St","city":"Phoenix","state":"AZ","zip":"85001"}}]}'
```

**Phone Verification (Sync):**
```bash
curl -X POST "https://api.batchdata.com/api/v1/phone/verification" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phones":["555-123-4567"]}'
```

---

## Common Mistakes to Avoid

### ❌ WRONG Endpoint Formats
```
/property-skip-trace         # Hyphens instead of slashes
/phone-verification-async     # Hyphens instead of slashes
/v1/property/skip-trace      # Missing /api prefix
/api/property/skip-trace     # Missing version
```

### ✅ CORRECT Endpoint Formats
```
/api/v1/property/skip-trace
/api/v1/phone/verification/async
/api/v1/phone/dnc/async
/api/v1/phone/tcpa/async
```

### Common Issues and Solutions

1. **404 Not Found**
   - Check endpoint path uses slashes, not hyphens
   - Verify `/api/v1` prefix is included
   - Ensure HTTP method is correct (POST vs GET)

2. **403 Forbidden**
   - Verify API key has wallet credits
   - Check API key has permission for endpoint
   - Ensure Bearer token format is correct

3. **400 Bad Request**
   - Async endpoints require `webhookUrl` in options
   - Check request JSON is properly formatted
   - Verify all required fields are present

4. **429 Too Many Requests**
   - Implement rate limiting in your code
   - Use async endpoints for large batches
   - Add exponential backoff retry logic

---

## Support

**API Issues:**
- Email: support@batchdata.com
- Documentation: https://developer.batchdata.com/docs

**Integration Support:**
- Check this reference first
- Test with minimal example
- Include request/response in support tickets

---

**Document Version**: 1.0
**Last Updated**: 2025-01-17
**Maintained By**: ADHS ETL Pipeline Team