#!/usr/bin/env python3
"""
Scrape BatchData V1 API Documentation
Comprehensive scraper for all V1 endpoints and details
"""

import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urljoin

# Base URL for BatchData docs
BASE_DOC_URL = "https://developer.batchdata.com/docs/batchdata/batchdata-v1"

# All V1 endpoint documentation pages
ENDPOINT_PAGES = [
    # Address endpoints
    "operations/create-a-address-verify",
    "operations/create-a-address-autocomplete",
    "operations/create-a-address-geocode",
    "operations/create-a-address-reverse-geocode",

    # Property endpoints
    "operations/create-a-property-lookup",
    "operations/create-a-property-lookup-async",
    "operations/create-a-property-search",
    "operations/create-a-property-search-async",
    "operations/create-a-property-skip-trace",
    "operations/create-a-property-skip-trace-async",

    # Phone endpoints
    "operations/create-a-phone-verification",
    "operations/create-a-phone-verification-async",
    "operations/create-a-phone-dnc-status",
    "operations/create-a-phone-dnc-async",
    "operations/create-a-phone-tcpa-litigator-status",
    "operations/create-a-phone-tcpa-litigator-status-async",
]

def fetch_with_retry(url: str, max_retries: int = 3) -> requests.Response:
    """Fetch URL with retry logic"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    for attempt in range(max_retries):
        try:
            print(f"  Fetching (attempt {attempt + 1}/{max_retries})...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"  ⚠️  Error: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                raise

    raise Exception(f"Failed to fetch {url} after {max_retries} attempts")

def parse_endpoint_docs(html_content: str, endpoint_path: str) -> Dict[str, Any]:
    """Parse endpoint documentation from HTML"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract basic info
    endpoint_info = {
        'path': endpoint_path,
        'raw_html_length': len(html_content),
        'title': None,
        'method': None,
        'url': None,
        'description': None,
        'request_example': None,
        'response_example': None,
        'parameters': [],
    }

    # Try to find title
    title_tag = soup.find('h1') or soup.find('title')
    if title_tag:
        endpoint_info['title'] = title_tag.get_text(strip=True)

    # Try to find method and URL
    code_blocks = soup.find_all('code')
    for code in code_blocks:
        text = code.get_text(strip=True)
        if 'POST' in text or 'GET' in text:
            endpoint_info['method'] = 'POST' if 'POST' in text else 'GET'
        if '/api/v1/' in text:
            endpoint_info['url'] = text

    # Try to find description
    paragraphs = soup.find_all('p')
    if paragraphs and len(paragraphs) > 0:
        endpoint_info['description'] = paragraphs[0].get_text(strip=True)[:500]

    # Try to find JSON examples
    pre_blocks = soup.find_all('pre')
    json_examples = []
    for pre in pre_blocks:
        text = pre.get_text(strip=True)
        if text.startswith('{') or text.startswith('['):
            try:
                parsed = json.loads(text)
                json_examples.append(parsed)
            except json.JSONDecodeError:
                pass

    if len(json_examples) > 0:
        endpoint_info['request_example'] = json_examples[0]
    if len(json_examples) > 1:
        endpoint_info['response_example'] = json_examples[1]

    return endpoint_info

def scrape_all_endpoints() -> Dict[str, Any]:
    """Scrape all BatchData V1 endpoint documentation"""

    print("="*80)
    print("BatchData V1 API Documentation Scraper")
    print("="*80)

    all_docs = {
        'base_url': 'https://api.batchdata.com/api/v1',
        'doc_url': BASE_DOC_URL,
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'endpoints': {}
    }

    # Scrape main overview page
    print(f"\n📄 Fetching main overview page...")
    try:
        response = fetch_with_retry(BASE_DOC_URL)
        all_docs['overview'] = {
            'url': BASE_DOC_URL,
            'html_length': len(response.text),
            'status_code': response.status_code
        }
        print(f"  ✓ Fetched {len(response.text)} bytes")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Scrape each endpoint page
    print(f"\n📋 Scraping {len(ENDPOINT_PAGES)} endpoint pages...\n")

    for idx, endpoint_path in enumerate(ENDPOINT_PAGES, 1):
        endpoint_name = endpoint_path.split('/')[-1].replace('create-a-', '')
        full_url = f"{BASE_DOC_URL}/{endpoint_path}"

        print(f"[{idx}/{len(ENDPOINT_PAGES)}] {endpoint_name}")
        print(f"  URL: {full_url}")

        try:
            response = fetch_with_retry(full_url)
            endpoint_docs = parse_endpoint_docs(response.text, endpoint_path)
            endpoint_docs['full_url'] = full_url
            endpoint_docs['status_code'] = response.status_code

            all_docs['endpoints'][endpoint_name] = endpoint_docs

            print(f"  ✓ Scraped: {endpoint_docs.get('title', 'Unknown')}")
            if endpoint_docs.get('url'):
                print(f"  ✓ API URL: {endpoint_docs['url']}")

            # Be nice to the server
            time.sleep(1)

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            all_docs['endpoints'][endpoint_name] = {
                'path': endpoint_path,
                'error': str(e)
            }

    return all_docs

def main():
    """Main scraper execution"""

    # Scrape all documentation
    docs_data = scrape_all_endpoints()

    # Save to JSON file
    output_file = Path(__file__).parent.parent / 'Batchdata' / 'batchdata_docs_raw.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(docs_data, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Saved {output_file.stat().st_size:,} bytes")

    # Print summary
    print("\n" + "="*80)
    print("SCRAPING SUMMARY")
    print("="*80)
    print(f"Total endpoints scraped: {len(docs_data['endpoints'])}")

    successful = sum(1 for ep in docs_data['endpoints'].values() if 'error' not in ep)
    failed = len(docs_data['endpoints']) - successful

    print(f"✓ Successful: {successful}")
    if failed > 0:
        print(f"✗ Failed: {failed}")

    # Show endpoints with extracted URLs
    endpoints_with_urls = {
        name: ep.get('url')
        for name, ep in docs_data['endpoints'].items()
        if ep.get('url')
    }

    if endpoints_with_urls:
        print(f"\n📍 Extracted API URLs ({len(endpoints_with_urls)}):")
        for name, url in sorted(endpoints_with_urls.items()):
            print(f"  • {name}: {url}")

    print("\n" + "="*80)
    print(f"✓ Complete! Data saved to: {output_file}")
    print("="*80)

    return docs_data

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
