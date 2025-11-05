# Forex, Commodities & Indices News Trading Bot

A Python-based automated trading bot that analyzes forex, commodities, and indices news and market data to generate trading signals. It combines sentiment analysis from news articles with technical analysis for automated trading.

## Features

- **News Aggregation**: Fetches forex, commodities, and indices-related news from NewsAPI and multiple RSS feeds from authoritative sources
  - Includes 27 news sources from reputable financial outlets
  - RSS feed sources: CNBC Business, Financial Times, Wall Street Journal, MarketWatch, Bloomberg, Reuters, Forbes, and more
  - Web sources: Forex Factory, DailyFX, Investing.com, FXStreet, ForexLive, and others
- **Sentiment Analysis**: Uses TextBlob to analyze news sentiment, with boosts for central bank and economic data sources
- **Technical Analysis**: Uses 7 essential indicators with additive scoring system:
  - RSI (Relative Strength Index) - 15% weight
  - MACD (Moving Average Convergence Divergence) - 15% weight
  - Bollinger Bands - 10% weight
  - EMA Trend (50 vs 200) - 25% weight (highest importance)
  - VWAP (Volume Weighted Average Price) - 15% weight
  - ADX (Average Directional Index) - 15% weight
  - Parabolic SAR - 5% weight
- **Correlation Analysis**: Filters highly correlated pairs to reduce portfolio risk
- **Economic Calendar**: Detects high-impact events and adjusts leverage accordingly
- **Execution Cost Modeling**: Accounts for spreads (1 pip) and slippage (0.5 pip) in forex trades
- **Conservative Risk Management**: 
  - Minimum 10 pip stop loss (0.1%)
  - Maximum 20x leverage (reduced from 100x)
  - Spreads and slippage automatically deducted from expected returns
- **Multi-Source Data**: Fallback data sources including YFinance, Alpha Vantage, Polygon, Twelve Data, FMP, Quandl, FRED, and IEX for robust market data
- **Automated Trading**: Integrates with forex broker APIs for automatic trade execution
- **Market Session Awareness**: Adjusts trading parameters based on current market session (Sydney, Tokyo, London, New York)
- **Telegram Notifications**: Sends trade recommendations via Telegram (optional)
- **Adaptive Learning**: Evaluates past trades and adjusts indicator weights for improved performance
- **Low Money Mode**: Optimized settings for smaller trading accounts

## Recent Improvements

### v2.1 - Critical Safety Updates
- ✅ **Stop Loss Fix**: Increased from 2 pips to 10 pips minimum (accounts for spreads)
- ✅ **Leverage Reduction**: Reduced from 100x to 20x maximum for safety
- ✅ **Weight System**: Replaced multiplicative weights with additive scoring (sum to 1.0)
- ✅ **Execution Costs**: Added spread (0.01%) and slippage (0.005%) modeling
- ✅ **Indicator Cleanup**: Removed redundant indicators (Stochastic, CCI, Williams %R, OBV, Hurst)
- ✅ **Correlation Filter**: Avoid trading highly correlated pairs (>70% correlation)
- ✅ **Economic Calendar**: Detects high-impact events and reduces leverage by 50%

## Requirements

- Python 3.8 or higher
- NewsAPI account (free tier available)
- Broker API access (e.g., Oanda, MetaTrader) for automated trading
- Internet connection for data fetching

## Dependencies

Install the required packages using pip:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install newsapi-python yfinance textblob requests alpha_vantage iexfinance polygon-api-client twelvedata fmp-python quandl fredapi
```

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/rqzbeh/simple-forex-trader.git
   cd simple-forex-trader
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables

Set the following environment variables:

- `NEWS_API_KEY`: Your NewsAPI key (required)
- `ALPHA_VANTAGE_API_KEY`: Your Alpha Vantage API key (optional, for forex data fallback)
- `POLYGON_API_KEY`: Your Polygon.io API key (optional, for advanced market data)
- `TWELVE_DATA_API_KEY`: Your Twelve Data API key (optional, for global market data)
- `FMP_API_KEY`: Your Financial Modeling Prep API key (optional, for stock data)
- `QUANDL_API_KEY`: Your Quandl/Nasdaq Data Link API key (optional, for economic data)
- `FRED_API_KEY`: Your FRED API key (optional, for macroeconomic data)
- `IEX_API_TOKEN`: Your IEX Cloud API token (optional, for stock data)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (optional, for notifications)
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (optional, for notifications)
- `BROKER_API_KEY`: Your forex broker API key (optional, for automated trading)
- `BROKER_ACCOUNT_ID`: Your broker account ID (optional, for automated trading)

### Settings

Edit the constants in `main.py` to customize:

- `LOW_MONEY_MODE`: Set to `True` for smaller accounts (< $500)
- `MAX_LEVERAGE_FOREX`: Maximum leverage for forex trades (default: 20x)
- `MIN_STOP_PCT`: Minimum stop loss percentage (default: 0.1% or 10 pips)
- `CORRELATION_THRESHOLD`: Maximum correlation between pairs (default: 0.7)
- Risk parameters: `EXPECTED_RETURN_PER_SENTIMENT`, `FOREX_SPREAD_PCT`, `FOREX_SLIPPAGE_PCT`, etc.
- Indicator weights in `WEIGHTS` dictionary (must sum to 1.0)

## Usage

Run the bot:

```bash
python main.py
```

The bot will:

1. Check the current market session
2. Fetch recent forex, commodities, and indices news
3. Analyze sentiment and technical indicators
4. Generate trade recommendations
5. Execute trades automatically via broker API (if configured)
6. Send notifications via Telegram (if configured)
7. Log trades to `trade_log.json`
8. Evaluate performance and adjust parameters

## Output

The bot outputs recommended trades in the console and via Telegram, including:

- Symbol and direction (LONG/SHORT)
- Entry price
- Stop loss and take profit levels
- Recommended leverage (max 20x for forex)
- Risk-reward ratio
- Indicator alignment score (0.0 to 1.0)
- Execution cost adjustments (spread + slippage)

## Files

- `main.py`: Main bot script
- `trade_log.json`: Log of recommended trades (created automatically)
- `README.md`: This file

## Risk Disclaimer

**IMPORTANT**: This software is for educational and research purposes only. It is not intended to provide financial advice, and trading forex, commodities, and indices involves significant risk of loss.

The authors are not responsible for any financial losses incurred through the use of this software.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you find this project helpful, please give it a star on GitHub!