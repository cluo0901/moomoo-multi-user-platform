#!/usr/bin/env python3
"""
Test script to verify SMS verification endpoint works properly
"""
import requests
import json

def test_sms_verify():
    """Test the verify-sms endpoint to see what error occurs"""

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

        # Test the verify-sms endpoint with a sample code
        headers = {'Authorization': f'Bearer {token}'}

        print("\n2. Testing verify-sms endpoint with sample code...")
        verify_data = {'sms_code': '123456'}
        verify_response = requests.post('http://localhost:8080/auth/verify-sms',
                                      json=verify_data, headers=headers)

        print(f"Response Status: {verify_response.status_code}")

        try:
            response_data = verify_response.json()
            print(f"Response Data: {json.dumps(response_data, indent=2)}")

            if verify_response.status_code == 400:
                print("✓ Got 400 error - let's see the error message")
                return response_data.get('error', 'Unknown error')
            else:
                print(f"Unexpected status code: {verify_response.status_code}")
                return response_data

        except json.JSONDecodeError:
            print(f"Non-JSON response: {verify_response.text}")
            return verify_response.text

    except Exception as e:
        print(f"Test failed with exception: {e}")
        return str(e)

if __name__ == '__main__':
    print("Testing SMS verification endpoint...")
    error = test_sms_verify()
    print(f"\nError details: {error}")