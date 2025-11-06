"""
Market Psychology Analyzer using Groq LLM
Analyzes market sentiment, fear, greed, and irrational behavior patterns
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq library not available")

# Import rate limiter
try:
    from groq_rate_limiter import get_rate_limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    logger.warning("Rate limiter not available")


class MarketPsychologyAnalyzer:
    """
    Analyzes market psychology using LLM to detect fear, greed, panic, and irrational behavior
    Helps identify when markets are driven by emotion rather than fundamentals
    """
    
    def __init__(self, model: str = None):
        """
        Initialize market psychology analyzer
        
        Args:
            model: Groq model to use (default: llama-3.3-70b-versatile)
        """
        if not GROQ_AVAILABLE:
            raise ImportError("Groq library is required for market psychology analysis")
        
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable must be set")
        
        self.client = Groq(api_key=api_key)
        self.model = model or 'llama-3.3-70b-versatile'
        logger.info(f"Initialized MarketPsychologyAnalyzer with model: {self.model}")
    
    def analyze_market_psychology(self, news_articles: List[Dict], 
                                  symbol: str,
                                  technical_signals: Dict = None,
                                  recent_volatility: float = None) -> Dict:
        """
        Analyze market psychology from news and context
        
        Args:
            news_articles: List of recent news articles
            symbol: Trading symbol
            technical_signals: Dict of technical indicator signals
            recent_volatility: Recent market volatility measure
            
        Returns:
            Dict with psychology analysis:
            - fear_greed_index: -1.0 (extreme fear) to 1.0 (extreme greed)
            - dominant_emotion: 'fear', 'greed', 'panic', 'euphoria', 'neutral', 'uncertainty'
            - irrationality_score: 0.0 (rational) to 1.0 (highly irrational)
            - confidence: 0.0 to 1.0
            - reasoning: Explanation of the analysis
            - trading_recommendation: 'contrarian', 'follow_momentum', 'stay_neutral'
            - key_psychological_factors: List of main factors
        """
        # Check rate limits
        if RATE_LIMITER_AVAILABLE:
            rate_limiter = get_rate_limiter()
            can_proceed, reason = rate_limiter.can_make_request(estimated_tokens=600)
            if not can_proceed:
                logger.warning(f"Rate limit reached: {reason}")
                return self._neutral_response(f"Rate limit: {reason}")
        
        try:
            # Build prompt
            prompt = self._create_psychology_prompt(news_articles, symbol, 
                                                    technical_signals, recent_volatility)
            
            # Call Groq
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a behavioral finance expert analyzing market psychology. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            
            content = response.choices[0].message.content
            
            # Validate and strip content before parsing
            content = content.strip() if content else ''
            if not content:
                logger.error("Groq returned empty content")
                return self._neutral_response("Empty response from API")
            
            # Try to parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from Groq: {e}")
                logger.error(f"Content received: {content[:200]}...")  # Log first 200 chars
                return self._neutral_response("JSON parse error")
            
            # Record usage
            if RATE_LIMITER_AVAILABLE:
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 600
                rate_limiter.record_usage(tokens_used)
            
            # Validate and normalize
            return self._normalize_psychology_result(result)
        
        except Exception as e:
            logger.error(f"Market psychology analysis error: {e}")
            return self._neutral_response(str(e))
    
    def _create_psychology_prompt(self, news_articles: List[Dict], 
                                  symbol: str,
                                  technical_signals: Dict = None,
                                  recent_volatility: float = None) -> str:
        """Create prompt for market psychology analysis"""
        
        # Summarize news
        news_summary = []
        for i, article in enumerate(news_articles[:10], 1):
            title = article.get('title', '')
            desc = article.get('description', '')
            news_summary.append(f"{i}. {title} - {desc}")
        
        news_text = "\n".join(news_summary) if news_summary else "No recent news"
        
        # Technical context
        tech_context = ""
        if technical_signals:
            signals = []
            for indicator, signal in technical_signals.items():
                if signal > 0:
                    signals.append(f"{indicator}: bullish")
                elif signal < 0:
                    signals.append(f"{indicator}: bearish")
            tech_context = f"\n\nTechnical Indicators: {', '.join(signals) if signals else 'mixed/neutral'}"
        
        # Volatility context
        vol_context = ""
        if recent_volatility is not None:
            if recent_volatility > 0.03:
                vol_context = f"\n\nRecent Volatility: HIGH ({recent_volatility:.2%}) - market is volatile"
            elif recent_volatility > 0.015:
                vol_context = f"\n\nRecent Volatility: MODERATE ({recent_volatility:.2%})"
            else:
                vol_context = f"\n\nRecent Volatility: LOW ({recent_volatility:.2%}) - market is calm"
        
        prompt = f"""Analyze the market psychology and behavioral patterns for {symbol} based on recent news and market context.

Recent News:
{news_text}
{tech_context}
{vol_context}

Focus on detecting:
1. **Fear vs Greed**: Are investors driven by fear (panic selling, flight to safety) or greed (FOMO, excessive optimism)?
2. **Irrational Behavior**: Is the market overreacting to news? Are emotions overriding fundamentals?
3. **Herd Mentality**: Are people following the crowd without thinking?
4. **Panic or Euphoria**: Extreme emotions that create opportunities?
5. **Uncertainty**: Is there confusion or lack of clear direction?

Consider:
- Language tone in news (panic words, euphoric language, uncertainty)
- Contradiction between technical signals and news sentiment
- Signs of overreaction or underreaction
- Market positioning (everyone on one side = contrarian opportunity)

Return JSON with:
{{
  "fear_greed_index": <float from -1.0 (extreme fear) to 1.0 (extreme greed)>,
  "dominant_emotion": "<fear|greed|panic|euphoria|neutral|uncertainty>",
  "irrationality_score": <float 0.0-1.0, how irrational is the market?>,
  "confidence": <float 0.0-1.0>,
  "reasoning": "<2-3 sentences explaining the psychology>",
  "trading_recommendation": "<contrarian|follow_momentum|stay_neutral>",
  "key_psychological_factors": ["<factor1>", "<factor2>", "<factor3>"]
}}

Examples:
- Panic selling after minor news = high irrationality, extreme fear, contrarian opportunity
- Euphoria with "can't lose" sentiment = extreme greed, high irrationality, contrarian sell
- Uncertainty with mixed signals = neutral, low irrationality, stay neutral
- Fear but fundamentals strong = moderate fear, moderate irrationality, contrarian buy

Return ONLY valid JSON, no additional text."""
        
        return prompt
    
    def _normalize_psychology_result(self, result: Dict) -> Dict:
        """Validate and normalize psychology analysis result"""
        normalized = {
            'fear_greed_index': max(-1.0, min(1.0, float(result.get('fear_greed_index', 0.0)))),
            'dominant_emotion': result.get('dominant_emotion', 'neutral').lower(),
            'irrationality_score': max(0.0, min(1.0, float(result.get('irrationality_score', 0.0)))),
            'confidence': max(0.0, min(1.0, float(result.get('confidence', 0.5)))),
            'reasoning': result.get('reasoning', 'Analysis completed'),
            'trading_recommendation': result.get('trading_recommendation', 'stay_neutral').lower(),
            'key_psychological_factors': result.get('key_psychological_factors', [])[:5]  # Max 5 factors
        }
        
        # Validate emotion
        valid_emotions = ['fear', 'greed', 'panic', 'euphoria', 'neutral', 'uncertainty']
        if normalized['dominant_emotion'] not in valid_emotions:
            normalized['dominant_emotion'] = 'neutral'
        
        # Validate recommendation
        valid_recommendations = ['contrarian', 'follow_momentum', 'stay_neutral']
        if normalized['trading_recommendation'] not in valid_recommendations:
            normalized['trading_recommendation'] = 'stay_neutral'
        
        return normalized
    
    def _neutral_response(self, reason: str = "") -> Dict:
        """Return neutral psychology response"""
        return {
            'fear_greed_index': 0.0,
            'dominant_emotion': 'neutral',
            'irrationality_score': 0.0,
            'confidence': 0.0,
            'reasoning': f'Analysis unavailable: {reason}' if reason else 'Neutral analysis',
            'trading_recommendation': 'stay_neutral',
            'key_psychological_factors': []
        }


# Global analyzer instance
_psychology_analyzer = None


def get_psychology_analyzer() -> MarketPsychologyAnalyzer:
    """Get or create global psychology analyzer instance"""
    global _psychology_analyzer
    if _psychology_analyzer is None:
        try:
            _psychology_analyzer = MarketPsychologyAnalyzer()
        except Exception as e:
            logger.error(f"Failed to initialize psychology analyzer: {e}")
            raise
    return _psychology_analyzer


def analyze_market_psychology(news_articles: List[Dict], 
                              symbol: str,
                              technical_signals: Dict = None,
                              recent_volatility: float = None) -> Dict:
    """
    Convenience function to analyze market psychology
    
    Args:
        news_articles: List of recent news articles
        symbol: Trading symbol
        technical_signals: Dict of technical indicator signals
        recent_volatility: Recent market volatility measure
        
    Returns:
        Dict with psychology analysis
    """
    try:
        analyzer = get_psychology_analyzer()
        return analyzer.analyze_market_psychology(
            news_articles, symbol, technical_signals, recent_volatility
        )
    except Exception as e:
        logger.error(f"Psychology analysis error: {e}")
        return MarketPsychologyAnalyzer(model='llama-3.3-70b-versatile')._neutral_response(str(e))
