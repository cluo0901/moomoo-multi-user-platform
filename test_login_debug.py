#!/usr/bin/env python3
"""
Debug login issues for Alice
"""

import requests
import json

def debug_login():
    print("🔍 Debugging Alice Login Issue")
    print("=" * 50)

    base_url = "http://localhost:8080"

    # Test 1: Server health
    print("1. Testing server health...")
    try:
        health = requests.get(f"{base_url}/health")
        if health.status_code == 200:
            print("   ✅ Server is healthy")
        else:
            print(f"   ❌ Server health check failed: {health.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect to server: {e}")
        return

    # Test 2: Auth page loads
    print("\n2. Testing auth page accessibility...")
    try:
        auth_page = requests.get(f"{base_url}/static/auth.html")
        if auth_page.status_code == 200 and "Moomoo Platform" in auth_page.text:
            print("   ✅ Auth page loads correctly")
        else:
            print(f"   ❌ Auth page issue: {auth_page.status_code}")
    except Exception as e:
        print(f"   ❌ Auth page error: {e}")

    # Test 3: JavaScript files load
    print("\n3. Testing JavaScript files...")
    try:
        auth_js = requests.get(f"{base_url}/static/auth.js")
        if auth_js.status_code == 200 and "AuthManager" in auth_js.text:
            print("   ✅ auth.js loads correctly")
        else:
            print(f"   ❌ auth.js issue: {auth_js.status_code}")
    except Exception as e:
        print(f"   ❌ auth.js error: {e}")

    # Test 4: API login
    print("\n4. Testing API login...")
    login_data = {"username": "alice", "password": "password123"}

    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data)

        if response.status_code == 200:
            data = response.json()
            print("   ✅ API login successful")
            print(f"   📝 User: {data['user']['username']}")
            print(f"   🔑 Token preview: {data['access_token'][:50]}...")
            print(f"   📊 Container status: {data['user']['container_status']}")
        else:
            print(f"   ❌ API login failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
    except Exception as e:
        print(f"   ❌ API login error: {e}")

    # Test 5: User verification
    print("\n5. Testing user database...")
    try:
        # Check if alice exists with different passwords
        test_passwords = ["password123", "alice123", "admin123"]
        for pwd in test_passwords:
            test_response = requests.post(f"{base_url}/auth/login",
                                        json={"username": "alice", "password": pwd})
            if test_response.status_code == 200:
                print(f"   ✅ Alice login works with password: {pwd}")
                break
        else:
            print("   ❌ None of the test passwords work")
    except Exception as e:
        print(f"   ❌ User verification error: {e}")

    print("\n" + "=" * 50)
    print("🎯 TROUBLESHOOTING STEPS:")
    print("1. Open browser to: http://localhost:8080/static/auth.html")
    print("2. Try login with: alice / password123")
    print("3. Check browser console (F12) for JavaScript errors")
    print("4. If login still fails, check:")
    print("   - Network tab for failed requests")
    print("   - Console for error messages")
    print("   - Try clearing browser cache (Cmd+Shift+R)")
    print("\n💡 Alternative: Use dashboard directly at http://localhost:8080/")

if __name__ == "__main__":
    debug_login()