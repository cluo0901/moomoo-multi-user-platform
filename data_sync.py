from futu import *
import pandas as pd
from datetime import datetime, timedelta
from models import Trade, Order, Position, db
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
HOST = os.getenv('MOOMOO_HOST', '127.0.0.1')
PORT = int(os.getenv('MOOMOO_PORT', 11111))
SECURITY_FIRM_MAP = {
    'FUTUSG': SecurityFirm.FUTUSG,
    'FUTUSECURITIES': SecurityFirm.FUTUSECURITIES,
    'FUTUINC': SecurityFirm.FUTUINC,
    'FUTUAU': SecurityFirm.FUTUAU
}
TRADE_MARKET_MAP = {
    'US': TrdMarket.US,
    'HK': TrdMarket.HK,
    'CN': TrdMarket.CN,
    'SG': TrdMarket.SG,
    'AU': TrdMarket.AU
}

SECURITY_FIRM = SECURITY_FIRM_MAP.get(os.getenv('MOOMOO_SECURITY_FIRM', 'FUTUSG'))
TRADE_MARKET = TRADE_MARKET_MAP.get(os.getenv('MOOMOO_TRADE_MARKET', 'US'))
LOOKBACK_DAYS = int(os.getenv('LOOKBACK_DAYS', 730))  # Total days to retrieve
CHUNK_SIZE = 180  # Max days per API call to avoid timeouts/limits

def safe_call(desc, fn, *args, **kwargs) -> pd.DataFrame:
    """Safe API call wrapper from original code"""
    ret, data = fn(*args, **kwargs)
    if ret == RET_OK:
        return data if isinstance(data, pd.DataFrame) else pd.DataFrame()
    else:
        print(f"[WARN] {desc} failed: {data}")
        return pd.DataFrame()

def parse_datetime(date_str):
    """Parse datetime string from moomoo API"""
    if pd.isna(date_str) or date_str == '':
        return None

    # Try multiple datetime formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(str(date_str), fmt)
        except ValueError:
            continue

    print(f"Could not parse datetime: {date_str}")
    return None

def get_date_chunks(start_date, end_date, chunk_days):
    """Split date range into chunks of specified size"""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    chunks = []
    current_start = start_dt

    while current_start < end_dt:
        current_end = min(current_start + timedelta(days=chunk_days - 1), end_dt)
        chunks.append((
            current_start.strftime('%Y-%m-%d'),
            current_end.strftime('%Y-%m-%d')
        ))
        current_start = current_end + timedelta(days=1)

    return chunks

def sync_trades(trd_ctx, start_date, end_date):
    """Sync trades data to database using chunked retrieval"""
    print(f"Syncing trades from {start_date} to {end_date}...")

    # Get date chunks
    chunks = get_date_chunks(start_date, end_date, CHUNK_SIZE)
    print(f"Processing {len(chunks)} date chunks of max {CHUNK_SIZE} days each")

    synced_count = 0

    for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
        print(f"  Chunk {i}/{len(chunks)}: {chunk_start} to {chunk_end}")

        deals_df = safe_call(f"history_deal_list_query chunk {i}",
                            trd_ctx.history_deal_list_query,
                            start=chunk_start, end=chunk_end)

        if deals_df.empty:
            print(f"    No trades found in chunk {i}")
            continue

        print(f"    Found {len(deals_df)} trades in chunk {i}")

        for _, row in deals_df.iterrows():
            # Check if trade already exists
            existing = Trade.query.filter_by(deal_id=str(row.get('deal_id', ''))).first()
            if existing:
                continue

            # Parse create_time (deals use create_time in API response)
            deal_time = parse_datetime(row.get('create_time'))
            if not deal_time:
                continue

            # Calculate val if not present
            qty = float(row.get('qty', 0))
            price = float(row.get('price', 0))
            val = float(row.get('val', 0)) if row.get('val') else qty * price

            trade = Trade(
                deal_id=str(row.get('deal_id', '')),
                code=str(row.get('code', '')),
                stock_name=str(row.get('stock_name', '')),
                deal_time=deal_time,
                qty=qty,
                price=price,
                val=val,
                side=str(row.get('trd_side', '')).upper(),
                order_id=str(row.get('order_id', ''))
            )

            db.session.add(trade)
            synced_count += 1

        # Commit after each chunk to avoid losing data
        db.session.commit()
        print(f"    Synced {len(deals_df)} trades from chunk {i}")

    print(f"Total synced: {synced_count} trades")
    return synced_count

def sync_orders(trd_ctx, start_date, end_date):
    """Sync orders data to database using chunked retrieval"""
    print(f"Syncing orders from {start_date} to {end_date}...")

    # Get date chunks
    chunks = get_date_chunks(start_date, end_date, CHUNK_SIZE)
    print(f"Processing {len(chunks)} date chunks of max {CHUNK_SIZE} days each")

    synced_count = 0

    for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
        print(f"  Chunk {i}/{len(chunks)}: {chunk_start} to {chunk_end}")

        orders_df = safe_call(f"history_order_list_query chunk {i}",
                             trd_ctx.history_order_list_query,
                             start=chunk_start, end=chunk_end, status_filter_list=[])

        if orders_df.empty:
            print(f"    No orders found in chunk {i}")
            continue

        print(f"    Found {len(orders_df)} orders in chunk {i}")

        for _, row in orders_df.iterrows():
            # Check if order already exists
            existing = Order.query.filter_by(order_id=str(row.get('order_id', ''))).first()
            if existing:
                # Update existing order
                existing.order_status = str(row.get('order_status', ''))
                existing.dealt_qty = float(row.get('dealt_qty', 0))
                existing.dealt_avg_price = float(row.get('dealt_avg_price', 0)) if row.get('dealt_avg_price') else None
                existing.updated_time = parse_datetime(row.get('updated_time'))
                continue

            # Parse create_time
            create_time = parse_datetime(row.get('create_time'))
            if not create_time:
                continue

            order = Order(
                order_id=str(row.get('order_id', '')),
                code=str(row.get('code', '')),
                stock_name=str(row.get('stock_name', '')),
                trd_side=str(row.get('trd_side', '')).upper(),
                order_type=str(row.get('order_type', '')),
                order_status=str(row.get('order_status', '')),
                qty=float(row.get('qty', 0)),
                price=float(row.get('price', 0)) if row.get('price') else None,
                create_time=create_time,
                updated_time=parse_datetime(row.get('updated_time')),
                dealt_qty=float(row.get('dealt_qty', 0)),
                dealt_avg_price=float(row.get('dealt_avg_price', 0)) if row.get('dealt_avg_price') else None
            )

            db.session.add(order)
            synced_count += 1

        # Commit after each chunk
        db.session.commit()
        print(f"    Synced {len(orders_df)} orders from chunk {i}")

    print(f"Total synced: {synced_count} orders")
    return synced_count

def sync_positions(trd_ctx):
    """Sync current positions to database"""
    print("Syncing positions...")

    positions_df = safe_call("position_list_query", trd_ctx.position_list_query)

    if positions_df.empty:
        print("No positions data found")
        return 0

    synced_count = 0
    snapshot_time = datetime.utcnow()

    for _, row in positions_df.iterrows():
        position = Position(
            code=str(row.get('code', '')),
            stock_name=str(row.get('stock_name', '')),
            qty=float(row.get('qty', 0)),
            can_sell_qty=float(row.get('can_sell_qty', 0)),
            cost_price=float(row.get('cost_price', 0)) if row.get('cost_price') else None,
            cost_price_valid=bool(row.get('cost_price_valid', True)),
            market_val=float(row.get('market_val', 0)) if row.get('market_val') else None,
            nominal_price=float(row.get('nominal_price', 0)) if row.get('nominal_price') else None,
            unrealized_pl=float(row.get('unrealized_pl', 0)) if row.get('unrealized_pl') else None,
            unrealized_pl_ratio=float(row.get('unrealized_pl_ratio', 0)) if row.get('unrealized_pl_ratio') else None,
            realized_pl=float(row.get('realized_pl', 0)) if row.get('realized_pl') else None,
            today_buy_val=float(row.get('today_buy_val', 0)),
            today_buy_qty=float(row.get('today_buy_qty', 0)),
            today_sell_val=float(row.get('today_sell_val', 0)),
            today_sell_qty=float(row.get('today_sell_qty', 0)),
            snapshot_time=snapshot_time
        )

        db.session.add(position)
        synced_count += 1

    db.session.commit()

    print(f"Synced {synced_count} positions")
    return synced_count

def sync_moomoo_data():
    """Main function to sync all moomoo data"""
    from app import app

    try:
        # Calculate date range
        end_dt = datetime.now().date()
        start_dt = end_dt - timedelta(days=LOOKBACK_DAYS - 1)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")

        print(f"Syncing data from {start_date} to {end_date}")

        # Initialize trading context
        trd_ctx = OpenSecTradeContext(
            filter_trdmarket=TRADE_MARKET,
            host=HOST,
            port=PORT,
            security_firm=SECURITY_FIRM
        )

        result = {
            'status': 'success',
            'sync_time': datetime.utcnow().isoformat(),
            'date_range': {'start': start_date, 'end': end_date},
            'synced_counts': {}
        }

        try:
            with app.app_context():
                # Sync trades
                trades_count = sync_trades(trd_ctx, start_date, end_date)
                result['synced_counts']['trades'] = trades_count

                # Sync orders
                orders_count = sync_orders(trd_ctx, start_date, end_date)
                result['synced_counts']['orders'] = orders_count

                # Sync positions
                positions_count = sync_positions(trd_ctx)
                result['synced_counts']['positions'] = positions_count

            print("Data sync completed successfully!")
            return result

        finally:
            trd_ctx.close()

    except Exception as e:
        print(f"Error syncing data: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'sync_time': datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    # Run data sync
    result = sync_moomoo_data()
    print(f"Sync result: {result}")