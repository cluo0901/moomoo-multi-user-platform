#!/usr/bin/env python3
"""
Test script to verify complete SMS verification flow works properly
"""
import requests
import json
import time

def test_full_sms_flow():
    """Test the complete SMS verification flow"""

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

        headers = {'Authorization': f'Bearer {token}'}

        # Configure credentials first
        print("\n2. Configuring moomoo credentials...")
        config_data = {
            'moomoo_username': '102872417',
            'moomoo_password': 'L850901c',
            'security_firm': 'FUTUSG',
            'trade_market': 'US'
        }

        config_response = requests.post(
            'http://localhost:8080/auth/opend-config',
            json=config_data,
            headers=headers
        )

        if config_response.status_code != 200:
            print(f"Config failed: {config_response.status_code} - {config_response.text}")
            return

        print("✓ Credentials configured successfully")

        # Now test the connect-opend endpoint
        print("\n3. Calling connect-opend endpoint...")
        connect_response = requests.post('http://localhost:8080/auth/connect-opend', headers=headers)

        print(f"Response Status: {connect_response.status_code}")

        try:
            response_data = connect_response.json()
            print(f"Response Data: {json.dumps(response_data, indent=2)}")

            if response_data.get('requires_sms_verification'):
                print("✓ SUCCESS: SMS verification requirement detected!")

                # Now test SMS verification with a fake code
                print("\n4. Testing SMS verification with sample code...")
                verify_data = {'sms_code': '123456'}
                verify_response = requests.post('http://localhost:8080/auth/verify-sms',
                                              json=verify_data, headers=headers)

                print(f"Verify Response Status: {verify_response.status_code}")
                verify_data = verify_response.json()
                print(f"Verify Response Data: {json.dumps(verify_data, indent=2)}")

                if verify_response.status_code == 400 and verify_data.get('error') == 'No SMS verification pending':
                    print("❌ FAILED: SMS verification state lost")
                    return False
                else:
                    print("✓ SUCCESS: SMS verification endpoint accepts codes now!")
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
    print("Testing complete SMS verification flow...")
    success = test_full_sms_flow()

    if success:
        print("\n🎉 Test PASSED: Complete SMS verification flow is working!")
    else:
        print("\n❌ Test FAILED: SMS verification flow has issues")