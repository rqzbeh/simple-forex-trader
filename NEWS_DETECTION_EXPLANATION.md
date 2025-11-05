# News-Driven vs Logic-Driven Failure Detection

## Overview

The trading system now intelligently distinguishes between two types of trade failures:

1. **Logic-Driven Failures** - Trades that fail because the technical analysis or indicator signals were incorrect
2. **News-Driven Failures** - Trades that fail due to unexpected news events or market shocks (external, irrational reactions)

## Problem Statement

Previously, the ML system and indicator weight adjustments treated all failures equally. This caused issues:

- **False Learning**: The ML model would learn to avoid technically sound setups just because they were occasionally hit by unpredictable news
- **Unfair Penalization**: Technical indicators were penalized even when their signals were correct, but external events disrupted the trade
- **Poor Parameter Tuning**: Stop losses and indicator weights were adjusted based on noise from news events rather than actual strategy performance

## Solution

The system now analyzes market conditions at trade entry and exit to determine the failure type:

### News-Driven Failure Indicators

A failure is classified as **news-driven** if any of these conditions are met:

1. **Sudden Volatility Spike** (>2x normal)
   - Entry volatility: 0.8%
   - Exit volatility: 3.5%
   - Result: 4.4x increase → News-driven

2. **Extreme Volatility** (>3% hourly)
   - Any hourly volatility exceeding 3% suggests major news event

3. **Quick Stop-Out with High Volatility** (<2 hours + >1.5% volatility)
   - Trade duration: 1.5 hours
   - Exit volatility: 2.0%
   - Result: Sudden market event → News-driven

4. **Extreme Price Movement** (>5x expected ATR)
   - Expected move: 0.5% (2 ATR)
   - Actual move: 3.0%
   - Result: 6x expected → News-driven (likely shock)

### Logic-Driven Failure Indicators

A failure is classified as **logic-driven** if:

- Normal volatility changes (<2x)
- Gradual price movement
- Normal market conditions at entry and exit
- No sudden market shocks

## Implementation Details

### Trade Logging Enhancement

Trades now capture additional data at entry:

```python
trade = {
    # ... existing fields ...
    'entry_volatility': 0.008,      # Volatility at trade entry
    'entry_atr_pct': 0.005,         # ATR percentage at entry
    'entry_sentiment': 0.3,         # News sentiment at entry
    'entry_news_count': 5           # Number of news articles
}
```

### Failure Detection Function

```python
def detect_news_driven_failure(trade, current_market_data):
    """
    Detect if a trade failure was likely caused by news events
    
    Returns: (is_news_driven, reason)
    """
    # Analyzes volatility spikes, extreme moves, timing, etc.
    # Returns True for news-driven, False for logic-driven
```

### ML Training Adjustment

The ML predictor now excludes news-driven failures:

```python
def prepare_training_data(self, trade_log_file):
    # Skip news-driven losses from training
    if status == 'loss_news_driven':
        news_driven_count += 1
        continue  # Don't train on this
    
    # Only train on wins and logic-driven losses
    label = 1 if status == 'win' else 0
```

### Indicator Weight Adjustment

Indicator performance tracking separates failure types:

```python
indicator_wins = {...}
indicator_losses = {...}          # Only logic-driven
indicator_news_losses = {...}     # Tracked separately, not penalized

# Only logic-driven failures affect weights
if win:
    indicator_wins[ind] += 1
elif is_news_driven:
    indicator_news_losses[ind] += 1  # Track but don't penalize
else:
    indicator_losses[ind] += 1       # Count against indicator
```

## Benefits

### 1. Accurate Learning
The ML model learns from genuine strategy failures, not unpredictable external events:

```
Before: 100 trades → 60 wins, 40 losses (all counted equally)
        ML learns to avoid 40% of setups

After:  100 trades → 60 wins, 25 logic losses, 15 news losses
        ML learns to avoid 25% of setups (actual bad ones)
        ML doesn't penalize the 15% hit by news
```

### 2. Fair Indicator Evaluation
Technical indicators are only judged on their actual performance:

```
RSI Bullish Signal Performance:
- 30 wins
- 10 logic-driven losses
- 5 news-driven losses

Before: 30/45 = 66.7% win rate → weight reduced
After:  30/40 = 75.0% win rate → weight increased
```

### 3. Better Performance Metrics

The evaluate_trades() function now provides detailed breakdowns:

```
=== Trade Evaluation Results ===
Evaluated 100 trades:
  Wins: 60 (60.0%)
  Logic-driven losses: 25 (25.0%)
  News-driven losses: 15 (15.0%)
Overall win rate: 60.0%

=== Indicator Performance (Logic-driven only) ===
RSI: 75.0% win rate (30W/10L/5N out of 45 total), new weight: 1.43
MACD: 72.0% win rate (28W/12L/8N out of 48 total), new weight: 1.38
...
```

### 4. Smarter Risk Management
The system makes better decisions by understanding failure context:

- **News-driven failure**: "Market was hit by unexpected event, setup was fine"
  → Keep using similar setups
  → Don't tighten stops unnecessarily
  → Don't reduce indicator weights

- **Logic-driven failure**: "Setup was wrong, indicators conflicted"
  → Adjust indicator weights
  → Review entry criteria
  → Potentially tighten stops

## Usage

### Viewing Failure Analysis

After trades are evaluated, check the logs:

```json
{
  "status": "loss_news_driven",
  "failure_reason": "Volatility spike detected: 4.38x increase (likely news event)",
  "entry_volatility": 0.008,
  "exit_volatility": 0.035
}
```

vs

```json
{
  "status": "loss",
  "failure_reason": "Normal market conditions - likely technical/logic failure",
  "entry_volatility": 0.008,
  "exit_volatility": 0.010
}
```

### Testing the Feature

Run the test script to see the detection in action:

```bash
python3 test_detection_simple.py
```

This demonstrates 4 scenarios:
- 2 logic-driven failures (correctly classified)
- 2 news-driven failures (correctly classified)

## Real-World Example

### Scenario: ECB Interest Rate Announcement

**Trade Setup (Before Announcement)**
- Symbol: EURUSD
- Direction: LONG
- Entry: 1.0500
- Stop: 1.0480
- All technical indicators: BULLISH
- Entry volatility: 0.8%
- Entry ATR: 0.5%

**Market Event**
- ECB announces unexpected rate hike
- EUR spikes 200 pips in 10 minutes
- Then crashes 300 pips as traders panic sell

**Exit Conditions**
- Price: 1.0470 (stopped out)
- Exit volatility: 4.2% (5.25x spike!)
- Exit ATR: 1.8% (3.6x spike!)

**Detection Result**
```
Type: NEWS-DRIVEN FAILURE
Reason: Volatility spike detected: 5.25x increase (likely news event)

Impact:
- Technical indicators remain trusted
- ML model excludes this from training
- Similar setups will still be taken in future
```

### Without This Feature

The system would have:
- Reduced weights on all bullish indicators
- Learned to avoid similar technically sound setups
- Incorrectly concluded "strong bullish signals are unreliable"

### With This Feature

The system correctly:
- Recognizes this was an external event
- Preserves trust in the technical setup
- Doesn't penalize indicators for unpredictable news
- Continues to take similar high-quality setups

## Configuration

No configuration needed - the feature is automatically enabled and uses these thresholds:

```python
VOLATILITY_SPIKE_THRESHOLD = 2.0    # 2x increase
EXTREME_VOLATILITY_THRESHOLD = 0.03 # 3% hourly
QUICK_STOPOUT_HOURS = 2             # Within 2 hours
PRICE_MOVE_MULTIPLIER = 5           # 5x expected ATR
```

These thresholds can be adjusted in `main.py` in the `detect_news_driven_failure()` function if needed.

## Technical Details

### Data Flow

1. **Trade Entry**: Capture volatility, ATR, sentiment, news count
2. **Trade Monitoring**: Continuously check open positions
3. **Trade Exit**: Compare exit conditions to entry conditions
4. **Failure Analysis**: Determine if news-driven or logic-driven
5. **ML Training**: Exclude news-driven failures
6. **Weight Adjustment**: Only use logic-driven failures

### Status Values

The trade log now uses these status values:

- `open` - Trade is still active
- `win` - Trade hit target (always included in training)
- `loss` - Logic-driven failure (included in training)
- `loss_news_driven` - News-driven failure (excluded from training)

## Conclusion

This feature significantly improves the trading system's ability to learn and adapt by:

1. Distinguishing between controllable (logic) and uncontrollable (news) failures
2. Preventing the ML model from learning false patterns
3. Fairly evaluating technical indicator performance
4. Providing clearer insights into true strategy effectiveness

The system now answers the key question: **"Did the trade fail because the analysis was wrong, or because of unpredictable external events?"**
