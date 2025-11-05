"""
LLM-Enhanced News Analyzer for Market Impact Prediction
Uses Large Language Models to deeply understand news and predict market impact
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Install with: pip install openai")

# Try to import Anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. Install with: pip install anthropic")


class LLMNewsAnalyzer:
    """Analyzes news using LLM to predict market impact"""
    
    def __init__(self, provider: str = 'openai', model: Optional[str] = None):
        """
        Initialize LLM News Analyzer
        
        Args:
            provider: 'openai', 'anthropic', or 'local'
            model: Model name (e.g., 'gpt-4', 'claude-3-sonnet-20240229')
        """
        self.provider = provider.lower()
        self.model = model
        self.client = None
        
        # Initialize based on provider
        if self.provider == 'openai':
            self._init_openai()
        elif self.provider == 'anthropic':
            self._init_anthropic()
        elif self.provider == 'local':
            self._init_local()
        else:
            logger.error(f"Unknown provider: {provider}")
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI not available. Install with: pip install openai")
            return
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. LLM analysis will be disabled.")
            return
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = self.model or 'gpt-4o-mini'  # Default to more affordable model
        logger.info(f"Initialized OpenAI with model: {self.model}")
    
    def _init_anthropic(self):
        """Initialize Anthropic client"""
        if not ANTHROPIC_AVAILABLE:
            logger.error("Anthropic not available. Install with: pip install anthropic")
            return
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set. LLM analysis will be disabled.")
            return
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = self.model or 'claude-3-5-sonnet-20241022'
        logger.info(f"Initialized Anthropic with model: {self.model}")
    
    def _init_local(self):
        """Initialize local LLM (placeholder for future implementation)"""
        logger.warning("Local LLM not yet implemented. Falling back to basic analysis.")
        self.client = None
    
    def analyze_news_article(self, article: Dict[str, str], symbol: str = '') -> Dict:
        """
        Analyze a single news article using LLM
        
        Args:
            article: Dict with 'title', 'description', 'source'
            symbol: Trading symbol (e.g., 'EURUSD', 'XAUUSD')
        
        Returns:
            Dict with analysis results including:
            - sentiment_score: -1.0 to 1.0
            - market_impact: 'high', 'medium', 'low'
            - affected_instruments: List of instruments
            - time_horizon: 'immediate', 'short_term', 'long_term'
            - confidence: 0.0 to 1.0
            - reasoning: Text explanation
        """
        if not self.client:
            # Fallback to basic analysis
            return self._basic_analysis(article, symbol)
        
        try:
            # Prepare prompt
            prompt = self._create_analysis_prompt(article, symbol)
            
            # Call LLM based on provider
            if self.provider == 'openai':
                response = self._call_openai(prompt)
            elif self.provider == 'anthropic':
                response = self._call_anthropic(prompt)
            else:
                response = self._basic_analysis(article, symbol)
            
            return response
        
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return self._basic_analysis(article, symbol)
    
    def _create_analysis_prompt(self, article: Dict[str, str], symbol: str) -> str:
        """Create prompt for LLM analysis"""
        title = article.get('title', '')
        description = article.get('description', '')
        source = article.get('source', {})
        if isinstance(source, dict):
            source = source.get('name', 'Unknown')
        
        prompt = f"""You are a financial market analyst with deep expertise in forex, commodities, and indices trading.

Analyze this news article and predict its market impact:

**Title:** {title}
**Description:** {description}
**Source:** {source}
**Target Symbol:** {symbol if symbol else 'General market analysis'}

Provide a detailed analysis in JSON format with these fields:

1. **sentiment_score**: A number from -1.0 (very bearish) to +1.0 (very bullish)
2. **market_impact**: One of: "high", "medium", "low"
3. **affected_instruments**: List of trading instruments affected (e.g., ["EURUSD", "XAUUSD", "SPX"])
4. **time_horizon**: One of: "immediate" (0-4 hours), "short_term" (4-24 hours), "medium_term" (1-7 days), "long_term" (>7 days)
5. **confidence**: Your confidence in this analysis (0.0 to 1.0)
6. **reasoning**: Brief explanation of your analysis (2-3 sentences)
7. **people_impact**: How this affects people/consumers/investors (1-2 sentences)
8. **market_mechanism**: The mechanism through which this affects markets (1-2 sentences)

Focus on:
- Central bank policy and interest rates
- Economic data (GDP, inflation, employment)
- Geopolitical events and their market implications
- Supply/demand shocks for commodities
- Corporate earnings and sector trends
- Market sentiment and risk appetite

Return ONLY valid JSON, no additional text."""
        
        return prompt
    
    def _call_openai(self, prompt: str) -> Dict:
        """Call OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial market analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validate and normalize result
            return self._normalize_result(result)
        
        except json.JSONDecodeError as e:
            logger.error(f"OpenAI returned invalid JSON: {e}")
            return self._default_result()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._default_result()
    
    def _call_anthropic(self, prompt: str) -> Dict:
        """Call Anthropic API"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text
            result = json.loads(content)
            
            # Validate and normalize result
            return self._normalize_result(result)
        
        except json.JSONDecodeError as e:
            logger.error(f"Anthropic returned invalid JSON: {e}")
            return self._default_result()
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return self._default_result()
    
    def _basic_analysis(self, article: Dict[str, str], symbol: str) -> Dict:
        """Fallback basic analysis without LLM"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        text = f"{title} {description}"
        
        # Simple keyword-based sentiment
        bullish_keywords = ['rise', 'gain', 'increase', 'growth', 'strong', 'positive', 'rally', 'surge', 'boost']
        bearish_keywords = ['fall', 'drop', 'decline', 'weak', 'negative', 'crash', 'plunge', 'cut']
        
        bullish_count = sum(1 for word in bullish_keywords if word in text)
        bearish_count = sum(1 for word in bearish_keywords if word in text)
        
        sentiment = (bullish_count - bearish_count) / max(bullish_count + bearish_count, 1)
        sentiment = max(-1.0, min(1.0, sentiment))
        
        # Determine impact
        high_impact_keywords = ['fed', 'ecb', 'bank', 'rate', 'inflation', 'gdp', 'employment', 'crisis', 'war']
        impact_count = sum(1 for word in high_impact_keywords if word in text)
        
        if impact_count >= 2:
            impact = 'high'
        elif impact_count >= 1:
            impact = 'medium'
        else:
            impact = 'low'
        
        return {
            'sentiment_score': sentiment,
            'market_impact': impact,
            'affected_instruments': [symbol] if symbol else ['EURUSD', 'XAUUSD'],
            'time_horizon': 'short_term',
            'confidence': 0.5,
            'reasoning': 'Basic keyword-based analysis (LLM not available)',
            'people_impact': 'General market sentiment impact',
            'market_mechanism': 'Direct market reaction to news sentiment'
        }
    
    def _normalize_result(self, result: Dict) -> Dict:
        """Normalize and validate LLM result"""
        normalized = {
            'sentiment_score': float(result.get('sentiment_score', 0.0)),
            'market_impact': result.get('market_impact', 'medium').lower(),
            'affected_instruments': result.get('affected_instruments', []),
            'time_horizon': result.get('time_horizon', 'short_term').lower(),
            'confidence': float(result.get('confidence', 0.5)),
            'reasoning': result.get('reasoning', 'No reasoning provided'),
            'people_impact': result.get('people_impact', 'General impact'),
            'market_mechanism': result.get('market_mechanism', 'Market reaction')
        }
        
        # Clamp values
        normalized['sentiment_score'] = max(-1.0, min(1.0, normalized['sentiment_score']))
        normalized['confidence'] = max(0.0, min(1.0, normalized['confidence']))
        
        # Validate enums
        if normalized['market_impact'] not in ['high', 'medium', 'low']:
            normalized['market_impact'] = 'medium'
        
        if normalized['time_horizon'] not in ['immediate', 'short_term', 'medium_term', 'long_term']:
            normalized['time_horizon'] = 'short_term'
        
        return normalized
    
    def _default_result(self) -> Dict:
        """Return default neutral result"""
        return {
            'sentiment_score': 0.0,
            'market_impact': 'low',
            'affected_instruments': [],
            'time_horizon': 'short_term',
            'confidence': 0.0,
            'reasoning': 'Analysis failed',
            'people_impact': 'Unknown',
            'market_mechanism': 'Unknown'
        }
    
    def analyze_news_batch(self, articles: List[Dict], symbol: str = '') -> Dict:
        """
        Analyze multiple news articles and aggregate results
        
        Args:
            articles: List of article dicts
            symbol: Trading symbol
        
        Returns:
            Aggregated analysis with enhanced sentiment and market impact
        """
        if not articles:
            return {
                'llm_sentiment': 0.0,
                'llm_confidence': 0.0,
                'market_impact': 'low',
                'affected_count': 0,
                'reasoning': 'No articles to analyze'
            }
        
        analyses = []
        for article in articles[:10]:  # Limit to 10 most recent to save API calls
            analysis = self.analyze_news_article(article, symbol)
            analyses.append(analysis)
        
        # Aggregate results
        sentiments = [a['sentiment_score'] for a in analyses]
        confidences = [a['confidence'] for a in analyses]
        impacts = [a['market_impact'] for a in analyses]
        
        # Weighted average sentiment (weight by confidence)
        total_confidence = sum(confidences)
        if total_confidence > 0:
            weighted_sentiment = sum(s * c for s, c in zip(sentiments, confidences)) / total_confidence
        else:
            weighted_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        # Average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Determine overall impact
        high_impact_count = sum(1 for i in impacts if i == 'high')
        medium_impact_count = sum(1 for i in impacts if i == 'medium')
        
        if high_impact_count >= len(analyses) * 0.3:
            overall_impact = 'high'
        elif (high_impact_count + medium_impact_count) >= len(analyses) * 0.5:
            overall_impact = 'medium'
        else:
            overall_impact = 'low'
        
        # Count how many articles mention this symbol
        affected_count = sum(1 for a in analyses if symbol in a.get('affected_instruments', []))
        
        # Collect reasoning
        top_reasoning = [a['reasoning'] for a in sorted(analyses, key=lambda x: x['confidence'], reverse=True)[:3]]
        
        return {
            'llm_sentiment': weighted_sentiment,
            'llm_confidence': avg_confidence,
            'market_impact': overall_impact,
            'affected_count': affected_count,
            'total_analyzed': len(analyses),
            'reasoning': ' | '.join(top_reasoning),
            'analyses': analyses  # Keep individual analyses for reference
        }


# Global LLM analyzer instance
_llm_analyzer = None

def get_llm_analyzer(provider: str = None, model: str = None) -> LLMNewsAnalyzer:
    """
    Get or create global LLM analyzer instance
    
    Args:
        provider: 'openai', 'anthropic', or 'local'
        model: Model name
    
    Returns:
        LLMNewsAnalyzer instance
    """
    global _llm_analyzer
    
    # Determine provider from environment if not specified
    if provider is None:
        if os.getenv('OPENAI_API_KEY'):
            provider = 'openai'
        elif os.getenv('ANTHROPIC_API_KEY'):
            provider = 'anthropic'
        else:
            provider = 'local'  # Fallback
    
    if _llm_analyzer is None:
        _llm_analyzer = LLMNewsAnalyzer(provider=provider, model=model)
    
    return _llm_analyzer


def enhance_sentiment_with_llm(articles: List[Dict], symbol: str, basic_sentiment: float) -> Tuple[float, float, Dict]:
    """
    Enhance basic sentiment analysis with LLM insights
    
    Args:
        articles: List of news articles
        symbol: Trading symbol
        basic_sentiment: Basic sentiment from TextBlob
    
    Returns:
        Tuple of (enhanced_sentiment, confidence, llm_analysis)
    """
    # Check if LLM is enabled
    llm_enabled = os.getenv('LLM_NEWS_ANALYSIS_ENABLED', 'false').lower() == 'true'
    
    if not llm_enabled or not articles:
        return basic_sentiment, 0.0, {}
    
    try:
        analyzer = get_llm_analyzer()
        llm_analysis = analyzer.analyze_news_batch(articles, symbol)
        
        # Blend basic sentiment with LLM sentiment
        # Weight LLM sentiment more if confidence is high
        llm_weight = llm_analysis['llm_confidence']
        basic_weight = 1.0 - llm_weight
        
        enhanced_sentiment = (basic_sentiment * basic_weight + llm_analysis['llm_sentiment'] * llm_weight)
        
        # Boost if market impact is high
        if llm_analysis['market_impact'] == 'high':
            enhanced_sentiment *= 1.3
        elif llm_analysis['market_impact'] == 'medium':
            enhanced_sentiment *= 1.15
        
        # Clamp to valid range
        enhanced_sentiment = max(-1.0, min(1.0, enhanced_sentiment))
        
        logger.info(f"Enhanced sentiment for {symbol}: {basic_sentiment:.3f} -> {enhanced_sentiment:.3f} (confidence: {llm_analysis['llm_confidence']:.2f})")
        
        return enhanced_sentiment, llm_analysis['llm_confidence'], llm_analysis
    
    except Exception as e:
        logger.error(f"LLM enhancement error: {e}")
        return basic_sentiment, 0.0, {}
