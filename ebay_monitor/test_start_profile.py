# -*- coding: utf-8 -*-
"""
Quick test to see the actual response from /open API
"""
from omnilogin_api import OmniloginAPI
import json


def test_start():
    api = OmniloginAPI()
    
    # Get first profile
    profiles_data = api.get_profiles()
    if not profiles_data or 'docs' not in profiles_data:
        print("Failed to get profiles")
        return
    
    profiles = profiles_data['docs']
    if not profiles:
        print("No profiles found")
        return
    
    profile_id = str(profiles[0]['id'])
    profile_name = profiles[0]['name']
    
    print(f"Testing with profile: {profile_name} (ID: {profile_id})")
    print("\nCalling /open API...")
    
    result = api.start(profile_id)
    
    if result:
        print("\nResponse from /open:")
        print(json.dumps(result, indent=2))
    else:
        print("\nFailed to start profile")
    
    # Stop profile
    print(f"\nStopping profile...")
    api.stop(profile_id)


if __name__ == '__main__':
    test_start()
