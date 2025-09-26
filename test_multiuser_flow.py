#!/usr/bin/env python3
"""
Test script for multi-user architecture
Tests the container-based data sync flow
"""

import requests
import json
import time
from container_data_sync import ContainerDataSync

def test_container_api():
    """Test container API endpoints"""
    print("🧪 Testing Container API Endpoints")
    base_url = "http://localhost:8000"

    # Test health check
    print("1. Testing health check...")
    response = requests.get(f"{base_url}/health")
    print(f"   Health: {response.status_code} - {response.json()}")

    # Test readiness check
    print("2. Testing readiness check...")
    response = requests.get(f"{base_url}/ready")
    print(f"   Ready: {response.status_code} - {response.json()}")

    # Test configuration endpoint
    print("3. Testing configuration endpoint...")
    response = requests.get(f"{base_url}/config")
    print(f"   Config: {response.status_code} - {response.json()}")

    # Test configuration update (simulate)
    print("4. Testing configuration update...")
    mock_config = {
        "moomoo_host": "127.0.0.1",
        "moomoo_port": 11111,
        "security_firm": "FUTUSG",
        "trade_market": "US",
        "moomoo_username": "test_user",
        "moomoo_password": "test_password"
    }
    response = requests.post(f"{base_url}/config", json=mock_config)
    print(f"   Config Update: {response.status_code} - {response.json()}")

def test_container_data_sync():
    """Test container-based data sync"""
    print("\n🔄 Testing Container Data Sync")

    # Create sync service
    sync_service = ContainerDataSync(user_id=1, container_url="http://localhost:8000")

    # Test container status check
    print("1. Testing container status check...")
    status = sync_service.check_container_status()
    print(f"   Container Ready: {status}")

    # Test sync calls (will fail without real OpenD, but tests API)
    print("2. Testing sync trades API call...")
    result = sync_service._make_request('/sync/trades', params={
        'start_date': '2024-01-01',
        'end_date': '2024-01-31'
    })
    print(f"   Sync Trades: {result.get('success', False)} - {result.get('error', 'OK')}")

def test_integration_with_platform():
    """Test integration with platform database"""
    print("\n🔗 Testing Platform Integration")

    from app import app
    from models import User, db
    from container_data_sync import sync_user_container_data

    with app.app_context():
        # Find Alice user
        alice = User.query.filter_by(username='alice').first()
        if alice:
            print(f"   Found user: {alice.username} (ID: {alice.id})")

            # Test container-based sync (will error due to no real OpenD, but tests flow)
            print("   Testing container data sync integration...")
            result = sync_user_container_data(
                user_id=alice.id,
                container_url="http://localhost:8000",
                lookback_days=30
            )
            print(f"   Sync Result: {result['status']} - {result.get('message', 'Success')}")
        else:
            print("   Alice user not found")

def main():
    """Run all tests"""
    print("🚀 Multi-User Architecture Test Suite")
    print("=" * 50)

    # Wait for container to be ready
    print("Waiting for container service to be ready...")
    time.sleep(2)

    try:
        # Test container API
        test_container_api()

        # Test container data sync
        test_container_data_sync()

        # Test platform integration
        test_integration_with_platform()

        print("\n✅ Test Suite Complete!")
        print("\nNext Steps:")
        print("1. Build and test Docker container")
        print("2. Deploy to Kubernetes cluster")
        print("3. Test with real moomoo credentials")
        print("4. Test multi-user isolation")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()