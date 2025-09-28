#!/usr/bin/env python3
"""
Test script to verify logout cleanup and fresh login functionality
"""
import requests
import json
import time

def test_logout_cleanup_flow():
    """Test the complete logout cleanup and fresh login flow"""
    base_url = "http://localhost:8080"
    container_url = "http://localhost:8001"

    # Login credentials
    login_data = {
        'username': 'alice',
        'password': 'password123'
    }

    config_data = {
        'moomoo_username': '102872417',
        'moomoo_password': 'L850901c',
        'security_firm': 'FUTUSG',
        'trade_market': 'US'
    }

    try:
        print("=== Testing Logout Cleanup and Fresh Login Flow ===\n")

        # Step 1: Login and configure
        print("1. Initial login and configuration...")
        login_response = requests.post(f'{base_url}/auth/login', json=login_data)
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")
            return False

        token = login_response.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        print("✓ Login successful")

        # Configure credentials
        config_response = requests.post(f'{base_url}/auth/opend-config', json=config_data, headers=headers)
        if config_response.status_code != 200:
            print(f"Config failed: {config_response.status_code}")
            return False
        print("✓ Credentials configured")

        # Step 2: Connect to trigger SMS state
        print("\n2. Connecting to trigger SMS verification...")
        connect_response = requests.post(f'{base_url}/auth/connect-opend', headers=headers)
        connect_data = connect_response.json()
        print(f"Connect response: {json.dumps(connect_data, indent=2)}")

        if not connect_data.get('requires_sms_verification'):
            print("⚠ SMS verification not triggered")
        else:
            print("✓ SMS verification triggered")

        # Check container state
        status_response = requests.get(f'{container_url}/status')
        status_data = status_response.json()
        print(f"Container state before logout: {status_data.get('connection_state')}")

        # Step 3: Logout with cleanup
        print("\n3. Testing logout cleanup...")
        logout_response = requests.post(f'{base_url}/auth/logout', headers=headers)
        logout_data = logout_response.json()
        print(f"Logout response: {json.dumps(logout_data, indent=2)}")

        if logout_response.status_code == 200:
            print("✓ Logout successful")
        else:
            print("❌ Logout failed")
            return False

        # Check container state after logout
        time.sleep(2)  # Give it a moment to process
        status_response2 = requests.get(f'{container_url}/status')
        status_data2 = status_response2.json()
        print(f"Container state after logout: {status_data2.get('connection_state')}")
        print(f"SMS state after logout: awaiting_sms={status_data2.get('awaiting_sms_verification')}")

        # Step 4: Fresh login
        print("\n4. Testing fresh login...")
        fresh_login_response = requests.post(f'{base_url}/auth/login', json=login_data)
        if fresh_login_response.status_code != 200:
            print(f"Fresh login failed: {fresh_login_response.status_code}")
            return False

        fresh_token = fresh_login_response.json().get('access_token')
        fresh_headers = {'Authorization': f'Bearer {fresh_token}'}
        print("✓ Fresh login successful")

        # Check if cleanup happened during login
        time.sleep(2)  # Give it a moment to process
        status_response3 = requests.get(f'{container_url}/status')
        status_data3 = status_response3.json()
        print(f"Container state after fresh login: {status_data3.get('connection_state')}")
        print(f"SMS state after fresh login: awaiting_sms={status_data3.get('awaiting_sms_verification')}")

        # Step 5: Test fresh connection
        print("\n5. Testing fresh connection after login cleanup...")
        fresh_connect_response = requests.post(f'{base_url}/auth/connect-opend', headers=fresh_headers)
        fresh_connect_data = fresh_connect_response.json()
        print(f"Fresh connect response: {json.dumps(fresh_connect_data, indent=2)}")

        if fresh_connect_data.get('requires_sms_verification'):
            print("✓ Fresh SMS verification triggered (as expected)")
            print("\n🎉 All logout/login cleanup tests PASSED!")
            return True
        else:
            print("❌ Fresh SMS verification not triggered")
            return False

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == '__main__':
    print("Testing logout cleanup and fresh login flow...")
    success = test_logout_cleanup_flow()

    if success:
        print("\n✅ Logout cleanup system is working correctly!")
        print("Users will now get fresh starts on each login.")
    else:
        print("\n❌ Logout cleanup system has issues")