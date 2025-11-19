# Phone DNC Async

> Asynchronous endpoint for bulk Do-Not-Call registry checking with webhook delivery

## Overview

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST https://api.batchdata.com/api/v1/phone/dnc/async` |
| **Cost** | $0.002 per phone number |
| **Rate Limit** | See [BatchData API Rate Limits](https://developer.batchdata.com/docs/batchdata/rate-limits) |
| **Documentation** | https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-phone-dnc-async |

## Description

This is the asynchronous version of the Phone DNC Check API endpoint.

### Async Request Pattern

1. **Immediate Response**: HTTP response returns immediately with only a `status` object indicating the request was accepted
2. **Webhook Delivery**: Full results are delivered asynchronously to the `webhookUrl` specified in the request options
3. **Payload Format**: The webhook payload contains the complete response matching the synchronous Phone DNC Check endpoint format

**Recommended for**: Processing large batches of DNC check requests.

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
    "2024561111"
  ],
  "options": {
    "webhookUrl": "string",
    "errorWebhookUrl": "string",
    "showRequests": false
  }
}
```

### Request Parameters

#### `requests` (array of strings, required)

A list of phone numbers for which you want DNC information.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `requests` | array[string] | Yes | Array of phone numbers (10 digits, US format) |

#### `options` (object, required)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `webhookUrl` | string | Yes | URL where results will be POSTed |
| `errorWebhookUrl` | string | Yes | URL for error notifications |
| `showRequests` | boolean | No | Return original requests in response |

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

Complete DNC check results delivered to your webhook URL.

## Example Request

### cURL

```bash
curl --request POST \
  --url https://api.batchdata.com/api/v1/phone/dnc/async \
  --header 'Accept: application/json, application/xml' \
  --header 'Authorization: Bearer YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
  "requests": [
    "2024561111"
  ],
  "options": {
    "webhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ea-0c91645659bf",
    "errorWebhookUrl": "https://webhook.site/a9b12eb4-81b1-4c86-99ea-0c91645659bf"
  }
}'
```

### Python

```python
import requests

url = "https://api.batchdata.com/api/v1/phone/dnc/async"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json",
    "Accept": "application/json, application/xml"
}

payload = {
    "requests": [
        "5551234567",
        "5559876543"
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "errorWebhookUrl": "https://your-webhook.com/errors"
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
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

## Related Endpoints

- [Phone Verification Async](phone-verification-async.md) - Validate phone numbers
- [Phone TCPA Async](phone-tcpa-async.md) - TCPA litigation screening
- [Property Skip Trace Async](property-skip-trace-async.md) - Discover phone numbers
