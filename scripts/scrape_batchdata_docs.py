#!/usr/bin/env python3
"""
Scrape BatchData API Documentation using Playwright
Comprehensive documentation scraper for API reference
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

# Documentation pages to scrape
DOC_PAGES = [
    "https://developer.batchdata.com/docs/batchdata/welcome-to-batchdata",
    "https://developer.batchdata.com/docs/batchdata/authentication",
    "https://developer.batchdata.com/docs/batchdata/property-skip-trace",
    "https://developer.batchdata.com/docs/batchdata/property-skip-trace-async",
    "https://developer.batchdata.com/docs/batchdata/phone-verification",
    "https://developer.batchdata.com/docs/batchdata/phone-dnc",
    "https://developer.batchdata.com/docs/batchdata/phone-tcpa",
    "https://developer.batchdata.com/docs/batchdata/address-verification",
    "https://developer.batchdata.com/docs/batchdata/property-search",
    "https://developer.batchdata.com/docs/batchdata/api-reference",
    "https://developer.batchdata.com/docs/batchdata/errors",
    "https://developer.batchdata.com/docs/batchdata/rate-limits",
]

async def scrape_page(page, url):
    """Scrape a single documentation page."""
    print(f"📄 Scraping: {url}")

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)  # Wait for dynamic content

        # Extract page title
        title = await page.title()

        # Extract main content - try multiple selectors
        content_selectors = [
            "article",
            "[role='main']",
            ".sl-elements-article",
            "main",
            ".markdown-body",
            "#content"
        ]

        content_html = None
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content_html = await element.inner_html()
                    break
            except:
                continue

        if not content_html:
            # Fallback: get body content
            content_html = await page.inner_html("body")

        # Extract text content
        content_text = await page.evaluate("""
            () => {
                // Remove script and style tags
                const scripts = document.querySelectorAll('script, style');
                scripts.forEach(s => s.remove());

                // Try to get main content area
                const selectors = ['article', '[role="main"]', 'main', '.sl-elements-article'];
                for (const selector of selectors) {
                    const elem = document.querySelector(selector);
                    if (elem) {
                        return elem.innerText;
                    }
                }
                return document.body.innerText;
            }
        """)

        # Extract code examples
        code_blocks = await page.evaluate("""
            () => {
                const blocks = [];
                document.querySelectorAll('pre code, .code-block, pre').forEach(block => {
                    blocks.push({
                        language: block.className.match(/language-(\\w+)/)?.[1] || 'text',
                        code: block.innerText || block.textContent
                    });
                });
                return blocks;
            }
        """)

        # Extract navigation/sidebar links
        nav_links = await page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('nav a, .sidebar a, [role="navigation"] a').forEach(link => {
                    links.push({
                        text: link.innerText.trim(),
                        href: link.href
                    });
                });
                return links;
            }
        """)

        return {
            "url": url,
            "title": title,
            "content_text": content_text,
            "content_html": content_html,
            "code_blocks": code_blocks,
            "nav_links": nav_links,
            "scraped_at": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return {
            "url": url,
            "error": str(e),
            "scraped_at": datetime.now().isoformat()
        }

async def discover_additional_pages(page):
    """Discover additional documentation pages from the navigation."""
    print("🔍 Discovering documentation structure...")

    try:
        await page.goto(DOC_PAGES[0], wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # Extract all documentation links
        doc_links = await page.evaluate("""
            () => {
                const links = new Set();
                document.querySelectorAll('a').forEach(link => {
                    const href = link.href;
                    if (href && href.includes('developer.batchdata.com/docs')) {
                        links.add(href);
                    }
                });
                return Array.from(links);
            }
        """)

        print(f"📚 Found {len(doc_links)} documentation pages")
        return doc_links

    except Exception as e:
        print(f"❌ Error discovering pages: {e}")
        return []

def convert_to_markdown(scraped_data):
    """Convert scraped data to comprehensive markdown documentation."""

    md = f"""# BatchData API Documentation

**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source:** https://developer.batchdata.com/

---

"""

    # Group pages by category
    sections = {}
    for page_data in scraped_data:
        if "error" in page_data:
            continue

        title = page_data.get("title", "Untitled")
        content = page_data.get("content_text", "")
        url = page_data.get("url", "")

        # Categorize
        if "authentication" in url.lower():
            category = "Authentication"
        elif "skip-trace" in url.lower():
            category = "Skip-Trace API"
        elif "phone" in url.lower():
            category = "Phone APIs"
        elif "address" in url.lower():
            category = "Address API"
        elif "property" in url.lower() and "skip" not in url.lower():
            category = "Property API"
        elif "error" in url.lower():
            category = "Error Handling"
        elif "rate" in url.lower():
            category = "Rate Limits"
        else:
            category = "General"

        if category not in sections:
            sections[category] = []

        sections[category].append(page_data)

    # Write sections
    section_order = [
        "General",
        "Authentication",
        "Skip-Trace API",
        "Phone APIs",
        "Address API",
        "Property API",
        "Error Handling",
        "Rate Limits"
    ]

    for section_name in section_order:
        if section_name not in sections:
            continue

        md += f"\n## {section_name}\n\n"

        for page_data in sections[section_name]:
            title = page_data.get("title", "Untitled")
            url = page_data.get("url", "")
            content = page_data.get("content_text", "").strip()
            code_blocks = page_data.get("code_blocks", [])

            md += f"### {title}\n\n"
            md += f"**URL:** {url}\n\n"

            if content:
                # Clean up content
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 1:  # Skip empty and single-char lines
                        cleaned_lines.append(line)

                md += '\n'.join(cleaned_lines) + "\n\n"

            # Add code examples
            if code_blocks:
                md += "#### Code Examples\n\n"
                for i, block in enumerate(code_blocks):
                    lang = block.get('language', 'text')
                    code = block.get('code', '').strip()
                    if code and len(code) > 10:  # Skip tiny/empty blocks
                        md += f"```{lang}\n{code}\n```\n\n"

            md += "---\n\n"

    return md

async def main():
    """Main scraping orchestration."""
    print("🚀 Starting BatchData Documentation Scraper")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch browser
        print("🌐 Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # Discover all pages
        all_pages = await discover_additional_pages(page)

        # Merge with predefined pages
        pages_to_scrape = list(set(DOC_PAGES + all_pages))
        print(f"📋 Total pages to scrape: {len(pages_to_scrape)}")

        # Scrape all pages
        scraped_data = []
        for i, url in enumerate(pages_to_scrape, 1):
            print(f"[{i}/{len(pages_to_scrape)}] ", end="")
            data = await scrape_page(page, url)
            scraped_data.append(data)
            await asyncio.sleep(1)  # Be nice to the server

        await browser.close()

    # Save raw data
    raw_output = Path("Batchdata/batchdata_docs_raw.json")
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_output, 'w') as f:
        json.dump(scraped_data, f, indent=2)
    print(f"\n✅ Raw data saved: {raw_output}")

    # Convert to markdown
    markdown_doc = convert_to_markdown(scraped_data)

    # Save markdown
    md_output = Path("Batchdata/BATCHDATA_API_DOCUMENTATION.md")
    with open(md_output, 'w') as f:
        f.write(markdown_doc)
    print(f"✅ Markdown documentation saved: {md_output}")

    # Print summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING COMPLETE")
    print("=" * 60)
    print(f"Pages scraped: {len([d for d in scraped_data if 'error' not in d])}")
    print(f"Errors: {len([d for d in scraped_data if 'error' in d])}")
    print(f"Documentation size: {len(markdown_doc):,} characters")
    print("\n📁 Output files:")
    print(f"  • {raw_output}")
    print(f"  • {md_output}")

if __name__ == "__main__":
    asyncio.run(main())
