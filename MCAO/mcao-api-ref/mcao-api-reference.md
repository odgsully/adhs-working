# Maricopa County Assessor's Office API Documentation

## Base URL
`https://mcassessor.maricopa.gov`

## Authentication

### Required Headers
- **AUTHORIZATION**: Your API token value
- **user-agent**: `null` (must be explicitly set to null)

### Getting a Token
Use the contact form on the website and select "API Question/Token" option.

## HTTP Status Codes

| Status | Description |
|--------|-------------|
| 200 | OK - Request was successful |
| 201 | Created - Request was successful and a resource was created |
| 204 | No Content - Request was successful but no representation to return |
| 400 | Bad Request - Request could not be understood or missing required parameters |
| 401 | Unauthorized - Authentication failed or insufficient permissions |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource was not found |
| 405 | Method Not Allowed - Requested method not supported for resource |

## API Endpoints

### Search Functions

#### 1. Search Property
Searches all data points available. Returns structured JSON with Real Property, BPP, MH, Rentals, Subdivisions, and Content.

**Endpoint:** `/search/property/`
- **Method:** GET
- **Parameters:**
  - `q` (required): URL encoded search query
  - `page` (optional): Page number for pagination (25 results per page)
- **Example:**
  - Basic: `https://mcassessor.maricopa.gov/search/property/?q={query}`
  - With pagination: `https://mcassessor.maricopa.gov/search/property/?q={query}&page=9`
- **Response:** JSON object containing:
  - Real Property results
  - BPP (Business Personal Property) results
  - MH (Mobile Home) results
  - Rentals
  - Subdivisions
  - Content
  - Total counts for each category

#### 2. Search Subdivisions
Searches only subdivision names.

**Endpoint:** `/search/sub/`
- **Method:** GET
- **Parameters:**
  - `q` (required): URL encoded search query
- **Example:** `https://mcassessor.maricopa.gov/search/sub/?q={query}`
- **Response:** JSON array with:
  - Subdivision names
  - Parcel counts per subdivision

#### 3. Search Rentals
Searches only rental registrations.

**Endpoint:** `/search/rental/`
- **Method:** GET
- **Parameters:**
  - `q` (required): URL encoded search query
  - `page` (optional): Page number for pagination (25 results per page)
- **Example:**
  - Basic: `https://mcassessor.maricopa.gov/search/rental/?q={query}`
  - With pagination: `https://mcassessor.maricopa.gov/search/rental/?q={query}&page=9`
- **Response:** JSON array of rental registration records

### Parcel Functions

#### 1. Parcel Details
Returns all available parcel data.

**Endpoint:** `/parcel/{apn}`
- **Method:** GET
- **Parameters:**
  - `apn` (required): Assessor Parcel Number (can be formatted with/without spaces, dashes, or dots)
- **Works with:** Residential, Commercial, Land, Agriculture parcels
- **Example:** `https://mcassessor.maricopa.gov/parcel/123-45-678`
- **Response:** Complete JSON object with all parcel information

#### 2. Property Information
Returns information specific to the property.

**Endpoint:** `/parcel/{apn}/propertyinfo`
- **Method:** GET
- **Parameters:**
  - `apn` (required): Assessor Parcel Number
- **Works with:** Residential, Commercial, Land, Agriculture parcels
- **Example:** `https://mcassessor.maricopa.gov/parcel/123-45-678/propertyinfo`
- **Response:** JSON object with property-specific details

#### 3. Property Address
Returns address of the property.

**Endpoint:** `/parcel/{apn}/address`
- **Method:** GET
- **Parameters:**
  - `apn` (required): Assessor Parcel Number
- **Works with:** Residential, Commercial, Land, Agriculture parcels
- **Example:** `https://mcassessor.maricopa.gov/parcel/123-45-678/address`
- **Response:** JSON object with property address

#### 4. Valuation Details
Returns past 5 years of valuation data.

**Endpoint:** `/parcel/{apn}/valuations`
- **Method:** GET
- **Parameters:**
  - `apn` (required): Assessor Parcel Number
- **Works with:** Residential, Commercial, Land, Agriculture parcels
- **Example:** `https://mcassessor.maricopa.gov/parcel/123-45-678/valuations`
- **Response:** JSON array with historical valuation data

#### 5. Residential Details
Returns all available residential parcel data.

**Endpoint:** `/parcel/{apn}/residential-details`
- **Method:** GET
- **Parameters:**
  - `apn` (required): Assessor Parcel Number
- **Works with:** Residential, Commercial, Land parcels (not Agriculture)
- **Example:** `https://mcassessor.maricopa.gov/parcel/123-45-678/residential-details`
- **Response:** JSON object with residential-specific information

#### 6. Owner Details
Returns owner information for the parcel.

**Endpoint:** `/parcel/{apn}/owner-details`
- **Method:** GET
- **Parameters:**
  - `apn` (required): Assessor Parcel Number
- **Works with:** Residential, Commercial, Land, Agriculture parcels
- **Example:** `https://mcassessor.maricopa.gov/parcel/123-45-678/owner-details`
- **Response:** JSON object with owner information

#### 7. MCR Search
Search by MCR (Maricopa County Recorder) number.

**Endpoint:** `/parcel/mcr/{mcr}`
- **Method:** GET
- **Parameters:**
  - `mcr` (required): MCR Number
  - `page` (optional): Page number for pagination (25 results per page)
- **Works with:** Residential, Commercial, Land, Agriculture parcels
- **Example:**
  - Basic: `https://mcassessor.maricopa.gov/parcel/mcr/123456`
  - With pagination: `https://mcassessor.maricopa.gov/parcel/mcr/123456/?page=9`
- **Response:** JSON object with parcel information

#### 8. Section/Township/Range (STR) Search
Search by Section/Township/Range.

**Endpoint:** `/parcel/str/{str}`
- **Method:** GET
- **Parameters:**
  - `str` (required): Section/Township/Range (can be formatted with dashes only)
  - `page` (optional): Page number for pagination (25 results per page)
- **Works with:** Residential, Commercial, Land, Agriculture parcels
- **Example:**
  - Basic: `https://mcassessor.maricopa.gov/parcel/str/01-02N-03E`
  - With pagination: `https://mcassessor.maricopa.gov/parcel/str/01-02N-03E/?page=9`
- **Response:** JSON array of matching parcels

### Map Functions

#### 1. Parcel Maps
Returns map file names for a parcel.

**Endpoint:** `/mapid/parcel/{apn}`
- **Method:** GET
- **Parameters:**
  - `apn` (required): Assessor Parcel Number
- **Example:** `https://mcassessor.maricopa.gov/mapid/parcel/123-45-678`
- **Response:** JSON array of map file names

#### 2. Book/Map Maps
Returns map file names for book/map combination.

**Endpoint:** `/mapid/bookmap/{book}/{map}`
- **Method:** GET
- **Parameters:**
  - `book` (required): Three digit book portion of an APN
  - `map` (required): Two digit map portion of an APN
- **Example:** `https://mcassessor.maricopa.gov/mapid/bookmap/123/45`
- **Response:** JSON array of map file names

#### 3. MCR Maps
Returns map file names for MCR number.

**Endpoint:** `/mapid/mcr/{mcr}`
- **Method:** GET
- **Parameters:**
  - `mcr` (required): MCR Number
- **Example:** `https://mcassessor.maricopa.gov/mapid/mcr/123456`
- **Response:** JSON array of map file names

### Business Personal Property (BPP) Functions

#### 1. BPP Account Details
Returns account details for commercial, multiple, or lessor accounts.

**Endpoint:** `/bpp/{type}/{acct}[/{year}]`
- **Method:** GET
- **Parameters:**
  - `type` (required): Account type character (lowercase)
    - `c` = Commercial
    - `m` = Multiple
    - `l` = Lessor
  - `acct` (required): Business personal property account number
  - `year` (optional): Four digit tax year (defaults to current year)
- **Example:**
  - Current year: `https://mcassessor.maricopa.gov/bpp/c/123456`
  - Specific year: `https://mcassessor.maricopa.gov/bpp/m/123456/2024`
- **Response:** JSON object with account details
- **Note:** Tax year parameter does not apply to commercial accounts

### Mobile Home Functions

#### 1. Mobile Home Account
Returns account details for an unsecured mobile home.

**Endpoint:** `/mh/{acct}`
- **Method:** GET
- **Parameters:**
  - `acct` (required): Mobile home account number
- **Example:** `https://mcassessor.maricopa.gov/mh/123456`
- **Response:** JSON object with mobile home account details

#### 2. Mobile Home VIN Search
Returns account number for a mobile home VIN.

**Endpoint:** `/mh/vin/{vin}`
- **Method:** GET
- **Parameters:**
  - `vin` (required): Mobile home VIN
- **Example:** `https://mcassessor.maricopa.gov/mh/vin/ABC123456789`
- **Response:** JSON object with account number

## Pagination

Most endpoints that return multiple results support pagination:
- Results are returned 25 at a time
- Add `page` parameter to access additional pages
- Example: To access results 201-225 out of 250 total, use `page=9`

## Parameter Formatting Guidelines

### APN (Assessor Parcel Number)
- Can be formatted with or without spaces, dashes, or dots
- Examples: `123-45-678`, `123 45 678`, `12345678`

### MCR (Maricopa County Recorder) Number
- Numeric format
- Example: `123456`

### Section/Township/Range (STR)
- Can be formatted with dashes only
- Example: `01-02N-03E`

### Subdivision Names
- Must be URL encoded
- Example: `Desert%20Ridge` for "Desert Ridge"

### Book/Map
- Book: Three digit format (e.g., `123`)
- Map: Two digit format (e.g., `45`)

## Implementation Examples

### cURL (PHP/Command Line)
```bash
curl -H "AUTHORIZATION: your-token-here" \
     -H "user-agent: null" \
     "https://mcassessor.maricopa.gov/parcel/123-45-678"
```

### PHP with GuzzleHTTP
```php
$client = new \GuzzleHttp\Client();
$response = $client->request('GET', 'https://mcassessor.maricopa.gov/parcel/123-45-678', [
    'headers' => [
        'AUTHORIZATION' => 'your-token-here',
        'user-agent' => 'null'
    ]
]);
```

### Node.js with Request
```javascript
const request = require('request');
const options = {
    url: 'https://mcassessor.maricopa.gov/parcel/123-45-678',
    headers: {
        'AUTHORIZATION': 'your-token-here',
        'user-agent': 'null'
    }
};
request(options, (error, response, body) => {
    // Handle response
});
```

### C#/.NET
```csharp
var request = WebRequest.Create("https://mcassessor.maricopa.gov/parcel/123-45-678");
request.Headers.Add("AUTHORIZATION", "your-token-here");
request.Headers.Add("user-agent", "null");
var response = request.GetResponse();
```

## Best Practices

1. **Always include both required headers** (AUTHORIZATION and user-agent)
2. **URL encode query parameters** when searching
3. **Handle pagination** for large result sets (>25 results)
4. **Cache responses** when appropriate to minimize API calls
5. **Check response status codes** and handle errors appropriately
6. **Format APNs consistently** in your application

## Rate Limiting

The documentation does not specify rate limits, but it's recommended to:
- Implement exponential backoff for retries
- Cache frequently accessed data
- Batch requests when possible
- Monitor for 429 (Too Many Requests) responses

## Support

For API questions or token requests:
- Use the contact form on the Maricopa County Assessor's website
- Select "API Question/Token" option

---

*Last Updated: February 1, 2024*