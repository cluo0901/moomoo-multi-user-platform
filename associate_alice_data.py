#!/usr/bin/env python3
"""
Associate existing synced trading data with Alice's user ID
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Trade, Order, Position

def associate_alice_data():
    with app.app_context():
        print("🔧 Associating existing trading data with Alice...")

        # Find Alice's user ID
        alice = User.query.filter_by(username='alice').first()
        if not alice:
            print("❌ Alice user not found!")
            return

        print(f"✅ Found Alice (ID: {alice.id})")

        # Check current data without user_id filters
        total_trades = Trade.query.count()
        total_orders = Order.query.count()
        total_positions = Position.query.count()

        print(f"Total data in database: {total_trades} trades, {total_orders} orders, {total_positions} positions")

        # Check Alice's current data
        alice_trades = Trade.query.filter_by(user_id=alice.id).count()
        alice_orders = Order.query.filter_by(user_id=alice.id).count()
        alice_positions = Position.query.filter_by(user_id=alice.id).count()

        print(f"Alice's current data: {alice_trades} trades, {alice_orders} orders, {alice_positions} positions")

        if alice_trades == 0 and total_trades > 0:
            print("🔄 Associating existing data with Alice...")

            # Update all trades without user_id to belong to Alice
            trades_updated = db.session.execute(
                "UPDATE trades SET user_id = :user_id WHERE user_id IS NULL",
                {"user_id": alice.id}
            ).rowcount

            # Update all orders without user_id to belong to Alice
            orders_updated = db.session.execute(
                "UPDATE orders SET user_id = :user_id WHERE user_id IS NULL",
                {"user_id": alice.id}
            ).rowcount

            # Update all positions without user_id to belong to Alice
            positions_updated = db.session.execute(
                "UPDATE positions SET user_id = :user_id WHERE user_id IS NULL",
                {"user_id": alice.id}
            ).rowcount

            db.session.commit()

            print(f"✅ Updated {trades_updated} trades to belong to Alice")
            print(f"✅ Updated {orders_updated} orders to belong to Alice")
            print(f"✅ Updated {positions_updated} positions to belong to Alice")

        # Final verification
        final_trades = Trade.query.filter_by(user_id=alice.id).count()
        final_orders = Order.query.filter_by(user_id=alice.id).count()
        final_positions = Position.query.filter_by(user_id=alice.id).count()

        print(f"🎉 Alice's final data: {final_trades} trades, {final_orders} orders, {final_positions} positions")

        if final_trades > 0:
            print("✅ Alice should now see her trading data in the dashboard!")
        else:
            print("⚠️ No data found. You may need to run the data sync process.")

if __name__ == '__main__':
    associate_alice_data()