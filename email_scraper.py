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
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EmailScraper:
    def __init__(self, 
                 log_file: str = 'email_history.log',
                 timeout: int = 30,
                 max_retries: int = 3,
                 verify_ssl: bool = False,  # Make SSL verification optional
                 user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'):
        # Regular expressions for email validation
        self.email_patterns = [
            re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # Standard email
            re.compile(r'[a-zA-Z0-9._%+-]+\[at\][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # [at] format
            re.compile(r'[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # Spaces around @
            re.compile(r'[a-zA-Z0-9._%+-]+\s*\[at\]\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # Spaces around [at]
            re.compile(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'),  # mailto: links
        ]
        self.log_file = log_file
        self.timeout = timeout
        self.user_agent = user_agent
        self.verify_ssl = verify_ssl
        self.visited_urls = set()
        
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
        self.session.headers.update({'User-Agent': user_agent})
        self.session.verify = verify_ssl  # Set SSL verification
        
    def is_valid_email(self, email: str) -> bool:
        """Validate if an email follows standard format."""
        # Clean up the email first
        email = email.replace('[at]', '@').replace(' ', '')
        if email.startswith('mailto:'):
            email = email[7:]
        return bool(self.email_patterns[0].fullmatch(email))
    
    def extract_emails(self, text: str) -> Set[str]:
        """Extract all email addresses from text using multiple patterns."""
        emails = set()
        for pattern in self.email_patterns:
            matches = pattern.findall(text)
            for match in matches:
                # Handle tuple results from groups in regex
                if isinstance(match, tuple):
                    match = match[0]
                # Clean up the email
                email = match.replace('[at]', '@').replace(' ', '')
                if email.startswith('mailto:'):
                    email = email[7:]
                emails.add(email)
        return emails
    
    def get_contact_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract contact page links from the page."""
        contact_links = []
        contact_keywords = ['contact', 'about', 'support', 'help', 'customer', 'privacy', 'terms']
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text().lower()
            
            if any(keyword in href or keyword in text for keyword in contact_keywords):
                full_url = urljoin(base_url, href)
                if full_url not in self.visited_urls and urlparse(full_url).netloc == urlparse(base_url).netloc:
                    contact_links.append(full_url)
        
        return contact_links
    
    def get_page_content(self, url: str) -> Optional[str]:
        """Fetch webpage content using requests."""
        if url in self.visited_urls:
            return None
            
        self.visited_urls.add(url)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            content = response.text
            
            # Parse the content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for contact pages
            contact_links = self.get_contact_links(soup, url)
            
            # Visit contact pages
            all_content = [content]
            for link in contact_links[:3]:  # Limit to first 3 contact pages
                try:
                    response = self.session.get(link, timeout=self.timeout)
                    response.raise_for_status()
                    all_content.append(response.text)
                except Exception as e:
                    self.logger.warning(f"Error fetching contact page {link}: {str(e)}")
            
            return '\n'.join(all_content)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_logged_in_email(self, soup) -> Optional[str]:
        """Extract logged-in email from the page."""
        # Look for common patterns where logged-in email might be displayed
        selectors = [
            'input[type="email"][value]',  # Email input with value
            '.user-email',  # Common class for user email
            '#user-email',  # Common ID for user email
            '.account-email',  # Common class for account email
            '.profile-email'  # Common class for profile email
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                email = element.get('value', '') or element.get_text()
                if email and self.is_valid_email(email):
                    return email
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
        
        # Also check href attributes for mailto: links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('mailto:'):
                email = href[7:]  # Remove mailto:
                if self.is_valid_email(email):
                    all_emails.add(email)
        
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
