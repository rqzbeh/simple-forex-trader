# Training Mode Documentation

## Overview

Training Mode is a specialized mode designed to collect high-quality data for training the machine learning models. It focuses exclusively on technical analysis while intelligently filtering out noise from emotional market movements.

**Key Distinction from Backtesting:**
- **Backtesting** = Fast simulation on historical data (90 days in minutes) to validate parameters
- **Training Mode** = Real trades over time, uses ACTUAL market price data to determine outcomes

**Training Mode Process:**
1. Generate trade signal based on technical indicators
2. Log trade to file with entry price, stop loss, take profit
3. Wait (sleep) for 30 minutes
4. Check historical price data to see if trade hit stop loss or take profit
5. Record actual outcome (win/loss) based on what market REALLY did
6. Train ML models on real results

**Yes, we use REAL data:** Training mode fetches actual historical prices from data providers (yfinance, etc.) to determine if trades would have hit TP/SL. This is NOT simulated - it's what actually happened in the markets.

## Quick Start

```bash
python main.py --training
```

Press `Ctrl+C` to stop the training loop.

## Key Features

### 1. Pure Technical Analysis
- **Sentiment Neutralized**: All trades use `sentiment = 0` (neutral)
- **No AI Adjustments**: Psychology-based trade adjustments are disabled
- **Focus**: Only technical indicators drive trade decisions

### 2. Smart Failure Classification
- **Psychology Analysis**: Still runs in background for failure classification
- **Purpose**: Determines WHY a trade failed:
  - **Analytical Failure**: Technical indicators were wrong
  - **Emotional Failure**: Market moved due to news, fear, greed, panic, or euphoria
  - **Mixed Failure**: Both factors contributed

### 3. Intelligent ML Training

#### ML System 1: Technical Predictor (`ml_predictor.py`)
- **Trains on**: Technical trades with analytical failures
- **Excludes**: Emotional and mixed failures
- **Goal**: Learn better technical indicator usage
- **Retrains**: After every 10 new completed trades

#### ML System 2: News Impact Predictor (`news_impact_predictor.py`)
- **Trains on**: ALL trades (both training and normal mode)
- **Uses**: Psychology features (irrationality, fear/greed) to learn emotional patterns
- **Goal**: Learn how news/psychology impacts trade outcomes
- **Retrains**: After every 10 new completed trades

### 4. Continuous Operation
- **Loop**: Runs indefinitely until manually stopped
- **Check Interval**: Every 1800 seconds (30 minutes)
- **Auto-Retrain**: After every 10 new completed trades

### 5. Reduced Overhead
- **Telegram**: Disabled
- **News Fetching**: Minimal (only for psychology classification)
- **LLM Calls**: Reduced (only for psychology, not for sentiment)

## Configuration

### Environment Variables
No special environment variables needed beyond the standard ones.

### Code Configuration
Edit `main.py` to customize:

```python
TRAINING_MODE = False  # Set to True to enable (or use --training flag)
TRAINING_CHECK_INTERVAL = 1800  # Seconds between checks (30 minutes)
TRAINING_RETRAIN_AFTER = 1  # Retrain after this many new completed trades
```

## How It Works

### Trade Generation
1. Fetch market data and minimal news
2. Analyze psychology (for classification only, not trade decisions)
3. Set sentiment to 0 (neutral)
4. Generate trades based purely on technical indicators
5. Log trades with `training_mode: True` flag

### Trade Evaluation
1. Wait 30 minutes (configurable)
2. Check if any trades hit stop-loss or take-profit
3. Classify failures:
   - If emotional/mixed → mark `excluded_from_training: True`
   - If analytical → keep for ML training
4. Update trade log with results

### ML Training
1. After every 10 new completed trades
2. ML System 1 trains on:
   - All training mode trades
   - Excludes emotional/mixed failures
3. ML System 2 trains on:
   - ALL trades (both training and normal mode)
   - Uses psychology features to learn emotional patterns

## Trade Log Structure

Trades logged in training mode include:

```json
{
  "timestamp": "2024-01-01T10:00:00",
  "symbol": "EURUSD",
  "direction": "long",
  "entry_price": 1.1000,
  "stop_price": 1.0990,
  "target_price": 1.1020,
  "status": "open",
  "training_mode": true,
  "entry_sentiment": 0.0,
  "psychology": {
    "dominant_emotion": "fear",
    "irrationality_score": 0.65,
    "fear_greed_index": -0.4
  },
  "rsi_signal": 1,
  "macd_signal": 1,
  ...
}
```

After evaluation:

```json
{
  ...
  "status": "loss",
  "failure_type": "emotional",
  "excluded_from_training": true,
  "failure_classification": {
    "failure_type": "emotional",
    "confidence": 0.85,
    "reason": "High irrationality score and panic emotion detected"
  }
}
```

## When to Use Training Mode

### Use Training Mode When:
- ✅ Building initial ML models (need 50+ trades minimum)
- ✅ Improving technical indicator performance
- ✅ Testing new technical indicators
- ✅ Accumulating clean training data
- ✅ Running overnight/unattended for data collection

### Use Normal Mode When:
- ✅ Actually trading with news/sentiment
- ✅ Testing news impact predictions
- ✅ Evaluating psychology-based adjustments
- ✅ Live trading with Telegram notifications

## Output Example

```
======================================================================
TRAINING MODE ENABLED
======================================================================
Configuration:
  - Focus: Technical analysis only
  - News/Sentiment: Minimal (sentiment neutralized to 0)
  - Psychology Data: COLLECTED (for failure classification)
  - Psychology Adjustments: DISABLED (pure technical trades)
  - Telegram: Disabled
  - Failure Classification: Active (prevents bad training)
  - Check Interval: 1800 seconds
  - Auto-retrain: After every 1 new completed trade(s)

Why collect psychology if not using it?
  - Determines if trade failed due to poor analytics OR news/emotion
  - Emotional failures are EXCLUDED from ML training
  - Ensures ML learns only from analytical mistakes

ML Training Exclusions in Training Mode:
  - ML System 1 (Technical): Excludes emotional/mixed failures
  - ML System 2 (News Impact): Excludes ALL training mode trades
  - Reason: Psychology not used for decisions, so can't train on it
======================================================================

Checking previous trades against real historical data...
...
======================================================================
TRAINING ITERATION 1
Time: 2024-01-01 10:00:00
======================================================================
...
NEW COMPLETED TRADES: 1 (total: 51)
----------------------------------------------------------------------
RETRAINING ML MODEL (1 new completed trades)
----------------------------------------------------------------------
✓ ML model retrained successfully
  Current dataset: 51 trades, 54.90% win rate
----------------------------------------------------------------------
Iteration 1 complete. Waiting 1800 seconds...
Next check at: 2024-01-01 10:30:00
----------------------------------------------------------------------
```

## Best Practices

1. **Start Fresh**: Use training mode with a new `trade_log.json` or separate log file
2. **Run Long**: Let it run for hours/days to accumulate sufficient data
3. **Monitor**: Check win rates and ML performance periodically
4. **Minimum Data**: Need at least 50 completed trades before ML training works
5. **Mix Modes**: Use training mode for data collection, normal mode for live trading

## Troubleshooting

### "Not enough trades for ML training"
- Need 50+ completed trades
- Let training mode run longer
- Trades complete when they hit TP or SL (takes time)

### "All trades excluded from training"
- All failures were emotional (high irrationality)
- Market very news-driven during collection period
- Consider collecting during calmer market conditions

### ML not improving
- May need more diverse training data
- Try different market sessions
- Check if too many emotional exclusions

## Technical Details

### Failure Classification Logic

```python
if irrationality_score > 0.6:
    if indicator_agreement < 0.3 or volatility_spike > 2.0:
        failure_type = "emotional"
    elif sentiment_strength > 0.7 or news_volume > 10:
        failure_type = "emotional"
    else:
        failure_type = "mixed"
else:
    failure_type = "analytical"
```

### ML Exclusion Logic

```python
# ML System 1 (Technical Predictor)
if trade.get('excluded_from_training', False):
    skip_trade()  # Excludes emotional/mixed failures

# ML System 2 (News Impact Predictor)  
# Trains on ALL trades (training and normal mode)
# Uses psychology features: irrationality_score, fear_greed_index
```

## See Also

- `README.md` - Main documentation
- `ml_predictor.py` - ML System 1 implementation
- `news_impact_predictor.py` - ML System 2 implementation
- `ai_performance_tracker.py` - AI psychology performance tracking
