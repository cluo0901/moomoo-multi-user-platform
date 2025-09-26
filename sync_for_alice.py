#!/usr/bin/env python3
"""
Sync moomoo trading data specifically for Alice user
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Trade, Order, Position
from data_sync import sync_moomoo_data

def sync_alice_data():
    with app.app_context():
        print("🔄 Syncing data for Alice...")

        # Find Alice's user ID
        alice = User.query.filter_by(username='alice').first()
        if not alice:
            print("❌ Alice user not found!")
            return

        print(f"✅ Found Alice (ID: {alice.id})")

        # Ensure database has proper schema
        print("📋 Creating database tables with multi-user schema...")
        db.create_all()

        # Skip checking current data - just sync fresh
        print("📊 Starting fresh data sync...")

        # Sync data for Alice
        print("🚀 Starting data sync with moomoo API...")
        result = sync_moomoo_data(user_id=alice.id)

        if result['status'] == 'success':
            print(f"✅ Data sync completed successfully!")
            print(f"   📈 Synced {result['synced_counts']['trades']} trades")
            print(f"   📋 Synced {result['synced_counts']['orders']} orders")
            print(f"   💼 Synced {result['synced_counts']['positions']} positions")
        else:
            print(f"❌ Data sync failed: {result.get('message', 'Unknown error')}")
            return

        # Verification will be done by checking dashboard directly
        print("🎉 Data sync completed! Alice should now see her trading data in the dashboard.")
        print("   Dashboard: http://localhost:8080")
        print("   Login with: username=alice, password=password123")

if __name__ == '__main__':
    sync_alice_data()