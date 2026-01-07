#!/usr/bin/env python3
"""
Scraper for Simon Willison's "Year in LLMs" blog posts.

This script fetches and extracts structured data from Simon's annual
year-in-review posts about LLMs/AI developments.

Usage:
    python scrape_year_in_llms.py 2025
    python scrape_year_in_llms.py 2026  # For when the 2026 post is published
    python scrape_year_in_llms.py --all  # Fetch all available years

Output:
    Creates JSON files with structured event data that can be used
    to update the timeline visualization.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Known URL patterns for Simon's year-in-review posts
URL_PATTERNS = {
    2023: "https://simonwillison.net/2023/Dec/31/ai-in-2023/",
    2024: "https://simonwillison.net/2024/Dec/31/llms-in-2024/",
    2025: "https://simonwillison.net/2025/Dec/31/the-year-in-llms/",
    # Future years - pattern: /YYYY/Dec/31/ with slug TBD
}

# Predict URL for future years (may need adjustment)
def get_url_for_year(year: int) -> str:
    if year in URL_PATTERNS:
        return URL_PATTERNS[year]
    # Try common patterns for future years
    possible_slugs = [
        f"https://simonwillison.net/{year}/Dec/31/the-year-in-llms/",
        f"https://simonwillison.net/{year}/Dec/31/llms-in-{year}/",
        f"https://simonwillison.net/{year}/Dec/31/ai-in-{year}/",
    ]
    return possible_slugs[0]  # Return first guess, will need manual verification


def fetch_page(url: str) -> str | None:
    """Fetch page content with error handling."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Extract all links from the article."""
    links = []
    article = soup.find('article') or soup.find('div', class_='entry-content') or soup

    for a in article.find_all('a', href=True):
        href = a['href']
        # Make relative URLs absolute
        if not href.startswith(('http://', 'https://')):
            href = urljoin(base_url, href)

        text = a.get_text(strip=True)
        if text and href:
            links.append({
                'text': text,
                'url': href
            })

    return links


def extract_headings_and_sections(soup: BeautifulSoup) -> list[dict]:
    """Extract section headings and their content."""
    sections = []
    article = soup.find('article') or soup.find('div', class_='entry-content') or soup

    for heading in article.find_all(['h2', 'h3']):
        section = {
            'title': heading.get_text(strip=True),
            'level': int(heading.name[1]),
            'content': []
        }

        # Get content until next heading
        for sibling in heading.find_next_siblings():
            if sibling.name in ['h2', 'h3']:
                break
            if sibling.name == 'p':
                section['content'].append(sibling.get_text(strip=True))

        sections.append(section)

    return sections


def categorize_content(text: str) -> list[str]:
    """Attempt to categorize content based on keywords."""
    categories = []
    text_lower = text.lower()

    # Model-related keywords
    if any(kw in text_lower for kw in ['gpt', 'claude', 'llama', 'gemini', 'mistral',
                                        'qwen', 'deepseek', 'model', 'parameter']):
        categories.append('models')

    # Tools and products
    if any(kw in text_lower for kw in ['tool', 'cli', 'api', 'code', 'app', 'plugin',
                                        'extension', 'library', 'sdk']):
        categories.append('tools')

    # Concepts and terminology
    if any(kw in text_lower for kw in ['concept', 'term', 'coined', 'definition',
                                        'paradigm', 'pattern', 'methodology']):
        categories.append('concepts')

    # Pricing and business
    if any(kw in text_lower for kw in ['$', 'price', 'cost', 'subscription',
                                        'revenue', 'million', 'billion']):
        categories.append('pricing')

    # Companies
    if any(kw in text_lower for kw in ['openai', 'anthropic', 'google', 'meta',
                                        'microsoft', 'alibaba', 'amazon']):
        categories.append('companies')

    # Research
    if any(kw in text_lower for kw in ['research', 'paper', 'study', 'benchmark',
                                        'leaderboard', 'competition', 'olympiad']):
        categories.append('research')

    return categories if categories else ['concepts']


def extract_dates(text: str, year: int) -> str | None:
    """Try to extract date references from text."""
    # Common patterns
    month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{1,2})?,?\s*(\d{4})?'
    match = re.search(month_pattern, text, re.IGNORECASE)

    if match:
        month = match.group(1)
        day = match.group(2)
        found_year = match.group(3) or str(year)
        if day:
            return f"{month} {day}, {found_year}"
        return f"{month} {found_year}"

    return str(year)


def verify_link(url: str) -> dict:
    """Verify if a link is accessible."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return {
            'url': url,
            'status': response.status_code,
            'valid': response.status_code < 400,
            'final_url': response.url if response.url != url else None
        }
    except requests.RequestException as e:
        return {
            'url': url,
            'status': None,
            'valid': False,
            'error': str(e)
        }


def scrape_year(year: int, verify_links: bool = False) -> dict | None:
    """Scrape a single year's blog post."""
    url = get_url_for_year(year)
    print(f"Fetching {year} from {url}...")

    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Extract title
    title_elem = soup.find('h1') or soup.find('title')
    title = title_elem.get_text(strip=True) if title_elem else f"Year in LLMs {year}"

    # Extract all links
    links = extract_links(soup, url)

    # Extract sections
    sections = extract_headings_and_sections(soup)

    # Build events from sections
    events = []
    for section in sections:
        if section['content']:
            content_text = ' '.join(section['content'])
            event = {
                'title': section['title'],
                'date': extract_dates(content_text, year),
                'categories': categorize_content(section['title'] + ' ' + content_text),
                'description': content_text[:300] + '...' if len(content_text) > 300 else content_text,
                'links': []
            }

            # Find links that appear in this section's content
            for link in links:
                if link['text'].lower() in content_text.lower() or link['text'] in section['title']:
                    event['links'].append(link)

            events.append(event)

    # Verify links if requested
    link_verification = []
    if verify_links:
        print(f"Verifying {len(links)} links...")
        unique_urls = list(set(link['url'] for link in links))
        for i, url in enumerate(unique_urls[:50]):  # Limit to first 50
            print(f"  Checking [{i+1}/{min(len(unique_urls), 50)}]: {url[:60]}...")
            link_verification.append(verify_link(url))

    return {
        'year': year,
        'source_url': url,
        'title': title,
        'scraped_at': datetime.now().isoformat(),
        'events': events,
        'all_links': links,
        'sections': sections,
        'link_verification': link_verification if verify_links else None
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Simon Willison's Year in LLMs blog posts"
    )
    parser.add_argument(
        'year',
        nargs='?',
        help='Year to scrape (e.g., 2025) or --all for all years'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Scrape all available years'
    )
    parser.add_argument(
        '--verify-links',
        action='store_true',
        help='Verify all extracted links are accessible'
    )
    parser.add_argument(
        '--output',
        '-o',
        default='data',
        help='Output directory for JSON files (default: data)'
    )

    args = parser.parse_args()

    # Determine which years to scrape
    if args.all:
        years = list(URL_PATTERNS.keys())
    elif args.year:
        years = [int(args.year)]
    else:
        # Default to current year
        years = [datetime.now().year]

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    results = {}
    for year in years:
        data = scrape_year(year, verify_links=args.verify_links)
        if data:
            results[year] = data

            # Save individual year file
            output_file = output_dir / f"year_in_llms_{year}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved {output_file}")

    # Save combined file
    if results:
        combined_file = output_dir / "year_in_llms_all.json"
        with open(combined_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Saved combined data to {combined_file}")

    # Print summary
    print("\n=== Summary ===")
    for year, data in results.items():
        print(f"{year}: {len(data['events'])} events, {len(data['all_links'])} links")
        if data.get('link_verification'):
            valid = sum(1 for v in data['link_verification'] if v['valid'])
            print(f"  Links verified: {valid}/{len(data['link_verification'])} valid")


if __name__ == '__main__':
    main()
