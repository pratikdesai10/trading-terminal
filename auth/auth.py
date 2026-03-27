"""JWT-based authentication for the Indian Bloomberg Terminal."""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import streamlit as st

from data.database import create_user, get_user_by_username
from utils.logger import logger


def _get_secret_key():
    """Read JWT secret from Streamlit secrets, env var, or raise."""
    try:
        return st.secrets["JWT_SECRET"]
    except (FileNotFoundError, KeyError):
        pass
    val = os.environ.get("JWT_SECRET")
    if val:
        return val
    raise RuntimeError(
        "JWT_SECRET not configured. "
        "Set it in .streamlit/secrets.toml (local) or Streamlit Cloud secrets (production)."
    )


_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24

# Session state keys cleared on logout
_USER_STATE_KEYS = [
    "auth_token", "user", "user_id",
    "watchlist", "portfolio_holdings",
    "paper_balance", "paper_orders",
    "price_alerts", "screener_results",
]


def _hash_password(password):
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password, password_hash):
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(user_id, username):
    """Create a JWT token."""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=_JWT_ALGORITHM)


def verify_token(token):
    """Decode and verify a JWT token. Returns payload dict or None."""
    try:
        return jwt.decode(token, _get_secret_key(), algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.info("auth | token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"auth | invalid token: {e}")
        return None


def require_auth():
    """Gate function — renders login page if not authenticated. Returns user dict."""
    token = st.session_state.get("auth_token")
    if token:
        payload = verify_token(token)
        if payload:
            return {"user_id": payload["user_id"], "username": payload["username"]}
        # Token expired/invalid — clear and re-auth
        for key in _USER_STATE_KEYS:
            st.session_state.pop(key, None)

    _render_auth_page()
    st.stop()


def logout():
    """Clear auth state and rerun."""
    for key in _USER_STATE_KEYS:
        st.session_state.pop(key, None)
    st.rerun()


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
            <div class="auth-subtitle">SECURE ACCESS</div>
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
            token = _create_token(user["id"], user["username"])
            st.session_state["auth_token"] = token
            st.session_state["user"] = {"user_id": user["id"], "username": user["username"]}
            logger.info(f"auth | login success | user={username}")
            st.rerun()
        else:
            st.error("Invalid username or password.")
            logger.warning(f"auth | login failed | user={username}")


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
        if len(username) < 3:
            st.error("Username must be at least 3 characters.")
            return
        if "@" not in email:
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

        token = _create_token(user["id"], user["username"])
        st.session_state["auth_token"] = token
        st.session_state["user"] = {"user_id": user["id"], "username": user["username"]}
        logger.info(f"auth | signup success | user={username}")
        st.rerun()
