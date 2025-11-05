# AI-Powered News Impact Prediction

## Overview

This enhancement adds an **AI-powered news impact prediction system** that analyzes current news to predict how it will affect trading opportunities **right now**. This goes beyond the existing news-driven failure detection by **proactively** analyzing news before trades are placed.

## The Enhancement

### Two-Layer Approach

The system now has **two complementary AI/ML systems** for news analysis:

1. **News-Driven Failure Detection** (Post-Trade Analysis)
   - Analyzes why a trade failed after it's closed
   - Distinguishes news-driven from logic-driven failures
   - Prevents ML from learning false patterns

2. **AI News Impact Prediction** (Pre-Trade Analysis) ⭐ NEW!
   - Analyzes current news **before** placing trades
   - Predicts how news will affect market volatility
   - Can halt trading during high-impact news events

## How It Works

### 1. Text Analysis with Machine Learning

The system uses **TF-IDF (Term Frequency-Inverse Document Frequency)** vectorization combined with **ensemble ML models** to analyze news content:

```python
# Extracts features from news articles
- TF-IDF features: 100 dimensions capturing text patterns
- Category features: Counts of high-impact keywords
  - Central bank actions (Fed, ECB, rate decisions)
  - Economic data (GDP, employment, inflation)
  - Crisis events (collapse, default, bankruptcy)
  - Geopolitical events (war, sanctions, elections)
  - Market events (stimulus, bailout, QE)
- Aggregate features: News count, authoritative source count
```

### 2. Impact Classification

The predictor categorizes news into three levels:

- **HIGH Impact**: Central bank decisions, crises, major economic events
  - Impact score: ±0.7
  - Confidence: 80%
  - Action: **Avoid trading**

- **MEDIUM Impact**: Significant economic data, policy changes
  - Impact score: ±0.4
  - Confidence: 60%
  - Action: Trade with caution

- **LOW Impact**: Routine updates, minor news
  - Impact score: ±0.1
  - Confidence: 50%
  - Action: **Trade normally**

### 3. ML-Based Prediction

Once trained on historical data, the ML model learns:

- Which types of news lead to news-driven failures
- Patterns in news that predict high volatility
- Keywords and phrases associated with market disruption

The model outputs:
- **Probability**: Likelihood of news-driven failure (0-100%)
- **Confidence**: How confident the model is in its prediction

### 4. Trading Decision

The system combines rule-based and ML predictions:

```python
if impact_level == 'high' and abs(impact_score) > 0.5:
    → AVOID TRADING (high volatility expected)

if ml_prediction > 0.8:
    → AVOID TRADING (80%+ chance of news-driven failure)

else:
    → TRADE NORMALLY
```

## Integration with Main System

### Automatic Pre-Trade Analysis

The system runs automatically at the start of each trading session:

```
1. Fetch news articles (NewsAPI + RSS feeds)
   ↓
2. AI News Impact Analysis
   - Analyzes all current news
   - Predicts impact on market
   - Provides recommendation
   ↓
3. Decision Point
   - HIGH impact → Stop trading, return early
   - LOW/MEDIUM impact → Continue to trade analysis
   ↓
4. Normal trading flow...
```

### Console Output

When running, you'll see:

```
======================================================================
AI NEWS IMPACT ANALYSIS
======================================================================
Impact Level: HIGH
Impact Score: -0.70 (-1=bearish, +1=bullish)
Confidence: 80.00%
ML Prediction: 75.00% (prob of news-driven failure)
Recommendation: AVOID TRADING
Reason: High news impact detected (score: -0.70) - high volatility expected
======================================================================

⚠️  AI News Analysis suggests AVOIDING trading due to high news impact.
The current news environment indicates high volatility risk.
```

## Training the ML Model

The system trains automatically on historical data:

### Data Requirements

- Minimum: 30 completed trades
- Optimal: 100+ trades with varied news conditions
- Uses existing `trade_log.json` with news context

### Training Process

```python
# Runs every 24 hours (same as main ML model)
1. Load historical trades with outcomes
2. Extract features from news at trade entry
3. Label: 1 if news-driven failure, 0 otherwise
4. Train ensemble model (Random Forest + Gradient Boosting)
5. Select best model via cross-validation
6. Save model for production use
```

### What It Learns

The model identifies patterns like:

- "Fed rate decision" + "surprise" → High probability of news-driven failure
- Multiple central bank news → High volatility expected
- Crisis keywords → Avoid trading
- Routine earnings reports → Normal conditions, safe to trade

## Real-World Example

### Scenario: ECB Rate Decision Day

**Morning News (9:00 AM):**
```
- "ECB to announce rate decision at 2pm"
- "Market awaits central bank policy update"
- "Analysts expect 25bp rate hike"
```

**AI Analysis:**
```
Impact Level: HIGH
Impact Score: 0.70 (bullish expectation)
Confidence: 80%
ML Prediction: 65% (moderate risk)
Recommendation: AVOID TRADING
Reason: Central bank rate decision - high volatility expected
```

**Result:**
- Bot does NOT place any trades
- Waits for news event to pass
- Avoids being caught in volatility spike

**After News (3:00 PM):**
```
- Market has settled after ECB announcement
- Volatility returning to normal
```

**AI Analysis:**
```
Impact Level: LOW
Impact Score: 0.10
Confidence: 50%
ML Prediction: 30%
Recommendation: TRADE NORMALLY
Reason: News impact: low - normal conditions
```

**Result:**
- Bot resumes normal trading
- Places trades based on technical analysis
- Confident that major news impact has passed

## Benefits

### 1. Proactive Protection

**Before:** React to news-driven failures after they happen
**After:** Avoid high-impact news periods proactively

### 2. Reduces Losses

By avoiding trading during:
- Central bank announcements
- Major economic data releases
- Crisis events
- Geopolitical shocks

### 3. Better Timing

System learns optimal times to trade:
- After news has been digested
- When volatility normalizes
- During routine market conditions

### 4. Complements Existing System

Works together with news-driven failure detection:

```
Pre-Trade: AI predicts news impact → Avoid high-impact periods
During Trade: Normal market analysis → Place trades
Post-Trade: Detect news-driven failures → Learn from outcomes
```

## Configuration

No configuration needed! The feature works automatically:

```python
# Automatically enabled if available
NEWS_IMPACT_ML_AVAILABLE = True  # Set automatically

# Uses same retraining schedule as main ML
ML_RETRAIN_INTERVAL = 24  # Hours
```

### Optional: Adjust Thresholds

If you want to customize sensitivity, edit `news_impact_predictor.py`:

```python
# In predict_news_impact():
if impact_level == 'high' and abs(impact_score) > 0.5:  # Change 0.5
    should_trade = False

if ml_prediction > 0.8:  # Change 0.8 threshold
    should_trade = False
```

## Testing

Run the test script to see it in action:

```bash
python3 test_news_impact.py
```

You'll see analysis of 4 scenarios:
1. Central bank rate decision (HIGH impact, avoid)
2. Economic data release (HIGH impact, avoid)
3. Routine market updates (LOW impact, trade)
4. Market crisis (HIGH impact, avoid)

## Files Added

1. **news_impact_predictor.py** - Core ML predictor
   - 350+ lines of AI logic
   - TF-IDF text analysis
   - Ensemble ML models
   - Training and prediction functions

2. **test_news_impact.py** - Test suite
   - Demonstrates 4 scenarios
   - Shows expected outputs
   - Explains how it works

## Model Files (Auto-Generated)

These are created and updated automatically:

- `news_impact_model.pkl` - Trained ML model
- `news_impact_vectorizer.pkl` - TF-IDF vectorizer
- `news_impact_scaler.pkl` - Feature scaler
- `news_impact_last_train.json` - Training timestamp

(Already added to .gitignore)

## Free AI Approach

This implementation uses **scikit-learn** (completely free and open-source):

- No API keys needed
- No external AI services
- Runs locally
- No cost per prediction
- Full control and privacy

The ML models are:
- **Random Forest**: Tree-based ensemble
- **Gradient Boosting**: Sequential ensemble
- **TF-IDF**: Text feature extraction

All powered by scikit-learn's battle-tested algorithms.

## Future Enhancements

Potential improvements:

1. **Symbol-Specific Analysis**: Analyze news impact per currency pair
2. **Sentiment Scoring**: Add sentiment polarity to impact score
3. **Real-Time APIs**: Integrate with real-time news APIs
4. **Economic Calendar**: Incorporate scheduled event data
5. **Deep Learning**: Use transformers (BERT) for better text understanding

## Summary

The system now has **two-layer AI protection**:

**Layer 1: Pre-Trade (NEW!)**
- Analyzes current news
- Predicts impact
- Can halt trading

**Layer 2: Post-Trade (Existing)**
- Analyzes failures
- Distinguishes causes
- Improves learning

Together, they provide:
- ✅ Proactive avoidance of high-impact news
- ✅ Reactive learning from news-driven failures
- ✅ Better ML training on genuine strategy failures
- ✅ Improved overall performance and risk management

**The bot now understands news impact both BEFORE and AFTER trades!**
