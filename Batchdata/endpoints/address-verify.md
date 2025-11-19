# Address Verify

> Synchronous endpoint for address standardization and validation

## Overview

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST https://api.batchdata.com/api/v1/address/verify` |
| **Cost** | Varies by plan |
| **Rate Limit** | See [BatchData API Rate Limits](https://developer.batchdata.com/docs/batchdata/rate-limits) |
| **Documentation** | https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-address-verify |

## Description

Verify and normalize one or more addresses to conform to USPS conventions and generate a unique MD5 hash for the address.

This is a **synchronous** endpoint - results are returned immediately.

### Billing

Each requested address counts as a billable API request.

## Authentication

```http
Authorization: Bearer [40 digit API token]
Content-Type: application/json
Accept: application/json, application/xml
```

## Request Body

### Schema

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
  ],
  "options": {
    "showRequests": false
  }
}
```

### Request Parameters

#### `requests` (array of objects, required)

An array of address objects. Minimum 1 item.

| Field | Type | Required | Min Length | Description |
|-------|------|----------|------------|-------------|
| `street` | string | Yes | 1 | Street address including house number, street name, and street type. Example: "2800 N 24th St" |
| `city` | string | Yes | 1 | Address city |
| `state` | string | Yes | 1 | Address state. Can be two letter abbreviation (AZ), or full name (Arizona) |
| `zip` | string | No | 1 | US ZIP code or ZIP+4 code |
| `requestId` | string or null | No | - | Optional parameter to uniquely identify the requested address and its response |

#### `options` (object)

| Field | Type | Description |
|-------|------|-------------|
| `showRequests` | boolean | Return original request in response |

## Response

### Success Response (200 OK)

```json
{
  "status": {
    "code": 200,
    "text": "OK"
  },
  "results": {
    "addresses": [
      {
        "oldHashes": [],
        "street": "2800 N 24th St",
        "city": "Phoenix",
        "cityAlias": null,
        "state": "AZ",
        "zip": "85008",
        "zipPlus4": "1234",
        "houseNumber": "2800",
        "county": "Maricopa",
        "countyFipsCode": "04013",
        "hash": "abc123def456",
        "latitude": 33.4484,
        "longitude": -112.0740
      }
    ],
    "meta": {
      "requestCount": 1,
      "matchCount": 1
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `street` | string | Standardized street address |
| `city` | string | Standardized city name |
| `cityAlias` | string | Alternative city name |
| `state` | string | Two-letter state abbreviation |
| `zip` | string | 5-digit ZIP code |
| `zipPlus4` | string | ZIP+4 extension |
| `houseNumber` | string | House/building number |
| `county` | string | County name |
| `countyFipsCode` | string | 5-digit FIPS code |
| `hash` | string | MD5 hash of the normalized address |
| `oldHashes` | array | Previous hash values |
| `latitude` | number | Latitude coordinate |
| `longitude` | number | Longitude coordinate |

## Example Request

### cURL

```bash
curl --request POST \
  --url https://api.batchdata.com/api/v1/address/verify \
  --header 'Accept: application/json, application/xml' \
  --header 'Authorization: Bearer YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
  "requests": [
    {
      "street": "2800 N 24th St",
      "city": "Phoenix",
      "state": "Arizona",
      "zip": "85008",
      "requestId": ""
    }
  ]
}'
```

### Python

```python
import requests

url = "https://api.batchdata.com/api/v1/address/verify"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json",
    "Accept": "application/json, application/xml"
}

payload = {
    "requests": [
        {
            "street": "2800 N 24th St",
            "city": "Phoenix",
            "state": "Arizona",
            "zip": "85008",
            "requestId": "addr-001"
        }
    ],
    "options": {
        "showRequests": True
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Addresses verified |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Best Practices

1. **Validate First**: Use address verification before skip tracing to avoid wasted API calls
2. **Store Hash**: Save the address hash for future deduplication
3. **Use requestId**: Correlate responses with your internal records

## Related Endpoints

- [Property Skip Trace Async](property-skip-trace-async.md) - Uses verified addresses
- [Property Search Async](property-search-async.md) - Find properties
- [Property Lookup Async](property-lookup-async.md) - Get property details
