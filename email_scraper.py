#!/usr/bin/env python3

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
from typing import List, Set, Tuple, Optional, Dict
import sys
import os
import datetime
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class EmailScraper:
    def __init__(self, 
                 log_file: str = 'email_history.log',
                 timeout: int = 10,
                 max_retries: int = 3,
                 user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'):
        # Regular expression for email validation
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.log_file = log_file
        self.timeout = timeout
        self.user_agent = user_agent
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def is_valid_email(self, email: str) -> bool:
        """Validate if an email follows standard format."""
        return bool(self.email_pattern.fullmatch(email))
    
    def extract_emails(self, text: str) -> Set[str]:
        """Extract all email addresses from text."""
        return set(self.email_pattern.findall(text))
    
    def get_page_content(self, url: str) -> Optional[str]:
        """Fetch webpage content with enhanced error handling."""
        try:
            headers = {'User-Agent': self.user_agent}
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=self.timeout,
                verify=True  # SSL verification
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_logged_in_email(self, soup) -> Optional[str]:
        """Extract logged-in email from the page."""
        mail_input = soup.find('input', {'id': 'mail'})
        if mail_input and mail_input.has_attr('value'):
            return mail_input['value']
        return None

    def log_email(self, email: str):
        """Log email with timestamp."""
        now = datetime.datetime.now().isoformat()
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{now}\t{email}\n")
        except IOError as e:
            self.logger.error(f"Error writing to log file: {str(e)}")

    def get_recent_emails(self, days: int = 3) -> Set[str]:
        """Get emails from the last N days."""
        recent_emails = set()
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        
        if not os.path.exists(self.log_file):
            return recent_emails
            
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        timestamp, email = line.strip().split('\t')
                        dt = datetime.datetime.fromisoformat(timestamp)
                        if dt >= cutoff:
                            recent_emails.add(email)
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Error parsing log line: {str(e)}")
                        continue
        except IOError as e:
            self.logger.error(f"Error reading log file: {str(e)}")
            
        return recent_emails

    def scrape_emails(self, url: str) -> Tuple[Set[str], Set[str], Optional[str]]:
        """Scrape emails from the given URL."""
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
            self.log_email(logged_in_email)
            
        return valid_emails, invalid_emails, logged_in_email

def main():
    parser = argparse.ArgumentParser(description='Web Email Scraper and Validator')
    parser.add_argument('url', help='URL to scrape for emails')
    parser.add_argument('--output', '-o', help='Output file for results')
    args = parser.parse_args()
    
    scraper = EmailScraper()
    valid_emails, invalid_emails, logged_in_email = scraper.scrape_emails(args.url)
    
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
    recent_emails = scraper.get_recent_emails(days=3)
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
