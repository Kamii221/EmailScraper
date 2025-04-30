# Email Scraper

A command-line tool that scrapes email addresses from websites and identifies invalid or malformed emails.

## Features

- Scrapes email addresses from any given website URL
- Validates email addresses against standard format
- Categorizes emails as valid or invalid
- Supports output to file or console
- User-friendly command-line interface

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Kamii221/EmailScraper
cd email-scraper
```

2. Make the scripts executable:
```bash
chmod +x email_scraper.sh
chmod +x email_scraper.py
```

3. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage

Basic usage:
```bash
./email_scraper.sh https://example.com
```

Save results to a file:
```bash
./email_scraper.sh -o results.txt https://example.com
```

Show help:
```bash
./email_scraper.sh --help
```

## Output Format

The tool will display:
- The URL being scraped
- A list of valid email addresses found
- A list of invalid email addresses found

## Requirements

- Python 3.x
- requests
- beautifulsoup4

## License

MIT License
