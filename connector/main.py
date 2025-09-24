#!/usr/bin/env python3
"""
Per-user OpenD Connector Service
Runs in each user's dedicated container and handles moomoo API integration
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging

# Add parent directory to path for imports
sys.path.append('/app')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class ConnectorService:
    def __init__(self):
        self.user_id = os.getenv('USER_ID')
        self.platform_api_url = os.getenv('PLATFORM_API_URL', 'http://platform-api:5000')
        self.api_key = os.getenv('API_KEY')

        self.opend_process = None
        self.opend_configured = False
        self.config = self.load_config()

        logger.info(f"Connector started for user {self.user_id}")

    def load_config(self):
        """Load configuration from mounted secret"""
        config_path = '/app/config/config.json'
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {
                'configured': False,
                'moomoo_host': '127.0.0.1',
                'moomoo_port': 11111,
                'security_firm': 'FUTUSG',
                'trade_market': 'US'
            }

    def start_opend(self):
        """Start OpenD process"""
        if not self.config.get('configured', False):
            logger.warning("OpenD not configured, cannot start")
            return False

        try:
            # In production, this would start the actual OpenD binary
            # For now, we'll simulate it
            logger.info("Starting OpenD...")

            # Simulate OpenD startup
            time.sleep(5)
            self.opend_configured = True

            logger.info("OpenD started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start OpenD: {e}")
            return False

    def sync_data_to_platform(self):
        """Sync trading data to the main platform"""
        if not self.opend_configured:
            return {'status': 'error', 'message': 'OpenD not configured'}

        try:
            # Import data sync functionality
            from data_sync import sync_moomoo_data

            # Perform data sync
            result = sync_moomoo_data()

            # Send data to platform API
            if result.get('status') == 'success':
                self.send_data_to_platform(result)

            return result

        except Exception as e:
            logger.error(f"Data sync failed: {e}")
            return {'status': 'error', 'message': str(e)}

    def send_data_to_platform(self, sync_result):
        """Send synced data to the main platform"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            # This would send the data to the platform's API
            # For now, just log it
            logger.info(f"Would send sync result to platform: {sync_result}")

        except Exception as e:
            logger.error(f"Failed to send data to platform: {e}")

# Initialize connector service
connector = ConnectorService()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'user_id': connector.user_id,
        'opend_configured': connector.opend_configured,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    ready = connector.config.get('configured', False)
    status_code = 200 if ready else 503

    return jsonify({
        'status': 'ready' if ready else 'not_ready',
        'configured': ready,
        'user_id': connector.user_id
    }), status_code

@app.route('/configure', methods=['POST'])
def configure_opend():
    """Configure OpenD settings"""
    try:
        data = request.get_json()

        # Update configuration
        connector.config.update(data)
        connector.config['configured'] = True

        # Save configuration
        with open('/app/config/config.json', 'w') as f:
            json.dump(connector.config, f)

        # Start OpenD with new configuration
        if connector.start_opend():
            return jsonify({'status': 'success', 'message': 'OpenD configured and started'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to start OpenD'}), 500

    except Exception as e:
        logger.error(f"Configuration failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/sync', methods=['POST'])
def trigger_sync():
    """Trigger data synchronization"""
    result = connector.sync_data_to_platform()
    status_code = 200 if result.get('status') == 'success' else 500
    return jsonify(result), status_code

@app.route('/status', methods=['GET'])
def get_status():
    """Get connector status"""
    return jsonify({
        'user_id': connector.user_id,
        'opend_configured': connector.opend_configured,
        'config': {
            'configured': connector.config.get('configured', False),
            'security_firm': connector.config.get('security_firm'),
            'trade_market': connector.config.get('trade_market')
        },
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    # Start OpenD if configured
    if connector.config.get('configured', False):
        connector.start_opend()

    # Start Flask app
    app.run(host='0.0.0.0', port=8000, debug=False)