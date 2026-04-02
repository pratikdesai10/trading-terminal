"""JWT-based authentication for the Indian Bloomberg Terminal."""

import os
import secrets
from datetime import datetime, timedelta, timezone

import re

import bcrypt
import streamlit as st

from data.database import (
    create_user, get_user_by_username,
    create_session, get_session, delete_session,
)
from utils.logger import logger


_SESSION_EXPIRY_HOURS = 24
_SESSION_PARAM = "s"  # short query param name


def _hash_password(password):
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password, password_hash):
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _new_session(user_id, username):
    """Create a new server-side session. Returns the opaque session ID."""
    session_id = secrets.token_urlsafe(12)  # ~16 chars, URL-safe
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=_SESSION_EXPIRY_HOURS)
    ).strftime("%Y-%m-%d %H:%M:%S")
    create_session(session_id, user_id, username, expires_at)
    return session_id


# Session state keys cleared on logout
_USER_STATE_KEYS = [
    "session_id", "user", "user_id",
    "watchlist", "portfolio_holdings",
    "paper_balance", "paper_orders",
    "price_alerts", "screener_results",
]


def require_auth():
    """Gate function — renders login page if not authenticated. Returns user dict.

    Session persistence across refreshes:
    - On login/signup: short opaque session_id written to st.query_params["s"]
    - On F5 refresh: Streamlit reloads the URL (?s=<id>), session_id looked up
      in DB to restore the user — no JWT or credentials in the URL.
    """
    # 1. Try session_state first (already validated this run)
    sid = st.session_state.get("session_id")

    # 2. On refresh session_state is empty — restore from query param
    if not sid:
        sid = st.query_params.get(_SESSION_PARAM)
        if sid:
            st.session_state["session_id"] = sid

    if sid:
        user = get_session(sid)
        if user:
            return user
        # Session expired or not found — clear everything
        for key in _USER_STATE_KEYS:
            st.session_state.pop(key, None)
        st.query_params.clear()

    _render_auth_page()
    st.stop()


def logout():
    """Clear auth state and rerun."""
    sid = st.session_state.get("session_id")
    if sid:
        delete_session(sid)
    for key in _USER_STATE_KEYS:
        st.session_state.pop(key, None)
    st.query_params.clear()
    st.rerun()


def _start_session(user_id, username):
    """Create session, update state and query params. Call after successful auth."""
    sid = _new_session(user_id, username)
    st.session_state["session_id"] = sid
    st.session_state["user"] = {"user_id": user_id, "username": username}
    st.query_params[_SESSION_PARAM] = sid


def _render_auth_page():
    """Render Bloomberg-themed login/signup page."""
    st.markdown(
        """
        <style>
        .auth-container {
            max-width: 420px;
            margin: 60px auto;
            padding: 32px;
            border: 1px solid #333333;
            border-radius: 4px;
            background-color: #111111;
        }
        .auth-title {
            color: #FF9900;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            letter-spacing: 2px;
            margin-bottom: 4px;
        }
        .auth-subtitle {
            color: #888888;
            font-family: 'Fira Code', monospace;
            font-size: 11px;
            text-align: center;
            letter-spacing: 1px;
            margin-bottom: 24px;
        }
        </style>
        <div style="text-align:center;margin-top:40px">
            <div class="auth-title">INDIAN BLOOMBERG TERMINAL</div>
            <div class="auth-subtitle">DEVELOPED BY PRATIK DESAI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["LOGIN", "SIGN UP"])

    with tab_login:
        _render_login_form()

    with tab_signup:
        _render_signup_form()


def _render_login_form():
    """Render the login form."""
    with st.form("login_form"):
        username = st.text_input("USERNAME", key="login_username")
        password = st.text_input("PASSWORD", type="password", key="login_password")
        submitted = st.form_submit_button("LOGIN", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("Enter both username and password.")
            return
        user = get_user_by_username(username)
        if user and _verify_password(password, user["password_hash"]):
            _start_session(user["id"], user["username"])
            logger.info(f"auth | login success | user={username!r}")
            st.rerun()
        else:
            st.error("Invalid username or password.")
            logger.warning(f"auth | login failed | user={username!r}")


def _render_signup_form():
    """Render the sign-up form."""
    with st.form("signup_form"):
        username = st.text_input("USERNAME", key="signup_username")
        email = st.text_input("EMAIL", key="signup_email")
        password = st.text_input("PASSWORD", type="password", key="signup_password")
        confirm = st.text_input("CONFIRM PASSWORD", type="password", key="signup_confirm")
        submitted = st.form_submit_button("CREATE ACCOUNT", use_container_width=True)

    if submitted:
        if not username or not email or not password:
            st.error("All fields are required.")
            return
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
            st.error("Username must be 3-30 characters (letters, numbers, underscore only).")
            return
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            st.error("Enter a valid email address.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return

        hashed = _hash_password(password)
        user = create_user(username, email, hashed)
        if user is None:
            st.error("Username or email already taken.")
            return

        _start_session(user["id"], user["username"])
        logger.info(f"auth | signup success | user={username!r}")
        st.rerun()
