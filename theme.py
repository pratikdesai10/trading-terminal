"""Bloomberg dark terminal theme for Streamlit."""

import streamlit as st


def apply_theme():
    """Inject Bloomberg-style dark CSS into Streamlit."""
    st.markdown(
        """
        <style>
        /* ── Global background & text ── */
        .stApp, .main, [data-testid="stAppViewContainer"] {
            background-color: #0A0A0A !important;
            color: #E0E0E0 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
        }
        [data-testid="stHeader"] {
            background-color: #0A0A0A !important;
        }

        /* ── Font ── */
        html, body, .stApp, .stMarkdown, .stText,
        [data-testid="stMarkdownContainer"],
        .stDataFrame, .stTable {
            font-family: 'Fira Code', 'Consolas', 'Courier New', monospace !important;
            font-size: 13px !important;
        }

        /* ── Headings: Bloomberg amber ── */
        h1, h2, h3, h4, h5, h6,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #FF9900 !important;
            font-family: 'Fira Code', 'Consolas', 'Courier New', monospace !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px;
        }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 15px !important; }

        /* ── Metrics ── */
        [data-testid="stMetric"] {
            background-color: #1A1A1A !important;
            border: 1px solid #333333 !important;
            border-radius: 4px;
            padding: 10px 14px !important;
        }
        [data-testid="stMetricLabel"] {
            color: #FF9900 !important;
            font-size: 11px !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        [data-testid="stMetricValue"] {
            color: #E0E0E0 !important;
            font-size: 20px !important;
            font-family: 'Fira Code', monospace !important;
        }
        [data-testid="stMetricDelta"] > div {
            font-family: 'Fira Code', monospace !important;
            font-size: 12px !important;
        }

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #111111 !important;
            border-bottom: 2px solid #333333 !important;
            gap: 0px;
        }
        .stTabs [data-baseweb="tab"] {
            color: #888888 !important;
            background-color: transparent !important;
            border: none !important;
            padding: 8px 20px !important;
            font-size: 12px !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-family: 'Fira Code', monospace !important;
        }
        .stTabs [aria-selected="true"] {
            color: #FF9900 !important;
            border-bottom: 2px solid #FF9900 !important;
            background-color: #1A1A1A !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #FF9900 !important;
        }

        /* ── DataFrames / Tables ── */
        .stDataFrame, [data-testid="stDataFrame"] {
            border: 1px solid #333333 !important;
        }
        .stDataFrame table {
            font-size: 12px !important;
            font-family: 'Fira Code', monospace !important;
        }
        .stDataFrame thead th {
            background-color: #1A1A1A !important;
            color: #FF9900 !important;
            font-size: 11px !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #FF9900 !important;
        }
        .stDataFrame tbody td {
            background-color: #0A0A0A !important;
            color: #E0E0E0 !important;
            border-bottom: 1px solid #1A1A1A !important;
        }

        /* ── Sidebar widgets ── */
        .stSelectbox label, .stMultiSelect label, .stTextInput label,
        .stNumberInput label, .stDateInput label, .stSlider label {
            color: #FF9900 !important;
            font-size: 11px !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stSelectbox [data-baseweb="select"],
        .stMultiSelect [data-baseweb="select"],
        .stTextInput input, .stNumberInput input {
            background-color: #1A1A1A !important;
            color: #E0E0E0 !important;
            border: 1px solid #333333 !important;
            font-family: 'Fira Code', monospace !important;
        }

        /* ── Buttons ── */
        .stButton > button {
            background-color: #1A1A1A !important;
            color: #FF9900 !important;
            border: 1px solid #FF9900 !important;
            font-family: 'Fira Code', monospace !important;
            font-size: 12px !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stButton > button:hover {
            background-color: #FF9900 !important;
            color: #0A0A0A !important;
        }

        /* ── Expander ── */
        .streamlit-expanderHeader {
            background-color: #1A1A1A !important;
            color: #FF9900 !important;
            border: 1px solid #333333 !important;
        }

        /* ── Dividers ── */
        hr {
            border-color: #333333 !important;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0A0A0A;
        }
        ::-webkit-scrollbar-thumb {
            background: #333333;
            border-radius: 3px;
        }

        /* ── Toast / alerts ── */
        .stAlert {
            background-color: #1A1A1A !important;
            border: 1px solid #333333 !important;
            color: #E0E0E0 !important;
        }

        /* ── Reduce default Streamlit padding ── */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            max-width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
