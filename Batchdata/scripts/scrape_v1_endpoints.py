#!/usr/bin/env python3
"""
Scrape BatchData v1 API Endpoint Documentation using Playwright
Focused scraper for complete v1 operation schemas
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

# V1 endpoint operation pages to scrape
V1_ENDPOINTS = [
    {
        "name": "property-skip-trace-async",
        "url": "https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-property-skip-trace-async"
    },
    {
        "name": "phone-verification-async",
        "url": "https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-phone-verification-async"
    },
    {
        "name": "phone-dnc-async",
        "url": "https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-phone-dnc-async"
    },
    {
        "name": "phone-tcpa-async",
        "url": "https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-phone-tcpa-async"
    },
    {
        "name": "address-verify",
        "url": "https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-address-verify"
    },
    {
        "name": "property-search-async",
        "url": "https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-property-search-async"
    },
    {
        "name": "property-lookup-async",
        "url": "https://developer.batchdata.com/docs/batchdata/batchdata-v1/operations/create-a-property-lookup-async"
    },
]

async def scrape_endpoint(page, endpoint):
    """Scrape a single v1 endpoint documentation page with comprehensive extraction."""
    name = endpoint["name"]
    url = endpoint["url"]
    print(f"📄 Scraping: {name}")
    print(f"   URL: {url}")

    try:
        # Navigate with extended timeout
        await page.goto(url, wait_until="networkidle", timeout=60000)

        # Wait for Stoplight elements to render
        await page.wait_for_timeout(5000)

        # Try to expand all collapsible sections
        try:
            await page.evaluate("""
                () => {
                    // Click all expand buttons
                    document.querySelectorAll('[aria-expanded="false"]').forEach(el => el.click());
                    document.querySelectorAll('.sl-overflow-x-hidden button').forEach(btn => btn.click());
                }
            """)
            await page.wait_for_timeout(1000)
        except:
            pass

        # Extract page title
        title = await page.title()

        # Extract main content text
        content_text = await page.evaluate("""
            () => {
                // Remove scripts and styles
                document.querySelectorAll('script, style, nav').forEach(s => s.remove());

                // Try to get main content
                const main = document.querySelector('article, [role="main"], main, .sl-elements-article');
                if (main) {
                    return main.innerText;
                }
                return document.body.innerText;
            }
        """)

        # Extract HTTP method and endpoint URL
        endpoint_info = await page.evaluate("""
            () => {
                const result = {method: '', path: ''};

                // Look for HTTP method badge
                const methodEl = document.querySelector('.sl-badge, [class*="method"]');
                if (methodEl) {
                    result.method = methodEl.innerText.trim().toUpperCase();
                }

                // Look for endpoint path
                const pathEl = document.querySelector('[class*="endpoint"], [class*="path"], .sl-text-base');
                if (pathEl) {
                    const text = pathEl.innerText;
                    if (text.includes('api.batchdata.com')) {
                        result.path = text.trim();
                    }
                }

                return result;
            }
        """)

        # Extract request schema
        request_schema = await page.evaluate("""
            () => {
                const schema = {
                    parameters: [],
                    body: {
                        contentType: 'application/json',
                        fields: []
                    }
                };

                // Look for schema property rows
                document.querySelectorAll('[class*="property"], [class*="schema"] > div').forEach(row => {
                    const nameEl = row.querySelector('[class*="name"], strong, b');
                    const typeEl = row.querySelector('[class*="type"], code, .sl-text-muted');
                    const descEl = row.querySelector('[class*="description"], p');

                    if (nameEl) {
                        schema.body.fields.push({
                            name: nameEl.innerText.trim(),
                            type: typeEl ? typeEl.innerText.trim() : 'unknown',
                            description: descEl ? descEl.innerText.trim() : '',
                            required: row.innerText.includes('required')
                        });
                    }
                });

                return schema;
            }
        """)

        # Extract code examples (requests and responses)
        code_examples = await page.evaluate("""
            () => {
                const examples = [];

                document.querySelectorAll('pre, code, .CodeMirror, [class*="code"]').forEach(block => {
                    const text = block.innerText || block.textContent;
                    if (text && text.length > 20) {
                        // Detect type
                        let type = 'unknown';
                        if (text.includes('curl')) type = 'curl';
                        else if (text.includes('"requests"') || text.includes('"options"')) type = 'request';
                        else if (text.includes('"status"') || text.includes('"result"')) type = 'response';
                        else if (text.includes('{') || text.includes('[')) type = 'json';

                        examples.push({
                            type: type,
                            code: text.trim()
                        });
                    }
                });

                return examples;
            }
        """)

        # Extract response schema
        response_schema = await page.evaluate("""
            () => {
                const schema = {
                    statusCodes: [],
                    fields: []
                };

                // Look for response status codes
                document.querySelectorAll('[class*="response"], [class*="status"]').forEach(el => {
                    const code = el.innerText.match(/\\b(200|201|400|401|403|404|429|500)\\b/);
                    if (code) {
                        schema.statusCodes.push(code[1]);
                    }
                });

                return schema;
            }
        """)

        # Get full page HTML for reference
        full_html = await page.content()

        return {
            "name": name,
            "url": url,
            "title": title,
            "endpoint": endpoint_info,
            "content_text": content_text,
            "request_schema": request_schema,
            "response_schema": response_schema,
            "code_examples": code_examples,
            "html_length": len(full_html),
            "scraped_at": datetime.now().isoformat(),
            "success": True
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "name": name,
            "url": url,
            "error": str(e),
            "scraped_at": datetime.now().isoformat(),
            "success": False
        }

async def main():
    """Main scraping orchestration for v1 endpoints."""
    print("🚀 BatchData v1 Endpoint Documentation Scraper")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch browser
        print("🌐 Launching browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-web-security']
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Enable console logging for debugging
        page.on("console", lambda msg: None)  # Suppress console logs

        # Scrape all v1 endpoints
        scraped_data = []
        for i, endpoint in enumerate(V1_ENDPOINTS, 1):
            print(f"\n[{i}/{len(V1_ENDPOINTS)}] ", end="")
            data = await scrape_endpoint(page, endpoint)
            scraped_data.append(data)

            # Brief pause between requests
            await asyncio.sleep(2)

        await browser.close()

    # Save results
    output_dir = Path(__file__).parent.parent / "endpoints"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "v1_endpoints_scraped.json"
    with open(output_file, 'w') as f:
        json.dump(scraped_data, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING COMPLETE")
    print("=" * 60)

    success_count = len([d for d in scraped_data if d.get("success")])
    error_count = len([d for d in scraped_data if not d.get("success")])

    print(f"✅ Successful: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"\n📁 Output: {output_file}")

    # Show content summary
    print("\n📋 Content Summary:")
    for data in scraped_data:
        name = data.get("name", "unknown")
        if data.get("success"):
            content_len = len(data.get("content_text", ""))
            examples = len(data.get("code_examples", []))
            print(f"   • {name}: {content_len:,} chars, {examples} code examples")
        else:
            print(f"   • {name}: ERROR - {data.get('error', 'unknown')}")

    return scraped_data

if __name__ == "__main__":
    asyncio.run(main())
