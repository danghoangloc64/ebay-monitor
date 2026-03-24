# -*- coding: utf-8 -*-
"""
Test script for Omnilogin API
"""
from omnilogin_api import OmniloginAPI
import time


def test_omnilogin():
    """Test Omnilogin API connection and profile management"""
    
    print("=" * 60)
    print("Testing Omnilogin API")
    print("=" * 60)
    
    # Initialize API
    api = OmniloginAPI()
    print("\n✓ Omnilogin API initialized")
    
    # Get profiles
    print("\n1. Getting profiles...")
    profiles_data = api.get_profiles()
    
    if not profiles_data:
        print("✗ Failed to get profiles. Is Omnilogin running?")
        return False
    
    print(f"✓ Response: {profiles_data}")
    
    if 'docs' not in profiles_data:
        print("✗ No 'docs' field in response")
        return False
    
    profiles = profiles_data['docs']
    if not profiles or len(profiles) == 0:
        print("✗ No profiles found. Please create a profile in Omnilogin first.")
        return False
    
    total = profiles_data.get('total', len(profiles))
    print(f"✓ Found {total} profile(s)")
    
    # Use first profile
    first_profile = profiles[0]
    profile_id = str(first_profile.get('id'))
    profile_name = first_profile.get('name', 'Unknown')
    
    print(f"\n2. Using first profile:")
    print(f"   ID: {profile_id}")
    print(f"   Name: {profile_name}")
    
    # Start profile
    print(f"\n3. Starting profile {profile_id}...")
    start_result = api.start(profile_id)
    
    if not start_result:
        print("✗ Failed to start profile")
        return False
    
    print(f"✓ Profile started successfully")
    print(f"   Response: {start_result}")
    
    if 'data' in start_result and 'ws' in start_result['data']:
        ws_endpoint = start_result['data']['ws'].get('selenium')
        print(f"   WebSocket endpoint: {ws_endpoint}")
    
    # Wait a bit
    print("\n4. Waiting 5 seconds...")
    time.sleep(5)
    
    # Stop profile
    print(f"\n5. Stopping profile {profile_id}...")
    stop_result = api.stop(profile_id)
    
    if stop_result:
        print("✓ Profile stopped successfully")
    else:
        print("✗ Failed to stop profile")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    try:
        test_omnilogin()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
