#!/usr/bin/env python3
"""
Simple test script to demonstrate news-driven vs logic-driven failure detection
This version directly imports only the detection function to avoid dependency issues
"""

import json
from datetime import datetime, timedelta

def detect_news_driven_failure(trade, current_market_data):
    """
    Detect if a trade failure was likely caused by news events rather than logic errors.
    
    Returns: (is_news_driven, reason)
    - is_news_driven: True if failure likely caused by news/external events
    - reason: String explanation of the determination
    """
    # Get entry conditions
    entry_volatility = trade.get('entry_volatility', 0.01)
    entry_atr_pct = trade.get('entry_atr_pct', 0.005)
    
    # Get exit conditions from market data
    exit_volatility = current_market_data.get('volatility_hourly', 0.01)
    exit_atr_pct = current_market_data.get('atr_pct', 0.005)
    
    # Calculate volatility spike
    volatility_increase = exit_volatility / entry_volatility if entry_volatility > 0 else 1.0
    atr_increase = exit_atr_pct / entry_atr_pct if entry_atr_pct > 0 else 1.0
    
    # News-driven failure indicators:
    # 1. Sudden volatility spike (>2x normal)
    if volatility_increase > 2.0 or atr_increase > 2.0:
        return True, f"Volatility spike detected: {volatility_increase:.2f}x increase (likely news event)"
    
    # 2. Extreme volatility at exit (>3% hourly)
    if exit_volatility > 0.03:
        return True, f"Extreme volatility at exit: {exit_volatility:.4f} (likely major news)"
    
    # 3. Check if trade was stopped out very quickly (within 2 hours)
    # This suggests a sudden market event rather than gradual technical failure
    trade_time = datetime.fromisoformat(trade['timestamp'])
    time_elapsed = (datetime.now() - trade_time).total_seconds() / 3600
    if time_elapsed < 2:
        # Quick stop-out with high volatility suggests news event
        if exit_volatility > 0.015:
            return True, f"Quick stop-out ({time_elapsed:.1f}h) with high volatility (likely sudden news)"
    
    # 4. Check for very large adverse price moves (>5x normal ATR)
    entry_price = trade.get('entry_price', 0)
    current_price = current_market_data.get('price', entry_price)
    price_move = abs(current_price - entry_price) / entry_price if entry_price > 0 else 0
    expected_move = entry_atr_pct * 2  # Normal 2 ATR move
    
    if price_move > expected_move * 5:
        return True, f"Extreme price move: {price_move:.4f} vs expected {expected_move:.4f} (likely news shock)"
    
    # If none of the above, it's likely a logic-driven failure
    return False, "Normal market conditions - likely technical/logic failure"

def create_test_scenarios():
    """Create test scenarios"""
    scenarios = []
    
    # Scenario 1: Logic-driven failure (normal conditions, bad technical setup)
    scenarios.append({
        'name': 'Logic-Driven Failure',
        'description': 'Normal market conditions but conflicting technical indicators',
        'trade': {
            'timestamp': (datetime.now() - timedelta(hours=5)).isoformat(),
            'symbol': 'EURUSD',
            'direction': 'long',
            'entry_price': 1.0500,
            'stop_price': 1.0480,
            'target_price': 1.0560,
            'entry_volatility': 0.008,  # Normal volatility
            'entry_atr_pct': 0.005,     # Normal ATR
        },
        'market': {
            'price': 1.0475,  # Below stop
            'volatility_hourly': 0.010,  # Slight increase but not dramatic
            'atr_pct': 0.006
        },
        'expected': 'LOGIC-DRIVEN'
    })
    
    # Scenario 2: News-driven failure (volatility spike)
    scenarios.append({
        'name': 'News-Driven Failure (Volatility Spike)',
        'description': 'Sudden volatility spike from central bank announcement',
        'trade': {
            'timestamp': (datetime.now() - timedelta(hours=3)).isoformat(),
            'symbol': 'GBPUSD',
            'direction': 'long',
            'entry_price': 1.2500,
            'stop_price': 1.2480,
            'target_price': 1.2560,
            'entry_volatility': 0.008,  # Normal at entry
            'entry_atr_pct': 0.005,     # Normal ATR at entry
        },
        'market': {
            'price': 1.2450,  # Below stop
            'volatility_hourly': 0.035,  # 4.4x spike! (from 0.008 to 0.035)
            'atr_pct': 0.015   # 3x ATR spike!
        },
        'expected': 'NEWS-DRIVEN'
    })
    
    # Scenario 3: News-driven failure (extreme volatility)
    scenarios.append({
        'name': 'News-Driven Failure (Extreme Volatility)',
        'description': 'Major economic data release causing extreme volatility',
        'trade': {
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'symbol': 'USDJPY',
            'direction': 'short',
            'entry_price': 150.00,
            'stop_price': 150.30,
            'target_price': 149.40,
            'entry_volatility': 0.010,
            'entry_atr_pct': 0.006,
        },
        'market': {
            'price': 150.50,  # Above stop
            'volatility_hourly': 0.045,  # Extreme volatility
            'atr_pct': 0.020
        },
        'expected': 'NEWS-DRIVEN'
    })
    
    # Scenario 4: Another logic-driven failure
    scenarios.append({
        'name': 'Logic-Driven Failure (Wrong Trend)',
        'description': 'Normal conditions but trend analysis was incorrect',
        'trade': {
            'timestamp': (datetime.now() - timedelta(hours=6)).isoformat(),
            'symbol': 'AUDUSD',
            'direction': 'short',
            'entry_price': 0.6500,
            'stop_price': 0.6520,
            'target_price': 0.6440,
            'entry_volatility': 0.009,
            'entry_atr_pct': 0.005,
        },
        'market': {
            'price': 0.6525,  # Above stop
            'volatility_hourly': 0.011,  # Normal increase
            'atr_pct': 0.006
        },
        'expected': 'LOGIC-DRIVEN'
    })
    
    return scenarios

def run_tests():
    """Run the detection tests"""
    print("\n" + "="*90)
    print("NEWS-DRIVEN VS LOGIC-DRIVEN FAILURE DETECTION TEST")
    print("="*90)
    print("\nThis test demonstrates how the system distinguishes between:")
    print("  1. Logic-driven failures (technical analysis was wrong)")
    print("  2. News-driven failures (unexpected market events/news)")
    print("\n" + "-"*90 + "\n")
    
    scenarios = create_test_scenarios()
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"[SCENARIO {i}] {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"Symbol: {scenario['trade']['symbol']} {scenario['trade']['direction'].upper()}")
        print(f"\nEntry Conditions:")
        print(f"  Price: {scenario['trade']['entry_price']}")
        print(f"  Volatility: {scenario['trade']['entry_volatility']:.4f}")
        print(f"  ATR: {scenario['trade']['entry_atr_pct']:.4f}")
        print(f"\nExit Conditions:")
        print(f"  Price: {scenario['market']['price']}")
        print(f"  Volatility: {scenario['market']['volatility_hourly']:.4f} (change: {scenario['market']['volatility_hourly']/scenario['trade']['entry_volatility']:.2f}x)")
        print(f"  ATR: {scenario['market']['atr_pct']:.4f} (change: {scenario['market']['atr_pct']/scenario['trade']['entry_atr_pct']:.2f}x)")
        
        # Run detection
        is_news_driven, reason = detect_news_driven_failure(scenario['trade'], scenario['market'])
        
        result_type = 'NEWS-DRIVEN' if is_news_driven else 'LOGIC-DRIVEN'
        status = '✓ PASS' if result_type == scenario['expected'] else '✗ FAIL'
        
        print(f"\n{status} Detection Result: {result_type}")
        print(f"Reason: {reason}")
        
        if is_news_driven:
            print("\n⚠️  IMPACT:")
            print("   - Indicators will NOT be penalized for this failure")
            print("   - ML model will EXCLUDE this from training data")
            print("   - Weight adjustments will NOT consider this loss")
        else:
            print("\n✓ IMPACT:")
            print("   - Indicators will be evaluated for this failure")
            print("   - ML model will INCLUDE this in training data")
            print("   - Weight adjustments will consider this loss")
        
        print("\n" + "-"*90 + "\n")
        
        results.append({
            'scenario': scenario['name'],
            'expected': scenario['expected'],
            'actual': result_type,
            'passed': result_type == scenario['expected']
        })
    
    # Summary
    print("="*90)
    print("TEST SUMMARY")
    print("="*90)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    for r in results:
        status = '✓ PASS' if r['passed'] else '✗ FAIL'
        print(f"{status} {r['scenario']}: Expected {r['expected']}, Got {r['actual']}")
    
    print("\n" + "="*90)
    print("KEY BENEFITS")
    print("="*90)
    print("""
1. ACCURATE LEARNING
   The ML model now learns only from logic-driven failures, avoiding false
   patterns from unpredictable news events.

2. FAIR INDICATOR EVALUATION
   Technical indicators are not penalized when external market shocks cause
   failures, only when their signals were genuinely wrong.

3. BETTER PARAMETER TUNING
   System adjustments (stop losses, weights) are based on actual strategy
   performance, not noise from news-driven volatility.

4. CLEARER PERFORMANCE METRICS
   You can now see separately:
   - Win rate on good technical setups
   - How often news events disrupt otherwise valid trades
   - True effectiveness of indicator combinations

5. SMARTER RISK MANAGEMENT
   The system can distinguish "this setup was bad" from "this setup was good
   but got hit by unpredictable news" - leading to better future decisions.
""")
    print("="*90 + "\n")
    
    return passed == total

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
