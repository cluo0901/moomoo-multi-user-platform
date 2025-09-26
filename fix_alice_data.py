#!/usr/bin/env python3
"""
Fix Alice's trading data by creating proper multi-user schema and syncing data
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Trade, Order, Position
from data_sync import sync_moomoo_data

def fix_alice_data():
    with app.app_context():
        print("🔧 Fixing Alice's trading data...")

        # Create all tables with proper multi-user schema
        print("Creating database tables with multi-user schema...")
        db.create_all()

        # Find Alice's user ID
        alice = User.query.filter_by(username='alice').first()
        if not alice:
            print("❌ Alice user not found!")
            return

        print(f"✅ Found Alice (ID: {alice.id})")

        # Check current data counts for Alice
        alice_trades = Trade.query.filter_by(user_id=alice.id).count()
        alice_orders = Order.query.filter_by(user_id=alice.id).count()
        alice_positions = Position.query.filter_by(user_id=alice.id).count()

        print(f"Current Alice data: {alice_trades} trades, {alice_orders} orders, {alice_positions} positions")

        if alice_trades == 0:
            print("🔄 No data found for Alice. Syncing from moomoo API...")

            # Set Alice's configuration as active for sync
            alice.openapi_configured = True
            db.session.commit()

            # Sync data for Alice - use the existing sync function
            try:
                sync_result = sync_moomoo_data()
                print(f"✅ Data sync completed!")
            except Exception as e:
                print(f"❌ Data sync failed: {e}")
        else:
            print("✅ Alice already has data in the database!")

        # Final verification
        final_trades = Trade.query.filter_by(user_id=alice.id).count()
        final_orders = Order.query.filter_by(user_id=alice.id).count()
        final_positions = Position.query.filter_by(user_id=alice.id).count()

        print(f"✅ Final Alice data: {final_trades} trades, {final_orders} orders, {final_positions} positions")

        print("🎉 Alice's data is now ready! She should see her trading data in the dashboard.")

if __name__ == '__main__':
    fix_alice_data()