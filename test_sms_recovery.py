#!/usr/bin/env python3
"""
Test script to verify SMS state recovery and force reconnect functionality
"""
import requests
import json
import time

def test_sms_recovery_flow():
    """Test the complete SMS recovery flow"""
    base_url = "http://localhost:8080"
    container_url = "http://localhost:8001"

    # First login to get auth token
    login_data = {
        'username': 'alice',
        'password': 'password123'
    }

    try:
        print("=== Testing SMS State Recovery Flow ===\n")

        print("1. Logging in as alice...")
        login_response = requests.post(f'{base_url}/auth/login', json=login_data)
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code} - {login_response.text}")
            return False

        token = login_response.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        print(f"✓ Login successful")

        # Configure credentials
        print("\n2. Configuring moomoo credentials...")
        config_data = {
            'moomoo_username': '102872417',
            'moomoo_password': 'L850901c',
            'security_firm': 'FUTUSG',
            'trade_market': 'US'
        }
        config_response = requests.post(f'{base_url}/auth/opend-config', json=config_data, headers=headers)
        if config_response.status_code != 200:
            print(f"Config failed: {config_response.status_code}")
            return False
        print("✓ Credentials configured")

        # Test 1: First connection attempt (should trigger SMS)
        print("\n3. Testing first connection attempt...")
        connect_response = requests.post(f'{base_url}/auth/connect-opend', headers=headers)
        connect_data = connect_response.json()
        print(f"Response: {json.dumps(connect_data, indent=2)}")

        if not connect_data.get('requires_sms_verification'):
            print("❌ First connection didn't trigger SMS verification")
            return False
        print("✓ First connection triggered SMS verification")

        # Check container status (should be awaiting_sms)
        print("\n4. Checking container status...")
        status_response = requests.get(f'{container_url}/status')
        status_data = status_response.json()
        print(f"Container status: awaiting_sms={status_data.get('awaiting_sms_verification')}, state={status_data.get('connection_state')}")

        if not status_data.get('awaiting_sms_verification'):
            print("❌ Container not in awaiting_sms state")
            return False
        print("✓ Container properly in awaiting_sms state")

        # Test 2: Second connection attempt without force_reconnect (should return existing SMS requirement)
        print("\n5. Testing second connection attempt (should return existing SMS requirement)...")
        connect_response2 = requests.post(f'{base_url}/auth/connect-opend', headers=headers)
        connect_data2 = connect_response2.json()
        print(f"Response: {json.dumps(connect_data2, indent=2)}")

        if not connect_data2.get('requires_sms_verification'):
            print("❌ Second connection didn't return SMS requirement")
            return False
        print("✓ Second connection properly returned existing SMS requirement")

        # Test 3: Reset SMS state
        print("\n6. Testing SMS state reset...")
        reset_response = requests.post(f'{container_url}/reset-sms')
        reset_data = reset_response.json()
        print(f"Reset response: {json.dumps(reset_data, indent=2)}")

        if not reset_data.get('success'):
            print("❌ SMS reset failed")
            return False
        print("✓ SMS state reset successfully")

        # Check status after reset
        status_response2 = requests.get(f'{container_url}/status')
        status_data2 = status_response2.json()
        print(f"Status after reset: awaiting_sms={status_data2.get('awaiting_sms_verification')}, state={status_data2.get('connection_state')}")

        if status_data2.get('awaiting_sms_verification'):
            print("❌ SMS state not properly reset")
            return False
        print("✓ SMS state properly reset")

        # Test 4: Connection attempt after reset (should trigger fresh SMS)
        print("\n7. Testing connection after reset (should trigger fresh SMS)...")
        connect_response3 = requests.post(f'{base_url}/auth/connect-opend', headers=headers)
        connect_data3 = connect_response3.json()
        print(f"Response: {json.dumps(connect_data3, indent=2)}")

        if not connect_data3.get('requires_sms_verification'):
            print("❌ Connection after reset didn't trigger fresh SMS")
            return False
        print("✓ Connection after reset triggered fresh SMS")

        # Test 5: Force reconnect functionality
        print("\n8. Testing force reconnect functionality...")
        force_connect_data = {'force_reconnect': True}
        force_response = requests.post(f'{container_url}/connect', json=force_connect_data)
        force_data = force_response.json()
        print(f"Force reconnect response: {json.dumps(force_data, indent=2)}")

        if not force_data.get('requires_sms_verification'):
            print("❌ Force reconnect didn't trigger fresh SMS")
            return False
        print("✓ Force reconnect triggered fresh SMS")

        print("\n🎉 All SMS recovery tests PASSED!")
        return True

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == '__main__':
    success = test_sms_recovery_flow()
    if success:
        print("\n✅ SMS state recovery system is working correctly!")
    else:
        print("\n❌ SMS state recovery system has issues")