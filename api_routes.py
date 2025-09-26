from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models import User, Trade, Order, Position, db
import pandas as pd
from currency_converter import convert_to_usd, converter

api_bp = Blueprint('api', __name__)

def get_current_user():
    """Get current authenticated user"""
    user_id = get_jwt_identity()
    return User.query.get(int(user_id)) if user_id else None

@api_bp.route('/trades', methods=['GET'])
@jwt_required()
def get_trades():
    try:
        # Get current user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        code = request.args.get('code')
        side = request.args.get('side')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))

        # Build query filtered by user
        query = Trade.query.filter_by(user_id=user.id)

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Trade.deal_time >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Trade.deal_time < end_dt)

        if code:
            query = query.filter(Trade.code.ilike(f'%{code}%'))

        if side:
            query = query.filter(Trade.side == side.upper())

        # Order by deal_time desc
        query = query.order_by(desc(Trade.deal_time))

        # Paginate
        trades = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'trades': [trade.to_dict() for trade in trades.items],
            'total': trades.total,
            'pages': trades.pages,
            'current_page': page,
            'per_page': per_page
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    try:
        # Get current user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        code = request.args.get('code')
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))

        # Build query filtered by user
        query = Order.query.filter_by(user_id=user.id)

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Order.create_time >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Order.create_time < end_dt)

        if code:
            query = query.filter(Order.code.ilike(f'%{code}%'))

        if status:
            query = query.filter(Order.order_status == status.upper())

        # Order by create_time desc
        query = query.order_by(desc(Order.create_time))

        # Paginate
        orders = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page,
            'per_page': per_page
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/positions', methods=['GET'])
@jwt_required()
def get_positions():
    try:
        # Get current user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get latest positions for this user
        latest_snapshot = db.session.query(func.max(Position.snapshot_time)).filter_by(user_id=user.id).scalar()

        if not latest_snapshot:
            return jsonify({'positions': [], 'snapshot_time': None})

        positions = Position.query.filter(
            Position.user_id == user.id,
            Position.snapshot_time == latest_snapshot
        ).order_by(desc(Position.market_val)).all()

        return jsonify({
            'positions': [pos.to_dict() for pos in positions],
            'snapshot_time': latest_snapshot.isoformat() if latest_snapshot else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/dashboard-stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    try:
        # Get current user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Default to last 30 days if no dates provided
        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)
        else:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        # Get trades in date range for current user
        trades = Trade.query.filter(
            Trade.user_id == user.id,
            Trade.deal_time >= start_dt,
            Trade.deal_time < end_dt
        ).all()

        # Calculate stats with currency conversion
        total_trades = len(trades)
        total_volume = sum(convert_to_usd(trade.val, trade.code, trade.deal_time) for trade in trades)
        buy_volume = sum(convert_to_usd(trade.val, trade.code, trade.deal_time) for trade in trades if trade.side == 'BUY')
        sell_volume = sum(convert_to_usd(trade.val, trade.code, trade.deal_time) for trade in trades if trade.side == 'SELL')

        # Get current positions stats for user
        latest_snapshot = db.session.query(func.max(Position.snapshot_time)).filter_by(user_id=user.id).scalar()
        positions_stats = {'total_positions': 0, 'total_market_value': 0, 'total_unrealized_pl': 0}

        if latest_snapshot:
            positions = Position.query.filter(
                Position.user_id == user.id,
                Position.snapshot_time == latest_snapshot
            ).all()
            positions_stats = {
                'total_positions': len(positions),
                'total_market_value': sum(convert_to_usd(pos.market_val or 0, pos.code) for pos in positions),
                'total_unrealized_pl': sum(convert_to_usd(pos.unrealized_pl or 0, pos.code) for pos in positions),
                'total_realized_pl': sum(convert_to_usd(pos.realized_pl or 0, pos.code) for pos in positions)
            }

        # Daily trade volume for chart (with currency conversion) for user
        daily_trades = db.session.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.deal_time >= start_dt,
            Trade.deal_time < end_dt
        ).all()

        # Group by date and sum with currency conversion
        daily_volumes_dict = {}
        for trade in daily_trades:
            trade_date = trade.deal_time.date()
            usd_value = convert_to_usd(trade.val, trade.code, trade.deal_time)

            if trade_date not in daily_volumes_dict:
                daily_volumes_dict[trade_date] = 0
            daily_volumes_dict[trade_date] += usd_value

        # Convert to sorted list
        daily_volumes = [
            {'date': str(date), 'volume': float(volume)}
            for date, volume in sorted(daily_volumes_dict.items())
        ]

        return jsonify({
            'trades_stats': {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'buy_volume': buy_volume,
                'sell_volume': sell_volume
            },
            'positions_stats': positions_stats,
            'daily_volumes': daily_volumes,
            'currency_info': {
                'base_currency': 'USD',
                'note': 'All amounts converted to USD using current exchange rates'
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/currency-info', methods=['GET'])
@jwt_required()
def get_currency_info():
    """Get currency conversion information"""
    try:
        # Get current user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get sample of different stock codes for this user
        sample_trades = Trade.query.filter_by(user_id=user.id).limit(20).all()
        currency_info = {}

        for trade in sample_trades:
            if trade.code not in currency_info:
                rate_info = converter.get_rate_info(trade.code)
                currency_info[trade.code] = rate_info

        return jsonify({
            'base_currency': 'USD',
            'currencies': currency_info,
            'static_rates': converter.static_rates,
            'note': 'Live rates are fetched when possible, falling back to static rates'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/refresh-data', methods=['POST'])
@jwt_required()
def refresh_data():
    try:
        # Get current user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if container is configured and running
        if not user.openapi_configured:
            return jsonify({
                'error': 'OpenD not configured. Please configure your moomoo credentials first.'
            }), 400

        if user.container_status not in ['running', 'simulated_local']:
            return jsonify({
                'error': f'Container is not running (status: {user.container_status}). Please start your container first.'
            }), 400

        # Trigger data sync in user's container
        from container_manager import ContainerManager
        container_mgr = ContainerManager()

        # Use the username for Docker Compose container name matching
        result = container_mgr.trigger_data_sync(user.container_id, user.username)

        if result.get('status') == 'success':
            # Update last sync time
            user.last_sync = datetime.utcnow()
            db.session.commit()

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500