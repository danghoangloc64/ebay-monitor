# -*- coding: utf-8 -*-
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, BrowserContext

_playwright = None
_browser: Browser = None
_context: BrowserContext = None

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

def get_context() -> BrowserContext:
    global _playwright, _browser, _context
    if _context is None:
        try:
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(headless=True)
            _context = _browser.new_context(user_agent=USER_AGENT, locale='en-US')
            print('[scraper] Browser started')
        except Exception as e:
            print(f'[scraper] Failed to start browser: {e}')
            # If there's an existing event loop, try to reuse it
            _playwright = None
            _browser = None
            _context = None
            raise
    return _context

def close_browser():
    global _playwright, _browser, _context
    try:
        if _context:
            _context.close()
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception as e:
        print(f'[scraper] close_browser warning: {e}')
    finally:
        _context = None
        _browser = None
        _playwright = None

def scrape_item(url: str, retries: int = 3) -> dict | None:
    for attempt in range(1, retries + 1):
        result = _scrape_once(url)
        if result and result.get('title') != 'Unknown' and result.get('price') is not None:
            return result
        print(f'[scraper] Attempt {attempt}/{retries} got incomplete data, retrying...')
        time.sleep(5)
    return result

def _scrape_once(url: str) -> dict | None:
    # --- fetch HTML ---
    html = None
    try:
        context = get_context()
        page = context.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            html = page.content()
        finally:
            page.close()
    except Exception as e:
        print(f'[scraper] Browser error for {url}: {e}')
        close_browser()
        return None

    # --- parse HTML ---
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Title
        title_el = soup.find('h1', class_='x-item-title__mainTitle')
        title = title_el.text.strip() if title_el else 'Unknown'

        # Price
        price_el = soup.find('div', class_='x-price-primary')
        price = price_el.text.strip() if price_el else None

        # Out of stock detection
        bin_btn    = soup.find('a', id='binBtn_btn_1') or soup.find(id='binBtn_btn')
        atc_btn    = soup.find('a', id='atcBtn_btn_1') or soup.find(id='atcBtn_btn')
        bin_action = (soup.find('div', class_='vim x-bin-action vim-flex-cta loading')
                      or soup.find('div', class_='vim x-bin-action'))
        oos_el     = soup.find('div', class_='vim x-oos-status')

        if oos_el:
            sold_out = True
        elif bin_btn or atc_btn or bin_action:
            sold_out = False
        else:
            sold_out = True

        # Sold count
        sold_count = None
        qty_section_m = re.search(
            r'x-quantity__availability.*?(?=vim vi-evo-row-gap|$)',
            html, re.IGNORECASE | re.DOTALL
        )
        search_html = qty_section_m.group(0) if qty_section_m else html

        m = re.search(
            r'ux-textspans--BOLD[^>]*ux-textspans--EMPHASIS[^>]*>([\d,]+)\s+sold'
            r'|ux-textspans--EMPHASIS[^>]*ux-textspans--BOLD[^>]*>([\d,]+)\s+sold',
            search_html, re.IGNORECASE
        )
        if m:
            sold_count = int((m.group(1) or m.group(2)).replace(',', ''))

        if sold_count is None:
            m = re.search(
                r'ux-textspans--SECONDARY[^>]*>([\d,]+)\s+sold',
                search_html, re.IGNORECASE
            )
            if m:
                sold_count = int(m.group(1).replace(',', ''))

        print(f'[scraper] title={title!r} price={price!r} sold_out={sold_out} sold_count={sold_count}')
        return {'title': title, 'price': price, 'sold_out': sold_out, 'sold_count': sold_count, 'url': url}

    except Exception as e:
        print(f'[scraper] Parse error for {url}: {e}')
        return None
