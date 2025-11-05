# Forex, Commodities & Indices News Trading Bot

A Python-based automated trading bot that analyzes forex, commodities, and indices news and market data to generate trading signals. It combines sentiment analysis from news articles with technical analysis, **LLM-enhanced news analysis**, **AI-powered market psychology detection**, **dual machine learning systems**, and **advanced quantitative risk management** for automated trading.

## Features

### Core Intelligence Systems

- **LLM-Enhanced News Analysis** (MANDATORY): Uses Groq LLMs for all sentiment and market impact analysis
  - Analyzes how news affects people, markets, and specific instruments
  - Predicts market impact level (high/medium/low) and time horizon
  - Provides reasoning and market mechanisms for each analysis
  - Supports multiple Groq models (llama-3.3-70b-versatile, llama-3.1-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it, llama3-70b-8192)
  - Default model: llama-3.3-70b-versatile (GPT OSS 120B equivalent)
  - **No fallback** - LLM handles all sentiment analysis (no TextBlob)
  - **Rate limiting**: Built-in Groq free tier limit enforcement (1k requests/day, 500K tokens/day)
  - **Duplicate detection**: Automatically skips already-analyzed news articles
  - **Free tier available** with Groq

- **Market Psychology Analysis**: AI-powered detection of fear, greed, and irrational behavior
  - Analyzes market sentiment beyond fundamentals (fear, greed, panic, euphoria, uncertainty)
  - Detects irrational market behavior caused by human emotions
  - Fear/Greed Index: -1.0 (extreme fear) to +1.0 (extreme greed)
  - Irrationality Score: 0.0 (rational) to 1.0 (highly irrational)
  - Trading recommendations: contrarian opportunities, follow momentum, or stay neutral
  - Adjusts trade strategy when markets are driven by emotion rather than fundamentals
  - Helps identify when technical analysis may be unreliable due to panic/euphoria
  - **AI Performance Tracker**: Learns from emotional trade failures to improve psychology analysis

- **Advanced Risk Management** (NEW - Inspired by Renaissance Technologies):
  - **Kelly Criterion Position Sizing**: Optimal position sizing based on win rate and risk/reward
  - **Market Regime Detection**: Auto-detects trending, ranging, or volatile markets
  - **Correlation-Based Trade Filtering**: Prevents opening correlated positions that compound risk
  - **Sharpe Ratio Optimization**: Dynamically adjusts component weights based on risk-adjusted returns
  - **Multi-layer Risk Controls**: Daily limits, per-trade limits, correlation-adjusted exposure
  - **Dynamic Stop-Loss**: ATR-based stops that adapt to market volatility
  - Configurable via environment variables (all features can be enabled/disabled)

- **Dual Machine Learning System**: Two ML models work together for optimal performance
  - **ML System 1** (ml_predictor.py): Optimizes technical analysis, learns from analytical failures
  - **ML System 2** (news_impact_predictor.py): Classifies failures as analytical vs emotional
  - Automatically trains on historical trade data
  - Filters trades based on ML confidence and probability scores
  - Periodic retraining every 24 hours for continuous improvement
  - Enhanced with LLM features for better predictions
  - Routes failures to appropriate learning system (analytical → ML, emotional → AI)
- **News Aggregation**: Fetches forex, commodities, and indices-related news from NewsAPI and multiple RSS feeds from authoritative sources
  - Includes 27 news sources from reputable financial outlets
  - RSS feed sources: CNBC Business, Financial Times, Wall Street Journal, MarketWatch, Bloomberg, Reuters, Forbes, and more
  - Web sources: Forex Factory, DailyFX, Investing.com, FXStreet, ForexLive, and others
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
- **Groq API key** (REQUIRED for LLM-enhanced news analysis - free tier available)
- Broker API access (e.g., Oanda, MetaTrader) for automated trading
- Internet connection for data fetching

## Dependencies

Install the required packages using pip:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install newsapi-python yfinance textblob requests alpha_vantage iexfinance polygon-api-client twelvedata fmp-python quandl fredapi scikit-learn numpy pandas joblib groq
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
- `GROQ_API_KEY`: Your Groq API key (REQUIRED - get free tier at console.groq.com)
- `LLM_PROVIDER`: LLM provider (only `groq` is supported, default: groq)
- `LLM_MODEL`: Specific model to use (default: `llama-3.3-70b-versatile`)
  - Available models: `llama-3.3-70b-versatile`, `llama-3.1-70b-versatile`, `mixtral-8x7b-32768`, `gemma2-9b-it`, `llama3-70b-8192`
- `GROQ_MAX_REQUESTS_PER_DAY`: Max API requests per day (default: 1000, set to 0 to disable)
- `GROQ_MAX_TOKENS_PER_DAY`: Max tokens per day (default: 500000, set to 0 to disable)
- `GROQ_ENFORCE_LIMITS`: Enforce rate limits (default: true, set to false to disable all limits)
- `PSYCHOLOGY_ANALYSIS_ENABLED`: Enable market psychology analysis (default: true)
- `PSYCHOLOGY_IRRATIONALITY_THRESHOLD`: Threshold for applying psychology adjustments (default: 0.6)
- `KELLY_CRITERION_ENABLED`: Enable Kelly Criterion position sizing (default: true)
- `KELLY_FRACTION`: Kelly fraction for safety (default: 0.5 for half-Kelly)
- `REGIME_DETECTION_ENABLED`: Enable market regime detection (default: true)
- `CORRELATION_FILTER_ENABLED`: Enable correlation-based trade filtering (default: true)
- `MAX_CORRELATION_EXPOSURE`: Maximum correlation exposure multiplier (default: 2.0)
- `SHARPE_TRACKING_ENABLED`: Enable Sharpe ratio tracking and optimization (default: true)
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
- `LLM_PROVIDER`: LLM provider (only 'groq' is supported)
- `LLM_MODEL`: Specific model name (default: 'llama-3.3-70b-versatile')
- `GROQ_MAX_REQUESTS_PER_DAY`: Daily request limit (default: 1000)
- `GROQ_MAX_TOKENS_PER_DAY`: Daily token limit (default: 500000)
- `GROQ_ENFORCE_LIMITS`: Enable rate limiting (default: true)
- `PSYCHOLOGY_ANALYSIS_ENABLED`: Enable market psychology analysis (default: true)
- `PSYCHOLOGY_IRRATIONALITY_THRESHOLD`: Irrationality threshold for trade adjustments (default: 0.6)
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

The bot includes TWO sophisticated ML systems working together:

### ML System 1: Trade Predictor (ml_predictor.py)
Optimizes analytical trading decisions and learns from past performance:

1. **Trains on historical trades**: Learns from past wins and losses
2. **Predicts trade outcomes**: Estimates probability of success for each trade
3. **Filters low-quality trades**: Only suggests trades with high ML confidence
4. **Continuous learning**: Retrains every 24 hours to adapt to market conditions
5. **Indicator weight optimization**: Adjusts technical indicator weights based on performance

The ML model uses ensemble methods (Random Forest + Gradient Boosting) with 23 features including:
- Sentiment and news count
- All 14 technical indicator signals
- Market volatility and ATR
- Price distance to support/resistance/pivot levels
- LLM confidence and market impact scores
- Psychology irrationality scores and fear/greed index

### ML System 2: Failure Classifier (news_impact_predictor.py)
Classifies trade failures to improve learning:

1. **Determines failure cause**: Identifies if failure was due to:
   - **Analytical**: Technical indicators were wrong (fundamental issue)
   - **Emotional**: Market psychology/news-driven behavior caused unexpected moves
   - **Mixed**: Combination of both factors

2. **Feeds learning**: Routes failures to appropriate learning system:
   - Analytical failures → ML System 1 learns better indicator weighting
   - Emotional failures → AI Performance Tracker learns better psychology analysis

3. **Considers multiple factors**:
   - Technical indicator agreement rate
   - News volume and sentiment strength
   - Psychology irrationality scores
   - Volatility patterns suggesting emotional moves

### AI Performance Tracker (NEW)
Learns from emotional/psychology-driven failures to improve AI analysis:

1. **Tracks AI accuracy**: Monitors when psychology analysis was correct vs incorrect
2. **Pattern recognition**: Identifies which emotions (fear, greed, panic, euphoria) AI misjudges
3. **Confidence weighting**: Adjusts how much to trust AI psychology recommendations
   - Success rate > 65% → increase AI confidence weight up to 1.5x
   - Success rate < 45% → decrease AI confidence weight down to 0.5x
4. **Prompt improvement**: Suggests better API prompts based on failure patterns
5. **Performance statistics**: Shows success rate, failure patterns, and improvements

**Why Two ML Systems?**
- Technical analysis and human psychology require different learning approaches
- ML trained on price patterns excels at technical analysis
- LLM pre-trained on human language excels at understanding emotions
- Combining both creates a complete trading system that handles rational AND irrational markets

## LLM-Enhanced News Analysis

The bot **requires** Groq LLM for news analysis to provide deeper market insights:

### What It Does

- **Deep Understanding**: Uses Groq LLM to understand news context and implications
- **Market Impact Analysis**: Predicts how news affects specific instruments (high/medium/low)
- **People & Market Effects**: Analyzes how news impacts consumers, investors, and market mechanisms
- **Time Horizon**: Estimates when effects will materialize (immediate/short/medium/long-term)
- **Confidence Scoring**: Provides confidence levels for each prediction
- **Reasoning**: Explains the analysis in human-readable terms
- **Duplicate Detection**: Automatically skips news articles that have already been analyzed
- **Rate Limiting**: Built-in protection against exceeding free tier limits

### How It Works

1. Analyzes up to 10 most recent news articles per trading symbol
2. Checks rate limits before making API calls (respects free tier: 1k requests/day, 500K tokens/day)
3. Sends articles to Groq LLM with specialized financial analyst prompt
4. Receives structured analysis (sentiment, impact, reasoning, etc.)
5. Uses LLM sentiment directly (no TextBlob fallback)
6. Boosts expected returns for high-impact news
7. Feeds LLM features into ML predictor for better trade filtering
8. Tracks usage and warns when approaching limits

### Setup (REQUIRED)

Get a free Groq API key at [console.groq.com](https://console.groq.com) and set:

```bash
export GROQ_API_KEY=your_groq_api_key
```

Optional configuration:

```bash
export LLM_MODEL=llama-3.3-70b-versatile  # Default, can use other models
# Available: llama-3.3-70b-versatile, llama-3.1-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it, llama3-70b-8192

# Rate limiting (defaults to Groq free tier)
export GROQ_MAX_REQUESTS_PER_DAY=1000
export GROQ_MAX_TOKENS_PER_DAY=500000
export GROQ_ENFORCE_LIMITS=true  # Set to false to disable (may exceed free tier)
```

### Free Tier & Rate Limits

- **Free tier**: 1,000 requests/day, 500,000 tokens/day
- **Automatic tracking**: Bot tracks usage and prevents exceeding limits
- **Smart optimization**: 
  - Duplicate detection reduces redundant API calls
  - Caching prevents re-analyzing same articles
  - Running hourly (24 times/day) stays well within limits
- **Manual override**: Set `GROQ_ENFORCE_LIMITS=false` to disable (use with caution)
- **Usage stats**: Displayed in bot output and logged to `groq_usage.json`

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