# Property Skip Trace Async

> Asynchronous endpoint for bulk contact discovery with webhook delivery

## Overview

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST https://api.batchdata.com/api/v1/property/skip-trace/async` |
| **Cost** | $0.07 per matched record |
| **Rate Limit** | See [BatchData API Rate Limits](https://developer.batchdata.com/docs/batchdata/rate-limits) |
| **Documentation** | https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-property-skip-trace-async |

## Description

This is the asynchronous version of the Property Skip Trace API endpoint. It returns contact information (emails & phone numbers) for property owners.

### Async Request Pattern

1. **Immediate Response**: HTTP response returns immediately with only a `status` object indicating the request was accepted
2. **Webhook Delivery**: Full results are delivered asynchronously to the `webhookUrl` specified in the request options
3. **Payload Format**: The webhook payload contains the complete response matching the synchronous Property Skip Trace endpoint format

**Recommended for**: Processing large batches of skip trace requests.

### V1 TCPA Filtering Behavior

By default (when `includeTCPABlacklistedPhones=false` or not specified), V1 **filters out** phone numbers with TCPA restrictions. To include TCPA-restricted phones with a `tcpa` boolean attribute for programmatic filtering, set `includeTCPABlacklistedPhones` to `true` in the request options.

### Billing

Each record returned in the webhook payload counts as a billable API request.

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
      "propertyAddress": {
        "street": "string",
        "city": "string",
        "state": "string",
        "zip": "string"
      },
      "mailingAddress": {
        "street": "string",
        "city": "string",
        "state": "string",
        "zip": "string"
      },
      "name": {
        "first": "string",
        "last": "string"
      },
      "apn": "string",
      "county": "string",
      "countyFipsCode": "string",
      "state": "string",
      "requestId": "string"
    }
  ],
  "options": {
    "webhookUrl": "string",
    "errorWebhookUrl": "string",
    "includeTCPABlacklistedPhones": false
  }
}
```

### Request Parameters

#### `requests` (array, required)

An array of skip trace requests. Owner contact information for a property can be retrieved by either passing the address or the assessor's parcel number (APN).

##### By Property Address

Use the `propertyAddress` object with one of these combinations:
- `street`, `city`, `state`, `zip`
- `street`, `zip`
- `street`, `city`, `state`

| Field | Type | Description |
|-------|------|-------------|
| `street` | string | Street address (e.g., "1011 Rosegold St") |
| `city` | string | City name |
| `state` | string | State abbreviation (e.g., "AZ") |
| `zip` | string | ZIP code (5-digit) |

##### By Assessor Parcel Number (APN)

Use these combinations:
- `apn`, `county`, `state`
- `apn`, `countyFipsCode`

| Field | Type | Description |
|-------|------|-------------|
| `apn` | string | Assessor Parcel Number |
| `county` | string | County name |
| `countyFipsCode` | string | 5-digit FIPS code |
| `state` | string | State abbreviation |

##### Additional Request Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | object | Property owner's name (`first`, `last`). By default, the API automatically determines the owner's name. You can override this to influence what contact information is returned. If the person is confirmed to be associated with the property, that person's contact information will be returned. |
| `mailingAddress` | object | Owner's mailing address |
| `requestId` | string | Custom ID to correlate responses with requests |

#### `options` (object)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `webhookUrl` | string | Yes | URL where results will be POSTed |
| `errorWebhookUrl` | string | No | URL for error notifications |
| `includeTCPABlacklistedPhones` | boolean | No | Include TCPA-restricted phones (default: false) |

## Response

### Immediate HTTP Response (200 OK)

```json
{
  "status": {
    "code": 200,
    "text": "OK"
  }
}
```

### Webhook Payload

The complete results are delivered to your webhook URL with the full contact information including phones, emails, and person details.

## Example Request

### cURL

```bash
curl --request POST \
  --url https://api.batchdata.com/api/v1/property/skip-trace/async \
  --header 'Accept: application/json, application/xml' \
  --header 'Authorization: Bearer YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
  "requests": [
    {
      "propertyAddress": {
        "street": "1011 Rosegold St",
        "city": "Franklin Square",
        "state": "NY",
        "zip": "11010"
      }
    },
    {
      "propertyAddress": {
        "street": "25866 W Globe Ave",
        "city": "Buckeye",
        "state": "AZ",
        "zip": "85326"
      }
    }
  ],
  "options": {
    "webhookUrl": "https://webhook.site/your-webhook-id",
    "errorWebhookUrl": "https://webhook.site/your-webhook-id",
    "includeTCPABlacklistedPhones": false
  }
}'
```

### Python

```python
import requests

url = "https://api.batchdata.com/api/v1/property/skip-trace/async"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json",
    "Accept": "application/json, application/xml"
}

payload = {
    "requests": [
        {
            "propertyAddress": {
                "street": "1011 Rosegold St",
                "city": "Franklin Square",
                "state": "NY",
                "zip": "11010"
            },
            "requestId": "request-001"
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "errorWebhookUrl": "https://your-webhook.com/errors",
        "includeTCPABlacklistedPhones": False
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### By APN

```python
payload = {
    "requests": [
        {
            "apn": "123-45-678",
            "county": "Maricopa",
            "state": "AZ",
            "requestId": "request-001"
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results"
    }
}
```

### With Owner Name Override

```python
payload = {
    "requests": [
        {
            "propertyAddress": {
                "street": "123 Main St",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85001"
            },
            "name": {
                "first": "John",
                "last": "Smith"
            }
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results"
    }
}
```

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Request accepted for async processing |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Access denied |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Best Practices

1. **Batch Size**: Submit up to 5,000 records per request for optimal throughput
2. **Request IDs**: Always set `requestId` to correlate results with input
3. **TCPA Compliance**: Keep `includeTCPABlacklistedPhones: false` for marketing campaigns
4. **Webhook Security**: Use HTTPS endpoints
5. **Retry Logic**: Implement exponential backoff for failed webhook deliveries

## Related Endpoints

- [Phone Verification Async](phone-verification-async.md) - Validate discovered phone numbers
- [Phone DNC Async](phone-dnc-async.md) - Check Do-Not-Call registry
- [Phone TCPA Async](phone-tcpa-async.md) - TCPA litigation screening
- [Property Lookup Async](property-lookup-async.md) - Get property details
