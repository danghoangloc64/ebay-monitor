# -*- coding: utf-8 -*-
"""
Test BestBuy scraper with Omnilogin
"""
from bestbuy_scraper import BestBuyScraper
import sys


def test_bestbuy_scraper():
    """Test BestBuy scraper functionality"""
    
    # Example BestBuy URLs for testing
    test_urls = [
        "https://www.bestbuy.com/site/apple-airpods-pro-2nd-generation-with-magsafe-case-usbc-white/6447382.p",
        "https://www.bestbuy.com/site/sony-playstation-5-console/6523167.p",
    ]
    
    # Check if user wants headless mode (not recommended for BestBuy)
    headless = False
    if len(sys.argv) > 1 and sys.argv[1] == '--headless':
        headless = True
        print("WARNING: BestBuy may block headless mode!")
    
    print("=" * 60)
    print("Testing BestBuy Scraper with Omnilogin")
    print(f"Mode: {'Headless (may be blocked)' if headless else 'Visible'}")
    print("=" * 60)
    
    scraper = BestBuyScraper(headless=headless)
    
    try:
        # Start browser
        print("\n1. Starting Omnilogin browser...")
        if not scraper.start_browser():
            print("✗ Failed to start browser")
            return False
        
        print("✓ Browser started successfully")
        
        # Test scraping
        for i, url in enumerate(test_urls, 1):
            print(f"\n{i + 1}. Testing URL:")
            print(f"   {url}")
            
            result = scraper.scrape_item(url)
            
            if result:
                print(f"   ✓ Scrape successful:")
                print(f"      Title: {result.get('title')}")
                print(f"      Price: {result.get('price')}")
                print(f"      In Stock: {not result.get('sold_out')}")
                print(f"      Reviews: {result.get('review_count')}")
            else:
                print(f"   ✗ Scrape failed")
            
            # Only test first URL if you want to save time
            if len(sys.argv) > 1 and sys.argv[1] == '--quick':
                break
        
        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\nClosing browser...")
        scraper.close_browser()
        print("✓ Browser closed")


if __name__ == '__main__':
    test_bestbuy_scraper()
