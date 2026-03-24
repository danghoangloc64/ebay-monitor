# -*- coding: utf-8 -*-
"""
Debug a single BestBuy URL
"""
from bestbuy_scraper import BestBuyScraper
import sys


def debug_url(url: str):
    """Debug a specific URL"""
    
    print("=" * 60)
    print(f"Debugging URL: {url}")
    print("=" * 60)
    
    scraper = BestBuyScraper(headless=False)
    
    try:
        if not scraper.start_browser():
            print("Failed to start browser")
            return
        
        print(f"\nOpening URL...")
        page = scraper.context.new_page()
        
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            print("Page loaded, waiting 10 seconds...")
            import time
            time.sleep(10)
            
            # Save screenshot
            screenshot_path = "debug_url.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved: {screenshot_path}")
            
            # Check for "Add to cart" button
            print("\n--- Checking 'Add to cart' button ---")
            try:
                btn = page.locator('button:has-text("Add to cart")').first
                count = btn.count()
                print(f"Found {count} 'Add to cart' button(s)")
                if count > 0:
                    is_visible = btn.is_visible(timeout=5000)
                    is_enabled = btn.is_enabled(timeout=5000)
                    text = btn.inner_text(timeout=5000)
                    print(f"  Visible: {is_visible}")
                    print(f"  Enabled: {is_enabled}")
                    print(f"  Text: {text}")
            except Exception as e:
                print(f"  Error: {e}")
            
            # Check for "Sold Out" text
            print("\n--- Checking 'Sold Out' text ---")
            try:
                sold_out_count = page.locator('text=/sold out/i').count()
                print(f"Found {sold_out_count} 'Sold Out' text(s)")
                if sold_out_count > 0:
                    for i in range(min(sold_out_count, 5)):
                        el = page.locator('text=/sold out/i').nth(i)
                        text = el.inner_text()
                        visible = el.is_visible()
                        # Get parent element info
                        parent_text = el.locator('xpath=..').inner_text()[:100]
                        print(f"  [{i}] visible={visible}: {text}")
                        print(f"       parent: {parent_text}")
            except Exception as e:
                print(f"  Error: {e}")
            
            # Check for "Coming soon" text
            print("\n--- Checking 'Coming soon' text ---")
            try:
                coming_soon_count = page.locator('text=/coming soon/i').count()
                print(f"Found {coming_soon_count} 'Coming soon' text(s)")
            except Exception as e:
                print(f"  Error: {e}")
            
            # Check for "Unavailable" text
            print("\n--- Checking 'Unavailable' text ---")
            try:
                unavailable_count = page.locator('text=/unavailable/i').count()
                print(f"Found {unavailable_count} 'Unavailable' text(s)")
            except Exception as e:
                print(f"  Error: {e}")
            
            # Check all buttons
            print("\n--- All buttons on page ---")
            try:
                buttons = page.locator('button').all()
                print(f"Total buttons: {len(buttons)}")
                for i, btn in enumerate(buttons[:20]):  # First 20 buttons
                    try:
                        text = btn.inner_text(timeout=2000).strip()
                        visible = btn.is_visible(timeout=2000)
                        if text and visible:
                            print(f"  [{i}] visible={visible}: {text[:50]}")
                    except:
                        pass
            except Exception as e:
                print(f"  Error: {e}")
            
            # Now test the actual scraper
            print("\n--- Testing scraper result ---")
            result = scraper.scrape_item(url)
            if result:
                print(f"Title: {result.get('title')}")
                print(f"Price: {result.get('price')}")
                print(f"Sold Out: {result.get('sold_out')}")
                print(f"Reviews: {result.get('review_count')}")
            
        finally:
            page.close()
    
    finally:
        scraper.close_browser()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test URLs
        urls = [
            "https://www.bestbuy.com/product/hp-omen-16-2k-144hz-gaming-laptop-amd-ryzen-9-8940hx-2025-32gb-ddr5-memory-nvidia-geforce-rtx-5060-1tb-ssd-shadow-black/JJGH2L954G",
            "https://www.bestbuy.com/product/dell-plus-14-2k-2-in-1-touchscreen-laptop-intel-core-ultra-7-256v-2024-16gb-memory-1tb-storage-copilot-pc-ice-blue/J3K4L6XF79",
            "https://www.bestbuy.com/product/asus-vivobook-14-14-fhd-laptop-intel-core-5-120u-with-8gb-memory-256gb-ssd-quiet-blue/JJGHGPYRYX",
        ]
        print("Available test URLs:")
        for i, u in enumerate(urls, 1):
            print(f"{i}. {u}")
        
        choice = input("\nEnter number (or press Enter for first URL): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(urls):
            url = urls[int(choice) - 1]
        else:
            url = urls[0]
    
    debug_url(url)
