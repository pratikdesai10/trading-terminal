"""SQLite persistence layer for the Indian Bloomberg Terminal.

Provides CRUD functions for users, portfolio holdings, watchlist, price alerts,
and paper trading data. All user-data tables are scoped by user_id.
Auto-creates tables on first run.
"""

import os
import sqlite3
from contextlib import contextmanager

from utils.logger import logger

DB_PATH = os.path.join(os.path.dirname(__file__), "terminal.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    symbol      TEXT NOT NULL,
    qty         INTEGER NOT NULL,
    avg_price   REAL NOT NULL,
    buy_date    TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlist (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol  TEXT NOT NULL,
    UNIQUE(user_id, symbol)
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
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
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    balance REAL NOT NULL DEFAULT 1000000.0
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty         INTEGER NOT NULL,
    price       REAL NOT NULL,
    total       REAL NOT NULL,
    timestamp   TEXT NOT NULL,
    status      TEXT DEFAULT 'FILLED'
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    username    TEXT NOT NULL,
    expires_at  TEXT NOT NULL
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
        conn.rollback()
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
# USERS
# ═════════════════════════════════════════════════════════════════════

def create_user(username, email, password_hash):
    """Insert a new user. Returns user dict or None on duplicate."""
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            conn.commit()
            return {"id": cur.lastrowid, "username": username, "email": email}
    except sqlite3.IntegrityError:
        return None
    except sqlite3.Error as e:
        logger.error(f"database | create_user failed: {e}")
        return None


def get_user_by_username(username):
    """Look up a user by username. Returns dict with id, username, email, password_hash or None."""
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT id, username, email, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                }
            return None
    except sqlite3.Error as e:
        logger.error(f"database | get_user_by_username failed: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════
# PORTFOLIO HOLDINGS
# ═════════════════════════════════════════════════════════════════════

def load_holdings(user_id):
    """Load all portfolio holdings for a user. Returns list of dicts."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT id, symbol, qty, avg_price, buy_date FROM portfolio_holdings "
                "WHERE user_id = ? ORDER BY id",
                (user_id,),
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


def save_holding(user_id, holding):
    """Insert a single holding. Returns the new row id or None on failure."""
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO portfolio_holdings (user_id, symbol, qty, avg_price, buy_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, holding["symbol"], holding["qty"], holding["avg_price"], holding["buy_date"]),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        logger.error(f"database | save_holding failed: {e}")
        return None


def remove_holding(user_id, row_id):
    """Delete a holding by its DB id, scoped to user."""
    try:
        with _db() as conn:
            conn.execute(
                "DELETE FROM portfolio_holdings WHERE id = ? AND user_id = ?",
                (row_id, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | remove_holding failed: {e}")


def update_holding_qty(user_id, row_id, new_qty):
    """Update qty for a holding. If new_qty <= 0, removes it."""
    try:
        with _db() as conn:
            if new_qty <= 0:
                conn.execute(
                    "DELETE FROM portfolio_holdings WHERE id = ? AND user_id = ?",
                    (row_id, user_id),
                )
            else:
                conn.execute(
                    "UPDATE portfolio_holdings SET qty = ? WHERE id = ? AND user_id = ?",
                    (new_qty, row_id, user_id),
                )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | update_holding_qty failed: {e}")


def replace_all_holdings(user_id, holdings):
    """Replace all holdings for a user (for JSON import). Runs in a transaction."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM portfolio_holdings WHERE user_id = ?", (user_id,))
            for h in holdings:
                conn.execute(
                    "INSERT INTO portfolio_holdings (user_id, symbol, qty, avg_price, buy_date) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, h["symbol"], h["qty"], h["avg_price"], h["buy_date"]),
                )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | replace_all_holdings failed: {e}")
        raise


# ═════════════════════════════════════════════════════════════════════
# WATCHLIST
# ═════════════════════════════════════════════════════════════════════

def load_watchlist(user_id):
    """Load watchlist symbols for a user. Returns list of strings."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT symbol FROM watchlist WHERE user_id = ? ORDER BY id",
                (user_id,),
            ).fetchall()
            return [row["symbol"] for row in rows]
    except sqlite3.Error as e:
        logger.error(f"database | load_watchlist failed: {e}")
        return []


def add_watchlist_symbol(user_id, symbol):
    """Add a symbol to the user's watchlist. Ignores duplicates."""
    try:
        with _db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (user_id, symbol) VALUES (?, ?)",
                (user_id, symbol),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | add_watchlist_symbol failed: {e}")


def remove_watchlist_symbol(user_id, symbol):
    """Remove a symbol from the user's watchlist."""
    try:
        with _db() as conn:
            conn.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
                (user_id, symbol),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | remove_watchlist_symbol failed: {e}")


def replace_watchlist(user_id, symbols):
    """Replace entire watchlist for a user. Runs in a transaction."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM watchlist WHERE user_id = ?", (user_id,))
            for sym in symbols:
                conn.execute(
                    "INSERT INTO watchlist (user_id, symbol) VALUES (?, ?)",
                    (user_id, sym),
                )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | replace_watchlist failed: {e}")
        raise


# ═════════════════════════════════════════════════════════════════════
# PRICE ALERTS
# ═════════════════════════════════════════════════════════════════════

def load_alerts(user_id):
    """Load all alerts for a user. Returns list of dicts."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT id, symbol, condition, value, created_at, triggered, "
                "triggered_at, trigger_price, trigger_pchange FROM price_alerts "
                "WHERE user_id = ? ORDER BY id",
                (user_id,),
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


def save_alert(user_id, alert):
    """Insert a single alert. Returns the new row id or None on failure."""
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO price_alerts (user_id, symbol, condition, value, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, alert["symbol"], alert["condition"], alert["value"], alert["created_at"]),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        logger.error(f"database | save_alert failed: {e}")
        return None


def update_alert_triggered(user_id, alert_id, triggered_at, trigger_price, trigger_pchange):
    """Mark an alert as triggered with metadata."""
    try:
        with _db() as conn:
            conn.execute(
                "UPDATE price_alerts SET triggered = 1, triggered_at = ?, "
                "trigger_price = ?, trigger_pchange = ? WHERE id = ? AND user_id = ?",
                (triggered_at, trigger_price, trigger_pchange, alert_id, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | update_alert_triggered failed: {e}")


def remove_alert(user_id, alert_id):
    """Delete an alert by its DB id, scoped to user."""
    try:
        with _db() as conn:
            conn.execute(
                "DELETE FROM price_alerts WHERE id = ? AND user_id = ?",
                (alert_id, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | remove_alert failed: {e}")


def clear_all_alerts(user_id):
    """Delete all alerts for a user."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM price_alerts WHERE user_id = ?", (user_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | clear_all_alerts failed: {e}")


# ═════════════════════════════════════════════════════════════════════
# PAPER TRADING
# ═════════════════════════════════════════════════════════════════════

def load_paper_balance(user_id):
    """Load paper trading balance for a user. Creates default row if none exists."""
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT balance FROM paper_balance WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO paper_balance (user_id, balance) VALUES (?, ?)",
                    (user_id, PAPER_DEFAULT_BALANCE),
                )
                conn.commit()
                return PAPER_DEFAULT_BALANCE
            return row["balance"]
    except sqlite3.Error as e:
        logger.error(f"database | load_paper_balance failed: {e}")
        return PAPER_DEFAULT_BALANCE


def update_paper_balance(user_id, new_balance):
    """Update the paper trading balance for a user."""
    try:
        with _db() as conn:
            conn.execute(
                "UPDATE paper_balance SET balance = ? WHERE user_id = ?",
                (new_balance, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | update_paper_balance failed: {e}")


def load_paper_orders(user_id):
    """Load all paper orders for a user. Returns list of dicts, newest first."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT id, symbol, side, qty, price, total, timestamp, status "
                "FROM paper_orders WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
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


def save_paper_order(user_id, order):
    """Insert a paper trade order. Returns the new row id or None on failure."""
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO paper_orders (user_id, symbol, side, qty, price, total, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, order["symbol"], order["side"], order["qty"],
                 order["price"], order["total"], order["timestamp"]),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        logger.error(f"database | save_paper_order failed: {e}")
        return None


def clear_paper_trading(user_id):
    """Reset paper trading for a user — clear all orders and reset balance."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM paper_orders WHERE user_id = ?", (user_id,))
            conn.execute(
                "UPDATE paper_balance SET balance = ? WHERE user_id = ?",
                (PAPER_DEFAULT_BALANCE, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | clear_paper_trading failed: {e}")


# ═════════════════════════════════════════════════════════════════════
# SESSIONS
# ═════════════════════════════════════════════════════════════════════

def create_session(session_id, user_id, username, expires_at):
    """Insert a new session row."""
    try:
        with _db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, user_id, username, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, user_id, username, expires_at),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | create_session failed: {e}")


def get_session(session_id):
    """Look up a session by ID. Returns dict or None if not found/expired."""
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT user_id, username, expires_at FROM sessions "
                "WHERE session_id = ? AND expires_at > datetime('now')",
                (session_id,),
            ).fetchone()
            if row:
                return {"user_id": row["user_id"], "username": row["username"]}
            return None
    except sqlite3.Error as e:
        logger.error(f"database | get_session failed: {e}")
        return None


def delete_session(session_id):
    """Remove a session (logout)."""
    try:
        with _db() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"database | delete_session failed: {e}")
