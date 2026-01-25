#!/usr/bin/env python3
"""
Run the NCAAB H1 scraper to collect full season data.
This will take 15-20 hours to complete.
"""

from ncaab_h1_scraper import NCAAB_H1_Scraper

if __name__ == "__main__":
    scraper = NCAAB_H1_Scraper()
    scraper.run()
