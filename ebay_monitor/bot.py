import json
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from scraper import scrape_item, close_browser
from bestbuy_scraper import BestBuyScraper

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CONFIG_FILE = 'config.txt'
STATE_FILE = 'state.json'
CHECK_INTERVAL_EBAY = 150        # seconds between each eBay check
CHECK_INTERVAL_BESTBUY = 3600    # seconds between each BestBuy check (1 hour)
SOLD_THRESHOLD = 10              # alert if sold count in 24h window exceeds this
RESET_HOUR = 21                  # 9 PM — window resets and alert fires

# BestBuy scraper instance (using first Omnilogin profile)
bestbuy_scraper = None

# ── Telegram ──────────────────────────────────────────────────────────────────

def send_message(text: str):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f'[telegram] Failed: {resp.text}')
    except Exception as e:
        print(f'[telegram] Error: {e}')

# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_config() -> list[str]:
    with open(CONFIG_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# ── Sold window helpers ───────────────────────────────────────────────────────

def current_window_date() -> str:
    """Returns the date string of the current 9pm→9pm window (keyed by start date)."""
    now = datetime.now()
    if now.hour >= RESET_HOUR:
        return now.strftime('%Y-%m-%d')
    else:
        from datetime import timedelta
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')

def is_reset_time() -> bool:
    """True during the CHECK_INTERVAL window right after 9 PM."""
    now = datetime.now()
    return now.hour == RESET_HOUR and now.minute < (CHECK_INTERVAL_EBAY // 60 + 1)

# ── Alert messages ────────────────────────────────────────────────────────────

def get_platform_name(url: str) -> str:
    """Get platform name from URL"""
    if 'bestbuy.com' in url.lower():
        return 'BestBuy'
    elif 'ebay.com' in url.lower():
        return 'eBay'
    return 'Unknown'

def build_change_alert(data: dict, changes: list[str]) -> str:
    platform = get_platform_name(data['url'])
    lines = [
        f'🔔 <b>{data["title"]}</b>',
        '',
        '\n'.join(changes),
        '',
        f'💰 Giá: <b>{data.get("price") or "N/A"}</b>',
        f'🔗 <a href="{data["url"]}">Xem trên {platform}</a>',
    ]
    return '\n'.join(lines)

def build_snapshot(data: dict) -> str:
    platform = get_platform_name(data['url'])
    status = '❌ Hết hàng' if data.get('sold_out') else '✅ Còn hàng'
    lines = [
        f'🛒 <b>{data["title"]}</b>',
        '',
        f'💰 Giá: <b>{data.get("price") or "N/A"}</b>',
        f'📦 Trạng thái: {status}',
    ]
    
    # Only show sold count for eBay
    if 'ebay.com' in data['url'].lower():
        lines.append(f'📊 Đã bán: <b>{data.get("sold_count") or "N/A"}</b>')
    
    lines.extend([
        '',
        f'🔗 <a href="{data["url"]}">Xem trên {platform}</a>',
    ])
    return '\n'.join(lines)

def build_sold_alert(data: dict, sold_in_window: int) -> str:
    platform = get_platform_name(data['url'])
    lines = [
        f'🔥 <b>{data["title"]}</b>',
        '',
        f'📈 Đã bán <b>{sold_in_window}</b> lượt trong 24h qua!',
        '',
        f'💰 Giá: <b>{data.get("price") or "N/A"}</b>',
        f'🔗 <a href="{data["url"]}">Xem trên {platform}</a>',
    ]
    return '\n'.join(lines)

# ── Main check ────────────────────────────────────────────────────────────────

def is_bestbuy_url(url: str) -> bool:
    """Check if URL is from BestBuy"""
    return 'bestbuy.com' in url.lower()

def is_ebay_url(url: str) -> bool:
    """Check if URL is from eBay"""
    return 'ebay.com' in url.lower()

def scrape_url(url: str) -> dict:
    """Scrape URL based on domain"""
    global bestbuy_scraper
    
    if is_bestbuy_url(url):
        # Use BestBuy scraper with Omnilogin (visible mode - BestBuy blocks headless)
        if bestbuy_scraper is None:
            bestbuy_scraper = BestBuyScraper(headless=False)
        result = bestbuy_scraper.scrape_item(url)
        return result
    elif is_ebay_url(url):
        # Close BestBuy browser before using eBay scraper to avoid Playwright conflicts
        if bestbuy_scraper is not None:
            try:
                bestbuy_scraper.close_browser()
                print("[monitor] Closed BestBuy browser before eBay scrape")
            except Exception as e:
                print(f"[monitor] Error closing BestBuy browser: {e}")
            bestbuy_scraper = None
        
        # Use eBay scraper (original flow)
        return scrape_item(url)
    else:
        print(f'[monitor] Unknown domain for {url}')
        return None

def check_items(first_run: bool = False):
    urls = load_config()
    state = load_state()
    window = current_window_date()
    reset_now = is_reset_time()
    
    # Track last check time for each URL
    now = time.time()

    for url in urls:
        # Check if enough time has passed since last check
        entry = state.get(url, {})
        last_check = entry.get('last_check_time', 0)
        
        # Determine check interval based on platform
        if is_bestbuy_url(url):
            check_interval = CHECK_INTERVAL_BESTBUY
        else:
            check_interval = CHECK_INTERVAL_EBAY
        
        # Skip if not enough time has passed
        if not first_run and (now - last_check) < check_interval:
            remaining = int(check_interval - (now - last_check))
            print(f'[monitor] Skipping {url} (check again in {remaining}s)')
            continue
        
        print(f'[monitor] Checking {url}')
        data = scrape_url(url)
        
        # Close eBay browser after each eBay scrape to avoid conflicts
        if is_ebay_url(url):
            try:
                close_browser()
            except:
                pass
        
        if data is None:
            print(f'[monitor] Could not scrape {url}, skipping')
            continue
        if data.get('title') == 'Unknown' and data.get('price') is None:
            print(f'[monitor] Incomplete data for {url}, skipping to preserve state')
            continue

        entry = state.get(url, {})

        # ── First run snapshot ────────────────────────────────────────────
        is_new = not bool(entry)
        if is_new or first_run:
            send_message(build_snapshot(data))
            print(f'[monitor] Snapshot sent for {url}')

        # ── Price / stock change detection ────────────────────────────────
        changes = []
        if entry:
            if entry.get('price') != data.get('price'):
                old_p = entry.get('price') or 'N/A'
                new_p = data.get('price') or 'N/A'
                changes.append(f'💰 <b>Giá:</b> {old_p} → {new_p}')

            if entry.get('sold_out') != data.get('sold_out'):
                if data.get('sold_out'):
                    changes.append('❌ <b>Hết hàng!</b>')
                else:
                    changes.append('✅ <b>Có hàng trở lại!</b>')

        if changes:
            send_message(build_change_alert(data, changes))
            print(f'[monitor] Change alert sent for {url}')

        # ── Sold count 24h window ─────────────────────────────────────────
        sold_now = data.get('sold_count')
        sold_data = entry.get('sold_window', {})
        prev_window = sold_data.get('window_date')
        sold_at_window_start = sold_data.get('sold_at_start')
        alerted = sold_data.get('alerted', False)

        if reset_now:
            # New window starts — record baseline and reset alert flag
            new_sold_data = {
                'window_date': window,
                'sold_at_start': sold_now,
                'alerted': False,
            }
            # Check if previous window exceeded threshold and we haven't alerted yet
            if prev_window and prev_window != window and not alerted and sold_at_window_start is not None and sold_now is not None:
                sold_in_window = sold_now - sold_at_window_start
                if sold_in_window > SOLD_THRESHOLD:
                    send_message(build_sold_alert(data, sold_in_window))
                    print(f'[monitor] Sold alert sent for {url}: {sold_in_window} sold')
                    new_sold_data['alerted'] = True
            sold_data = new_sold_data
        elif prev_window != window:
            # First time seeing this window (bot just started mid-day)
            sold_data = {
                'window_date': window,
                'sold_at_start': sold_now,
                'alerted': False,
            }

        entry.update(data)
        entry['sold_window'] = sold_data
        entry['last_check_time'] = now  # Update last check time
        state[url] = entry

    save_state(state)

def main():
    global bestbuy_scraper
    print(f'[monitor] Starting')
    print(f'  eBay check interval: {CHECK_INTERVAL_EBAY}s ({CHECK_INTERVAL_EBAY//60} minutes)')
    print(f'  BestBuy check interval: {CHECK_INTERVAL_BESTBUY}s ({CHECK_INTERVAL_BESTBUY//60} minutes)')
    print(f'  Sold alert at {RESET_HOUR}:00')
    send_message('🤖 <b>Monitor đã khởi động!</b>')

    try:
        check_items(first_run=False)

        while True:
            # Use shorter interval for main loop
            sleep_time = CHECK_INTERVAL_EBAY
            print(f'[monitor] Sleeping {sleep_time}s...')
            time.sleep(sleep_time)
            check_items()
    finally:
        close_browser()
        if bestbuy_scraper:
            bestbuy_scraper.close_browser()

if __name__ == '__main__':
    main()
