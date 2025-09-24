from moomoo import *
import pandas as pd
from datetime import datetime, timedelta

# ====== CONFIG ======
HOST = "127.0.0.1"
PORT = 11111
SECURITY_FIRM = SecurityFirm.FUTUSG      # Moomoo Singapore
TRADE_MARKET  = TrdMarket.US             # change to HK / CN if needed
LOOKBACK_DAYS = 90
OUT_FILE = f"moomoo_snapshot_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
# ====================

end_dt = datetime.now().date()
start_dt = end_dt - timedelta(days=LOOKBACK_DAYS - 1)
START = start_dt.strftime("%Y-%m-%d")
END   = end_dt.strftime("%Y-%m-%d")

def autofit_with_filters(writer, sheet_name, df: pd.DataFrame):
    ws = writer.sheets[sheet_name]
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))
    for c, col in enumerate(df.columns):
        vals = df[col].astype(str).tolist() if not df.empty else []
        max_len = max([len(col)] + [len(v) for v in vals]) if vals else len(col)
        ws.set_column(c, c, min(max_len + 2, 60))

def safe_call(desc, fn, *args, **kwargs) -> pd.DataFrame:
    ret, data = fn(*args, **kwargs)
    if ret == RET_OK:
        return data if isinstance(data, pd.DataFrame) else pd.DataFrame()
    else:
        print(f"[WARN] {desc} failed: {data}")
        return pd.DataFrame()

trd_ctx = OpenSecTradeContext(
    filter_trdmarket=TRADE_MARKET,
    host=HOST,
    port=PORT,
    security_firm=SECURITY_FIRM
)

try:
    # 1) Historical trades (deals)
    deals = safe_call("history_deal_list_query",
                      trd_ctx.history_deal_list_query,
                      start=START, end=END)

    # 2) Historical orders — pass [] (not None) to include all statuses
    orders = safe_call("history_order_list_query",
                       trd_ctx.history_order_list_query,
                       start=START, end=END, status_filter_list=[])

    # 3) Current positions
    positions = safe_call("position_list_query",
                          trd_ctx.position_list_query)

    with pd.ExcelWriter(OUT_FILE, engine="xlsxwriter") as writer:
        (deals if not deals.empty else pd.DataFrame()).to_excel(writer, sheet_name="Trades", index=False)
        autofit_with_filters(writer, "Trades", deals if not deals.empty else pd.DataFrame(columns=[""]))

        (orders if not orders.empty else pd.DataFrame()).to_excel(writer, sheet_name="Orders", index=False)
        autofit_with_filters(writer, "Orders", orders if not orders.empty else pd.DataFrame(columns=[""]))

        (positions if not positions.empty else pd.DataFrame()).to_excel(writer, sheet_name="Positions", index=False)
        autofit_with_filters(writer, "Positions", positions if not positions.empty else pd.DataFrame(columns=[""]))

    print(f"Saved Excel → {OUT_FILE}")
    print(f"Rows: Trades={len(deals)} | Orders={len(orders)} | Positions={len(positions)}")

finally:
    trd_ctx.close()