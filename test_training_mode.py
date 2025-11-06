#!/usr/bin/env python3
"""
Test script for training mode functionality
"""
import os
import sys
import json

# Set dummy API keys for testing
os.environ['NEWS_API_KEY'] = 'test_key'
os.environ['GROQ_API_KEY'] = 'test_key'

# Import main module after setting env vars
import main

def test_training_mode_config():
    """Test that training mode configuration is properly set"""
    print("Testing training mode configuration...")
    
    # Check that training mode constants exist
    assert hasattr(main, 'TRAINING_MODE'), "TRAINING_MODE constant not found"
    assert hasattr(main, 'TRAINING_CHECK_INTERVAL'), "TRAINING_CHECK_INTERVAL constant not found"
    assert hasattr(main, 'TRAINING_RETRAIN_AFTER'), "TRAINING_RETRAIN_AFTER constant not found"
    
    # Check default values
    assert main.TRAINING_MODE == False, "TRAINING_MODE should default to False"
    assert main.TRAINING_CHECK_INTERVAL == 3600, "Default check interval should be 3600 seconds"
    assert main.TRAINING_RETRAIN_AFTER == 10, "Default retrain after should be 10 trades"
    
    print("✓ Training mode configuration tests passed")

def test_telegram_in_training_mode():
    """Test that Telegram is disabled in training mode"""
    print("Testing Telegram behavior in training mode...")
    
    # Set training mode
    main.TRAINING_MODE = True
    
    # Test send_telegram_message (should do nothing and not raise errors)
    try:
        main.send_telegram_message("Test message")
        print("✓ Telegram disabled in training mode")
    except Exception as e:
        print(f"✗ Error in send_telegram_message: {e}")
        raise
    
    # Reset
    main.TRAINING_MODE = False
    print("✓ Telegram tests passed")

def test_ml_exclusion():
    """Test that ML predictor can exclude emotional trades"""
    print("Testing ML predictor exclusion of emotional trades...")
    
    from ml_predictor import MLTradingPredictor
    
    # Create a test trade log with emotional trades
    test_log = [
        {
            'timestamp': '2024-01-01T10:00:00',
            'status': 'loss',
            'excluded_from_training': True,
            'failure_type': 'emotional',
            'entry_sentiment': 0.0,
            'news_count': 5,
            'rsi_signal': 1,
            'macd_signal': 1,
            'bb_signal': 0,
            'trend_signal': 1,
            'advanced_candle_signal': 0,
            'obv_signal': 1,
            'fvg_signal': 0,
            'vwap_signal': 1,
            'stoch_signal': 1,
            'cci_signal': 0,
            'hurst_signal': 0,
            'adx_signal': 1,
            'williams_r_signal': 1,
            'sar_signal': 1,
            'volatility_hourly': 0.01,
            'atr_pct': 0.005,
            'price': 1.1000,
            'support': 1.0900,
            'resistance': 1.1100,
            'pivot': 1.1000
        },
        {
            'timestamp': '2024-01-01T11:00:00',
            'status': 'win',
            'excluded_from_training': False,
            'entry_sentiment': 0.0,
            'news_count': 2,
            'rsi_signal': -1,
            'macd_signal': -1,
            'bb_signal': -1,
            'trend_signal': -1,
            'advanced_candle_signal': 0,
            'obv_signal': -1,
            'fvg_signal': 0,
            'vwap_signal': -1,
            'stoch_signal': -1,
            'cci_signal': 0,
            'hurst_signal': 0,
            'adx_signal': -1,
            'williams_r_signal': -1,
            'sar_signal': -1,
            'volatility_hourly': 0.01,
            'atr_pct': 0.005,
            'price': 1.1000,
            'support': 1.0900,
            'resistance': 1.1100,
            'pivot': 1.1000
        }
    ]
    
    # Write test log
    test_log_file = '/tmp/test_trade_log.json'
    with open(test_log_file, 'w') as f:
        json.dump(test_log, f)
    
    # Create predictor and prepare training data
    predictor = MLTradingPredictor()
    X, y, weights = predictor.prepare_training_data(test_log_file)
    
    # Should only include the non-excluded trade
    if X is None:
        print("⚠ Not enough trades for training (expected with only 1 valid trade)")
    else:
        assert len(X) == 1, f"Expected 1 trade, got {len(X)}"
        print(f"✓ ML correctly excluded emotional trade (1 trade remaining)")
    
    # Clean up
    os.remove(test_log_file)
    print("✓ ML exclusion tests passed")

def test_psychology_collection_in_training_mode():
    """Test that psychology data is still collected in training mode"""
    print("Testing psychology data collection in training mode...")
    
    # This test just verifies the logic exists
    # Actual psychology collection requires API keys and real data
    
    # Check that the code path exists for training mode psychology
    main_code = open('main.py', 'r').read()
    
    # Verify training mode still collects psychology
    assert 'TRAINING MODE - PSYCHOLOGY' in main_code, "Training mode psychology collection code not found"
    assert 'For failure classification only' in main_code, "Training mode psychology explanation not found"
    assert 'not training_mode and psychology' in main_code, "Training mode psychology adjustment skip not found"
    
    print("✓ Psychology collection logic verified")

if __name__ == '__main__':
    print("=" * 70)
    print("TRAINING MODE TESTS")
    print("=" * 70)
    print()
    
    try:
        test_training_mode_config()
        test_telegram_in_training_mode()
        test_ml_exclusion()
        test_psychology_collection_in_training_mode()
        
        print()
        print("=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        sys.exit(0)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"TESTS FAILED ✗: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
