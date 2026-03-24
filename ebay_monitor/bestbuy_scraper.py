# -*- coding: utf-8 -*-
"""
BestBuy scraper using Omnilogin browser profile
"""
import re
import time
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from omnilogin_api import OmniloginAPI


class BestBuyScraper:
    """Scraper for BestBuy using Omnilogin profile"""
    
    def __init__(self, profile_id: Optional[str] = None, headless: bool = False):
        """
        Initialize BestBuy scraper
        
        Args:
            profile_id: Omnilogin profile ID (if None, will use first profile)
            headless: Run browser in headless mode (default: False, BestBuy blocks headless)
        """
        self.omni_api = OmniloginAPI()
        self.profile_id = profile_id
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # Get first profile if not specified
        if self.profile_id is None:
            self._get_first_profile()
    
    def _get_first_profile(self):
        """Get the first available profile from Omnilogin"""
        profiles_data = self.omni_api.get_profiles()
        if profiles_data and 'docs' in profiles_data:
            profiles = profiles_data['docs']
            if profiles and len(profiles) > 0:
                profile = profiles[0]
                self.profile_id = str(profile.get('id'))
                profile_name = profile.get('name', 'Unknown')
                print(f"[bestbuy] Using first profile: ID={self.profile_id}, Name={profile_name}")
            else:
                print("[bestbuy] No profiles found in Omnilogin")
        else:
            print("[bestbuy] Failed to get profiles from Omnilogin")
    
    def start_browser(self) -> bool:
        """
        Start Omnilogin browser profile
        
        Returns:
            True if successful, False otherwise
        """
        if not self.profile_id:
            print("[bestbuy] No profile ID available")
            return False
        
        mode = "headless" if self.headless else "visible"
        print(f"[bestbuy] Starting Omnilogin profile: {self.profile_id} ({mode})")
        result = self.omni_api.start(self.profile_id, headless=self.headless)
        
        if not result:
            print("[bestbuy] Failed to start Omnilogin profile")
            return False
        
        # Extract WebSocket endpoint from response
        ws_endpoint = result.get('web_socket_debugger_url')
        
        if not ws_endpoint:
            print(f"[bestbuy] No WebSocket endpoint found in response: {result}")
            return False
        
        print(f"[bestbuy] WebSocket endpoint: {ws_endpoint}")
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(ws_endpoint)
            self.context = self.browser.contexts[0] if self.browser.contexts else None
            
            if not self.context:
                print("[bestbuy] No browser context available")
                return False
            
            print("[bestbuy] Browser connected successfully")
            return True
        except Exception as e:
            print(f"[bestbuy] Browser connection error: {e}")
            self.close_browser()
            return False
    
    def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.context:
                self.context.close()
                self.context = None
        except Exception as e:
            print(f"[bestbuy] Context close warning: {e}")
        
        try:
            if self.browser:
                self.browser.close()
                self.browser = None
        except Exception as e:
            print(f"[bestbuy] Browser close warning: {e}")
        
        try:
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
        except Exception as e:
            print(f"[bestbuy] Playwright stop warning: {e}")
        
        try:
            if self.profile_id:
                self.omni_api.stop(self.profile_id)
                print(f"[bestbuy] Stopped profile: {self.profile_id}")
        except Exception as e:
            print(f"[bestbuy] Profile stop warning: {e}")
    
    def scrape_item(self, url: str, retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Scrape BestBuy item details
        
        Args:
            url: BestBuy product URL
            retries: Number of retry attempts
            
        Returns:
            Dictionary with item details or None on error
        """
        for attempt in range(1, retries + 1):
            result = self._scrape_once(url)
            if result and result.get('title') != 'Unknown' and result.get('price') is not None:
                return result
            print(f"[bestbuy] Attempt {attempt}/{retries} got incomplete data, retrying...")
            time.sleep(5)
        return result
    
    def _scrape_once(self, url: str) -> Optional[Dict[str, Any]]:
        """Single scrape attempt"""
        if not self.context:
            if not self.start_browser():
                return None
        
        page: Optional[Page] = None
        try:
            page = self.context.new_page()
            print(f"[bestbuy] Navigating to {url}")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for page to fully load - increased wait time
            print("[bestbuy] Waiting for page to fully load...")
            time.sleep(12)
            
            # Title - h1 tag
            title = 'Unknown'
            try:
                title_el = page.locator('h1').first
                if title_el.count() > 0:
                    title = title_el.inner_text(timeout=5000).strip()
                    print(f"[bestbuy] Found title: {title[:50]}...")
            except Exception as e:
                print(f"[bestbuy] Title error: {e}")
            
            # Price - look for price in span[aria-hidden="true"] near the top
            price = None
            try:
                # Get all price-like spans
                price_spans = page.locator('span[aria-hidden="true"]').all()
                for span in price_spans[:10]:  # Check first 10 spans
                    text = span.inner_text(timeout=2000).strip()
                    # Look for price pattern like $238.89
                    if re.match(r'^\$[\d,]+\.?\d*$', text):
                        price = text
                        print(f"[bestbuy] Found price: {price}")
                        break
            except Exception as e:
                print(f"[bestbuy] Price error: {e}")
            
            # Stock status - improved logic with longer timeouts
            sold_out = False
            has_add_to_cart = False
            has_unavailable = False
            
            # First, check for "Unavailable" button (primary stock indicator)
            try:
                unavailable = page.locator('button:has-text("Unavailable")').first
                if unavailable.count() > 0 and unavailable.is_visible(timeout=8000):
                    has_unavailable = True
                    print("[bestbuy] Found 'Unavailable' button")
            except:
                pass
            
            # Then check if there's a working "Add to cart" button
            try:
                add_to_cart = page.locator('button:has-text("Add to cart")').first
                if add_to_cart.count() > 0:
                    is_visible = add_to_cart.is_visible(timeout=8000)
                    is_enabled = add_to_cart.is_enabled(timeout=8000)
                    if is_visible and is_enabled:
                        has_add_to_cart = True
                        print("[bestbuy] Found working 'Add to cart' button")
            except:
                pass
            
            # Decision logic:
            # If "Unavailable" button exists, item is out of stock (even if Add to cart exists for other sellers)
            if has_unavailable:
                sold_out = True
                print("[bestbuy] Item out of stock (Unavailable button present)")
            elif has_add_to_cart:
                sold_out = False
                print("[bestbuy] Item in stock (Add to cart button available)")
            else:
                # No clear indicators, check for other out of stock signals
                
                # Check for "Sold Out" text
                try:
                    if page.locator('text=/sold out/i').count() > 0:
                        sold_out = True
                        print("[bestbuy] Found 'Sold Out' text - item out of stock")
                except:
                    pass
                
                # Check for "Coming Soon" text
                if not sold_out:
                    try:
                        if page.locator('text=/coming soon/i').count() > 0:
                            sold_out = True
                            print("[bestbuy] Found 'Coming Soon' text")
                    except:
                        pass
                
                # If no indicators found, assume out of stock
                if not sold_out:
                    sold_out = True
                    print("[bestbuy] No clear stock indicators - assuming out of stock")
            
            # Reviews - look for pattern like (31,579 reviews)
            review_count = None
            try:
                review_spans = page.locator('span[aria-hidden="true"]').all()
                for span in review_spans[:20]:
                    text = span.inner_text(timeout=2000).strip()
                    # Look for pattern like (31,579 reviews)
                    match = re.search(r'\(([\d,]+)\s+reviews?\)', text, re.IGNORECASE)
                    if match:
                        review_count = int(match.group(1).replace(',', ''))
                        print(f"[bestbuy] Found reviews: {review_count}")
                        break
            except Exception as e:
                print(f"[bestbuy] Reviews error: {e}")
            
            print(f"[bestbuy] RESULT: title={title!r} price={price!r} sold_out={sold_out} reviews={review_count}")
            return {
                'title': title,
                'price': price,
                'sold_out': sold_out,
                'review_count': review_count,
                'url': url
            }
        
        except Exception as e:
            print(f"[bestbuy] Scrape error for {url}: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if page:
                page.close()
