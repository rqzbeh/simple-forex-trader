"""
LLM-Enhanced News Analyzer for Market Impact Prediction
Uses Groq LLMs to deeply understand news and predict market impact
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import deque

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq library not available. Install with: pip install groq")

# Import rate limiter
try:
    from groq_rate_limiter import get_rate_limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    logger.warning("Rate limiter not available")


class LLMNewsAnalyzer:
    """Analyzes news using LLM to predict market impact - Groq only"""
    
    # Class constant for cache size limit
    MAX_CACHE_SIZE = 1000
    
    def __init__(self, provider: str = 'groq', model: Optional[str] = None):
        """
        Initialize LLM News Analyzer
        
        Args:
            provider: Only 'groq' is supported.
            model: Model name (e.g., 'llama-3.3-70b-versatile', 'llama-3.1-70b-versatile', 
                   'mixtral-8x7b-32768', 'gemma2-9b-it', 'llama3-70b-8192')
        """
        self.provider = provider.lower()
        self.model = model
        self.client = None
        self.analyzed_news_cache: deque = deque(maxlen=self.MAX_CACHE_SIZE)  # Track analyzed articles
        self.analyzed_news_set: set = set()  # Fast O(1) lookup for duplicates
        self.cache_file = 'analyzed_news_cache.json'
        
        # Load cached news hashes
        self._load_cache()
        
        # Initialize based on provider
        if self.provider == 'groq':
            self._init_groq()
        else:
            logger.error(f"Provider '{provider}' not supported. Only 'groq' is supported.")
            raise ValueError(f"Unsupported provider: {provider}. Only 'groq' is supported.")
    
    def _load_cache(self):
        """Load analyzed news cache from disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    hashes = cache_data.get('hashes', [])
                    
                    # If more than MAX_CACHE_SIZE hashes, only keep the most recent ones
                    if len(hashes) > self.MAX_CACHE_SIZE:
                        logger.warning(f"Cache file contains {len(hashes)} hashes, keeping only the most recent {self.MAX_CACHE_SIZE}")
                        hashes = hashes[-self.MAX_CACHE_SIZE:]
                    
                    # Load into deque and set
                    for h in hashes:
                        self.analyzed_news_cache.append(h)
                        self.analyzed_news_set.add(h)
                    
                logger.info(f"Loaded {len(self.analyzed_news_cache)} cached news hashes")
        except Exception as e:
            logger.error(f"Error loading news cache: {e}")
            self.analyzed_news_cache = deque(maxlen=self.MAX_CACHE_SIZE)
            self.analyzed_news_set = set()
    
    def _save_cache(self):
        """Save analyzed news cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({'hashes': list(self.analyzed_news_cache)}, f)
            logger.debug(f"Saved {len(self.analyzed_news_cache)} news hashes to cache")
        except Exception as e:
            logger.error(f"Error saving news cache: {e}")
    
    def _get_article_hash(self, article: Dict[str, str]) -> str:
        """Generate unique hash for article to detect duplicates - using SHA-256 for better collision resistance"""
        title = article.get('title', '')
        description = article.get('description', '')
        # Use JSON for robust serialization to avoid separator collision issues
        content = json.dumps({'title': title, 'description': description}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _is_already_analyzed(self, article: Dict[str, str]) -> bool:
        """Check if article has already been analyzed - O(1) lookup using set"""
        article_hash = self._get_article_hash(article)
        return article_hash in self.analyzed_news_set
    
    def _mark_as_analyzed(self, article: Dict[str, str]):
        """Mark article as analyzed"""
        article_hash = self._get_article_hash(article)
        
        # If cache is at max capacity, retrieve the oldest hash before it gets evicted
        # Use try-except to handle edge cases safely
        oldest_hash = None
        try:
            if len(self.analyzed_news_cache) == self.analyzed_news_cache.maxlen and len(self.analyzed_news_cache) > 0:
                oldest_hash = self.analyzed_news_cache[0]  # Get oldest before appending
        except (IndexError, AttributeError):
            # Failsafe in case of unexpected state
            pass
        
        # Add to deque (will auto-evict oldest if full)
        self.analyzed_news_cache.append(article_hash)
        
        # Update set: remove oldest if it was evicted, add new
        if oldest_hash is not None:
            self.analyzed_news_set.discard(oldest_hash)
        self.analyzed_news_set.add(article_hash)
        
        self._save_cache()
    
    def _init_groq(self):
        """Initialize Groq client"""
        if not GROQ_AVAILABLE:
            logger.error("Groq not available. Install with: pip install groq")
            raise ImportError("Groq library is required. Install with: pip install groq")
        
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            logger.error("GROQ_API_KEY not set. LLM analysis requires Groq API key.")
            raise ValueError("GROQ_API_KEY environment variable must be set")
        
        self.client = Groq(api_key=api_key)
        # Default to llama-3.3-70b-versatile (GPT OSS 120B equivalent)
        self.model = self.model or 'llama-3.3-70b-versatile'
        logger.info(f"Initialized Groq with model: {self.model}")
    
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
            - was_cached: True if result was from cache
        """
        # Check if already analyzed
        if self._is_already_analyzed(article):
            logger.info(f"Skipping duplicate article: {article.get('title', 'Unknown')[:50]}...")
            return {
                'sentiment_score': 0.0,
                'market_impact': 'low',
                'affected_instruments': [],
                'time_horizon': 'short_term',
                'confidence': 0.0,
                'reasoning': 'Article already analyzed (duplicate)',
                'people_impact': 'Already processed',
                'market_mechanism': 'Duplicate detection',
                'was_cached': True
            }
        
        # Check rate limits before making API call
        if RATE_LIMITER_AVAILABLE:
            rate_limiter = get_rate_limiter()
            can_proceed, reason = rate_limiter.can_make_request(estimated_tokens=500)
            if not can_proceed:
                logger.warning(f"Rate limit reached: {reason}")
                return {
                    'sentiment_score': 0.0,
                    'market_impact': 'low',
                    'affected_instruments': [],
                    'time_horizon': 'short_term',
                    'confidence': 0.0,
                    'reasoning': f'Rate limit: {reason}',
                    'people_impact': 'Rate limit reached',
                    'market_mechanism': 'API quota exceeded',
                    'was_cached': False,
                    'rate_limited': True
                }
        
        try:
            # Prepare prompt
            prompt = self._create_analysis_prompt(article, symbol)
            
            # Call LLM - only Groq is supported
            response = self._call_groq(prompt)
            
            # Mark as analyzed
            self._mark_as_analyzed(article)
            response['was_cached'] = False
            response['rate_limited'] = False
            
            return response
        
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            # Still mark as analyzed even on error to avoid repeated failures
            self._mark_as_analyzed(article)
            return {
                'sentiment_score': 0.0,
                'market_impact': 'low',
                'affected_instruments': [],
                'time_horizon': 'short_term',
                'confidence': 0.0,
                'reasoning': f'Analysis failed: {str(e)}',
                'people_impact': 'Error occurred',
                'market_mechanism': 'Analysis error',
                'was_cached': False
            }
    
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
    
    def _call_groq(self, prompt: str) -> Dict:
        """Call Groq API and record usage"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial market analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=500,
                response_format={"type": "json_object"}  # Ensure valid JSON output
            )
            
            content = response.choices[0].message.content
            
            # Validate and strip content before parsing
            content = content.strip() if content else ''
            if not content:
                logger.error("Groq returned empty content")
                return self._default_result()
            
            # Try to parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Groq returned invalid JSON: {e}")
                logger.error(f"Content received: {content[:200]}...")  # Log first 200 chars
                return self._default_result()
            
            # Record API usage
            if RATE_LIMITER_AVAILABLE:
                rate_limiter = get_rate_limiter()
                # Estimate tokens used (input + output)
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 500
                rate_limiter.record_usage(tokens_used)
            
            # Validate and normalize result
            return self._normalize_result(result)
        
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return self._default_result()
    
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
            'market_mechanism': 'Unknown',
            'was_cached': False  # Default results are never cached
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
        provider: Only 'groq' is supported
        model: Model name (defaults to LLM_MODEL environment variable if not provided)
    
    Returns:
        LLMNewsAnalyzer instance
    """
    global _llm_analyzer
    
    # Determine provider from environment if not specified
    if provider is None:
        if os.getenv('GROQ_API_KEY'):
            provider = 'groq'
        else:
            raise ValueError("GROQ_API_KEY environment variable must be set")
    
    # Use LLM_MODEL environment variable if model not explicitly provided
    if model is None:
        model = os.getenv('LLM_MODEL')
    
    if _llm_analyzer is None:
        _llm_analyzer = LLMNewsAnalyzer(provider=provider, model=model)
    
    return _llm_analyzer


def enhance_sentiment_with_llm(articles: List[Dict], symbol: str, basic_sentiment: float = 0.0) -> Tuple[float, float, Dict]:
    """
    Analyze sentiment using LLM (no TextBlob fallback - LLM is mandatory)
    
    Args:
        articles: List of news articles
        symbol: Trading symbol
        basic_sentiment: Legacy parameter, ignored (LLM only now)
    
    Returns:
        Tuple of (sentiment, confidence, llm_analysis)
    """
    # LLM is now mandatory - no fallback
    if not articles:
        return 0.0, 0.0, {}
    
    try:
        analyzer = get_llm_analyzer()
        llm_analysis = analyzer.analyze_news_batch(articles, symbol)
        
        # Use LLM sentiment directly (no blending)
        llm_sentiment = llm_analysis['llm_sentiment']
        llm_confidence = llm_analysis['llm_confidence']
        
        # Boost if market impact is high
        if llm_analysis['market_impact'] == 'high':
            llm_sentiment *= 1.3
        elif llm_analysis['market_impact'] == 'medium':
            llm_sentiment *= 1.15
        
        # Clamp to valid range
        llm_sentiment = max(-1.0, min(1.0, llm_sentiment))
        
        logger.info(f"LLM sentiment for {symbol}: {llm_sentiment:.3f} (confidence: {llm_confidence:.2f})")
        
        return llm_sentiment, llm_confidence, llm_analysis
    
    except Exception as e:
        logger.error(f"LLM analysis error: {e}")
        return 0.0, 0.0, {}
