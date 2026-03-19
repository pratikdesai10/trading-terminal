"""Number formatting utilities for Indian market display."""


def format_inr(value, decimals=2):
    """Format a number as ₹ with Indian comma grouping (12,34,567)."""
    if value is None:
        return "—"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "—"

    negative = value < 0
    value = abs(value)

    # Split integer and decimal parts
    int_part = int(value)
    dec_part = f".{round(value % 1 * (10 ** decimals)):0{decimals}d}" if decimals > 0 else ""

    # Indian grouping: last 3 digits, then groups of 2
    s = str(int_part)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while rest:
            groups.append(rest[-2:])
            rest = rest[:-2]
        groups.reverse()
        s = ",".join(groups) + "," + last3
    result = f"₹{s}{dec_part}"
    return f"-{result}" if negative else result


def format_crore(value):
    """Convert a number to ₹ Crores format."""
    if value is None:
        return "—"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "—"

    cr = value / 1e7
    if abs(cr) >= 100:
        return f"₹{cr:,.0f} Cr"
    elif abs(cr) >= 1:
        return f"₹{cr:,.2f} Cr"
    else:
        lakh = value / 1e5
        return f"₹{lakh:,.2f} L"


def format_lakh(value):
    """Convert a number to ₹ Lakhs format."""
    if value is None:
        return "—"
    try:
        lakh = float(value) / 1e5
    except (ValueError, TypeError):
        return "—"
    return f"₹{lakh:,.2f} L"


def format_pct(value, decimals=2):
    """Format a number as percentage."""
    if value is None:
        return "—"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "—"
    return f"{value:+.{decimals}f}%"


def format_number(value, decimals=2):
    """Format a plain number with commas."""
    if value is None:
        return "—"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "—"
    if abs(value) >= 1e7:
        return f"{value / 1e7:,.2f} Cr"
    elif abs(value) >= 1e5:
        return f"{value / 1e5:,.2f} L"
    else:
        return f"{value:,.{decimals}f}"


def format_volume(value):
    """Format volume with K/L/Cr suffixes."""
    if value is None:
        return "—"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "—"
    if value >= 1e7:
        return f"{value / 1e7:,.2f} Cr"
    elif value >= 1e5:
        return f"{value / 1e5:,.2f} L"
    elif value >= 1e3:
        return f"{value / 1e3:,.1f}K"
    else:
        return f"{value:,.0f}"


def color_change(value):
    """Return CSS color based on positive/negative value."""
    if value is None:
        return "#E0E0E0"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "#E0E0E0"
    if value > 0:
        return "#00CC66"
    elif value < 0:
        return "#FF3333"
    return "#E0E0E0"


def colored_text(text, value):
    """Wrap text in a colored span based on value sign."""
    c = color_change(value)
    return f'<span style="color:{c};font-family:monospace">{text}</span>'
