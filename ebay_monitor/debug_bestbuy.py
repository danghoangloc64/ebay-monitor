# -*- coding: utf-8 -*-
"""
Debug BestBuy scraper - save HTML and screenshot
"""
from bestbuy_scraper import BestBuyScraper
import time


def debug_bestbuy():
    """Debug BestBuy page structure"""
    
    test_url = "https://www.bestbuy.com/site/apple-airpods-pro-2nd-generation-with-magsafe-case-usbc-white/6447382.p"
    
    print("Starting debug session...")
    scraper = BestBuyScraper()
    
    try:
        if not scraper.start_browser():
            print("Failed to start browser")
            return
        
        print(f"Opening URL: {test_url}")
        page = scraper.context.new_page()
        
        try:
            page.goto(test_url, wait_until='domcontentloaded', timeout=60000)
            print("Page loaded, waiting 10 seconds...")
            time.sleep(10)
            
            # Save screenshot
            screenshot_path = "bestbuy_debug.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved: {screenshot_path}")
            
            # Save HTML
            html_path = "bestbuy_debug.html"
            html = page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"HTML saved: {html_path}")
            
            # Try to find title with different selectors
            print("\n--- Testing selectors ---")
            
            selectors = [
                'h1',
                'h1.heading-5',
                '[data-testid="product-title"]',
                '.sku-title',
                '.heading-5',
                'h1[class*="heading"]',
            ]
            
            for selector in selectors:
                try:
                    count = page.locator(selector).count()
                    print(f"\n{selector}: found {count} elements")
                    if count > 0:
                        for i in range(min(count, 3)):
                            text = page.locator(selector).nth(i).inner_text()
                            print(f"  [{i}]: {text[:100]}")
                except Exception as e:
                    print(f"{selector}: error - {e}")
            
            # Try to find price
            print("\n--- Testing price selectors ---")
            price_selectors = [
                '[data-testid="customer-price"]',
                '.priceView-customer-price',
                '.priceView-hero-price',
                '[class*="price"]',
                'span[aria-hidden="true"]',
            ]
            
            for selector in price_selectors:
                try:
                    count = page.locator(selector).count()
                    print(f"\n{selector}: found {count} elements")
                    if count > 0:
                        for i in range(min(count, 3)):
                            text = page.locator(selector).nth(i).inner_text()
                            print(f"  [{i}]: {text[:100]}")
                except Exception as e:
                    print(f"{selector}: error - {e}")
            
            # Try to find add to cart button
            print("\n--- Testing button selectors ---")
            button_selectors = [
                'button:has-text("Add to Cart")',
                '[data-testid="add-to-cart-button"]',
                'button[class*="add-to-cart"]',
                'button',
            ]
            
            for selector in button_selectors:
                try:
                    count = page.locator(selector).count()
                    print(f"\n{selector}: found {count} elements")
                    if count > 0 and count < 10:
                        for i in range(min(count, 5)):
                            text = page.locator(selector).nth(i).inner_text()
                            visible = page.locator(selector).nth(i).is_visible()
                            print(f"  [{i}] visible={visible}: {text[:50]}")
                except Exception as e:
                    print(f"{selector}: error - {e}")
            
            print("\n--- Debug complete ---")
            print(f"Check {screenshot_path} and {html_path} for details")
            
        finally:
            page.close()
    
    finally:
        scraper.close_browser()


if __name__ == '__main__':
    debug_bestbuy()
