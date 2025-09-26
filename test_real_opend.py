#!/usr/bin/env python3
"""
Test Real OpenD Integration with Actual Moomoo Credentials
This script tests the complete OpenD binary integration flow
"""

import requests
import json
import time
import sys

def test_real_opend_integration():
    """Test the complete real OpenD integration flow"""

    # Use the existing access token from login
    try:
        with open('/tmp/final_login.json', 'r') as f:
            login_data = json.load(f)
            access_token = login_data['access_token']
            print(f"Using existing access token: {access_token[:50]}...")
    except FileNotFoundError:
        print("ERROR: No login token found. Please log in first.")
        return False

    # API base URL
    base_url = "http://localhost"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    print("=== Testing Real OpenD Integration ===")
    print()

    # Step 1: Check container status
    print("1. Checking container status...")
    response = requests.get(f"{base_url}/auth/container-status", headers=headers)
    if response.status_code == 200:
        status_data = response.json()
        print(f"   Container Status: {status_data.get('container_status')}")
        print(f"   Container ID: {status_data.get('container_id')}")
        print(f"   OpenD Configured: {status_data.get('openapi_configured')}")
    else:
        print(f"   ERROR: Failed to get container status - {response.status_code}")
        return False

    # Step 2: Configure real moomoo credentials
    print("\n2. Configuring real moomoo credentials...")

    # Real moomoo credentials from user: 102872417 / L850901c
    # Using the field names that the web UI expects
    real_config = {
        "moomoo_host": "102872417",      # Using old field name for compatibility
        "moomoo_port": "L850901c",       # Using old field name for compatibility
        "security_firm": "FUTUSG",
        "trade_market": "US"
    }

    print(f"   Username: {real_config['moomoo_host']}")
    print(f"   Password: {'*' * len(real_config['moomoo_port'])}")
    print(f"   Security Firm: {real_config['security_firm']}")
    print(f"   Trade Market: {real_config['trade_market']}")

    response = requests.post(f"{base_url}/auth/opend-config",
                           headers=headers,
                           json=real_config)

    if response.status_code == 200:
        result = response.json()
        print(f"   Configuration Result: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
    else:
        print(f"   ERROR: Configuration failed - {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    # Step 3: Check container health
    print("\n3. Checking container health...")
    container_id = status_data.get('container_id', 'moomoo-user-alice')

    try:
        # Try to access container health endpoint directly
        container_response = requests.get(f"http://{container_id}:8000/health", timeout=10)
        if container_response.status_code == 200:
            health_data = container_response.json()
            print(f"   Container Health: {health_data.get('status')}")
            print(f"   OpenD Connected: {health_data.get('opend_connected')}")
            print(f"   OpenD Process Running: {health_data.get('opend_process_running')}")
            print(f"   Configured: {health_data.get('configured')}")
        else:
            print(f"   Container health check failed: {container_response.status_code}")
    except Exception as e:
        print(f"   Container health check error: {e}")

    # Step 4: Test detailed status
    print("\n4. Checking detailed OpenD status...")
    try:
        status_response = requests.get(f"http://{container_id}:8000/status", timeout=10)
        if status_response.status_code == 200:
            status_detail = status_response.json()
            print(f"   Process Running: {status_detail.get('process_running')}")
            print(f"   Trade Context Active: {status_detail.get('trade_context_active')}")
            print(f"   Process ID: {status_detail.get('process_id')}")
            print(f"   Return Code: {status_detail.get('return_code')}")
        else:
            print(f"   Detailed status check failed: {status_response.status_code}")
    except Exception as e:
        print(f"   Detailed status error: {e}")

    # Step 5: Test data refresh with real credentials
    print("\n5. Testing data refresh with real OpenD...")
    response = requests.post(f"{base_url}/api/refresh-data", headers=headers)

    if response.status_code == 200:
        refresh_result = response.json()
        print(f"   Data Refresh Status: {refresh_result.get('status')}")
        print(f"   Message: {refresh_result.get('message')}")

        # If successful, check for real trading data
        if refresh_result.get('status') == 'success':
            print("\n6. Checking for real trading data...")

            # Check trades
            trades_response = requests.get(f"{base_url}/api/trades?per_page=5", headers=headers)
            if trades_response.status_code == 200:
                trades_data = trades_response.json()
                print(f"   Total Trades Found: {trades_data.get('total', 0)}")

                if trades_data.get('trades'):
                    print("   Sample Trade Data:")
                    for i, trade in enumerate(trades_data['trades'][:2]):
                        print(f"     Trade {i+1}: {trade.get('code')} - {trade.get('side')} - {trade.get('val')}")

            # Check positions
            positions_response = requests.get(f"{base_url}/api/positions", headers=headers)
            if positions_response.status_code == 200:
                positions_data = positions_response.json()
                print(f"   Active Positions: {len(positions_data.get('positions', []))}")

                if positions_data.get('positions'):
                    print("   Sample Position Data:")
                    for i, pos in enumerate(positions_data['positions'][:2]):
                        print(f"     Position {i+1}: {pos.get('code')} - Value: {pos.get('market_val')}")

    else:
        print(f"   ERROR: Data refresh failed - {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    print("\n=== Real OpenD Integration Test Complete ===")
    return True

def check_container_logs():
    """Check container logs for OpenD startup messages"""
    print("\n=== Container Logs Analysis ===")

    import subprocess
    try:
        # Get recent container logs
        result = subprocess.run(['docker-compose', '-f', 'docker-compose.production.yml', 'logs', 'user-alice', '--tail=50'],
                              capture_output=True, text=True, cwd='/Users/lc/PycharmProjects/PythonProject/MoomooAccount')

        if result.returncode == 0:
            logs = result.stdout
            print("Recent Alice container logs:")
            print("---")
            for line in logs.split('\n')[-20:]:
                if line.strip():
                    print(f"   {line}")
            print("---")
        else:
            print(f"Failed to get logs: {result.stderr}")

    except Exception as e:
        print(f"Error getting container logs: {e}")

if __name__ == "__main__":
    print("Starting Real OpenD Integration Test")
    print("Using credentials: 102872417 / L850901c")
    print()

    success = test_real_opend_integration()
    check_container_logs()

    if success:
        print("\n✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test encountered errors")
        sys.exit(1)