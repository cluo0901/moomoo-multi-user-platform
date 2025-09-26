#!/usr/bin/env python3
"""
OpenD Connector Service
Runs inside each user's container and provides API wrapper around OpenD
Each user gets their own instance with isolated credentials
"""

import os
import json
import logging
import asyncio
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from flask import Flask, request, jsonify
from futu import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class OpenDConnector:
    """Manages OpenD connection and provides API wrapper"""

    def __init__(self):
        self.user_id = os.getenv('USER_ID')
        self.config_path = Path('/app/config/config.json')
        self.opend_host = '127.0.0.1'
        self.opend_port = 11111
        self.opend_process = None
        self.trade_context = None
        self.quote_context = None

        # Load user configuration
        self.config = self.load_config()

        # Security firm mapping
        self.security_firm_map = {
            'FUTUSG': SecurityFirm.FUTUSG,
            'FUTUSECURITIES': SecurityFirm.FUTUSECURITIES,
            'FUTUINC': SecurityFirm.FUTUINC,
            'FUTUAU': SecurityFirm.FUTUAU
        }

        self.trade_market_map = {
            'US': TrdMarket.US,
            'HK': TrdMarket.HK,
            'CN': TrdMarket.CN,
            'SG': TrdMarket.SG,
            'AU': TrdMarket.AU
        }

    def load_config(self) -> Dict[str, Any]:
        """Load user configuration from mounted secret"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration for user {self.user_id}")
                return config
            else:
                logger.warning(f"Configuration file not found at {self.config_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}

    def start_opend(self) -> bool:
        """Start OpenD process with user credentials"""
        try:
            if not self.config.get('configured', False):
                logger.warning("OpenD not configured - cannot start")
                return False

            # Extract credentials
            username = self.config.get('moomoo_username')
            password = self.config.get('moomoo_password')
            security_firm = self.config.get('security_firm', 'FUTUSG')
            trade_market = self.config.get('trade_market', 'US')

            if not username or not password:
                logger.error("Missing moomoo credentials")
                return False

            # Stop existing OpenD process if running
            if self.opend_process and self.opend_process.poll() is None:
                logger.info("Stopping existing OpenD process")
                self.stop_opend()

            logger.info(f"Starting real OpenD process for user {self.user_id}")
            logger.info(f"Credentials: {username}, Security Firm: {security_firm}, Market: {trade_market}")

            # Set environment variables for the startup script
            env = os.environ.copy()
            env.update({
                'USER_ID': str(self.user_id),
                'MOOMOO_USERNAME': username,
                'MOOMOO_PASSWORD': password,
                'SECURITY_FIRM': security_firm,
                'TRADE_MARKET': trade_market,
                'TRADE_ENV': '1',  # 1 = Real trading, 0 = Sandbox
                'LOG_LEVEL': 'info'
            })

            # Start OpenD using the startup script
            self.opend_process = subprocess.Popen([
                '/app/scripts/start-opend.sh'
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd='/app'
            )

            # Wait for OpenD to initialize
            logger.info("Waiting for OpenD to start...")
            time.sleep(10)

            # Check if process is still running
            if self.opend_process.poll() is not None:
                logger.error("OpenD process exited prematurely")
                return False

            # Initialize trading context with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempting to connect to OpenD (attempt {attempt + 1}/{max_retries})")

                    self.trade_context = OpenSecTradeContext(
                        filter_trdmarket=self.trade_market_map.get(trade_market),
                        host=self.opend_host,
                        port=self.opend_port,
                        security_firm=self.security_firm_map.get(security_firm)
                    )

                    # Test connection
                    ret, data = self.trade_context.get_acc_list()
                    if ret == RET_OK:
                        logger.info("OpenD started and connected successfully")
                        logger.info(f"Available accounts: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                        return True
                    else:
                        logger.warning(f"Connection attempt {attempt + 1} failed: {data}")
                        if attempt < max_retries - 1:
                            time.sleep(5)

                except Exception as e:
                    logger.warning(f"Connection attempt {attempt + 1} error: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(5)

            logger.error("Failed to establish connection to OpenD after all retries")
            return False

        except Exception as e:
            logger.error(f"Failed to start OpenD: {e}")
            return False

    def stop_opend(self):
        """Stop OpenD process"""
        try:
            logger.info(f"Stopping OpenD process for user {self.user_id}")

            # Close trading contexts first
            if self.trade_context:
                try:
                    self.trade_context.close()
                    logger.info("Trading context closed")
                except Exception as e:
                    logger.warning(f"Error closing trading context: {e}")
                finally:
                    self.trade_context = None

            if self.quote_context:
                try:
                    self.quote_context.close()
                    logger.info("Quote context closed")
                except Exception as e:
                    logger.warning(f"Error closing quote context: {e}")
                finally:
                    self.quote_context = None

            # Stop OpenD process
            if self.opend_process:
                try:
                    if self.opend_process.poll() is None:  # Process is still running
                        logger.info("Terminating OpenD process...")
                        self.opend_process.terminate()

                        # Wait for graceful termination
                        try:
                            self.opend_process.wait(timeout=10)
                            logger.info("OpenD process terminated gracefully")
                        except subprocess.TimeoutExpired:
                            logger.warning("OpenD process did not terminate gracefully, forcing kill...")
                            self.opend_process.kill()
                            self.opend_process.wait()
                            logger.info("OpenD process killed")
                    else:
                        logger.info("OpenD process already terminated")

                except Exception as e:
                    logger.error(f"Error terminating OpenD process: {e}")
                finally:
                    self.opend_process = None

            logger.info("OpenD stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping OpenD: {e}")

    def is_opend_running(self) -> bool:
        """Check if OpenD process is running"""
        if not self.opend_process:
            return False
        return self.opend_process.poll() is None

    def get_opend_status(self) -> dict:
        """Get detailed OpenD status information"""
        status = {
            'process_running': self.is_opend_running(),
            'trade_context_active': self.trade_context is not None,
            'quote_context_active': self.quote_context is not None,
            'configured': self.config.get('configured', False),
            'user_id': self.user_id
        }

        if self.opend_process:
            status['process_id'] = self.opend_process.pid
            status['return_code'] = self.opend_process.returncode

        return status

    def safe_api_call(self, description: str, api_func, *args, **kwargs) -> pd.DataFrame:
        """Safe wrapper for OpenD API calls"""
        try:
            ret, data = api_func(*args, **kwargs)
            if ret == RET_OK:
                return data if isinstance(data, pd.DataFrame) else pd.DataFrame()
            else:
                logger.warning(f"{description} failed: {data}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"{description} error: {e}")
            return pd.DataFrame()

    def get_trades(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get trading history for date range"""
        if not self.trade_context:
            return {'error': 'OpenD not connected', 'trades': []}

        try:
            # Get trades in chunks to handle large date ranges
            all_trades = []
            chunk_size = 180  # days

            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

            current_start = start_dt
            while current_start < end_dt:
                current_end = min(current_start + timedelta(days=chunk_size - 1), end_dt)

                chunk_start_str = current_start.strftime('%Y-%m-%d')
                chunk_end_str = current_end.strftime('%Y-%m-%d')

                logger.info(f"Fetching trades from {chunk_start_str} to {chunk_end_str}")

                trades_df = self.safe_api_call(
                    f"trades {chunk_start_str}-{chunk_end_str}",
                    self.trade_context.history_deal_list_query,
                    start=chunk_start_str,
                    end=chunk_end_str
                )

                if not trades_df.empty:
                    # Convert DataFrame to list of dictionaries
                    chunk_trades = trades_df.to_dict('records')
                    all_trades.extend(chunk_trades)

                current_start = current_end + timedelta(days=1)

            logger.info(f"Retrieved {len(all_trades)} trades total")

            return {
                'success': True,
                'trades': all_trades,
                'count': len(all_trades),
                'date_range': {'start': start_date, 'end': end_date}
            }

        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return {'error': str(e), 'trades': []}

    def get_orders(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get order history for date range"""
        if not self.trade_context:
            return {'error': 'OpenD not connected', 'orders': []}

        try:
            orders_df = self.safe_api_call(
                f"orders {start_date}-{end_date}",
                self.trade_context.history_order_list_query,
                start=start_date,
                end=end_date,
                status_filter_list=[]
            )

            orders = orders_df.to_dict('records') if not orders_df.empty else []

            return {
                'success': True,
                'orders': orders,
                'count': len(orders),
                'date_range': {'start': start_date, 'end': end_date}
            }

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return {'error': str(e), 'orders': []}

    def get_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        if not self.trade_context:
            return {'error': 'OpenD not connected', 'positions': []}

        try:
            positions_df = self.safe_api_call(
                "current positions",
                self.trade_context.position_list_query
            )

            positions = positions_df.to_dict('records') if not positions_df.empty else []

            return {
                'success': True,
                'positions': positions,
                'count': len(positions),
                'snapshot_time': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {'error': str(e), 'positions': []}

# Global connector instance
connector = OpenDConnector()

# API Endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    opend_status = connector.get_opend_status()
    return jsonify({
        'status': 'healthy',
        'user_id': connector.user_id,
        'opend_connected': connector.trade_context is not None,
        'opend_process_running': opend_status['process_running'],
        'configured': connector.config.get('configured', False),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/status', methods=['GET'])
def detailed_status():
    """Detailed OpenD status endpoint"""
    return jsonify(connector.get_opend_status())

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    ready = (
        connector.config.get('configured', False) and
        connector.trade_context is not None
    )

    status_code = 200 if ready else 503

    return jsonify({
        'status': 'ready' if ready else 'not_ready',
        'user_id': connector.user_id,
        'opend_connected': connector.trade_context is not None,
        'configured': connector.config.get('configured', False)
    }), status_code

@app.route('/start', methods=['POST'])
def start_opend():
    """Start OpenD connection"""
    try:
        success = connector.start_opend()
        return jsonify({
            'success': success,
            'message': 'OpenD started successfully' if success else 'Failed to start OpenD',
            'user_id': connector.user_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_opend():
    """Stop OpenD connection"""
    try:
        connector.stop_opend()
        return jsonify({
            'success': True,
            'message': 'OpenD stopped successfully',
            'user_id': connector.user_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/sync/trades', methods=['GET'])
def sync_trades():
    """Sync trades for date range"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400

    result = connector.get_trades(start_date, end_date)
    return jsonify(result)

@app.route('/sync/orders', methods=['GET'])
def sync_orders():
    """Sync orders for date range"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400

    result = connector.get_orders(start_date, end_date)
    return jsonify(result)

@app.route('/sync/positions', methods=['GET'])
def sync_positions():
    """Sync current positions"""
    result = connector.get_positions()
    return jsonify(result)

@app.route('/sync/all', methods=['POST'])
def sync_all_data():
    """Sync all trading data"""
    try:
        data = request.get_json() or {}

        # Default to last 730 days if not specified
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        start_date = data.get('start_date',
                            (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d'))

        # Sync trades
        trades_result = connector.get_trades(start_date, end_date)

        # Sync orders
        orders_result = connector.get_orders(start_date, end_date)

        # Sync positions
        positions_result = connector.get_positions()

        return jsonify({
            'success': True,
            'sync_time': datetime.utcnow().isoformat(),
            'date_range': {'start': start_date, 'end': end_date},
            'results': {
                'trades': trades_result,
                'orders': orders_result,
                'positions': positions_result
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration (sensitive data masked)"""
    config = connector.config.copy()

    # Mask sensitive data
    if 'moomoo_password' in config:
        config['moomoo_password'] = '*' * len(config['moomoo_password'])

    return jsonify({
        'user_id': connector.user_id,
        'config': config,
        'opend_connected': connector.trade_context is not None
    })

@app.route('/config', methods=['POST'])
def update_config():
    """Update configuration and restart OpenD"""
    try:
        new_config = request.get_json()

        # Update configuration
        connector.config.update(new_config)
        connector.config['configured'] = True

        # Restart OpenD with new config
        connector.stop_opend()
        time.sleep(1)
        success = connector.start_opend()

        return jsonify({
            'success': success,
            'message': 'Configuration updated and OpenD restarted' if success else 'Configuration updated but OpenD failed to start',
            'user_id': connector.user_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting OpenD Connector for user {connector.user_id}")

    # Auto-start OpenD if configured
    if connector.config.get('configured', False):
        logger.info("Auto-starting OpenD...")
        connector.start_opend()

    # Start API server
    app.run(host='0.0.0.0', port=8000, debug=False)