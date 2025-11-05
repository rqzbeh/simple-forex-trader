# Forex, Commodities & Indices News Trading Bot

A Python-based automated trading bot that analyzes forex, commodities, and indices news and market data to generate trading signals. It combines sentiment analysis from news articles with technical analysis, **LLM-enhanced news analysis**, and **machine learning predictions** for automated trading.

## Features

- **LLM-Enhanced News Analysis** (NEW!): Uses Large Language Models to deeply understand news and predict market impact
  - Analyzes how news affects people, markets, and specific instruments
  - Predicts market impact level (high/medium/low) and time horizon
  - Provides reasoning and market mechanisms for each analysis
  - Supports OpenAI GPT-4 and Anthropic Claude models
  - Blends LLM insights with traditional sentiment analysis
  - Falls back gracefully to keyword-based analysis when disabled
- **Machine Learning Integration**: Uses scikit-learn ensemble models (Random Forest & Gradient Boosting) to predict trade outcomes
  - Automatically trains on historical trade data
  - Filters trades based on ML confidence and probability scores
  - Periodic retraining every 24 hours for continuous improvement
  - Enhanced with LLM features (2 additional features) for better predictions
- **News Aggregation**: Fetches forex, commodities, and indices-related news from NewsAPI and multiple RSS feeds from authoritative sources
  - Includes 27 news sources from reputable financial outlets
  - RSS feed sources: CNBC Business, Financial Times, Wall Street Journal, MarketWatch, Bloomberg, Reuters, Forbes, and more
  - Web sources: Forex Factory, DailyFX, Investing.com, FXStreet, ForexLive, and others
- **Sentiment Analysis**: Uses TextBlob to analyze news sentiment, with boosts for central bank and economic data sources
- **Advanced Technical Analysis**: Incorporates 14 key indicators optimized for forex, commodities, and indices:
  - RSI (Relative Strength Index) - Momentum oscillator
  - MACD (Moving Average Convergence Divergence) - Trend following
  - Bollinger Bands - Volatility indicator
  - Trend (EMA50 vs EMA200) - Long-term trend
  - Advanced Candlestick Patterns - Price action
  - OBV (On-Balance Volume) - Volume confirmation
  - FVG (Fair Value Gaps) - Institutional levels
  - VWAP (Volume Weighted Average Price) - Institutional benchmark
  - Stochastic Oscillator - Momentum
  - CCI (Commodity Channel Index) - Momentum
  - Hurst Exponent - Trend persistence
  - ADX (Average Directional Index) - Trend strength
  - Williams %R - Momentum oscillator
  - Parabolic SAR - Trend and stop placement
- **Multi-Source Data**: Fallback data sources including YFinance, Alpha Vantage, Polygon, Twelve Data, FMP, Quandl, FRED, and IEX for robust market data
- **Automated Trading**: Integrates with forex broker APIs for automatic trade execution
- **Risk Management**: Calculates optimal stop losses (0.08-0.2%), leverage (up to 50:1 forex, 5:1 stocks), and risk-reward ratios (minimum 2:1)
- **Market Session Awareness**: Adjusts trading parameters based on current market session (Sydney, Tokyo, London, New York)
- **Telegram Notifications**: Sends trade recommendations via Telegram (optional)
- **Adaptive Learning**: Evaluates past trades and adjusts indicator weights for improved performance
- **Low Money Mode**: Optimized settings for smaller trading accounts (< $500)
- **Backtesting**: Automatic parameter validation on 90 days of historical data

## Requirements

- Python 3.8 or higher
- NewsAPI account (free tier available)
- Broker API access (e.g., Oanda, MetaTrader) for automated trading
- Internet connection for data fetching
- (Optional) OpenAI or Anthropic API key for LLM-enhanced news analysis

## Dependencies

Install the required packages using pip:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install newsapi-python yfinance textblob requests alpha_vantage iexfinance polygon-api-client twelvedata fmp-python quandl fredapi scikit-learn numpy pandas joblib openai anthropic
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
- `OPENAI_API_KEY`: Your OpenAI API key (optional, for LLM-enhanced news analysis)
- `ANTHROPIC_API_KEY`: Your Anthropic API key (optional, alternative to OpenAI)
- `LLM_NEWS_ANALYSIS_ENABLED`: Set to `true` to enable LLM news analysis (default: false)
- `LLM_PROVIDER`: LLM provider to use: `openai`, `anthropic`, or `local` (default: openai)
- `LLM_MODEL`: Specific model to use (e.g., `gpt-4o-mini`, `claude-3-5-sonnet-20241022`)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (optional, for notifications)
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (optional, for notifications)
- `BROKER_API_KEY`: Your forex broker API key (optional, for automated trading)
- `BROKER_ACCOUNT_ID`: Your broker account ID (optional, for automated trading)

### Settings

Edit the constants in `main.py` to customize:

- `ML_ENABLED`: Enable/disable machine learning predictions (default: True)
- `ML_MIN_CONFIDENCE`: Minimum ML confidence threshold (default: 0.60)
- `ML_MIN_PROBABILITY`: Minimum win probability from ML (default: 0.55)
- `ML_RETRAIN_INTERVAL`: Hours between ML model retraining (default: 24)
- `LLM_NEWS_ANALYSIS_ENABLED`: Enable/disable LLM-enhanced news analysis (default: False)
- `LLM_PROVIDER`: LLM provider: 'openai', 'anthropic', or 'local' (default: 'openai')
- `LLM_MODEL`: Specific model name (auto-selects if None)
- `LLM_SENTIMENT_WEIGHT`: Weight for LLM sentiment vs basic (0.0-1.0, default: 0.7)
- `LOW_MONEY_MODE`: Set to `True` for smaller accounts (< $500)
- `MAX_LEVERAGE_FOREX`: Maximum leverage for forex trades (default: 50)
- `MAX_LEVERAGE_STOCK`: Maximum leverage for stock/indices trades (default: 5)
- `DAILY_RISK_LIMIT`: Maximum daily loss as percentage (default: 0.02 = 2%)
- Risk parameters: `MIN_STOP_PCT`, `EXPECTED_RETURN_PER_SENTIMENT`, etc.

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
- Recommended leverage
- Risk-reward ratio
- **ML probability and confidence scores** (when ML is enabled)

## Machine Learning

The bot includes a sophisticated ML predictor that:

1. **Trains on historical trades**: Learns from past wins and losses
2. **Predicts trade outcomes**: Estimates probability of success for each trade
3. **Filters low-quality trades**: Only suggests trades with high ML confidence
4. **Continuous learning**: Retrains every 24 hours to adapt to market conditions

The ML model uses ensemble methods (Random Forest + Gradient Boosting) with 23 features including:
- Sentiment and news count
- All 14 technical indicator signals
- Market volatility and ATR
- Price distance to support/resistance/pivot levels
- LLM confidence and market impact scores (when LLM enabled)

## LLM-Enhanced News Analysis

The bot includes an **optional** LLM-powered news analyzer that provides deeper market insights:

### What It Does

- **Deep Understanding**: Uses GPT-4 or Claude to understand news context and implications
- **Market Impact Analysis**: Predicts how news affects specific instruments (high/medium/low)
- **People & Market Effects**: Analyzes how news impacts consumers, investors, and market mechanisms
- **Time Horizon**: Estimates when effects will materialize (immediate/short/medium/long-term)
- **Confidence Scoring**: Provides confidence levels for each prediction
- **Reasoning**: Explains the analysis in human-readable terms

### How It Works

1. Analyzes up to 10 most recent news articles per trading symbol
2. Sends articles to LLM with specialized financial analyst prompt
3. Receives structured analysis (sentiment, impact, reasoning, etc.)
4. Blends LLM sentiment with basic TextBlob sentiment (weighted average)
5. Boosts expected returns for high-impact news
6. Feeds LLM features into ML predictor for better trade filtering

### Enabling LLM Analysis

Set these environment variables:

```bash
export LLM_NEWS_ANALYSIS_ENABLED=true
export OPENAI_API_KEY=your_openai_key  # For GPT-4
# OR
export ANTHROPIC_API_KEY=your_anthropic_key  # For Claude
```

Optional configuration:

```bash
export LLM_PROVIDER=openai  # or 'anthropic'
export LLM_MODEL=gpt-4o-mini  # or 'claude-3-5-sonnet-20241022'
```

### Cost Considerations

- **Disabled by default** - zero cost unless explicitly enabled
- OpenAI GPT-4o-mini: ~$0.15 per million tokens (very affordable)
- Anthropic Claude Sonnet: ~$3 per million tokens
- Typical usage: ~10 articles × 10 symbols = 100 API calls per run
- Estimated cost per run: $0.01-0.05 depending on model

### Fallback Behavior

If LLM is disabled or API fails:
- Falls back to keyword-based sentiment analysis
- Still provides market impact estimates (simple rules)
- Trading continues normally without interruption
- Zero degradation in basic functionality

## Files

- `main.py`: Main bot script
- `ml_predictor.py`: Machine learning prediction module
- `llm_news_analyzer.py`: LLM-enhanced news analysis module (NEW!)
- `trade_log.json`: Log of recommended trades (created automatically)
- `ml_model.pkl`: Trained ML model (created after first training)
- `ml_scaler.pkl`: Feature scaler for ML (created after first training)
- `ml_last_train.json`: Timestamp of last ML training
- `daily_risk.json`: Daily risk tracking
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