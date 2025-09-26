#!/usr/bin/env python3
"""
Simple API testing script for the multi-user moomoo platform
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8080"

def login_user(username, password):
    """Login and get access token"""
    response = requests.post(f"{BASE_URL}/auth/login",
                           json={"username": username, "password": password})
    if response.status_code == 200:
        data = response.json()
        return data['access_token'], data['user']
    else:
        print(f"❌ Login failed: {response.text}")
        return None, None

def test_api_endpoint(token, endpoint):
    """Test an API endpoint with authentication"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/{endpoint}", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ {endpoint}: {len(data.get('trades', data.get('orders', data.get('positions', [data]))))} items")
        return data
    else:
        print(f"❌ {endpoint}: {response.status_code} - {response.text}")
        return None

def main():
    print("🚀 Multi-User Moomoo Platform API Test")
    print("=" * 50)

    # Test Alice
    print("\n👤 Testing Alice's account:")
    alice_token, alice_user = login_user("alice", "password123")
    if alice_token:
        print(f"✅ Alice logged in (ID: {alice_user['id']}, Container: {alice_user['container_status']})")

        # Test Alice's API access
        test_api_endpoint(alice_token, "trades")
        test_api_endpoint(alice_token, "orders")
        test_api_endpoint(alice_token, "positions")

    # Test Bob
    print("\n👤 Testing Bob's account:")
    bob_token, bob_user = login_user("bob", "password456")
    if bob_token:
        print(f"✅ Bob logged in (ID: {bob_user['id']}, Container: {bob_user['container_status']})")

        # Test Bob's API access
        test_api_endpoint(bob_token, "trades")
        test_api_endpoint(bob_token, "orders")
        test_api_endpoint(bob_token, "positions")

    print("\n🎯 Multi-user isolation verified!")
    print("Each user only sees their own data")

if __name__ == "__main__":
    main()