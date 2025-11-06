# Forex, Commodities & Indices Trading Signal Generator

A Python-based trading signal generator that analyzes forex, commodities, and indices news and market data to generate trading signals. It combines sentiment analysis from news articles with technical analysis, **LLM-enhanced news analysis**, **AI-powered market psychology detection**, **dual machine learning systems**, **advanced quantitative risk management**, and **self-learning parameters**.

**Note**: This is a **signal generator only**. It does not execute trades or connect to brokers. Signals are provided for manual trading or integration with your own trading system.

## Recent Fixes (November 2025)

**Major Update v2.1**: Fixed critical issues and improved ML learning:

- ✓ **Removed fake backtest data** - Backtest now uses real historical data instead of hardcoded results
- ✓ **Relaxed trade requirements** - Reduced minimum technical indicators from 3-4 to 2-3
- ✓ **Lowered sentiment threshold** - Reduced from 0.05 to 0.03 for easier trade triggers
- ✓ **Added technical-only trades** - Bot can now trade on pure technical signals without news sentiment
- ✓ **Increased expected returns** - Raised from 1.2% to 2.0-2.5% for more viable trades
- ✓ **Expanded trading hours** - Now trades in all sessions (not just London/NY), except weekends
- ✓ **Base return for tech trades** - Technical-only trades now have 0.2-1.0% base expected return
- ✓ **Real data learning** - ML now learns from actual price movements, checking if signals hit TP/SL
- ✓ **No broker needed** - Uses historical price data to evaluate trade outcomes for ML training

**Result**: Bot generates actionable signals consistently and learns from real market data without needing broker integration.

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
  - **Async/Concurrent**: Parallel news analysis for 3-4x faster execution

- **Market Psychology Analysis**: AI-powered detection of fear, greed, and irrational behavior
  - Analyzes market sentiment beyond fundamentals (fear, greed, panic, euphoria, uncertainty)
  - Detects irrational market behavior caused by human emotions
  - Fear/Greed Index: -1.0 (extreme fear) to +1.0 (extreme greed)
  - Irrationality Score: 0.0 (rational) to 1.0 (highly irrational)
  - Trading recommendations: contrarian opportunities, follow momentum, or stay neutral
  - Adjusts trade strategy when markets are driven by emotion rather than fundamentals
  - Helps identify when technical analysis may be unreliable due to panic/euphoria
  - **AI Performance Tracker**: Learns from emotional trade failures to improve psychology analysis

- **Advanced Risk Management** (Inspired by Renaissance Technologies):
  - **Kelly Criterion Position Sizing**: Optimal position sizing based on win rate and risk/reward
  - **Market Regime Detection**: Auto-detects trending, ranging, or volatile markets
  - **Correlation-Based Trade Filtering**: Prevents opening correlated positions that compound risk
  - **Sharpe Ratio Optimization**: Dynamically adjusts component weights based on risk-adjusted returns
  - **Multi-layer Risk Controls**: Daily limits, per-trade limits, correlation-adjusted exposure
  - **Dynamic Stop-Loss**: ATR-based stops that adapt to market volatility
  - **Learnable Parameters**: All thresholds and multipliers adapt based on trading performance
  - Configurable via environment variables (all features can be enabled/disabled)

- **Self-Learning Parameters** (NEW): Parameters that adapt based on performance
  - **Kelly Fraction**: Learns optimal leverage from win/loss patterns (0.3-0.7 range)
  - **Regime Thresholds**: ADX, volatility, trend agreement thresholds adapt to market behavior
  - **Correlation Limits**: Adjusts based on actual correlated trade performance
  - **Stop Multipliers**: Learns optimal stop-loss widths for different market regimes
  - **Psychology Thresholds**: Adjusts irrationality detection based on prediction accuracy
  - **Component Weights**: Sharpe-based optimization of technical/sentiment/psychology/ML weights
  - All parameters start with research-based defaults and improve over time
  - Stored in `learnable_params.json` (automatically managed)

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
- **Data Source**: YFinance provides all 14 indicators calculated from real historical data
- **Signal Generation**: Provides entry, stop loss, and take profit levels for manual trading
- **Risk Management**: Calculates optimal stop losses (0.08-0.2%), leverage (up to 50:1 forex, 5:1 stocks), and risk-reward ratios (minimum 2:1)
- **Market Session Awareness**: Adjusts trading parameters based on current market session (Sydney, Tokyo, London, New York)
- **Telegram Notifications**: Sends trade signals via Telegram (optional)
- **Adaptive Learning**: Evaluates past signals using real historical data and adjusts indicator weights for improved performance - **NO SIMULATED DATA**
- **Low Money Mode**: Optimized settings for smaller trading accounts (< $500)
- **Parameter Auto-Tuning**: Continuous parameter adjustment based on real trade outcomes (no backtesting/simulation)
- **ML Learning Without Broker**: Checks if previous signals hit TP/SL using historical price data, enabling ML to learn from real market movements

## Requirements

- Python 3.8 or higher
- NewsAPI account (free tier available)
- **Groq API key** (REQUIRED for LLM-enhanced news analysis - free tier available)
- Internet connection for data fetching

**Note**: No broker API needed. This tool generates signals only.

## Dependencies

Install the required packages using pip:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install newsapi-python yfinance requests aiohttp scikit-learn numpy pandas joblib groq
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

**Required:**
- `NEWS_API_KEY`: Your NewsAPI key (required)
- `GROQ_API_KEY`: Your Groq API key (REQUIRED - get free tier at console.groq.com)

**Optional Configuration:**
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

### Standard Mode

Run the bot:

```bash
python main.py
```

The bot will:

1. Check previous signals against real historical data to see if they hit TP/SL
2. Check the current market session
3. Fetch recent forex, commodities, and indices news
4. Analyze sentiment and technical indicators
5. Generate trading signals with entry, stop loss, and take profit levels
6. Send notifications via Telegram (if configured)
7. Log signals to `trade_log.json`
8. Learn from real market data to improve future signals

### Training Mode

Run the bot in training mode to collect data and train the ML model:

```bash
python main.py --training
```

Training mode features:

- **Pure Technical Analysis**: Trades based only on technical indicators (sentiment neutralized to 0)
- **Psychology Collection**: Still fetches news and analyzes market psychology for failure classification
- **Smart Filtering**: Automatically trains BOTH ML systems:
  - **ML System 1 (Technical)**: Trains on analytical trades, excludes emotional failures
  - **ML System 2 (News Impact)**: Trains on ALL trades using psychology data to learn emotional patterns
- **Continuous Loop**: Runs continuously until manually stopped (Ctrl+C)
- **Periodic Checks**: Evaluates trade outcomes every 30 minutes (configurable via `TRAINING_CHECK_INTERVAL`)
- **Auto-Retraining**: Automatically retrains BOTH ML models after every 10 completed trades (configurable via `TRAINING_RETRAIN_AFTER`)
- **No Notifications**: Telegram notifications are disabled

**Why collect psychology data if not using it for trades?**

In training mode, psychology data is collected but NOT used to adjust trade decisions. This ensures:
1. Trades are based purely on technical analysis
2. Trade failures can be classified as "analytical" (technical indicators were wrong) vs "emotional" (market moved due to news/fear/greed)
3. Emotional failures are excluded from Technical ML training
4. Psychology data is used to train News Impact ML to learn how emotions affect markets

**ML Training in Training Mode:**

- **ML System 1 (Technical Predictor)**: Trains on technical trades, excludes emotional/mixed failures
- **ML System 2 (News Impact Predictor)**: Trains on ALL trades using psychology features to learn how news/emotions cause failures
- **Both systems kept separate**: In training mode they learn independently, in normal mode they work together

**To stop training mode**: Press `Ctrl+C`

### ~~Backtest Mode~~ (DEPRECATED - Removed)

**Backtesting has been removed** as it used simulated data. We now use only real trade outcomes for all learning and parameter tuning.

All parameter optimization happens automatically via `evaluate_trades()` which uses real historical price data to determine actual trade outcomes.

If you want to validate parameters:
1. Use Training Mode to collect real trade data
2. Let evaluate_trades() adjust parameters based on real performance
3. Review trade_log.json to see actual win/loss results

**Why removed:**
- Backtesting simulated trades (fake data)
- Real trade evaluation via check_trade_outcomes() and evaluate_trades() provides better, actual results
- No need for simulated validation when we can learn from real market movements

## Output

The bot outputs recommended trading signals in the console and via Telegram, including:

- Symbol and direction (LONG/SHORT)
- Entry price
- Stop loss and take profit levels
- Recommended leverage
- Risk-reward ratio
- **ML probability and confidence scores** (when ML is enabled and trained)

Signals are also logged to `trade_log.json` and automatically evaluated on next run to check if they hit TP/SL using **real historical price data** (not simulated). This means:
- The bot fetches actual market prices from the time the trade was created
- Checks if stop-loss or take-profit was actually hit based on real price movements
- No broker connection needed - uses publicly available historical data
- ML learns from what markets ACTUALLY did, not simulated/fake data

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