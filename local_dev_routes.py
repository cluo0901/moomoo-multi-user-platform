"""
Local development routes that bypass JWT authentication
Only for testing purposes in local environment
"""

from flask import Blueprint, request, jsonify
from models import User, db
import os

# Only create this blueprint in local development
local_dev_bp = Blueprint('local_dev', __name__)

@local_dev_bp.route('/dev/save-credentials', methods=['POST'])
def save_credentials_dev():
    """
    Local development endpoint to save credentials without JWT authentication
    This bypasses the token issues we're having in local development
    """

    # Only allow in development (not production)
    if os.getenv('ENVIRONMENT') == 'production':
        return jsonify({'error': 'Endpoint not available in production'}), 404

    try:
        data = request.get_json()

        # Get Alice's user (hardcoded for local testing)
        user = User.query.filter_by(username='alice').first()
        if not user:
            return jsonify({'error': 'User alice not found'}), 404

        # Required OpenD configuration
        required_fields = ['moomoo_host', 'moomoo_port', 'security_firm', 'trade_market']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Log the configuration (in local development)
        print(f"=== LOCAL DEV: Configuring credentials for Alice ===")
        print(f"Host: {data.get('moomoo_host')}:{data.get('moomoo_port')}")
        print(f"Firm: {data.get('security_firm')}")
        print(f"Market: {data.get('trade_market')}")
        print(f"Username: {data.get('moomoo_username')}")
        print(f"Password: {'*' * len(data.get('moomoo_password', ''))}")
        print("=== Configuration would be saved in production ===")

        # Update user status to indicate configuration is complete
        user.openapi_configured = True
        user.container_status = 'configured_local'
        db.session.commit()

        return jsonify({
            'message': 'Credentials configured successfully (local development mode)',
            'status': 'success',
            'container_status': 'configured_local',
            'note': 'In production, this would provision a real container with OpenD'
        })

    except Exception as e:
        print(f"Local dev error: {e}")
        return jsonify({'error': 'Configuration failed', 'details': str(e)}), 500

@local_dev_bp.route('/dev/alice-data', methods=['GET'])
def get_alice_data_dev():
    """
    Development endpoint to check Alice's data without JWT authentication
    """
    if os.getenv('ENVIRONMENT') == 'production':
        return jsonify({'error': 'Endpoint not available in production'}), 404

    try:
        from models import Trade, Order, Position

        # Find Alice
        user = User.query.filter_by(username='alice').first()
        if not user:
            return jsonify({'error': 'Alice not found'}), 404

        # Get her data counts
        trades_count = Trade.query.filter_by(user_id=user.id).count()
        orders_count = Order.query.filter_by(user_id=user.id).count()
        positions_count = Position.query.filter_by(user_id=user.id).count()

        # Get sample trades
        sample_trades = Trade.query.filter_by(user_id=user.id).order_by(Trade.deal_time.desc()).limit(5).all()

        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'openapi_configured': user.openapi_configured,
                'container_status': user.container_status
            },
            'data_counts': {
                'trades': trades_count,
                'orders': orders_count,
                'positions': positions_count
            },
            'sample_trades': [
                {
                    'deal_id': trade.deal_id,
                    'code': trade.code,
                    'stock_name': trade.stock_name,
                    'deal_time': trade.deal_time.isoformat() if trade.deal_time else None,
                    'qty': trade.qty,
                    'price': trade.price,
                    'val': trade.val,
                    'side': trade.side
                } for trade in sample_trades
            ]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@local_dev_bp.route('/dev/alice-dashboard-stats', methods=['GET'])
def get_alice_dashboard_stats():
    """Development dashboard stats for Alice without authentication"""
    if os.getenv('ENVIRONMENT') == 'production':
        return jsonify({'error': 'Endpoint not available in production'}), 404

    try:
        from models import Trade, Order, Position
        from datetime import datetime, timedelta
        from sqlalchemy import func, desc

        user = User.query.filter_by(username='alice').first()
        if not user:
            return jsonify({'error': 'Alice not found'}), 404

        # Last 30 days stats
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=30)

        trades = Trade.query.filter(
            Trade.user_id == user.id,
            Trade.deal_time >= start_dt,
            Trade.deal_time < end_dt
        ).all()

        total_trades = len(trades)
        total_volume = sum(trade.val for trade in trades)
        buy_volume = sum(trade.val for trade in trades if trade.side == 'BUY')
        sell_volume = sum(trade.val for trade in trades if trade.side == 'SELL')

        # Get positions
        latest_snapshot = db.session.query(func.max(Position.snapshot_time)).filter_by(user_id=user.id).scalar()
        positions_stats = {'total_positions': 0, 'total_market_value': 0, 'total_unrealized_pl': 0}

        if latest_snapshot:
            positions = Position.query.filter(
                Position.user_id == user.id,
                Position.snapshot_time == latest_snapshot
            ).all()
            positions_stats = {
                'total_positions': len(positions),
                'total_market_value': sum(pos.market_val or 0 for pos in positions),
                'total_unrealized_pl': sum(pos.unrealized_pl or 0 for pos in positions),
            }

        return jsonify({
            'trades_stats': {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'buy_volume': buy_volume,
                'sell_volume': sell_volume
            },
            'positions_stats': positions_stats,
            'user_id': user.id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@local_dev_bp.route('/dev/alice-trades', methods=['GET'])
def get_alice_trades():
    """Development trades endpoint for Alice without authentication"""
    if os.getenv('ENVIRONMENT') == 'production':
        return jsonify({'error': 'Endpoint not available in production'}), 404

    try:
        from models import Trade
        from sqlalchemy import desc

        user = User.query.filter_by(username='alice').first()
        if not user:
            return jsonify({'error': 'Alice not found'}), 404

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        trades = Trade.query.filter_by(user_id=user.id).order_by(desc(Trade.deal_time)).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'trades': [{
                'deal_id': trade.deal_id,
                'code': trade.code,
                'stock_name': trade.stock_name,
                'deal_time': trade.deal_time.isoformat() if trade.deal_time else None,
                'qty': trade.qty,
                'price': trade.price,
                'val': trade.val,
                'side': trade.side,
                'order_id': trade.order_id
            } for trade in trades.items],
            'total': trades.total,
            'pages': trades.pages,
            'current_page': page,
            'per_page': per_page
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500