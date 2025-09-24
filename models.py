from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Index

db = SQLAlchemy()

class Trade(db.Model):
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(20), nullable=False)
    stock_name = db.Column(db.String(100))
    deal_time = db.Column(db.DateTime, nullable=False, index=True)
    qty = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    val = db.Column(db.Float, nullable=False)  # Total value
    side = db.Column(db.String(10), nullable=False)  # BUY/SELL
    order_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'deal_id': self.deal_id,
            'code': self.code,
            'stock_name': self.stock_name,
            'deal_time': self.deal_time.isoformat() if self.deal_time else None,
            'qty': self.qty,
            'price': self.price,
            'val': self.val,
            'side': self.side,
            'order_id': self.order_id
        }

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(20), nullable=False)
    stock_name = db.Column(db.String(100))
    trd_side = db.Column(db.String(10), nullable=False)  # BUY/SELL
    order_type = db.Column(db.String(20))
    order_status = db.Column(db.String(20), index=True)
    qty = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float)
    create_time = db.Column(db.DateTime, nullable=False, index=True)
    updated_time = db.Column(db.DateTime)
    dealt_qty = db.Column(db.Float, default=0)
    dealt_avg_price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'code': self.code,
            'stock_name': self.stock_name,
            'trd_side': self.trd_side,
            'order_type': self.order_type,
            'order_status': self.order_status,
            'qty': self.qty,
            'price': self.price,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'updated_time': self.updated_time.isoformat() if self.updated_time else None,
            'dealt_qty': self.dealt_qty,
            'dealt_avg_price': self.dealt_avg_price
        }

class Position(db.Model):
    __tablename__ = 'positions'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, index=True)
    stock_name = db.Column(db.String(100))
    qty = db.Column(db.Float, nullable=False)
    can_sell_qty = db.Column(db.Float)
    cost_price = db.Column(db.Float)
    cost_price_valid = db.Column(db.Boolean, default=True)
    market_val = db.Column(db.Float)
    nominal_price = db.Column(db.Float)
    unrealized_pl = db.Column(db.Float)
    unrealized_pl_ratio = db.Column(db.Float)
    realized_pl = db.Column(db.Float)
    today_buy_val = db.Column(db.Float, default=0)
    today_buy_qty = db.Column(db.Float, default=0)
    today_sell_val = db.Column(db.Float, default=0)
    today_sell_qty = db.Column(db.Float, default=0)
    snapshot_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'stock_name': self.stock_name,
            'qty': self.qty,
            'can_sell_qty': self.can_sell_qty,
            'cost_price': self.cost_price,
            'cost_price_valid': self.cost_price_valid,
            'market_val': self.market_val,
            'nominal_price': self.nominal_price,
            'unrealized_pl': self.unrealized_pl,
            'unrealized_pl_ratio': self.unrealized_pl_ratio,
            'realized_pl': self.realized_pl,
            'today_buy_val': self.today_buy_val,
            'today_buy_qty': self.today_buy_qty,
            'today_sell_val': self.today_sell_val,
            'today_sell_qty': self.today_sell_qty,
            'snapshot_time': self.snapshot_time.isoformat() if self.snapshot_time else None
        }

# Add compound indexes for better query performance
Index('idx_trades_code_time', Trade.code, Trade.deal_time)
Index('idx_orders_code_time', Order.code, Order.create_time)
Index('idx_positions_code_snapshot', Position.code, Position.snapshot_time)