# BatchData API v1 Endpoints Documentation

> Complete documentation for BatchData v1 API endpoints used in the ADHS ETL pipeline

## Overview

This directory contains comprehensive documentation for each BatchData v1 API endpoint used in the contact enrichment pipeline. These endpoints enable skip tracing, phone validation, and compliance checking for property owner contact discovery.

## Endpoints

### Core Contact Discovery

| Endpoint | Cost | Description |
|----------|------|-------------|
| [property-skip-trace-async](property-skip-trace-async.md) | $0.07/record | Core contact discovery - phones, emails for property owners |

### Phone Compliance

| Endpoint | Cost | Description |
|----------|------|-------------|
| [phone-verification-async](phone-verification-async.md) | $0.007/phone | Validate phone numbers, check line type, carrier |
| [phone-dnc-async](phone-dnc-async.md) | $0.002/phone | Do-Not-Call registry compliance check |
| [phone-tcpa-async](phone-tcpa-async.md) | $0.002/phone | TCPA litigation risk screening |

### Address & Property

| Endpoint | Cost | Description |
|----------|------|-------------|
| [address-verify](address-verify.md) | Varies | Address standardization and geocoding (sync) |
| [property-search-async](property-search-async.md) | Varies | Search for properties by criteria |
| [property-lookup-async](property-lookup-async.md) | Varies | Get detailed property information |

## Pipeline Integration

The standard contact enrichment pipeline flows through these endpoints in sequence:

```
                    ┌─────────────────────┐
                    │   Address Verify    │ (Optional)
                    │  Standardize input  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Property Skip Trace │
                    │  Discover contacts  │
                    │   $0.07/record      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Phone Verification  │
                    │  Validate phones    │
                    │  $0.007/phone       │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼─────────┐  ┌───▼───┐   ┌───────▼───────┐
    │    Phone DNC      │  │ AND   │   │  Phone TCPA   │
    │  Registry check   │  │       │   │ Litigation    │
    │  $0.002/phone     │  │       │   │ $0.002/phone  │
    └─────────┬─────────┘  │       │   └───────┬───────┘
              │            │       │           │
              └────────────┼───────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Clean Contact List  │
                │ Ready for outreach   │
                └─────────────────────┘
```

## Cost Summary

### Per-Record Costs (Typical Pipeline)

| Stage | Cost | Notes |
|-------|------|-------|
| Skip Trace | $0.07 | Per matched property |
| Phone Verification | ~$0.03 | ~4-5 phones per record @ $0.007 |
| DNC Check | ~$0.01 | ~4-5 phones per record @ $0.002 |
| TCPA Check | ~$0.01 | ~4-5 phones per record @ $0.002 |
| **Total** | **~$0.12** | Per input record |

## Async Pattern

All async endpoints follow the same pattern:

1. **Submit Request** → Receive immediate `200 OK` acknowledgment
2. **Wait for Webhook** → Results posted to your `webhookUrl`
3. **Process Results** → Parse webhook payload

### Webhook Configuration

```json
{
  "options": {
    "webhookUrl": "https://your-server.com/batchdata/results",
    "errorWebhookUrl": "https://your-server.com/batchdata/errors"
  }
}
```

## Authentication

All endpoints require API key authentication:

```http
Authorization: Bearer [40 digit API token]
Content-Type: application/json
Accept: application/json, application/xml
```

Configure in `.env`:
```bash
BD_PROPERTY_KEY=your-key-here
BD_ADDRESS_KEY=your-key-here
BD_PHONE_KEY=your-key-here
```

## API Key Permissions

Each API key must have specific permissions enabled in the BatchData dashboard. The table below shows which permission is required for each endpoint:

### Endpoint-to-Permission Mapping

| Endpoint | API Key | Required Permission |
|----------|---------|---------------------|
| `POST /api/v1/property/skip-trace` | `BD_PROPERTY_KEY` | `property-skip-trace` |
| `POST /api/v1/property/skip-trace/async` | `BD_PROPERTY_KEY` | `property-skip-trace-async` |
| `POST /api/v1/property/lookup` | `BD_PROPERTY_KEY` | `property-lookup-all-attributes` |
| `POST /api/v1/property/lookup/async` | `BD_PROPERTY_KEY` | `property-lookup-async` |
| `POST /api/v1/property/search` | `BD_PROPERTY_KEY` | `property-search` |
| `POST /api/v1/property/search/async` | `BD_PROPERTY_KEY` | `property-search-async` |
| `POST /api/v1/address/geocode` | `BD_ADDRESS_KEY` | `address-geocode` |
| `POST /api/v1/address/reverse-geocode` | `BD_ADDRESS_KEY` | `address-reverse-geocode` |
| `POST /api/v1/address/verify` | `BD_ADDRESS_KEY` | `address-verify` |
| `POST /api/v1/address/autocomplete` | `BD_ADDRESS_KEY` | `address-autocomplete` |
| `POST /api/v1/phone/verification` | `BD_PHONE_KEY` | `phone-verification` |
| `POST /api/v1/phone/verification/async` | `BD_PHONE_KEY` | `phone-verification-async` |
| `POST /api/v1/phone/dnc` | `BD_PHONE_KEY` | `phone-dnc` |
| `POST /api/v1/phone/dnc/async` | `BD_PHONE_KEY` | `phone-dnc-async` |
| `POST /api/v1/phone/tcpa` | `BD_PHONE_KEY` | `phone-tcpa` |
| `POST /api/v1/phone/tcpa/async` | `BD_PHONE_KEY` | `phone-tcpa-async` |

### Permission Summary by Key

| API Key | Permissions to Enable |
|---------|----------------------|
| `BD_PROPERTY_KEY` | `property-skip-trace`, `property-skip-trace-async`, `property-lookup-all-attributes`, `property-search`, `property-search-async`, `property-lookup-async` |
| `BD_ADDRESS_KEY` | `address-geocode`, `address-reverse-geocode`, `address-verify`, `address-autocomplete` |
| `BD_PHONE_KEY` | `phone-dnc`, `phone-tcpa`, `phone-verification`, `phone-verification-async`, `phone-dnc-async`, `phone-tcpa-async` |

## Best Practices

### Request Management

1. **Batch Size**: Up to 5,000 records per async request
2. **Request IDs**: Always set `requestId` to correlate results
3. **Deduplication**: Remove duplicates before submission
4. **Validation**: Verify addresses before skip tracing

### Compliance

1. **Always Check**: Run all phones through DNC + TCPA
2. **Zero Tolerance**: Block all serial TCPA litigators
3. **Document Everything**: Maintain audit trail
4. **Regular Updates**: Re-check contacts every 30 days

### Performance

1. **Parallel Processing**: Run DNC and TCPA checks in parallel
2. **Webhook Security**: Use HTTPS and validate payloads
3. **Retry Logic**: Implement exponential backoff
4. **Caching**: Cache verification results (valid 30-90 days)

## Error Handling

All endpoints return errors in consistent format:

```json
{
  "status": {
    "code": 400,
    "text": "Bad Request",
    "message": "Detailed error description"
  }
}
```

### Common Error Codes

| Code | Description | Action |
|------|-------------|--------|
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Verify API key |
| 429 | Rate Limited | Implement backoff |
| 500 | Server Error | Retry request |

## Additional Resources

- **BatchData Developer Portal**: https://developer.batchdata.com
- **v1 API Reference**: https://developer.batchdata.com/docs/batchdata/batchdata-v1
- **Rate Limits**: https://developer.batchdata.com/docs/batchdata/rate-limits

## File Inventory

```
Batchdata/endpoints/
├── README.md                      # This file
├── property-skip-trace-async.md   # Core contact discovery
├── phone-verification-async.md    # Phone validation
├── phone-dnc-async.md             # DNC registry check
├── phone-tcpa-async.md            # TCPA litigation check
├── address-verify.md              # Address standardization
├── property-search-async.md       # Property search
├── property-lookup-async.md       # Property details
└── v1_endpoints_scraped.json      # Raw scraped v1 API data
```

## Version

- **API Version**: v1
- **Documentation Date**: November 2025
- **Source**: BatchData Developer Portal v1 API specifications

---

*For integration with ADHS ETL pipeline, see [../docs/BATCHDATA.md](../docs/BATCHDATA.md)*
