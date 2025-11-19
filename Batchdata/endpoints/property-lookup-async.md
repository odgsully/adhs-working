# Property Lookup Async

> Asynchronous endpoint for bulk property detail retrieval with webhook delivery

## Overview

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST https://api.batchdata.com/api/v1/property/lookup/async` |
| **Cost** | Varies by plan |
| **Rate Limit** | See [BatchData API Rate Limits](https://developer.batchdata.com/docs/batchdata/rate-limits) |
| **Documentation** | https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-property-lookup-async |

## Description

This is the asynchronous version of the Property Lookup API endpoint.

### Async Request Pattern

1. **Immediate Response**: HTTP response returns immediately with only a `status` object indicating the request was accepted
2. **Webhook Delivery**: Full property results are delivered asynchronously to the `webhookUrl` specified in the request options
3. **Payload Format**: The webhook payload contains the complete response matching the synchronous Property Lookup endpoint format

**Recommended for**: Retrieving large amounts of property records.

### Billing

- Each property record returned in the webhook payload counts as a billable API request
- `resultCount` in the meta object indicates the number of returned properties that will be billed
- Additional costs apply if the request includes contact enrichment (`"skipTrace": true`)
- `skipTraceMatchCount` indicates the number of properties with matched contact information

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
      "address": {
        "street": "string",
        "city": "string",
        "state": "string",
        "zip": "string",
        "county": "string"
      },
      "propertyId": "any",
      "hash": "string",
      "apn": "string",
      "countyFipsCode": "string",
      "requestId": "string"
    }
  ],
  "options": {
    "webhookUrl": "string",
    "errorWebhookUrl": "string",
    "skip": 0,
    "take": 25,
    "showRequests": false,
    "areaPolygon": false,
    "quicklistCounts": false,
    "useDistance": true,
    "distanceMiles": 1,
    "skipTrace": false,
    "images": false
  }
}
```

### Request Parameters

#### `requests` (array, required)

An array of property requests. Each request can use one of the following lookup methods:

##### By Property Address

Use the `address` object with:
- `street`, `city`, `state`, `zip`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `street` | string | Yes | Street address including house number, street name, type |
| `city` | string | Yes | City name |
| `state` | string | Yes | State abbreviation or full name |
| `zip` | string | No | ZIP code or ZIP+4 |

##### By Assessor Parcel Number (APN)

Use these combinations:
- `apn`, `address.state`, `address.county`
- `apn`, `address.state`, `countyFipsCode`

| Field | Type | Description |
|-------|------|-------------|
| `apn` | string | Assessor's parcel number |
| `countyFipsCode` | string | 5-digit FIPS code for the county |

##### By Property Identifier

| Field | Type | Description |
|-------|------|-------------|
| `propertyId` | any | Unique identifier for the property. **Preferred ID for lookups** |
| `hash` | string | MD5 hash of the property address |

##### Other Fields

| Field | Type | Description |
|-------|------|-------------|
| `requestId` | string | A request ID used to correlate responses with requests |

#### `options` (object)

Controls request processing and response formatting.

##### Core Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `webhookUrl` | string | - | **Required**. URL where results will be POSTed |
| `errorWebhookUrl` | string | - | URL for error notifications |
| `skip` | number | 0 | Number of records to skip (pagination) |
| `take` | number | 25 | Number of property results to return. Min: 0, Max: 500 |
| `showRequests` | boolean | false | Return original request data in response |
| `areaPolygon` | boolean | false | Include area polygon data in response |
| `quicklistCounts` | boolean | false | Return quicklist counts. Only when skip=0 and take=0 |
| `skipTrace` | boolean | false | Include contact info (phones/emails) for property owners |
| `images` | boolean | false | Include property images in response |
| `aggregateLoanTypes` | boolean | false | Return matches for aggregate loan types |

##### Comparable Properties (Comps) Options

###### Distance Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `useDistance` | boolean | true | Consider distance for comps calculation |
| `distanceMiles` | number | 1 | Max distance in miles (when useDistance=true) |
| `distanceYards` | number | - | Distance in yards |
| `distanceFeet` | number | - | Distance in feet |
| `distanceKilometers` | number | - | Distance in kilometers |
| `distanceMeters` | number | - | Distance in meters |
| `useBoundingBox` | boolean | false | Use rectangle bounding box for distance |
| `boundingBoxNw` | object | - | Northwest corner geo point |
| `boundingBoxSe` | object | - | Southeast corner geo point |

###### Bedroom Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `useBedrooms` | boolean | true | Consider bedrooms for comps |
| `minBedrooms` | number | -1 | Min bedrooms delta from subject (-1 = one less) |
| `maxBedrooms` | number | 1 | Max bedrooms delta from subject (1 = one more) |

###### Bathroom Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `useBathrooms` | boolean | false | Consider bathrooms for comps |
| `minBathrooms` | number | - | Min bathrooms delta |
| `maxBathrooms` | number | - | Max bathrooms delta |

###### Stories Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `useStories` | boolean | false | Consider stories for comps |
| `minStories` | number | - | Min stories delta |
| `maxStories` | number | - | Max stories delta |

###### Living Area Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `useArea` | boolean | true | Consider living area sqft for comps |
| `minAreaPercent` | number | -20 | Min area as delta % from subject (-20 = 20% smaller) |
| `maxAreaPercent` | number | 20 | Max area as delta % from subject (20 = 20% larger) |

###### Year Built Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `useYearBuilt` | boolean | true | Consider year built for comps |
| `minYearBuilt` | number | -10 | Min years delta (-10 = built up to 10 years earlier) |
| `maxYearBuilt` | number | 10 | Max years delta (10 = built up to 10 years later) |

###### Lot Size Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `useLotSize` | boolean | false | Consider lot size for comps |
| `minLotSizePercent` | number | - | Min lot size delta % |
| `maxLotSizePercent` | number | - | Max lot size delta % |

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

### Error Response (400 Bad Request)

```json
{
  "status": {
    "text": "Bad Request",
    "message": "Invalid Request body",
    "code": 400
  }
}
```

### Webhook Payload

The complete results are delivered to your webhook URL.

## Example Request

### cURL

```bash
curl --request POST \
  --url https://api.batchdata.com/api/v1/property/lookup/async \
  --header 'Accept: application/json, application/xml' \
  --header 'Authorization: Bearer YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
  "requests": [
    {
      "address": {
        "street": "101 Portsmouth Cir",
        "city": "Victoria",
        "state": "TX",
        "zip": "77904-2501"
      }
    }
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

url = "https://api.batchdata.com/api/v1/property/lookup/async"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json",
    "Accept": "application/json, application/xml"
}

payload = {
    "requests": [
        {
            "address": {
                "street": "101 Portsmouth Cir",
                "city": "Victoria",
                "state": "TX",
                "zip": "77904-2501"
            }
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "errorWebhookUrl": "https://your-webhook.com/errors",
        "take": 100,
        "skipTrace": False
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### With Comps Options

```python
payload = {
    "requests": [
        {
            "address": {
                "street": "123 Main St",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85001"
            }
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "take": 50,
        "useDistance": True,
        "distanceMiles": 2,
        "useBedrooms": True,
        "minBedrooms": -1,
        "maxBedrooms": 1,
        "useArea": True,
        "minAreaPercent": -25,
        "maxAreaPercent": 25,
        "useYearBuilt": True,
        "minYearBuilt": -15,
        "maxYearBuilt": 15
    }
}
```

## Use Cases

### 1. Property Lookup by Address

```python
payload = {
    "requests": [
        {
            "address": {
                "street": "101 Portsmouth Cir",
                "city": "Victoria",
                "state": "TX",
                "zip": "77904-2501"
            }
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results"
    }
}
```

### 2. Property Lookup by APN

```python
payload = {
    "requests": [
        {
            "apn": "123-45-678",
            "address": {
                "state": "AZ",
                "county": "Maricopa"
            }
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results"
    }
}
```

### 3. Property Lookup with Skip Trace

```python
payload = {
    "requests": [
        {
            "address": {
                "street": "123 Main St",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85001"
            }
        }
    ],
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "skipTrace": True  # Include owner contact info
    }
}
```

### 4. Paginated Results

```python
# First page
payload = {
    "requests": [...],
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "skip": 0,
        "take": 100
    }
}

# Second page
payload = {
    "requests": [...],
    "options": {
        "webhookUrl": "https://your-webhook.com/results",
        "skip": 100,
        "take": 100
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
| 404 | Not Found - Endpoint not found |
| 405 | Method Not Allowed |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Best Practices

1. **Use propertyId When Available**: If you have the property ID from a previous lookup, use it instead of address for faster, more accurate results
2. **Pagination**: Use `skip` and `take` for large result sets (max 500 per request)
3. **Comps Tuning**: Adjust comps options based on property type and market
4. **Skip Trace Costs**: Only enable `skipTrace` when you need contact info (additional cost)
5. **Webhook Security**: Use HTTPS endpoints and validate incoming payloads

## Related Endpoints

- [Property Search Async](property-search-async.md) - Find properties by criteria
- [Property Skip Trace Async](property-skip-trace-async.md) - Contact discovery
- [Address Verify](address-verify.md) - Validate addresses
