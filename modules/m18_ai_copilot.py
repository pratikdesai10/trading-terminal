"""Module 18: AI Copilot — LLM chat interface for market data queries."""

import os

import streamlit as st

from config import COLORS
from utils.logger import logger


# ── Session state keys ──
_MSG_KEY = "copilot_messages"
_BACKEND_KEY = "copilot_backend"
_API_KEY_KEY = "copilot_api_key"
_PENDING_KEY = "copilot_pending"

# ── Quick-start suggestion prompts ──
_SUGGESTIONS = [
    "Show my portfolio P&L",
    "Top gainers and losers today",
    "Compare TCS vs INFY",
    "NIFTY option chain analysis",
    "What's the market sentiment?",
    "Analyze RELIANCE fundamentals",
]


def render():
    """Render the AI Copilot module."""
    st.markdown("### AI COPILOT")

    _init_state()

    # Setup panel (API key, backend selection)
    provider = _render_setup_panel()

    if provider is None:
        return

    # Suggestion buttons (only if no messages yet)
    if not st.session_state[_MSG_KEY]:
        _render_suggestions()

    # Chat interface
    _render_chat(provider)


def _init_state():
    """Initialize session state for copilot."""
    if _MSG_KEY not in st.session_state:
        st.session_state[_MSG_KEY] = []
    if _BACKEND_KEY not in st.session_state:
        st.session_state[_BACKEND_KEY] = "anthropic"
    if _API_KEY_KEY not in st.session_state:
        st.session_state[_API_KEY_KEY] = ""
    if _PENDING_KEY not in st.session_state:
        st.session_state[_PENDING_KEY] = None


def _resolve_api_key():
    """Resolve Anthropic API key from secrets, env, or session state."""
    # 1. Streamlit secrets
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
        if key:
            return key
    except Exception:
        pass

    # 2. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    # 3. Session state (manual input)
    return st.session_state.get(_API_KEY_KEY, "")


def _render_setup_panel():
    """Render the setup panel and return a configured provider or None."""
    from data.llm_agent import get_provider

    with st.expander("COPILOT SETTINGS", expanded=not bool(st.session_state[_MSG_KEY])):
        col1, col2 = st.columns([1, 2])

        with col1:
            backend = st.radio(
                "BACKEND",
                ["anthropic", "ollama"],
                format_func=lambda x: "Claude API" if x == "anthropic" else "Ollama (Local)",
                index=0 if st.session_state[_BACKEND_KEY] == "anthropic" else 1,
                key="copilot_backend_radio",
            )
            st.session_state[_BACKEND_KEY] = backend

        with col2:
            if backend == "anthropic":
                existing_key = _resolve_api_key()
                if existing_key:
                    st.markdown(
                        f'<p style="color:{COLORS["green"]};font-size:12px;font-family:monospace">'
                        f'API KEY CONFIGURED (sk-...{existing_key[-4:]})</p>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<p style="color:{COLORS["muted"]};font-size:11px">'
                        f'Set ANTHROPIC_API_KEY in environment, .streamlit/secrets.toml, or enter below:</p>',
                        unsafe_allow_html=True,
                    )
                    manual_key = st.text_input(
                        "API Key",
                        type="password",
                        placeholder="sk-ant-...",
                        label_visibility="collapsed",
                        key="copilot_key_input",
                    )
                    if manual_key:
                        st.session_state[_API_KEY_KEY] = manual_key
                        st.rerun()

            else:  # ollama
                st.markdown(
                    f'<p style="color:{COLORS["muted"]};font-size:11px">'
                    f'Requires Ollama running locally at localhost:11434</p>',
                    unsafe_allow_html=True,
                )
                ollama_model = st.text_input(
                    "Model",
                    value="llama3.1",
                    key="copilot_ollama_model",
                    label_visibility="collapsed",
                    placeholder="Model name (e.g. llama3.1)",
                )

        # Clear chat button
        if st.session_state[_MSG_KEY]:
            if st.button("CLEAR CHAT", key="copilot_clear"):
                st.session_state[_MSG_KEY] = []
                st.session_state[_PENDING_KEY] = None
                st.rerun()

    # Try to create provider
    try:
        if backend == "anthropic":
            api_key = _resolve_api_key()
            if not api_key:
                st.info(
                    "Enter your Anthropic API key above to start chatting. "
                    "Get one at console.anthropic.com"
                )
                return None
            return get_provider("anthropic", api_key=api_key)
        else:
            model = st.session_state.get("copilot_ollama_model", "llama3.1")
            return get_provider("ollama", model=model)
    except Exception as e:
        st.error(f"Failed to initialize provider: {e}")
        return None


def _render_suggestions():
    """Render quick-start suggestion buttons."""
    st.markdown(
        f'<p style="color:{COLORS["muted"]};font-size:12px;margin-bottom:8px">'
        f'TRY ASKING:</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for i, suggestion in enumerate(_SUGGESTIONS):
        with cols[i % 3]:
            if st.button(
                suggestion,
                key=f"copilot_suggest_{i}",
                use_container_width=True,
            ):
                # Set pending message — will be processed on this run
                st.session_state[_PENDING_KEY] = suggestion


def _render_chat(provider):
    """Render chat history and handle new messages."""
    from data.llm_agent import run_agent_turn

    # Inject chat-area styling
    st.markdown(
        f"""<style>
        .stChatMessage {{
            font-family: 'Fira Code', 'Consolas', 'Courier New', monospace;
            font-size: 13px;
        }}
        </style>""",
        unsafe_allow_html=True,
    )

    # Display message history
    for msg in st.session_state[_MSG_KEY]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                if msg.get("tools_called"):
                    _render_tools_expander(msg["tools_called"])

    # Check for new input: either from chat_input or from a suggestion button
    user_input = st.chat_input("Ask about markets, portfolio, or stocks...")

    # Pending message from suggestion button takes priority
    pending = st.session_state[_PENDING_KEY]
    if pending:
        user_input = pending
        st.session_state[_PENDING_KEY] = None

    if not user_input:
        return

    # Append and display user message
    st.session_state[_MSG_KEY].append({
        "role": "user",
        "content": user_input,
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    # Build messages for LLM (Anthropic format, last 20 messages)
    llm_messages = _build_llm_messages()

    # Get response
    with st.chat_message("assistant"):
        tools_log = []
        with st.spinner("ANALYZING..."):
            try:
                response_text = run_agent_turn(
                    provider, llm_messages, tools_called_log=tools_log
                )
            except Exception as e:
                logger.error(f"m18_copilot | agent error | {type(e).__name__}: {e}")
                error_str = str(e)
                if "credit balance" in error_str.lower() or "billing" in error_str.lower():
                    response_text = (
                        "Your Anthropic API account has insufficient credits. "
                        "Please visit console.anthropic.com to add credits or upgrade your plan."
                    )
                elif "authentication" in error_str.lower() or "api key" in error_str.lower():
                    response_text = "Invalid API key. Please check your Anthropic API key in the settings above."
                elif "rate" in error_str.lower() and "limit" in error_str.lower():
                    response_text = "Rate limited by the API. Please wait a moment and try again."
                elif "connection" in error_str.lower():
                    response_text = "Could not connect to the LLM backend. Please check your connection settings."
                else:
                    response_text = f"Error: {e}"

        st.markdown(response_text)

        if tools_log:
            _render_tools_expander(tools_log)

    # Save assistant message to state
    st.session_state[_MSG_KEY].append({
        "role": "assistant",
        "content": response_text,
        "tools_called": tools_log,
    })


def _render_tools_expander(tools_called):
    """Render the DATA FETCHED expander for tool calls."""
    with st.expander("DATA FETCHED", expanded=False):
        for tc in tools_called:
            args_str = ", ".join(
                f"{k}={v}" for k, v in tc["input"].items()
            ) if tc["input"] else ""
            st.markdown(
                f'<span style="color:{COLORS["blue"]};font-size:11px;font-family:monospace">'
                f'{tc["name"]}({args_str})</span>',
                unsafe_allow_html=True,
            )


def _build_llm_messages():
    """Build LLM message list from session state (last 20 messages, Anthropic format)."""
    messages = st.session_state[_MSG_KEY]

    # Keep last 20 messages (user + assistant pairs)
    recent = messages[-20:]

    llm_msgs = []
    for msg in recent:
        if msg["role"] == "user":
            llm_msgs.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            llm_msgs.append({"role": "assistant", "content": msg["content"]})

    return llm_msgs
