#!/usr/bin/env python3
"""
Database migration script to add UserCredentials table and migrate existing user data
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, User, UserCredentials
from flask_jwt_extended import JWTManager

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trading_dashboard.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'super-secret-key-change-in-production'

    db.init_app(app)
    JWTManager(app)

    return app

def migrate_database():
    """Create new tables and migrate existing data"""
    app = create_app()

    with app.app_context():
        print("Creating database tables...")
        db.create_all()

        # Check if alice user exists and create credentials if needed
        alice = User.query.filter_by(username='alice').first()
        if alice:
            # Check if alice already has credentials
            existing_creds = UserCredentials.query.filter_by(user_id=alice.id).first()
            if not existing_creds:
                print("Creating credentials for alice user...")
                credentials = UserCredentials(
                    user_id=alice.id,
                    moomoo_username='102872417',
                    security_firm='FUTUSG',
                    trade_market='US'
                )
                credentials.set_encrypted_password('L850901c')
                db.session.add(credentials)
                alice.openapi_configured = True
                db.session.commit()
                print("Alice credentials created successfully!")
            else:
                print("Alice credentials already exist.")
        else:
            print("Alice user not found - will be created on first login")

        print("Database migration completed successfully!")

if __name__ == '__main__':
    migrate_database()