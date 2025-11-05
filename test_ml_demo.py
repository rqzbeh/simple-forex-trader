#!/usr/bin/env python3
"""
Demo script showing how the ML predictor works in production
This creates synthetic training data to demonstrate the ML pipeline
"""

import json
import numpy as np
from ml_predictor import MLTradingPredictor

def create_synthetic_trade_log(filename='test_trade_log.json', num_trades=100):
    """Create synthetic trade data for demonstration"""
    trades = []
    
    for i in range(num_trades):
        # Simulate various trade scenarios
        # 60% winning trades, 40% losing trades for demo
        is_winner = np.random.rand() > 0.4
        
        # Winners tend to have better indicator alignment
        if is_winner:
            sentiment = np.random.uniform(0.1, 0.5)
            rsi = 1 if np.random.rand() > 0.3 else -1
            macd = 1 if np.random.rand() > 0.3 else -1
            trend = 1 if np.random.rand() > 0.4 else -1
        else:
            sentiment = np.random.uniform(-0.3, 0.2)
            rsi = -1 if np.random.rand() > 0.3 else 1
            macd = -1 if np.random.rand() > 0.3 else 1
            trend = -1 if np.random.rand() > 0.4 else 1
        
        trade = {
            'timestamp': f'2024-{(i//30)+1:02d}-{(i%30)+1:02d}T10:00:00',
            'symbol': ['EURUSD', 'GBPUSD', 'USDJPY'][i % 3],
            'direction': 'long' if sentiment > 0 else 'short',
            'status': 'win' if is_winner else 'loss',
            'avg_sentiment': float(sentiment),
            'news_count': int(np.random.randint(1, 10)),
            'price': float(1.0500 + np.random.uniform(-0.01, 0.01)),
            'volatility_hourly': float(np.random.uniform(0.005, 0.02)),
            'atr_pct': float(np.random.uniform(0.003, 0.01)),
            'support': 1.0450,
            'resistance': 1.0550,
            'pivot': 1.0500,
            'rsi_signal': int(rsi),
            'macd_signal': int(macd),
            'bb_signal': int(np.random.choice([-1, 0, 1])),
            'trend_signal': int(trend),
            'advanced_candle_signal': int(np.random.choice([-1, 0, 1])),
            'obv_signal': int(np.random.choice([-1, 1])),
            'fvg_signal': int(np.random.choice([-1, 0, 1])),
            'vwap_signal': int(np.random.choice([-1, 1])),
            'stoch_signal': int(np.random.choice([-1, 0, 1])),
            'cci_signal': int(np.random.choice([-1, 0, 1])),
            'hurst_signal': int(np.random.choice([-1, 0, 1])),
            'adx_signal': int(np.random.choice([-1, 0, 1])),
            'williams_r_signal': int(np.random.choice([-1, 0, 1])),
            'sar_signal': int(np.random.choice([-1, 1])),
        }
        trades.append(trade)
    
    with open(filename, 'w') as f:
        json.dump(trades, f, indent=2)
    
    print(f"✓ Created {num_trades} synthetic trades in {filename}")
    winning_trades = sum(1 for t in trades if t['status'] == 'win')
    print(f"  Win rate: {winning_trades/num_trades:.1%}")

def demonstrate_ml_workflow():
    """Demonstrate the complete ML workflow"""
    
    print("\n" + "="*70)
    print("ML PREDICTOR DEMONSTRATION")
    print("="*70)
    
    # Step 1: Create synthetic data
    print("\n[STEP 1] Creating synthetic training data...")
    create_synthetic_trade_log('test_trade_log.json', 100)
    
    # Step 2: Initialize predictor
    print("\n[STEP 2] Initializing ML predictor...")
    predictor = MLTradingPredictor(model_path='test_ml_model.pkl', scaler_path='test_ml_scaler.pkl')
    print("✓ ML predictor initialized")
    print(f"  Features: {len(predictor.feature_names)}")
    print(f"  Min training samples: {predictor.min_training_samples}")
    
    # Step 3: Train model
    print("\n[STEP 3] Training ML model on historical trades...")
    success = predictor.train('test_trade_log.json')
    if success:
        print("✓ Model trained successfully")
    else:
        print("✗ Training failed")
        return
    
    # Step 4: Test predictions
    print("\n[STEP 4] Testing predictions on new trade scenarios...")
    
    # Good trade scenario (strong bullish signals)
    good_trade = {
        'avg_sentiment': 0.35,
        'news_count': 5,
        'price': 1.0525,
        'volatility_hourly': 0.008,
        'atr_pct': 0.005,
        'support': 1.0450,
        'resistance': 1.0600,
        'pivot': 1.0525,
        'rsi_signal': 1,  # Bullish
        'macd_signal': 1,  # Bullish
        'bb_signal': 1,  # Bullish
        'trend_signal': 1,  # Bullish
        'advanced_candle_signal': 1,
        'obv_signal': 1,
        'fvg_signal': 1,
        'vwap_signal': 1,
        'stoch_signal': 1,
        'cci_signal': 1,
        'hurst_signal': 1,
        'adx_signal': 1,
        'williams_r_signal': 1,
        'sar_signal': 1,
    }
    
    should_trade, prob, conf = predictor.should_trade(good_trade, min_confidence=0.60, min_probability=0.55)
    print(f"\n  Scenario A - Strong Bullish Signals:")
    print(f"    Win Probability: {prob:.1%}")
    print(f"    Model Confidence: {conf:.1%}")
    print(f"    Decision: {'✓ TRADE' if should_trade else '✗ SKIP'}")
    
    # Poor trade scenario (conflicting signals)
    poor_trade = {
        'avg_sentiment': 0.05,
        'news_count': 2,
        'price': 1.0500,
        'volatility_hourly': 0.015,
        'atr_pct': 0.009,
        'support': 1.0450,
        'resistance': 1.0550,
        'pivot': 1.0500,
        'rsi_signal': -1,  # Bearish
        'macd_signal': 1,   # Bullish (conflict)
        'bb_signal': 0,
        'trend_signal': -1,  # Bearish
        'advanced_candle_signal': 0,
        'obv_signal': -1,
        'fvg_signal': 0,
        'vwap_signal': -1,
        'stoch_signal': 0,
        'cci_signal': -1,
        'hurst_signal': 0,
        'adx_signal': 0,
        'williams_r_signal': -1,
        'sar_signal': -1,
    }
    
    should_trade2, prob2, conf2 = predictor.should_trade(poor_trade, min_confidence=0.60, min_probability=0.55)
    print(f"\n  Scenario B - Conflicting Signals:")
    print(f"    Win Probability: {prob2:.1%}")
    print(f"    Model Confidence: {conf2:.1%}")
    print(f"    Decision: {'✓ TRADE' if should_trade2 else '✗ SKIP'}")
    
    # Neutral trade scenario
    neutral_trade = {
        'avg_sentiment': 0.0,
        'news_count': 3,
        'price': 1.0500,
        'volatility_hourly': 0.010,
        'atr_pct': 0.006,
        'support': 1.0450,
        'resistance': 1.0550,
        'pivot': 1.0500,
        'rsi_signal': 0,
        'macd_signal': 0,
        'bb_signal': 0,
        'trend_signal': 0,
        'advanced_candle_signal': 0,
        'obv_signal': 1,
        'fvg_signal': 0,
        'vwap_signal': 1,
        'stoch_signal': 0,
        'cci_signal': 0,
        'hurst_signal': 0,
        'adx_signal': 0,
        'williams_r_signal': 0,
        'sar_signal': 1,
    }
    
    should_trade3, prob3, conf3 = predictor.should_trade(neutral_trade, min_confidence=0.60, min_probability=0.55)
    print(f"\n  Scenario C - Neutral/Weak Signals:")
    print(f"    Win Probability: {prob3:.1%}")
    print(f"    Model Confidence: {conf3:.1%}")
    print(f"    Decision: {'✓ TRADE' if should_trade3 else '✗ SKIP'}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("\nThe ML predictor:")
    print("1. Trains on historical wins/losses (needs minimum 50 completed trades)")
    print("2. Extracts 21 features from each trade opportunity")
    print("3. Uses ensemble models (Random Forest + Gradient Boosting)")
    print("4. Selects best model via cross-validation")
    print("5. Predicts win probability and model confidence")
    print("6. Only accepts trades with probability ≥55% AND confidence ≥60%")
    print("\nThis filters out low-quality trades before execution, improving win rate.")
    print("\nIn production:")
    print("- Model auto-trains every 24 hours on new trade data")
    print("- Gracefully falls back if insufficient training data")
    print("- Saves/loads trained model for persistence")
    print("="*70 + "\n")

if __name__ == '__main__':
    demonstrate_ml_workflow()
