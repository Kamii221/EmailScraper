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
import json
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EmailScraper:
    def __init__(self, 
                 timeout: int = 30,
                 max_retries: int = 3,
                 verify_ssl: bool = False,
                 user_agent: str = None):
        # Regular expressions for email validation
        self.email_patterns = [
            re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # Standard email
            re.compile(r'[a-zA-Z0-9._%+-]+\[at\][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # [at] format
            re.compile(r'[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # Spaces around @
            re.compile(r'[a-zA-Z0-9._%+-]+\s*\[at\]\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # Spaces around [at]
            re.compile(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'),  # mailto: links
            # Temporary email specific patterns
            re.compile(r'data-email="([^"]+)"'),  # Data attributes
            re.compile(r'email":"([^"]+)"'),  # JSON email fields
            re.compile(r'value="([^"]+@[^"]+)"'),  # Input values
            re.compile(r'id="email"[^>]*value="([^"]+)"'),  # Email input fields
            re.compile(r'class="email"[^>]*>([^<]+)<'),  # Email class elements
        ]
        
        # List of known temporary email domains
        self.temp_email_domains = {
            'temp-mail.org',
            'tempmail.com',
            'maildrop.cc',
            'emailnator.com',
            'guerrillamail.com',
            'guerrillamail.net',
            'guerrillamail.org',
            'guerrillamail.biz',
            'sharklasers.com',
            'grr.la',
            'pokemail.net',
            'spam4.me',
            'yopmail.com',
            'yopmail.net',
            'yopmail.fr',
            'cool.fr.nf',
            'jetable.fr.nf',
            'nospam.ze.tc',
            'nomail.xl.cx',
            'mega.zik.dj',
            'speed.1s.fr',
            'courriel.fr.nf',
            'moncourrier.fr.nf',
            'monemail.fr.nf',
            'monmail.fr.nf',
            'tempr.email',
            'discard.email',
            'discardmail.com',
            'discardmail.de',
            'spambog.com',
            'spambog.de',
            'spambog.ru',
            'tempail.com',
            '10minutemail.com',
            '10minutemail.net',
            '20minutemail.com',
            '30minutemail.com',
            'mailinator.com',
            'mailinator.net',
            'mailinator2.com',
            'mailinator3.com',
            'mailinator4.com',
            'mailinator5.com',
            'mailinator6.com',
            'mailinator7.com',
            'mailinator8.com',
            'mailinator9.com',
            'mailinator10.com',
            'trashmail.com',
            'trashmail.net',
            'trashmail.org',
            'trashmail.de',
            'trashmail.me',
            'wegwerfmail.de',
            'wegwerfmail.net',
            'wegwerfmail.org',
            'wegwerfemail.de',
            'wegwerfemail.net',
            'wegwerfemail.org',
            'tempmailer.com',
            'tempmailer.net',
            'tempmailer.org',
            'tempmailer.de',
            'tempmailer.me',
            'disposable.com',
            'disposemail.com',
            'dispostable.com',
            'tempemail.com',
            'tempemail.net',
            'tempemail.org',
            'temp-email.com',
            'temp-email.net',
            'temp-email.org',
            'throwawaymail.com',
            'throwawaymail.net',
            'throwawaymail.org',
            'tempmail.com',
            'tempmail.net',
            'tempmail.org',
            'tempmail.de',
            'tempmail.me',
            'burnermail.com',
            'burnermail.net',
            'burnermail.org',
            'burnermail.de',
            'burnermail.me',
            'tempinbox.com',
            'tempinbox.net',
            'tempinbox.org',
            'tempinbox.de',
            'tempinbox.me',
        }
        
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.visited_urls = set()
        self.driver = None
        
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
        
        # Set up headers with a random user agent if none provided
        if not user_agent:
            user_agent = self._get_random_user_agent()
        
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        self.session.verify = verify_ssl

    def _get_random_user_agent(self) -> str:
        """Return a random modern user agent."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
        ]
        return random.choice(user_agents)

    def _init_selenium(self):
        """Initialize Selenium with anti-bot measures."""
        if not self.driver:
            try:
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--ignore-certificate-errors')
                chrome_options.add_argument('--ignore-ssl-errors')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # Use webdriver_manager to handle driver installation
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Set CDP commands to mask automation
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": self._get_random_user_agent()
                })
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    """
                })
                
                # Set insecure certificate handling
                self.driver.execute_cdp_cmd('Security.setIgnoreCertificateErrors', {'ignore': True})
                
                self.driver.set_page_load_timeout(self.timeout)
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize Selenium: {str(e)}")
                return False
        return True

    def _close_selenium(self):
        """Close Selenium browser if it's open."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def is_valid_email(self, email: str) -> bool:
        """Validate if an email follows standard format."""
        try:
            # Clean up the email string
            email = email.strip()
            email = re.sub(r'[^\w\s@.-]', '', email)  # Remove special characters except @ . -
            email = re.sub(r'\s+', '', email)  # Remove whitespace
            
            # Basic format validation
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                return False
                
            # Length checks
            if len(email) < 5 or len(email) > 254:  # RFC 5321
                return False
                
            # Split into local and domain parts
            local, domain = email.split('@')
            
            # Local part checks
            if len(local) > 64:  # RFC 5321
                return False
            if local.startswith('.') or local.endswith('.'):
                return False
            if '..' in local:
                return False
                
            # Domain part checks
            if domain.startswith('.') or domain.endswith('.'):
                return False
            if '..' in domain:
                return False
            if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                return False
                
            return True
        except:
            return False

    def extract_emails(self, content: str) -> Tuple[Set[str], Set[str]]:
        """Extract and validate emails from content."""
        valid_emails = set()
        invalid_emails = set()
        
        # Extract potential emails using various patterns
        potential_emails = set()
        
        # Process each line to handle potential concatenated emails
        for line in content.split('\n'):
            # Clean up the line
            line = re.sub(r'[^\w\s@.-]', ' ', line)  # Replace special chars with space
            line = re.sub(r'\s+', ' ', line)  # Normalize whitespace
            
            # Look for email patterns
            for pattern in self.email_patterns:
                matches = pattern.finditer(line)
                for match in matches:
                    # Get the email from the match
                    email = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    
                    # Clean up the email
                    email = email.strip()
                    email = re.sub(r'[^\w\s@.-]', '', email)
                    email = re.sub(r'\s+', '', email)
                    
                    # Handle [at] format
                    email = email.replace('[at]', '@')
                    
                    # Remove common suffixes that might be concatenated
                    email = re.sub(r'(View|Copy|Example|Site[AB]|App[AB]|and|Why|Copied)$', '', email)
                    
                    if email:
                        potential_emails.add(email)
        
        # Validate each potential email
        for email in potential_emails:
            if self.is_valid_email(email):
                valid_emails.add(email)
            else:
                invalid_emails.add(email)
        
        return valid_emails, invalid_emails
    
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
    
    def extract_temp_mail(self, content: str) -> Optional[str]:
        """Extract temporary email from common temp mail services."""
        try:
            # Check for JSON data in the page
            json_data = re.search(r'<script[^>]*>([^<]+)</script>', content)
            if json_data:
                try:
                    data = json.loads(json_data.group(1))
                    if isinstance(data, dict) and 'email' in data:
                        return data['email']
                except json.JSONDecodeError:
                    pass

            # Check for common temp mail selectors
            selectors = [
                'input[type="email"]',
                '#email',
                '.email-address',
                '[data-email]',
                '.mailbox-email',
                '#mailbox-email',
                '.temp-email',
                '#temp-email'
            ]
            
            soup = BeautifulSoup(content, 'html.parser')
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Check value attribute
                    if element.has_attr('value'):
                        email = element['value']
                        if self.is_valid_email(email):
                            return email
                    # Check data-email attribute
                    if element.has_attr('data-email'):
                        email = element['data-email']
                        if self.attr_valid_email(email):
                            return email
                    # Check text content
                    email = element.get_text().strip()
                    if self.is_valid_email(email):
                        return email

            return None
        except Exception as e:
            self.logger.error(f"Error extracting temp mail: {str(e)}")
            return None

    def get_page_content(self, url: str) -> Optional[str]:
        """Fetch webpage content using requests or Selenium for anti-bot bypass."""
        if url in self.visited_urls:
            return None
            
        self.visited_urls.add(url)
        content = None
        
        # Check if it's a temp-mail service
        is_temp_mail = any(domain in url.lower() for domain in ['temp-mail.org', 'tempmail.com', 'maildrop.cc'])
        
        try:
            if is_temp_mail:
                # Use Selenium for temp-mail services
                if not self._init_selenium():
                    return None
                    
                self.logger.info(f"Using Selenium for {url}")
                
                # Add random delays and mouse movements to appear more human-like
                time.sleep(random.uniform(2, 4))
                
                self.driver.get(url)
                
                # Scroll the page randomly
                for _ in range(3):
                    scroll_amount = random.randint(100, 500)
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                    time.sleep(random.uniform(0.5, 1.5))
                
                # Wait for the page to load and stabilize
                time.sleep(random.uniform(3, 5))
                
                try:
                    # Try to find the email generation button and click it
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        if any(text in button.text.lower() for text in ['generate', 'create', 'new', 'random']):
                            try:
                                button.click()
                                time.sleep(2)  # Wait for email generation
                            except:
                                pass
                            break
                    
                    # Wait for email elements with different strategies
                    selectors = [
                        (By.ID, "email"),
                        (By.CLASS_NAME, "email"),
                        (By.CSS_SELECTOR, "[data-email]"),
                        (By.CSS_SELECTOR, "input[type='email']"),
                        (By.CSS_SELECTOR, "[class*='email']"),
                        (By.CSS_SELECTOR, "[id*='email']"),
                    ]
                    
                    for selector in selectors:
                        try:
                            element = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located(selector)
                            )
                            if element:
                                email = element.get_attribute("value") or element.get_attribute("data-email") or element.text
                                if email and '@' in email:
                                    # Clean and validate the email
                                    email = self.clean_email(email)
                                    if email and self.is_valid_email(email):
                                        self.logger.info(f"Found temporary email: {email}")
                                        return f"TEMP_EMAIL:{email}"
                        except:
                            continue
                            
                except TimeoutException:
                    self.logger.warning("Timeout waiting for email elements")
                
                # Get both the page source and any dynamic content
                content = self.driver.page_source
                
                # Try to extract email from JavaScript variables
                try:
                    js_email = self.driver.execute_script("""
                        return (
                            window.email || 
                            document.querySelector('[data-email]')?.dataset.email ||
                            document.querySelector('#email')?.value ||
                            document.querySelector('.email')?.textContent ||
                            Array.from(document.querySelectorAll('*')).find(el => 
                                el.textContent?.includes('@') && 
                                el.textContent?.includes('.') && 
                                el.textContent?.length < 100
                            )?.textContent
                        );
                    """)
                    if js_email:
                        # Clean and validate the email
                        email = self.clean_email(js_email)
                        if email and self.is_valid_email(email):
                            self.logger.info(f"Found temporary email from JavaScript: {email}")
                            return f"TEMP_EMAIL:{email}"
                except:
                    pass
                
            else:
                # Use requests for regular websites
                time.sleep(random.uniform(1, 3))
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 403:
                    self.logger.info("Received 403, trying with Selenium...")
                    if not self._init_selenium():
                        return None
                    self.driver.get(url)
                    content = self.driver.page_source
                else:
                    response.raise_for_status()
                    content = response.text
            
            if not content:
                return None
                
            # Parse the content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for contact pages
            contact_links = self.get_contact_links(soup, url)
            
            # Visit contact pages
            all_content = [content]
            for link in contact_links[:3]:  # Limit to first 3 contact pages
                try:
                    time.sleep(random.uniform(1, 2))
                    if is_temp_mail or self.driver:
                        self.driver.get(link)
                        all_content.append(self.driver.page_source)
                    else:
                        response = self.session.get(link, timeout=self.timeout)
                        response.raise_for_status()
                        all_content.append(response.text)
                except Exception as e:
                    self.logger.warning(f"Error fetching contact page {link}: {str(e)}")
            
            return '\n'.join(all_content)
            
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None
        finally:
            if is_temp_mail:
                self._close_selenium()

    def clean_email(self, email: str) -> str:
        """Clean and normalize an email address."""
        try:
            # Remove any non-email text before and after the email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email)
            if not email_match:
                return ""
            email = email_match.group(0)
            
            # Basic cleanup
            email = email.strip()
            email = re.sub(r'[^\w\s@.-]', '', email)  # Remove special characters except @ . -
            email = re.sub(r'\s+', '', email)  # Remove whitespace
            email = email.lower()  # Convert to lowercase
            
            # Handle [at] format
            email = email.replace('[at]', '@')
            
            # Remove common suffixes that might be concatenated
            email = re.sub(r'(view|copy|example|site[ab]|app[ab]|and|why|copied)$', '', email, flags=re.IGNORECASE)
            
            return email
        except:
            return ""

    def __del__(self):
        """Cleanup method to ensure browser is closed."""
        self._close_selenium()

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
                if email:
                    email = self.clean_email(email)
                    if email and self.is_valid_email(email):
                        return email
        return None

    def validate_email_with_feedback(self, email: str) -> Tuple[bool, List[str]]:
        """Validate email and return reasons if invalid."""
        reasons = []
        
        try:
            # Clean up the email string
            email = self.clean_email(email)
            if not email:
                reasons.append("Invalid email format")
                return False, reasons
            
            # Basic format validation
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                reasons.append("Invalid email format")
                return False, reasons
            
            # Length checks
            if len(email) < 5:
                reasons.append("Email too short (minimum 5 characters)")
            if len(email) > 254:
                reasons.append("Email too long (maximum 254 characters)")
            
            # Split into local and domain parts
            local, domain = email.split('@')
            
            # Local part checks
            if len(local) > 64:
                reasons.append("Local part too long (maximum 64 characters)")
            if local.startswith('.') or local.endswith('.'):
                reasons.append("Local part cannot start or end with a dot")
            if '..' in local:
                reasons.append("Local part cannot contain consecutive dots")
            
            # Domain part checks
            if domain.startswith('.') or domain.endswith('.'):
                reasons.append("Domain cannot start or end with a dot")
            if '..' in domain:
                reasons.append("Domain cannot contain consecutive dots")
            if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                reasons.append("Invalid domain format")
            
            # Check if it's a temporary email domain
            if domain.lower() in self.temp_email_domains:
                reasons.append("Email is from a known temporary email service")
            
            return len(reasons) == 0, reasons
        except:
            reasons.append("Failed to parse email")
            return False, reasons

    def process_url(self, url: str) -> Tuple[Optional[str], Set[str], Set[str]]:
        """Process a URL to extract emails."""
        content = self.get_page_content(url)
        if not content:
            return None, set(), set()
            
        # Parse the content
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        valid_emails = set()
        invalid_emails = set()
        
        # Extract potential emails
        potential_emails = set()
        for pattern in self.email_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                email = match.group(1) if len(match.groups()) > 0 else match.group(0)
                email = self.clean_email(email)
                if email:
                    potential_emails.add(email)
        
        # Validate each email
        for email in potential_emails:
            is_valid, reasons = self.validate_email_with_feedback(email)
            if is_valid:
                valid_emails.add(email)
            else:
                invalid_emails.add(f"{email} ({', '.join(reasons)})")
        
        # Check mailto: links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href[7:]  # Remove mailto:
                email = self.clean_email(email)
                if email:
                    is_valid, reasons = self.validate_email_with_feedback(email)
                    if is_valid:
                        valid_emails.add(email)
                    else:
                        invalid_emails.add(f"{email} ({', '.join(reasons)})")
        
        logged_in_email = self.extract_logged_in_email(soup)
        
        return logged_in_email, valid_emails, invalid_emails

def main():
    parser = argparse.ArgumentParser(description='Web Email Scraper and Validator')
    parser.add_argument('url', help='URL to scrape for emails')
    parser.add_argument('--output', '-o', help='Output file for results')
    args = parser.parse_args()
    
    scraper = EmailScraper()
    logged_in_email, valid_emails, invalid_emails = scraper.process_url(args.url)
    
    # Prepare output
    output = []
    output.append(f"URL: {args.url}")
    output.append("")
    output.append("Logged-in Email:")
    if logged_in_email:
        output.append(f"  {logged_in_email}")
    else:
        output.append("  Not found")
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
