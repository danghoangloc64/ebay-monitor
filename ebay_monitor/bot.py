import json
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from scraper import scrape_item, close_browser

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CONFIG_FILE = 'config.txt'
STATE_FILE = 'state.json'
CHECK_INTERVAL = 150        # seconds between each check
SOLD_THRESHOLD = 10         # alert if sold count in 24h window exceeds this
RESET_HOUR = 21             # 9 PM — window resets and alert fires

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
    return now.hour == RESET_HOUR and now.minute < (CHECK_INTERVAL // 60 + 1)

# ── Alert messages ────────────────────────────────────────────────────────────

def build_change_alert(data: dict, changes: list[str]) -> str:
    lines = [
        f'🔔 <b>{data["title"]}</b>',
        '',
        '\n'.join(changes),
        '',
        f'💰 Giá: <b>{data.get("price") or "N/A"}</b>',
        f'🔗 <a href="{data["url"]}">Xem trên eBay</a>',
    ]
    return '\n'.join(lines)

def build_snapshot(data: dict) -> str:
    status = '❌ Hết hàng' if data.get('sold_out') else '✅ Còn hàng'
    lines = [
        f'🛒 <b>{data["title"]}</b>',
        '',
        f'💰 Giá: <b>{data.get("price") or "N/A"}</b>',
        f'📦 Trạng thái: {status}',
        f'📊 Đã bán: <b>{data.get("sold_count") or "N/A"}</b>',
        '',
        f'🔗 <a href="{data["url"]}">Xem trên eBay</a>',
    ]
    return '\n'.join(lines)

def build_sold_alert(data: dict, sold_in_window: int) -> str:
    lines = [
        f'🔥 <b>{data["title"]}</b>',
        '',
        f'� Đã bán <b>{sold_in_window}</b> lượt trong 24h qua!',
        '',
        f'� Giá: <b>{data.get("price") or "N/A"}</b>',
        f'🔗 <a href="{data["url"]}">Xem trên eBay</a>',
    ]
    return '\n'.join(lines)

# ── Main check ────────────────────────────────────────────────────────────────

def check_items(first_run: bool = False):
    urls = load_config()
    state = load_state()
    window = current_window_date()
    reset_now = is_reset_time()

    for url in urls:
        print(f'[monitor] Checking {url}')
        data = scrape_item(url)
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
        state[url] = entry

    save_state(state)

def main():
    print(f'[monitor] Starting — interval {CHECK_INTERVAL}s, sold alert at {RESET_HOUR}:00')
    send_message(f'🤖 <b>eBay Monitor đã khởi động!</b>')

    try:
        check_items(first_run=False)

        while True:
            print(f'[monitor] Sleeping {CHECK_INTERVAL}s...')
            time.sleep(CHECK_INTERVAL)
            check_items()
    finally:
        close_browser()

if __name__ == '__main__':
    main()
