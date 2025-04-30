#!/usr/bin/env python3

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
from typing import List, Set, Tuple
import sys

class EmailScraper:
    def __init__(self):
        # Regular expression for email validation
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        
    def is_valid_email(self, email: str) -> bool:
        """Validate if an email follows standard format."""
        return bool(self.email_pattern.fullmatch(email))
    
    def extract_emails(self, text: str) -> Set[str]:
        """Extract all email addresses from text."""
        return set(self.email_pattern.findall(text))
    
    def get_page_content(self, url: str) -> str:
        """Fetch webpage content with error handling."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {str(e)}", file=sys.stderr)
            return ""
    
    def scrape_emails(self, url: str) -> Tuple[Set[str], Set[str]]:
        """Scrape emails from a webpage and categorize them as valid/invalid."""
        content = self.get_page_content(url)
        if not content:
            return set(), set()
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # Extract all potential emails
        all_emails = self.extract_emails(text)
        
        # Categorize emails
        valid_emails = {email for email in all_emails if self.is_valid_email(email)}
        invalid_emails = all_emails - valid_emails
        
        return valid_emails, invalid_emails

def main():
    parser = argparse.ArgumentParser(description='Web Email Scraper and Validator')
    parser.add_argument('url', help='URL to scrape for emails')
    parser.add_argument('--output', '-o', help='Output file for results')
    args = parser.parse_args()
    
    scraper = EmailScraper()
    valid_emails, invalid_emails = scraper.scrape_emails(args.url)
    
    # Prepare output
    output = []
    output.append(f"URL: {args.url}")
    output.append("\nValid Emails:")
    for email in sorted(valid_emails):
        output.append(f"  {email}")
    
    output.append("\nInvalid Emails:")
    for email in sorted(invalid_emails):
        output.append(f"  {email}")
    
    # Write to file or print to console
    if args.output:
        with open(args.output, 'w') as f:
            f.write('\n'.join(output))
        print(f"Results saved to {args.output}")
    else:
        print('\n'.join(output))

if __name__ == "__main__":
    main() 