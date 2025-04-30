#!/usr/bin/env python3

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
from typing import List, Set, Tuple
import sys
import os
import datetime

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
    
    def extract_logged_in_email(self, soup) -> str:
        # For temp-mail.org, the email is in <input id="mail" value="...">
        mail_input = soup.find('input', {'id': 'mail'})
        if mail_input and mail_input.has_attr('value'):
            return mail_input['value']
        return None

    def log_email(self, email: str, log_file: str):
        now = datetime.datetime.now().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"{now}\t{email}\n")

    def get_recent_emails(self, log_file: str, days: int = 3):
        recent_emails = set()
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        if not os.path.exists(log_file):
            return recent_emails
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    timestamp, email = line.strip().split('\t')
                    dt = datetime.datetime.fromisoformat(timestamp)
                    if dt >= cutoff:
                        recent_emails.add(email)
                except Exception:
                    continue
        return recent_emails

    def scrape_emails(self, url: str, log_file: str) -> tuple:
        content = self.get_page_content(url)
        if not content:
            return set(), set(), None
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        all_emails = self.extract_emails(text)
        valid_emails = {email for email in all_emails if self.is_valid_email(email)}
        invalid_emails = all_emails - valid_emails
        logged_in_email = self.extract_logged_in_email(soup)
        if logged_in_email:
            self.log_email(logged_in_email, log_file)
        return valid_emails, invalid_emails, logged_in_email

def main():
    parser = argparse.ArgumentParser(description='Web Email Scraper and Validator')
    parser.add_argument('url', help='URL to scrape for emails')
    parser.add_argument('--output', '-o', help='Output file for results')
    args = parser.parse_args()
    
    scraper = EmailScraper()
    log_file = 'email_history.log'
    valid_emails, invalid_emails, logged_in_email = scraper.scrape_emails(args.url, log_file)
    
    # Prepare output
    output = []
    output.append(f"URL: {args.url}")
    output.append("")
    output.append("Logged-in Email:")
    if logged_in_email:
        validity = "Valid" if scraper.is_valid_email(logged_in_email) else "Invalid"
        output.append(f"  {logged_in_email} ({validity})")
    else:
        output.append("  Not found")
    output.append("")
    output.append("Emails used in the last 3 days:")
    recent_emails = scraper.get_recent_emails(log_file, days=3)
    if recent_emails:
        for email in sorted(recent_emails):
            validity = "Valid" if scraper.is_valid_email(email) else "Invalid"
            output.append(f"  {email} ({validity})")
    else:
        output.append("  None found")
    output.append("")
    output.append("Valid Emails:")
    for email in sorted(valid_emails):
        output.append(f"  {email}")
    output.append("")
    output.append("Invalid Emails:")
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
