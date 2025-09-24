from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models import Trade, Order, Position, db
import pandas as pd
from currency_converter import convert_to_usd, converter

api_bp = Blueprint('api', __name__)

@api_bp.route('/trades', methods=['GET'])
def get_trades():
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        code = request.args.get('code')
        side = request.args.get('side')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))

        # Build query
        query = Trade.query

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
def get_orders():
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        code = request.args.get('code')
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))

        # Build query
        query = Order.query

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
def get_positions():
    try:
        # Get latest positions
        latest_snapshot = db.session.query(func.max(Position.snapshot_time)).scalar()

        if not latest_snapshot:
            return jsonify({'positions': [], 'snapshot_time': None})

        positions = Position.query.filter(
            Position.snapshot_time == latest_snapshot
        ).order_by(desc(Position.market_val)).all()

        return jsonify({
            'positions': [pos.to_dict() for pos in positions],
            'snapshot_time': latest_snapshot.isoformat() if latest_snapshot else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Default to last 30 days if no dates provided
        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)
        else:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        # Get trades in date range
        trades = Trade.query.filter(
            Trade.deal_time >= start_dt,
            Trade.deal_time < end_dt
        ).all()

        # Calculate stats with currency conversion
        total_trades = len(trades)
        total_volume = sum(convert_to_usd(trade.val, trade.code, trade.deal_time) for trade in trades)
        buy_volume = sum(convert_to_usd(trade.val, trade.code, trade.deal_time) for trade in trades if trade.side == 'BUY')
        sell_volume = sum(convert_to_usd(trade.val, trade.code, trade.deal_time) for trade in trades if trade.side == 'SELL')

        # Get current positions stats
        latest_snapshot = db.session.query(func.max(Position.snapshot_time)).scalar()
        positions_stats = {'total_positions': 0, 'total_market_value': 0, 'total_unrealized_pl': 0}

        if latest_snapshot:
            positions = Position.query.filter(Position.snapshot_time == latest_snapshot).all()
            positions_stats = {
                'total_positions': len(positions),
                'total_market_value': sum(convert_to_usd(pos.market_val or 0, pos.code) for pos in positions),
                'total_unrealized_pl': sum(convert_to_usd(pos.unrealized_pl or 0, pos.code) for pos in positions),
                'total_realized_pl': sum(convert_to_usd(pos.realized_pl or 0, pos.code) for pos in positions)
            }

        # Daily trade volume for chart (with currency conversion)
        daily_trades = db.session.query(Trade).filter(
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
def get_currency_info():
    """Get currency conversion information"""
    try:
        # Get sample of different stock codes
        sample_trades = Trade.query.limit(20).all()
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
def refresh_data():
    try:
        from data_sync import sync_moomoo_data
        result = sync_moomoo_data()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500