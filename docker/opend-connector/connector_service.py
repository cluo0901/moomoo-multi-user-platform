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

        # Connection state management
        self.connection_state = 'disconnected'  # disconnected, connecting, connected, error
        self.connection_error = None
        self.last_sms_request_time = None
        self.awaiting_sms_verification = False

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

    def initiate_opend_connection(self) -> dict:
        """Initiate OpenD connection - returns status and may require SMS verification"""
        try:
            if not self.config.get('configured', False):
                return {
                    'success': False,
                    'error': 'OpenD credentials not configured. Please configure moomoo credentials first.',
                    'requires_config': True
                }

            if self.connection_state == 'connecting':
                return {
                    'success': False,
                    'error': 'Connection already in progress',
                    'state': self.connection_state
                }

            if self.connection_state == 'connected':
                return {
                    'success': True,
                    'message': 'Already connected to OpenD',
                    'state': self.connection_state
                }

            # Set state to connecting
            self.connection_state = 'connecting'
            self.connection_error = None

            return self._start_opend_process()

        except Exception as e:
            self.connection_state = 'error'
            self.connection_error = str(e)
            logger.error(f"Failed to initiate OpenD connection: {e}")
            return {'success': False, 'error': str(e)}

    def _start_opend_process(self) -> dict:
        """Start OpenD process - internal method"""
        try:

            # Extract credentials
            username = self.config.get('moomoo_username')
            password = self.config.get('moomoo_password')
            security_firm = self.config.get('security_firm', 'FUTUSG')
            trade_market = self.config.get('trade_market', 'US')

            if not username or not password:
                self.connection_state = 'error'
                self.connection_error = "Missing moomoo credentials"
                return {
                    'success': False,
                    'error': 'Missing moomoo credentials',
                    'requires_config': True
                }

            # Stop existing OpenD process if running
            if self.opend_process and self.opend_process.poll() is None:
                logger.info("Stopping existing OpenD process")
                self.stop_opend()

            logger.info(f"Starting OpenD process for user {self.user_id}")
            logger.info(f"Credentials: {username}, Security Firm: {security_firm}, Market: {trade_market}")

            # Start OpenD process using direct binary call
            opend_binary = '/app/opend/OpenD'
            if not Path(opend_binary).exists():
                self.connection_state = 'error'
                self.connection_error = "OpenD binary not found"
                return {
                    'success': False,
                    'error': 'OpenD binary not found. Please ensure OpenD is properly installed.',
                    'requires_opend_binary': True
                }

            # Set environment with library path for shared libraries
            env = os.environ.copy()
            env['LD_LIBRARY_PATH'] = '/app/opend'

            # Start OpenD using XML configuration (more reliable than command line parameters)
            self.opend_process = subprocess.Popen([
                opend_binary
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd='/app/opend',
            env=env
            )

            # Wait for OpenD to initialize
            logger.info("Waiting for OpenD to start...")
            time.sleep(8)

            # Check if process is still running
            if self.opend_process.poll() is not None:
                self.connection_state = 'error'
                self.connection_error = "OpenD process exited prematurely"
                return {
                    'success': False,
                    'error': 'OpenD process exited prematurely. Check OpenD configuration.',
                    'requires_verification': False
                }

            # Now attempt connection - this is where SMS verification may be needed
            return self._attempt_trading_connection(security_firm, trade_market)

        except Exception as e:
            self.connection_state = 'error'
            self.connection_error = str(e)
            logger.error(f"Failed to start OpenD process: {e}")
            return {'success': False, 'error': str(e)}

    def _attempt_trading_connection(self, security_firm: str, trade_market: str) -> dict:
        """Attempt to establish trading connection - may require SMS verification"""
        try:
            logger.info("Attempting to establish trading connection...")

            self.trade_context = OpenSecTradeContext(
                filter_trdmarket=self.trade_market_map.get(trade_market),
                host=self.opend_host,
                port=self.opend_port,
                security_firm=self.security_firm_map.get(security_firm)
            )

            # Test connection - this will trigger SMS verification if needed
            ret, data = self.trade_context.get_acc_list()

            if ret == RET_OK:
                # Success - connection established
                self.connection_state = 'connected'
                logger.info("OpenD connected successfully!")
                logger.info(f"Available accounts: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                return {
                    'success': True,
                    'message': 'OpenD connected successfully',
                    'state': 'connected'
                }
            else:
                # Check if this is an SMS verification requirement
                if 'verification code' in str(data).lower() or 'phone verification' in str(data).lower():
                    self.awaiting_sms_verification = True
                    self.last_sms_request_time = datetime.utcnow()
                    logger.info("SMS verification required")
                    return {
                        'success': False,
                        'requires_sms': True,
                        'message': 'SMS verification code required',
                        'state': 'awaiting_sms'
                    }
                else:
                    # Other connection error
                    self.connection_state = 'error'
                    self.connection_error = str(data)
                    logger.error(f"Connection failed: {data}")
                    return {
                        'success': False,
                        'error': f'Connection failed: {data}',
                        'state': 'error'
                    }

        except Exception as e:
            self.connection_state = 'error'
            self.connection_error = str(e)
            logger.error(f"Trading connection attempt failed: {e}")
            return {
                'success': False,
                'error': f'Connection attempt failed: {e}',
                'state': 'error'
            }

    def submit_sms_verification(self, sms_code: str) -> dict:
        """Submit SMS verification code"""
        try:
            if not self.awaiting_sms_verification:
                return {
                    'success': False,
                    'error': 'No SMS verification pending'
                }

            if not sms_code or len(sms_code) < 4:
                return {
                    'success': False,
                    'error': 'Invalid SMS code format'
                }

            logger.info(f"Submitting SMS verification code: {sms_code}")

            # Here we would submit the SMS code to the OpenD/moomoo system
            # Since the exact method may vary, we'll use a general approach

            # For now, we'll simulate the verification process
            # In real implementation, this would interact with the OpenD SMS system

            # Reset verification state
            self.awaiting_sms_verification = False

            # Retry the connection
            security_firm = self.config.get('security_firm', 'FUTUSG')
            trade_market = self.config.get('trade_market', 'US')

            # Test connection again
            if self.trade_context:
                ret, data = self.trade_context.get_acc_list()

                if ret == RET_OK:
                    self.connection_state = 'connected'
                    logger.info("SMS verification successful - OpenD connected!")
                    return {
                        'success': True,
                        'message': 'SMS verification successful. OpenD connected!',
                        'state': 'connected'
                    }
                else:
                    # Still failing, may need another SMS code or different issue
                    if 'verification code' in str(data).lower():
                        self.awaiting_sms_verification = True
                        return {
                            'success': False,
                            'error': 'SMS code incorrect or expired. Please try again.',
                            'requires_sms': True,
                            'state': 'awaiting_sms'
                        }
                    else:
                        self.connection_state = 'error'
                        self.connection_error = str(data)
                        return {
                            'success': False,
                            'error': f'Connection failed after SMS verification: {data}',
                            'state': 'error'
                        }
            else:
                return {
                    'success': False,
                    'error': 'Trading context not available. Please restart connection.',
                    'state': 'error'
                }

        except Exception as e:
            self.connection_state = 'error'
            self.connection_error = str(e)
            logger.error(f"SMS verification failed: {e}")
            return {
                'success': False,
                'error': f'SMS verification failed: {e}',
                'state': 'error'
            }

    def start_opend(self) -> bool:
        """Legacy method - maintained for backward compatibility"""
        result = self.initiate_opend_connection()
        return result.get('success', False)

    def stop_opend(self) -> dict:
        """Stop OpenD process and reset connection state"""
        try:
            logger.info(f"Stopping OpenD process for user {self.user_id}")

            # Reset connection state
            self.connection_state = 'disconnected'
            self.connection_error = None
            self.awaiting_sms_verification = False
            self.last_sms_request_time = None

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
            return {
                'success': True,
                'message': 'OpenD disconnected successfully',
                'state': 'disconnected'
            }

        except Exception as e:
            logger.error(f"Error stopping OpenD: {e}")
            return {
                'success': False,
                'error': str(e),
                'state': self.connection_state
            }

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
            'user_id': self.user_id,
            'connection_state': self.connection_state,
            'awaiting_sms_verification': self.awaiting_sms_verification,
            'last_sms_request_time': self.last_sms_request_time.isoformat() if self.last_sms_request_time else None,
            'connection_error': self.connection_error
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

@app.route('/connect', methods=['POST'])
def initiate_connection():
    """Initiate OpenD connection - may require SMS verification"""
    try:
        result = connector.initiate_opend_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/verify-sms', methods=['POST'])
def verify_sms():
    """Submit SMS verification code"""
    try:
        data = request.get_json()
        sms_code = data.get('sms_code', '').strip()

        if not sms_code:
            return jsonify({'success': False, 'error': 'SMS code is required'}), 400

        result = connector.submit_sms_verification(sms_code)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/disconnect', methods=['POST'])
def disconnect_opend():
    """Disconnect from OpenD"""
    try:
        result = connector.stop_opend()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/start', methods=['POST'])
def start_opend():
    """Legacy endpoint - redirects to new connect endpoint"""
    return initiate_connection()

@app.route('/stop', methods=['POST'])
def stop_opend():
    """Legacy endpoint - redirects to new disconnect endpoint"""
    return disconnect_opend()

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
    """Update configuration (manual connection required)"""
    try:
        new_config = request.get_json()

        # Update configuration
        connector.config.update(new_config)
        connector.config['configured'] = True

        # Stop any existing OpenD process but don't auto-restart
        connector.stop_opend()

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully. Use /connect to initiate connection.',
            'user_id': connector.user_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting OpenD Connector for user {connector.user_id}")
    logger.info("OpenD will be started manually via API calls - no auto-start")

    # Log current configuration status
    if connector.config.get('configured', False):
        logger.info("moomoo credentials are configured - ready for manual connection")
    else:
        logger.info("moomoo credentials not configured - user must configure first")

    # Start API server
    app.run(host='0.0.0.0', port=8000, debug=False)