"""
Container-based Data Sync Service
Communicates with user containers via API instead of direct OpenD connections
Each user has their own container with isolated credentials
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from models import Trade, Order, Position, db
import logging

logger = logging.getLogger(__name__)

class ContainerDataSync:
    """Handles data synchronization via user container APIs"""

    def __init__(self, user_id: int, container_url: str):
        self.user_id = user_id
        self.container_url = container_url.rstrip('/')
        self.timeout = 30

    def _make_request(self, endpoint: str, method: str = 'GET', params: dict = None, json_data: dict = None):
        """Make HTTP request to user container"""
        try:
            url = f"{self.container_url}{endpoint}"

            if method == 'GET':
                response = requests.get(url, params=params, timeout=self.timeout)
            elif method == 'POST':
                response = requests.post(url, json=json_data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Container API request failed: {e}")
            return {'success': False, 'error': str(e)}

    def check_container_status(self):
        """Check if user container is ready"""
        try:
            response = self._make_request('/ready')
            return response.get('status') == 'ready'
        except:
            return False

    def start_container_opend(self):
        """Start OpenD in user container"""
        return self._make_request('/start', method='POST')

    def sync_trades(self, start_date: str, end_date: str):
        """Sync trades from user container"""
        logger.info(f"Syncing trades for user {self.user_id} from {start_date} to {end_date}")

        # Get trades from container
        response = self._make_request('/sync/trades', params={
            'start_date': start_date,
            'end_date': end_date
        })

        if not response.get('success'):
            logger.error(f"Failed to sync trades: {response.get('error', 'Unknown error')}")
            return 0

        trades_data = response.get('trades', [])
        logger.info(f"Received {len(trades_data)} trades from container")

        # Process and save trades to database
        synced_count = 0
        for trade_data in trades_data:
            try:
                # Parse deal time
                deal_time = None
                if trade_data.get('create_time'):
                    deal_time = self._parse_datetime(trade_data['create_time'])

                if not deal_time:
                    logger.warning(f"Invalid deal_time in trade: {trade_data}")
                    continue

                # Calculate val if not present
                qty = float(trade_data.get('qty', 0))
                price = float(trade_data.get('price', 0))
                val = float(trade_data.get('val', 0)) if trade_data.get('val') else qty * price

                # Check if trade already exists
                existing_trade = Trade.query.filter_by(
                    deal_id=str(trade_data.get('deal_id', '')),
                    user_id=self.user_id
                ).first()

                if existing_trade:
                    continue  # Skip duplicates

                # Create new trade
                trade = Trade(
                    deal_id=str(trade_data.get('deal_id', '')),
                    code=str(trade_data.get('code', '')),
                    stock_name=str(trade_data.get('stock_name', '')),
                    deal_time=deal_time,
                    qty=qty,
                    price=price,
                    val=val,
                    side=str(trade_data.get('trd_side', '')).upper(),
                    order_id=str(trade_data.get('order_id', '')),
                    user_id=self.user_id
                )

                db.session.add(trade)
                synced_count += 1

            except Exception as e:
                logger.error(f"Error processing trade: {e}")
                continue

        # Commit all trades
        db.session.commit()
        logger.info(f"Synced {synced_count} trades for user {self.user_id}")
        return synced_count

    def sync_orders(self, start_date: str, end_date: str):
        """Sync orders from user container"""
        logger.info(f"Syncing orders for user {self.user_id} from {start_date} to {end_date}")

        # Get orders from container
        response = self._make_request('/sync/orders', params={
            'start_date': start_date,
            'end_date': end_date
        })

        if not response.get('success'):
            logger.error(f"Failed to sync orders: {response.get('error', 'Unknown error')}")
            return 0

        orders_data = response.get('orders', [])
        logger.info(f"Received {len(orders_data)} orders from container")

        # Process and save orders to database
        synced_count = 0
        for order_data in orders_data:
            try:
                # Parse create time
                create_time = None
                if order_data.get('create_time'):
                    create_time = self._parse_datetime(order_data['create_time'])

                if not create_time:
                    logger.warning(f"Invalid create_time in order: {order_data}")
                    continue

                # Check if order already exists
                existing_order = Order.query.filter_by(
                    order_id=str(order_data.get('order_id', '')),
                    user_id=self.user_id
                ).first()

                if existing_order:
                    continue  # Skip duplicates

                # Create new order
                order = Order(
                    order_id=str(order_data.get('order_id', '')),
                    code=str(order_data.get('code', '')),
                    stock_name=str(order_data.get('stock_name', '')),
                    trd_side=str(order_data.get('trd_side', '')).upper(),
                    order_type=str(order_data.get('order_type', '')),
                    order_status=str(order_data.get('order_status', '')),
                    qty=float(order_data.get('qty', 0)),
                    price=float(order_data.get('price', 0)) if order_data.get('price') else None,
                    create_time=create_time,
                    updated_time=self._parse_datetime(order_data.get('updated_time')),
                    dealt_qty=float(order_data.get('dealt_qty', 0)),
                    dealt_avg_price=float(order_data.get('dealt_avg_price', 0)) if order_data.get('dealt_avg_price') else None,
                    user_id=self.user_id
                )

                db.session.add(order)
                synced_count += 1

            except Exception as e:
                logger.error(f"Error processing order: {e}")
                continue

        # Commit all orders
        db.session.commit()
        logger.info(f"Synced {synced_count} orders for user {self.user_id}")
        return synced_count

    def sync_positions(self):
        """Sync positions from user container"""
        logger.info(f"Syncing positions for user {self.user_id}")

        # Get positions from container
        response = self._make_request('/sync/positions')

        if not response.get('success'):
            logger.error(f"Failed to sync positions: {response.get('error', 'Unknown error')}")
            return 0

        positions_data = response.get('positions', [])
        logger.info(f"Received {len(positions_data)} positions from container")

        # Clear existing positions for this user (positions are current state snapshots)
        Position.query.filter_by(user_id=self.user_id).delete()

        # Process and save positions to database
        synced_count = 0
        snapshot_time = datetime.utcnow()

        for position_data in positions_data:
            try:
                # Create new position
                position = Position(
                    code=str(position_data.get('code', '')),
                    stock_name=str(position_data.get('stock_name', '')),
                    qty=float(position_data.get('qty', 0)),
                    can_sell_qty=float(position_data.get('can_sell_qty', 0)),
                    cost_price=float(position_data.get('cost_price', 0)) if position_data.get('cost_price') else None,
                    cost_price_valid=bool(position_data.get('cost_price_valid', True)),
                    market_val=float(position_data.get('market_val', 0)) if position_data.get('market_val') else None,
                    nominal_price=float(position_data.get('nominal_price', 0)) if position_data.get('nominal_price') else None,
                    unrealized_pl=float(position_data.get('unrealized_pl', 0)) if position_data.get('unrealized_pl') else None,
                    unrealized_pl_ratio=float(position_data.get('unrealized_pl_ratio', 0)) if position_data.get('unrealized_pl_ratio') else None,
                    realized_pl=float(position_data.get('realized_pl', 0)) if position_data.get('realized_pl') else None,
                    today_buy_val=float(position_data.get('today_buy_val', 0)),
                    today_buy_qty=float(position_data.get('today_buy_qty', 0)),
                    today_sell_val=float(position_data.get('today_sell_val', 0)),
                    today_sell_qty=float(position_data.get('today_sell_qty', 0)),
                    snapshot_time=snapshot_time,
                    user_id=self.user_id
                )

                db.session.add(position)
                synced_count += 1

            except Exception as e:
                logger.error(f"Error processing position: {e}")
                continue

        # Commit all positions
        db.session.commit()
        logger.info(f"Synced {synced_count} positions for user {self.user_id}")
        return synced_count

    def sync_all_data(self, lookback_days: int = 730):
        """Sync all data from user container"""
        logger.info(f"Starting full data sync for user {self.user_id}")

        # Calculate date range
        end_dt = datetime.now().date()
        start_dt = end_dt - timedelta(days=lookback_days - 1)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")

        # Check container status
        if not self.check_container_status():
            # Try to start OpenD
            start_result = self.start_container_opend()
            if not start_result.get('success'):
                return {
                    'status': 'error',
                    'message': f'Container not ready and failed to start OpenD: {start_result.get("error", "Unknown error")}',
                    'sync_time': datetime.utcnow().isoformat()
                }

        result = {
            'status': 'success',
            'sync_time': datetime.utcnow().isoformat(),
            'date_range': {'start': start_date, 'end': end_date},
            'synced_counts': {}
        }

        try:
            # Sync trades
            trades_count = self.sync_trades(start_date, end_date)
            result['synced_counts']['trades'] = trades_count

            # Sync orders
            orders_count = self.sync_orders(start_date, end_date)
            result['synced_counts']['orders'] = orders_count

            # Sync positions
            positions_count = self.sync_positions()
            result['synced_counts']['positions'] = positions_count

            logger.info(f"Data sync completed for user {self.user_id}")
            return result

        except Exception as e:
            logger.error(f"Error during data sync for user {self.user_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'sync_time': datetime.utcnow().isoformat()
            }

    def _parse_datetime(self, date_str):
        """Parse datetime string from container response"""
        if pd.isna(date_str) or date_str == '' or date_str is None:
            return None

        # Try multiple datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse datetime: {date_str}")
        return None


def sync_user_container_data(user_id: int, container_url: str, lookback_days: int = 730):
    """
    Sync data for a specific user from their container
    This replaces the old direct OpenD connection approach
    """
    from app import app

    try:
        with app.app_context():
            sync_service = ContainerDataSync(user_id, container_url)
            return sync_service.sync_all_data(lookback_days)

    except Exception as e:
        logger.error(f"Error syncing data for user {user_id}: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'sync_time': datetime.utcnow().isoformat()
        }


# For compatibility with existing code
def sync_moomoo_data(user_id=None):
    """
    Legacy function - now redirects to container-based sync
    In production, this would get the container URL from the container manager
    """
    if not user_id:
        return {
            'status': 'error',
            'message': 'user_id is required for container-based sync',
            'sync_time': datetime.utcnow().isoformat()
        }

    # In production, get container URL from ContainerManager
    # For now, simulate local development behavior
    from models import User
    from app import app

    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            return {
                'status': 'error',
                'message': f'User {user_id} not found',
                'sync_time': datetime.utcnow().isoformat()
            }

        # For local development, fall back to old data_sync method
        # In production, this would get the actual container URL
        if user.container_status in ['running', 'configured_local']:
            # Simulate container URL (in production this would be real)
            container_url = f"http://moomoo-user-{user_id}.moomoo-users.svc.cluster.local:8000"
            return sync_user_container_data(user_id, container_url)
        else:
            return {
                'status': 'error',
                'message': f'User container not available (status: {user.container_status})',
                'sync_time': datetime.utcnow().isoformat()
            }