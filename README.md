# Indian Bloomberg Terminal

Bloomberg-style terminal for Indian markets (NSE/BSE) built with Python and Streamlit. Dark terminal aesthetic with dense, monospace data layout. 100% free, no API keys needed.

## Features

| Module | Function        | Description                                                                               |
| ------ | --------------- | ----------------------------------------------------------------------------------------- |
| M01    | Market Overview | Live indices, market breadth, sector performance, top gainers/losers                      |
| M02    | Watchlist       | Custom watchlist with live quotes                                                         |
| M03    | Charts          | Interactive candlestick charts with technical indicators (SMA, EMA, Bollinger, RSI, MACD) |
| M04    | Company         | Company description, key stats, shareholding                                              |
| M05    | Financials      | Income statement, balance sheet, cash flow, key ratios                                    |
| M06    | Screener        | Multi-criteria stock screener (P/E, P/B, ROE, D/E, dividend yield)                        |
| M07    | Options         | Option chain with OI heatmap, PCR, max pain                                               |
| M08    | Heatmap         | Sector treemap colored by performance                                                     |
| M09    | Comparison      | Normalized performance comparison of up to 5 stocks/indices                               |
| M10    | Portfolio       | Manual portfolio tracker with live P&L, allocation charts                                 |
| M11    | Backtest        | Strategy backtesting (SMA Crossover, RSI, MACD, Bollinger)                                |
| M12    | Optimizer       | Portfolio optimization (Max Sharpe, Min Vol, Risk Parity, Efficient Frontier)             |
| M13    | Economic        | RBI rates, USD/INR, crude oil, gold, treasury yields, economic calendar                   |
| M14    | FII/DII         | Foreign and domestic institutional investor flow tracker                                  |
| M15    | News            | RSS news aggregation with sentiment analysis                                              |
| M16    | Alerts          | Price and % change alerts with live monitoring                                            |
| M17    | Paper Trading   | Virtual cash trading with order execution, position tracking, realized P&L                |

## Tech Stack

- **Python 3.12+** / **Streamlit 1.55**
- **Data**: jugaad-data (NSE live/historical), yfinance (fundamentals), feedparser (news RSS)
- **Charts**: Plotly
- **Analytics**: scipy, ta, numpy, pandas

## Data Sources

| Source      | Role                | What It Provides                                                 |
| ----------- | ------------------- | ---------------------------------------------------------------- |
| jugaad-data | Primary             | NSE live quotes, historical OHLCV, index data, F&O data          |
| nsetools    | Fallback            | Real-time NSE quotes, index quotes                               |
| yfinance    | Fundamentals/Global | Company financials, balance sheet, cash flow, forex, commodities |
| feedparser  | News                | RSS feeds from financial news sources                            |

All sources are free and require no API keys. Data is scraped directly from NSE and Yahoo Finance.

## Architecture

```
app.py                    Streamlit entry point, tab router
  |
  +-- modules/            17 self-contained modules (m01-m17), each with a render() function
  |     |
  |     +-- data/         Data fetching layer with caching (jugaad-data, nsetools, yfinance)
  |     |
  |     +-- analytics/    Calculation engines (screener, risk metrics)
  |
  +-- theme.py            Bloomberg dark CSS (black #0A0A0A bg, amber #FF9900, green/red)
  +-- config.py           Nifty 50 symbols, sector mappings, constants
  +-- utils/              Formatting helpers (Indian number grouping, currency display)
```

Each module is a standalone file that fetches its own data through the `data/` layer and renders its UI. The data layer uses `st.cache_data` with TTL-based expiration to avoid rate limiting.

## Authentication

The terminal uses JWT-based authentication. Each user gets isolated data (portfolio, watchlist, alerts, paper trades).

- Sign up with username, email, and password
- Passwords are hashed with bcrypt
- JWT tokens expire after 24 hours

## Deployment (Streamlit Community Cloud)

1. Push the repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and click "New app"
3. Connect your GitHub repo, set `app.py` as the entry point
4. In **Advanced settings** > **Secrets**, add:
   ```
   JWT_SECRET = "your-secure-random-string"
   ```
5. Click **Deploy**

## Local Development

```bash
git clone https://github.com/pratikdesai10/trading-terminal.git
cd trading-terminal
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
JWT_SECRET = "dev-secret"
```

Run the app:
```bash
streamlit run app.py
```

## Market Hours

NSE trading hours: **9:15 AM - 3:30 PM IST**, Monday to Friday. The terminal shows live market status in the header. Data refreshes every 60 seconds during market hours.

## License

Apache 2.0
