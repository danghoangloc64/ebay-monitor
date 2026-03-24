# -*- coding: utf-8 -*-
"""
Omnilogin API Client - Converted from C# to Python
"""
import requests
import random
import string
from typing import Optional, Dict, Any


class OmniloginAPI:
    """Client for Omnilogin browser automation API"""
    
    API_START_PATH = "/open"
    API_STOP_PATH = "/stop"
    API_PROFILE_LIST_PATH = "/profiles"
    API_UPDATE_PROXY_PATH = "/profiles/embedded-proxy"
    
    def __init__(self, api_url: str = "http://localhost:35353"):
        """
        Initialize Omnilogin API client
        
        Args:
            api_url: Base URL of Omnilogin API (default: http://localhost:35353)
        """
        self.api_url = api_url
    
    def start(self, profile_id: str, headless: bool = False) -> Optional[Dict[str, Any]]:
        """
        Start a browser profile
        
        Args:
            profile_id: ID of the profile to start
            headless: Run browser in headless mode (default: False)
            
        Returns:
            JSON response with browser connection details or None on error
        """
        url = f"{self.api_url}{self.API_START_PATH}?profile_id={profile_id}"
        url += "&addition_args=--test-type"
        url += "&addition_args=--disable-popup-blocking"
        
        # Add headless mode if requested
        if headless:
            url += "&addition_args=--headless=new"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[omnilogin] Start error: {e}")
            return None
    
    def stop(self, profile_id: str) -> bool:
        """
        Stop a browser profile
        
        Args:
            profile_id: ID of the profile to stop
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.api_url}{self.API_STOP_PATH}/{profile_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[omnilogin] Stop error: {e}")
            return False
    
    def get_profiles(self) -> Optional[Dict[str, Any]]:
        """
        Get list of all profiles
        
        Returns:
            JSON response with profile list or None on error
        """
        url = f"{self.api_url}{self.API_PROFILE_LIST_PATH}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[omnilogin] Get profiles error: {e}")
            return None
    
    def update_proxy(self, profile_id: str, proxy: str) -> bool:
        """
        Update proxy for a profile
        
        Args:
            profile_id: ID of the profile
            proxy: Proxy string in format "host:port:username:password"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            parts = proxy.split(':')
            if len(parts) != 4:
                print(f"[omnilogin] Invalid proxy format: {proxy}")
                return False
            
            request_body = {
                "proxy": {
                    "name": "proxy",
                    "proxy_type": "HTTPS",
                    "host": parts[0],
                    "port": parts[1],
                    "user_name": parts[2],
                    "password": parts[3]
                },
                "profileIds": [profile_id]
            }
            
            url = f"{self.api_url}{self.API_UPDATE_PROXY_PATH}"
            response = requests.put(url, json=request_body, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[omnilogin] Update proxy error: {e}")
            return False
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random alphanumeric string"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
