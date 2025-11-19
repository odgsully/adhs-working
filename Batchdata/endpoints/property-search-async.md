# Property Search Async

> Asynchronous endpoint for bulk property search with webhook delivery

## Overview

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST https://api.batchdata.com/api/v1/property/search/async` |
| **Cost** | Varies by plan |
| **Rate Limit** | See [BatchData API Rate Limits](https://developer.batchdata.com/docs/batchdata/rate-limits) |
| **Documentation** | https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-property-search-async |

## Description

This is the asynchronous version of the Property Search API endpoint.

### Async Request Pattern

1. **Immediate Response**: HTTP response returns immediately with only a `status` object indicating the request was accepted
2. **Webhook Delivery**: Full results are delivered asynchronously to the `webhookUrl` specified in the request options
3. **Payload Format**: The webhook payload contains the complete response matching the synchronous Property Search endpoint format

**Recommended for**: Processing large batches of property search requests.

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
  "searchCriteria": {
    "query": "Phoenix, AZ",
    "quickList": "absentee-owner",
    "quickLists": ["absentee-owner", "high-equity"]
  },
  "options": {
    "webhookUrl": "string",
    "errorWebhookUrl": "string",
    "skip": 0,
    "take": 25
  }
}
```

### Request Parameters

#### `searchCriteria` (object, required)

An object containing property search criteria. Multiple search criteria are combined using an AND operation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Partial USPS address to limit results to a region. Example: "Phoenix, AZ" |
| `quickList` | string | No | Named query based on business rules |
| `quickLists` | array[string] | No | Array of named queries |

##### QuickList Values

Valid quickList values:
- `absentee-owner`
- `active-auction`
- `active-listing`
- `canceled-listing`
- `cash-buyer`
- `corporate-owned`
- `expired-listing`
- `failed-listing`
- `fix-and-flip`
- `free-and-clear`
- `for-sale-by-owner`
- `has-hoa`
- `has-hoa-fees`
- `high-equity`
- `inherited`
- `in-state-absentee-owner`
- `listed-below-market-price`
- `low-equity`
- `mailing-address-vacant`
- `notice-of-default`
- `notice-of-lis-pendens`
- `notice-of-sale`
- `on-market`
- `out-of-state-absentee-owner`
- `out-of-state-owner`
- `owner-occupied`
- `pending-listing`
- `preforeclosure`
- `recently-sold`
- `same-property-and-mailing-address`
- `tax-default`
- `tired-landlord`
- `unknown-equity`
- `vacant`
- `vacant-lot`

Use `not-` prefix to exclude (e.g., `not-owner-occupied`).

#### `options` (object)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `webhookUrl` | string | - | **Required**. URL where results will be POSTed |
| `errorWebhookUrl` | string | - | URL for error notifications |
| `skip` | number | 0 | Number of records to skip (pagination) |
| `take` | number | 25 | Number of results to return. Max: 500 |

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

Complete search results delivered to your webhook URL.

## Example Request

### cURL

```bash
curl --request POST \
  --url https://api.batchdata.com/api/v1/property/search/async \
  --header 'Accept: application/json, application/xml' \
  --header 'Authorization: Bearer YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
  "searchCriteria": {
    "query": "Phoenix, AZ",
    "quickList": "absentee-owner"
  },
  "options": {
    "webhookUrl": "https://webhook.site/your-webhook-id",
    "errorWebhookUrl": "https://webhook.site/your-webhook-id",
    "take": 100
  }
}'
```

### Python

```python
import requests

url = "https://api.batchdata.com/api/v1/property/search/async"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json",
    "Accept": "application/json, application/xml"
}

payload = {
    "searchCriteria": {
        "query": "Phoenix, AZ",
        "quickLists": ["absentee-owner", "high-equity"]
    },
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "errorWebhookUrl": "https://your-webhook.com/errors",
        "take": 100
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### Multiple QuickLists

```python
payload = {
    "searchCriteria": {
        "query": "Scottsdale, AZ",
        "quickLists": [
            "free-and-clear",
            "absentee-owner",
            "not-corporate-owned"
        ]
    },
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "take": 500
    }
}
```

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Request accepted |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Best Practices

1. **Be Specific**: Use query to narrow geographic area
2. **Combine QuickLists**: Use multiple quickLists for targeted searches
3. **Pagination**: Use skip and take for large result sets (max 500)
4. **Exclude with not-**: Use not- prefix to filter out results

## Related Endpoints

- [Property Lookup Async](property-lookup-async.md) - Get detailed property data
- [Property Skip Trace Async](property-skip-trace-async.md) - Contact discovery
- [Address Verify](address-verify.md) - Validate addresses
