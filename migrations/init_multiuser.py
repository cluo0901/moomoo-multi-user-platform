#!/usr/bin/env python3
"""
Database migration script for multi-user platform
Migrates existing single-user data to multi-user schema
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, User, Trade, Order, Position

def create_default_user():
    """Create a default user for existing data"""
    print("Creating default user for existing data migration...")

    default_user = User(
        username='admin',
        email='admin@moomoo-platform.local'
    )
    default_user.set_password('changeMe123!')

    db.session.add(default_user)
    db.session.commit()

    print(f"✅ Default user created with ID: {default_user.id}")
    print(f"   Username: {default_user.username}")
    print(f"   Email: {default_user.email}")
    print(f"   Password: changeMe123!")
    print("   ⚠️  Please change the default password after login!")

    return default_user

def migrate_existing_data(user_id, backup_db=True):
    """Migrate existing single-user data to multi-user schema"""
    db_path = 'moomoo_trading.db'

    if not os.path.exists(db_path):
        print(f"No existing database found at {db_path}")
        return

    if backup_db:
        backup_path = f'moomoo_trading_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        print(f"Creating backup: {backup_path}")
        os.system(f'cp {db_path} {backup_path}')

    # Check if migration is needed
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if user_id column exists in trades table
        cursor.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'user_id' in columns:
            print("Database already appears to be migrated to multi-user schema")
            conn.close()
            return

        print("Starting migration of existing data...")

        # Get count of existing data
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM positions")
        position_count = cursor.fetchone()[0]

        print(f"Found {trade_count} trades, {order_count} orders, {position_count} positions to migrate")

        if trade_count == 0 and order_count == 0 and position_count == 0:
            print("No existing data to migrate")
            conn.close()
            return

        # Start migration transaction
        cursor.execute("BEGIN TRANSACTION")

        # Add user_id columns
        cursor.execute("ALTER TABLE trades ADD COLUMN user_id INTEGER")
        cursor.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER")
        cursor.execute("ALTER TABLE positions ADD COLUMN user_id INTEGER")

        # Update all existing records to belong to the default user
        cursor.execute(f"UPDATE trades SET user_id = {user_id}")
        cursor.execute(f"UPDATE orders SET user_id = {user_id}")
        cursor.execute(f"UPDATE positions SET user_id = {user_id}")

        # Update unique constraints for multi-user
        # Drop existing unique constraints
        cursor.execute("DROP INDEX IF EXISTS ix_trades_deal_id")
        cursor.execute("DROP INDEX IF EXISTS ix_orders_order_id")

        # Create new composite unique indexes
        cursor.execute("CREATE UNIQUE INDEX idx_trades_user_deal_id ON trades(user_id, deal_id)")
        cursor.execute("CREATE UNIQUE INDEX idx_orders_user_order_id ON orders(user_id, order_id)")

        # Create user-specific indexes for performance
        cursor.execute("CREATE INDEX idx_trades_user_code_time ON trades(user_id, code, deal_time)")
        cursor.execute("CREATE INDEX idx_orders_user_code_time ON orders(user_id, code, create_time)")
        cursor.execute("CREATE INDEX idx_positions_user_code_snapshot ON positions(user_id, code, snapshot_time)")

        # Commit migration
        cursor.execute("COMMIT")

        print(f"✅ Migration completed successfully!")
        print(f"   Migrated {trade_count} trades")
        print(f"   Migrated {order_count} orders")
        print(f"   Migrated {position_count} positions")
        print(f"   All data assigned to user ID: {user_id}")

    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"❌ Migration failed: {e}")
        raise e

    finally:
        conn.close()

def verify_migration():
    """Verify migration completed successfully"""
    print("\nVerifying migration...")

    with app.app_context():
        # Check user count
        user_count = User.query.count()
        print(f"Users in system: {user_count}")

        # Check data counts per user
        users = User.query.all()
        for user in users:
            trade_count = Trade.query.filter_by(user_id=user.id).count()
            order_count = Order.query.filter_by(user_id=user.id).count()
            position_count = Position.query.filter_by(user_id=user.id).count()

            print(f"User '{user.username}' (ID: {user.id}):")
            print(f"  Trades: {trade_count}")
            print(f"  Orders: {order_count}")
            print(f"  Positions: {position_count}")

def main():
    parser = argparse.ArgumentParser(description='Migrate moomoo database to multi-user schema')
    parser.add_argument('--no-backup', action='store_true', help='Skip database backup')
    parser.add_argument('--verify-only', action='store_true', help='Only verify migration status')
    args = parser.parse_args()

    print("🚀 Moomoo Multi-User Database Migration")
    print("=" * 50)

    if args.verify_only:
        with app.app_context():
            verify_migration()
        return

    with app.app_context():
        # Create all tables with new schema
        print("Creating database tables with multi-user schema...")
        db.create_all()

        # Create default user
        default_user = create_default_user()

        # Migrate existing data
        migrate_existing_data(
            user_id=default_user.id,
            backup_db=not args.no_backup
        )

        # Verify migration
        verify_migration()

        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Login with default credentials:")
        print("   Username: admin")
        print("   Password: changeMe123!")
        print("2. Change the default password")
        print("3. Configure your moomoo OpenD connection")
        print("4. Start inviting other users!")

if __name__ == '__main__':
    main()