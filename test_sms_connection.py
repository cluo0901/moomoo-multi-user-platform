#!/usr/bin/env python3
"""
Test script to verify SMS verification detection works properly
"""
import requests
import json

def test_connect_opend():
    """Test the connect-opend endpoint to see if SMS verification is detected"""

    # First login to get auth token
    login_data = {
        'username': 'alice',
        'password': 'password123'
    }

    try:
        print("1. Logging in as alice...")
        login_response = requests.post('http://localhost:8080/auth/login', json=login_data)

        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code} - {login_response.text}")
            return

        token = login_response.json().get('access_token')
        print(f"✓ Login successful, got token: {token[:20]}...")

        # Now test the connect-opend endpoint
        headers = {'Authorization': f'Bearer {token}'}

        print("\n2. Calling connect-opend endpoint...")
        connect_response = requests.post('http://localhost:8080/auth/connect-opend', headers=headers)

        print(f"Response Status: {connect_response.status_code}")

        try:
            response_data = connect_response.json()
            print(f"Response Data: {json.dumps(response_data, indent=2)}")

            if response_data.get('requires_sms_verification'):
                print("✓ SUCCESS: SMS verification requirement detected!")
                return True
            elif response_data.get('success'):
                print("⚠ UNEXPECTED: Connection succeeded without SMS verification")
                return False
            else:
                print(f"✗ ERROR: {response_data.get('error', 'Unknown error')}")
                return False

        except json.JSONDecodeError:
            print(f"Non-JSON response: {connect_response.text}")
            return False

    except Exception as e:
        print(f"Test failed with exception: {e}")
        return False

if __name__ == '__main__':
    print("Testing SMS verification detection...")
    success = test_connect_opend()

    if success:
        print("\n🎉 Test PASSED: SMS verification detection is working!")
    else:
        print("\n❌ Test FAILED: SMS verification detection is not working")