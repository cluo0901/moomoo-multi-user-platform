#!/usr/bin/env python3
"""
Local development server runner with database initialization
"""

import os
import sys
from app import app, db
from data_sync import sync_moomoo_data

def init_database():
    """Initialize database tables"""
    print("Initializing database...")
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

def sync_initial_data():
    """Sync initial data from moomoo API"""
    print("Syncing initial data from moomoo API...")
    result = sync_moomoo_data()

    if result['status'] == 'success':
        print(f"✅ Data sync completed successfully!")
        print(f"Synced: {result['synced_counts']}")
    else:
        print(f"❌ Data sync failed: {result.get('message', 'Unknown error')}")
        return False

    return True

def main():
    """Main function to set up and run the application"""
    print("🚀 Starting Moomoo Trading Dashboard...")

    # Check if database file exists
    db_file = 'moomoo_trading.db'
    if not os.path.exists(db_file):
        print("Database not found. Initializing...")
        init_database()

        # Ask user if they want to sync data (skip in non-interactive mode)
        try:
            sync_data = input("Would you like to sync data from moomoo API now? (y/N): ").lower().strip()
            if sync_data == 'y':
                if not sync_initial_data():
                    print("⚠️  Warning: Data sync failed. You can try again later using the web interface.")
            else:
                print("⚠️  Skipping data sync. You can sync data later using the web interface.")
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️  Running in non-interactive mode. Skipping data sync.")
            print("   You can sync data later using the web interface at http://localhost:5000")
    else:
        print("Database found. Skipping initialization.")

    port = 8080
    print(f"\n📊 Dashboard will be available at: http://localhost:{port}")
    print(f"🔄 API endpoints available at: http://localhost:{port}/api")
    print("\nPress Ctrl+C to stop the server\n")

    # Run the Flask development server
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == '__main__':
    main()