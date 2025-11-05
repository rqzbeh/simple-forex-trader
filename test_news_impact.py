#!/usr/bin/env python3
"""
Test script to demonstrate AI-powered news impact prediction
"""

import sys
sys.path.insert(0, '/home/runner/work/simple-forex-trader/simple-forex-trader')

from news_impact_predictor import get_news_impact_predictor

def test_news_impact_prediction():
    """Test the news impact predictor with various scenarios"""
    
    print("\n" + "="*80)
    print("AI-POWERED NEWS IMPACT PREDICTION TEST")
    print("="*80)
    
    predictor = get_news_impact_predictor()
    
    # Scenario 1: High impact news (Central bank rate decision)
    print("\n[SCENARIO 1] Central Bank Rate Decision")
    print("-" * 80)
    high_impact_news = [
        {
            'title': 'Fed announces emergency rate hike to combat inflation',
            'description': 'Federal Reserve raises interest rates by 75 basis points in surprise move',
            'source': 'Reuters'
        },
        {
            'title': 'ECB signals more aggressive monetary policy tightening',
            'description': 'European Central Bank hints at faster rate increases',
            'source': 'Bloomberg'
        }
    ]
    
    result = predictor.predict_news_impact(high_impact_news)
    print(f"Impact Level: {result['impact_level'].upper()}")
    print(f"Impact Score: {result['impact_score']:.2f} (-1=bearish, +1=bullish)")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"ML Prediction: {result['ml_prediction']:.2%}")
    print(f"Should Trade: {'YES ✓' if result['should_trade'] else 'NO ✗'}")
    print(f"Reason: {result['reason']}")
    
    # Scenario 2: Medium impact news (Economic data)
    print("\n[SCENARIO 2] Economic Data Release")
    print("-" * 80)
    medium_impact_news = [
        {
            'title': 'US GDP growth beats expectations',
            'description': 'Economy expands 2.5% in Q3, above forecast of 2.1%',
            'source': 'CNBC'
        },
        {
            'title': 'Employment data shows steady job gains',
            'description': 'Nonfarm payrolls increase by 250,000',
            'source': 'MarketWatch'
        }
    ]
    
    result = predictor.predict_news_impact(medium_impact_news)
    print(f"Impact Level: {result['impact_level'].upper()}")
    print(f"Impact Score: {result['impact_score']:.2f}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"ML Prediction: {result['ml_prediction']:.2%}")
    print(f"Should Trade: {'YES ✓' if result['should_trade'] else 'NO ✗'}")
    print(f"Reason: {result['reason']}")
    
    # Scenario 3: Low impact news (Routine updates)
    print("\n[SCENARIO 3] Routine Market Updates")
    print("-" * 80)
    low_impact_news = [
        {
            'title': 'Stock market closes slightly higher',
            'description': 'Major indices end trading session with modest gains',
            'source': 'Financial Times'
        },
        {
            'title': 'Oil prices stable as traders await inventory data',
            'description': 'Crude futures trade in narrow range',
            'source': 'WSJ'
        }
    ]
    
    result = predictor.predict_news_impact(low_impact_news)
    print(f"Impact Level: {result['impact_level'].upper()}")
    print(f"Impact Score: {result['impact_score']:.2f}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"ML Prediction: {result['ml_prediction']:.2%}")
    print(f"Should Trade: {'YES ✓' if result['should_trade'] else 'NO ✗'}")
    print(f"Reason: {result['reason']}")
    
    # Scenario 4: Crisis news (Negative impact)
    print("\n[SCENARIO 4] Market Crisis")
    print("-" * 80)
    crisis_news = [
        {
            'title': 'Banking sector faces liquidity crisis',
            'description': 'Major bank collapses, triggering market panic',
            'source': 'Bloomberg'
        },
        {
            'title': 'Emergency measures announced to stabilize markets',
            'description': 'Government intervenes as financial crisis deepens',
            'source': 'Reuters'
        }
    ]
    
    result = predictor.predict_news_impact(crisis_news)
    print(f"Impact Level: {result['impact_level'].upper()}")
    print(f"Impact Score: {result['impact_score']:.2f} (negative = bearish)")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"ML Prediction: {result['ml_prediction']:.2%}")
    print(f"Should Trade: {'YES ✓' if result['should_trade'] else 'NO ✗'}")
    print(f"Reason: {result['reason']}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("""
The AI News Impact Predictor:

1. ANALYZES NEWS CONTENT
   - Uses TF-IDF text analysis
   - Identifies high-impact keywords (central banks, economic data, crises)
   - Categorizes news by impact level

2. PREDICTS MARKET IMPACT
   - Estimates impact score (-1 to +1)
   - Calculates confidence level
   - Predicts probability of news-driven failures

3. PROVIDES TRADING GUIDANCE
   - Recommends when to trade or avoid
   - Explains reasoning
   - Combines rule-based and ML approaches

4. LEARNS FROM HISTORY
   - Trains on past trades with news context
   - Identifies patterns in news-driven failures
   - Improves predictions over time

INTEGRATION WITH MAIN SYSTEM:
- Runs automatically before each trading session
- Can halt trading if high-impact news detected
- Helps avoid trades during volatile news periods
- Complements the news-driven failure detection
""")
    print("="*80 + "\n")

if __name__ == '__main__':
    test_news_impact_prediction()
