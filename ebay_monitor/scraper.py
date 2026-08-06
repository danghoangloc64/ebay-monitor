# -*- coding: utf-8 -*-
import re
import time
from collections.abc import Iterator
from concurrent.futures import as_completed, ThreadPoolExecutor
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, BrowserContext

_playwright = None
_browser: Browser = None
_context: BrowserContext = None

BLOCKED_RESOURCE_TYPES = {'image', 'media', 'font'}
CHROMIUM_ARGS = ['--disable-dev-shm-usage', '--disable-gpu']
BROWSER_HEADLESS = True

def get_context() -> BrowserContext:
    global _playwright, _browser, _context
    if _context is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=BROWSER_HEADLESS,
            args=CHROMIUM_ARGS,
        )
        _context = _browser.new_context(locale='en-US')
        print('[scraper] Browser started')
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
    return _scrape_item(url, get_context(), retries)

def scrape_items(urls: list[str], max_workers: int) -> Iterator[tuple[str, dict | None]]:
    """Scrape each URL in its own browser and yield results as they finish."""
    if not urls:
        return

    worker_count = min(max(1, max_workers), len(urls))

    def scrape_in_new_browser(url: str) -> tuple[str, dict | None]:
        data = None
        try:
            # Playwright's synchronous API is thread-bound. The complete
            # Playwright/browser lifecycle therefore stays inside one task.
            with sync_playwright() as playwright:
                for attempt in range(1, 4):
                    browser = None
                    context = None
                    try:
                        browser = playwright.chromium.launch(
                            headless=BROWSER_HEADLESS,
                            args=CHROMIUM_ARGS,
                        )
                        # Keep Chromium's own User-Agent. A hard-coded UA can
                        # disagree with client hints and cause eBay to return 403.
                        context = browser.new_context(locale='en-US')
                        context.route(
                            '**/*',
                            lambda route: (
                                route.abort()
                                if route.request.resource_type in BLOCKED_RESOURCE_TYPES
                                else route.continue_()
                            ),
                        )
                        print(f'[scraper] Browser started for {url} (attempt {attempt}/3)')
                        data = _scrape_once(url, context)
                    except Exception as e:
                        print(f'[scraper] Browser error for {url}: {e}')
                    finally:
                        _close_safely(context, 'context', url)
                        _close_safely(browser, 'browser', url)

                    if data and data.get('title') != 'Unknown' and data.get('price') is not None:
                        break
                    if attempt < 3:
                        print(f'[scraper] Attempt {attempt}/3 got incomplete data, retrying with a new browser...')
                        time.sleep(5)
        except Exception as e:
            print(f'[scraper] Playwright error for {url}: {e}')
        return url, data

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(scrape_in_new_browser, url) for url in urls]
        for future in as_completed(futures):
            yield future.result()

def _scrape_item(url: str, context: BrowserContext, retries: int = 3) -> dict | None:
    for attempt in range(1, retries + 1):
        result = _scrape_once(url, context)
        if result and result.get('title') != 'Unknown' and result.get('price') is not None:
            return result
        if attempt < retries:
            print(f'[scraper] Attempt {attempt}/{retries} got incomplete data, retrying...')
            time.sleep(5)
    return result

def _close_safely(resource, resource_name: str, url: str):
    if resource is None:
        return
    try:
        resource.close()
    except Exception as e:
        print(f'[scraper] Could not close {resource_name} for {url}: {e}')

def _scrape_once(url: str, context: BrowserContext) -> dict | None:
    # --- fetch HTML ---
    html = None
    try:
        page = context.new_page()
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=30000)
            if response and response.status >= 400:
                print(f'[scraper] eBay returned HTTP {response.status} for {url}')
            try:
                page.wait_for_selector(
                    'div.x-price-primary, meta[itemprop="price"], '
                    'meta[property="product:price:amount"], meta[property="og:price:amount"]',
                    timeout=10000,
                )
            except Exception:
                # Continue to parse the current HTML so retries can distinguish
                # incomplete markup from a browser-level failure.
                pass
            html = page.content()
        finally:
            page.close()
    except Exception as e:
        print(f'[scraper] Browser error for {url}: {e}')
        return None

    # --- parse HTML ---
    try:
        soup = BeautifulSoup(html, 'html.parser')

        lower_html = html.lower()
        if ('pardon our interruption' in lower_html
                or 'verify yourself to continue' in lower_html
                or '/splashui/captcha' in lower_html):
            print(f'[scraper] eBay challenge page detected for {url}')
            return None

        # Title
        title_el = (soup.find('h1', class_='x-item-title__mainTitle')
                    or soup.select_one('h1[itemprop="name"]'))
        title_meta = soup.find('meta', property='og:title')
        if title_el:
            title = title_el.get_text(' ', strip=True)
        elif title_meta and title_meta.get('content'):
            title = title_meta['content'].strip()
        else:
            title = 'Unknown'

        # Price
        price_el = soup.find('div', class_='x-price-primary')
        price_meta = (soup.find('meta', itemprop='price')
                      or soup.find('meta', property='product:price:amount')
                      or soup.find('meta', property='og:price:amount'))
        if price_el:
            price = price_el.get_text(' ', strip=True)
        elif price_meta and price_meta.get('content'):
            currency_meta = (soup.find('meta', itemprop='priceCurrency')
                             or soup.find('meta', property='product:price:currency')
                             or soup.find('meta', property='og:price:currency'))
            currency = currency_meta.get('content') if currency_meta else None
            price = f'{currency} {price_meta["content"]}'.strip() if currency else price_meta['content'].strip()
        else:
            price = None

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
