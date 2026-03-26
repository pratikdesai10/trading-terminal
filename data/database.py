"""SQLite persistence layer for the Indian Bloomberg Terminal.

Provides CRUD functions for portfolio holdings, watchlist, price alerts,
and paper trading data. Auto-creates tables on first run.
"""

import os
import sqlite3
from contextlib import contextmanager

from utils.logger import logger

DB_PATH = os.path.join(os.path.dirname(__file__), "terminal.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    qty         INTEGER NOT NULL,
    avg_price   REAL NOT NULL,
    buy_date    TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlist (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    condition       TEXT NOT NULL,
    value           REAL NOT NULL,
    created_at      TEXT NOT NULL,
    triggered       INTEGER DEFAULT 0,
    triggered_at    TEXT,
    trigger_price   REAL,
    trigger_pchange REAL
);

CREATE TABLE IF NOT EXISTS paper_balance (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    balance REAL NOT NULL DEFAULT 1000000.0
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty         INTEGER NOT NULL,
    price       REAL NOT NULL,
    total       REAL NOT NULL,
    timestamp   TEXT NOT NULL,
    status      TEXT DEFAULT 'FILLED'
);
"""

PAPER_DEFAULT_BALANCE = 1_000_000.0


def _get_conn():
    """Get a SQLite connection with WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def _db():
    """Context manager for safe database access with auto-close."""
    conn = _get_conn()
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"database | sqlite3 error: {type(e).__name__}: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist. Safe to call on every app start."""
    try:
        with _db() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()
        logger.info("database | init_db | tables ensured")
    except sqlite3.Error as e:
        logger.error(f"database | init_db FAILED: {type(e).__name__}: {e}")
        raise RuntimeError(f"Database initialization failed: {e}") from e


# ═════════════════════════════════════════════════════════════════════
# PORTFOLIO HOLDINGS
# ═════════════════════════════════════════════════════════════════════

def load_holdings():
    """Load all portfolio holdings from DB. Returns list of dicts."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT id, symbol, qty, avg_price, buy_date FROM portfolio_holdings ORDER BY id"
            ).fetchall()
            return [
                {
                    "_db_id": row["id"],
                    "symbol": row["symbol"],
                    "qty": row["qty"],
                    "avg_price": row["avg_price"],
                    "buy_date": row["buy_date"],
                }
                for row in rows
            ]
    except sqlite3.Error as e:
        logger.error(f"database | load_holdings failed: {e}")
        return []


def save_holding(holding):
    """Insert a single holding. Returns the new row id or None on failure."""
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO portfolio_holdings (symbol, qty, avg_price, buy_date) VALUES (?, ?, ?, ?)",
                (holding["symbol"], holding["qty"], holding["avg_price"], holding["buy_date"]),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        logger.error(f"database | save_holding failed: {e}")
        return None


def remove_holding(row_id):
    """Delete a holding by its DB id."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM portfolio_holdings WHERE id = ?", (row_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | remove_holding failed: {e}")


def replace_all_holdings(holdings):
    """Replace all holdings (for JSON import). Runs in a transaction."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM portfolio_holdings")
            for h in holdings:
                conn.execute(
                    "INSERT INTO portfolio_holdings (symbol, qty, avg_price, buy_date) VALUES (?, ?, ?, ?)",
                    (h["symbol"], h["qty"], h["avg_price"], h["buy_date"]),
                )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | replace_all_holdings failed: {e}")
        raise


# ═════════════════════════════════════════════════════════════════════
# WATCHLIST
# ═════════════════════════════════════════════════════════════════════

def load_watchlist():
    """Load watchlist symbols from DB. Returns list of strings."""
    try:
        with _db() as conn:
            rows = conn.execute("SELECT symbol FROM watchlist ORDER BY id").fetchall()
            return [row["symbol"] for row in rows]
    except sqlite3.Error as e:
        logger.error(f"database | load_watchlist failed: {e}")
        return []


def add_watchlist_symbol(symbol):
    """Add a symbol to the watchlist. Ignores duplicates."""
    try:
        with _db() as conn:
            conn.execute("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (symbol,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | add_watchlist_symbol failed: {e}")


def remove_watchlist_symbol(symbol):
    """Remove a symbol from the watchlist."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | remove_watchlist_symbol failed: {e}")


def replace_watchlist(symbols):
    """Replace entire watchlist. Runs in a transaction."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM watchlist")
            for sym in symbols:
                conn.execute("INSERT INTO watchlist (symbol) VALUES (?)", (sym,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | replace_watchlist failed: {e}")
        raise


# ═════════════════════════════════════════════════════════════════════
# PRICE ALERTS
# ═════════════════════════════════════════════════════════════════════

def load_alerts():
    """Load all alerts from DB. Returns list of dicts matching session_state format."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT id, symbol, condition, value, created_at, triggered, "
                "triggered_at, trigger_price, trigger_pchange FROM price_alerts ORDER BY id"
            ).fetchall()
            return [
                {
                    "_db_id": row["id"],
                    "symbol": row["symbol"],
                    "condition": row["condition"],
                    "value": row["value"],
                    "created_at": row["created_at"],
                    "triggered": bool(row["triggered"]),
                    "triggered_at": row["triggered_at"],
                    "trigger_price": row["trigger_price"],
                    "trigger_pchange": row["trigger_pchange"],
                }
                for row in rows
            ]
    except sqlite3.Error as e:
        logger.error(f"database | load_alerts failed: {e}")
        return []


def save_alert(alert):
    """Insert a single alert. Returns the new row id or None on failure."""
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO price_alerts (symbol, condition, value, created_at) VALUES (?, ?, ?, ?)",
                (alert["symbol"], alert["condition"], alert["value"], alert["created_at"]),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        logger.error(f"database | save_alert failed: {e}")
        return None


def update_alert_triggered(alert_id, triggered_at, trigger_price, trigger_pchange):
    """Mark an alert as triggered with metadata."""
    try:
        with _db() as conn:
            conn.execute(
                "UPDATE price_alerts SET triggered = 1, triggered_at = ?, "
                "trigger_price = ?, trigger_pchange = ? WHERE id = ?",
                (triggered_at, trigger_price, trigger_pchange, alert_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | update_alert_triggered failed: {e}")


def remove_alert(alert_id):
    """Delete an alert by its DB id."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | remove_alert failed: {e}")


def clear_all_alerts():
    """Delete all alerts."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM price_alerts")
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | clear_all_alerts failed: {e}")


# ═════════════════════════════════════════════════════════════════════
# PAPER TRADING
# ═════════════════════════════════════════════════════════════════════

def load_paper_balance():
    """Load paper trading balance. Creates default row if none exists."""
    try:
        with _db() as conn:
            row = conn.execute("SELECT balance FROM paper_balance WHERE id = 1").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO paper_balance (id, balance) VALUES (1, ?)",
                    (PAPER_DEFAULT_BALANCE,),
                )
                conn.commit()
                return PAPER_DEFAULT_BALANCE
            return row["balance"]
    except sqlite3.Error as e:
        logger.error(f"database | load_paper_balance failed: {e}")
        return PAPER_DEFAULT_BALANCE


def update_paper_balance(new_balance):
    """Update the paper trading balance."""
    try:
        with _db() as conn:
            conn.execute("UPDATE paper_balance SET balance = ? WHERE id = 1", (new_balance,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | update_paper_balance failed: {e}")


def load_paper_orders():
    """Load all paper orders. Returns list of dicts, newest first."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT id, symbol, side, qty, price, total, timestamp, status "
                "FROM paper_orders ORDER BY id DESC"
            ).fetchall()
            return [
                {
                    "_db_id": row["id"],
                    "symbol": row["symbol"],
                    "side": row["side"],
                    "qty": row["qty"],
                    "price": row["price"],
                    "total": row["total"],
                    "timestamp": row["timestamp"],
                    "status": row["status"],
                }
                for row in rows
            ]
    except sqlite3.Error as e:
        logger.error(f"database | load_paper_orders failed: {e}")
        return []


def save_paper_order(order):
    """Insert a paper trade order. Returns the new row id or None on failure."""
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO paper_orders (symbol, side, qty, price, total, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (order["symbol"], order["side"], order["qty"],
                 order["price"], order["total"], order["timestamp"]),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        logger.error(f"database | save_paper_order failed: {e}")
        return None


def clear_paper_trading():
    """Reset paper trading — clear all orders and reset balance."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM paper_orders")
            conn.execute(
                "UPDATE paper_balance SET balance = ? WHERE id = 1",
                (PAPER_DEFAULT_BALANCE,),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | clear_paper_trading failed: {e}")
