"""
Groq API Rate Limiter
Tracks and enforces Groq free tier limits to prevent exceeding quotas
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroqRateLimiter:
    """Manages Groq API usage to stay within free tier limits"""
    
    # Groq free tier limits (conservative estimates)
    DEFAULT_MAX_REQUESTS_PER_DAY = 1000
    DEFAULT_MAX_TOKENS_PER_DAY = 500000
    
    def __init__(self, usage_file: str = 'groq_usage.json'):
        """
        Initialize rate limiter
        
        Args:
            usage_file: Path to file storing usage data
        """
        self.usage_file = usage_file
        self.usage_data = self._load_usage()
        
        # Allow user to override limits (set to 0 to disable limits)
        self.max_requests_per_day = int(os.getenv('GROQ_MAX_REQUESTS_PER_DAY', self.DEFAULT_MAX_REQUESTS_PER_DAY))
        self.max_tokens_per_day = int(os.getenv('GROQ_MAX_TOKENS_PER_DAY', self.DEFAULT_MAX_TOKENS_PER_DAY))
        
        # Respect limits by default, allow manual override
        self.enforce_limits = os.getenv('GROQ_ENFORCE_LIMITS', 'true').lower() == 'true'
        
        if not self.enforce_limits:
            logger.warning("Groq rate limiting disabled - may exceed free tier limits")
        else:
            logger.info(f"Groq rate limits: {self.max_requests_per_day} requests/day, {self.max_tokens_per_day} tokens/day")
    
    def _load_usage(self) -> Dict:
        """Load usage data from file"""
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    # Check if data is from today
                    date_str = data.get('date', '')
                    if date_str == datetime.now().strftime('%Y-%m-%d'):
                        return data
        except Exception as e:
            logger.error(f"Error loading usage data: {e}")
        
        # Return fresh data for today
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'requests': 0,
            'tokens': 0
        }
    
    def _save_usage(self):
        """Save usage data to file"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving usage data: {e}")
    
    def _reset_if_new_day(self):
        """Reset counters if it's a new day"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.usage_data.get('date') != today:
            logger.info(f"New day - resetting usage counters (Previous: {self.usage_data.get('requests', 0)} requests, {self.usage_data.get('tokens', 0)} tokens)")
            self.usage_data = {
                'date': today,
                'requests': 0,
                'tokens': 0
            }
            self._save_usage()
    
    def can_make_request(self, estimated_tokens: int = 500) -> Tuple[bool, str]:
        """
        Check if a request can be made within limits
        
        Args:
            estimated_tokens: Estimated tokens for this request
            
        Returns:
            Tuple of (can_proceed, reason)
        """
        if not self.enforce_limits:
            return True, "Rate limiting disabled"
        
        self._reset_if_new_day()
        
        # Check request limit
        if self.max_requests_per_day > 0 and self.usage_data['requests'] >= self.max_requests_per_day:
            return False, f"Daily request limit reached ({self.max_requests_per_day})"
        
        # Check token limit
        if self.max_tokens_per_day > 0 and (self.usage_data['tokens'] + estimated_tokens) > self.max_tokens_per_day:
            return False, f"Daily token limit would be exceeded ({self.usage_data['tokens'] + estimated_tokens}/{self.max_tokens_per_day})"
        
        return True, "OK"
    
    def record_usage(self, tokens_used: int):
        """
        Record API usage
        
        Args:
            tokens_used: Number of tokens used in the request
        """
        self._reset_if_new_day()
        
        self.usage_data['requests'] += 1
        self.usage_data['tokens'] += tokens_used
        
        self._save_usage()
        
        if self.enforce_limits:
            requests_pct = (self.usage_data['requests'] / self.max_requests_per_day * 100) if self.max_requests_per_day > 0 else 0
            tokens_pct = (self.usage_data['tokens'] / self.max_tokens_per_day * 100) if self.max_tokens_per_day > 0 else 0
            
            logger.info(f"Groq usage: {self.usage_data['requests']}/{self.max_requests_per_day} requests ({requests_pct:.1f}%), "
                       f"{self.usage_data['tokens']}/{self.max_tokens_per_day} tokens ({tokens_pct:.1f}%)")
            
            # Warn when approaching limits
            if requests_pct > 80 or tokens_pct > 80:
                logger.warning(f"Approaching Groq daily limits - consider reducing frequency")
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        self._reset_if_new_day()
        return {
            'date': self.usage_data['date'],
            'requests': self.usage_data['requests'],
            'tokens': self.usage_data['tokens'],
            'requests_limit': self.max_requests_per_day,
            'tokens_limit': self.max_tokens_per_day,
            'requests_remaining': max(0, self.max_requests_per_day - self.usage_data['requests']),
            'tokens_remaining': max(0, self.max_tokens_per_day - self.usage_data['tokens']),
            'enforce_limits': self.enforce_limits
        }


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> GroqRateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = GroqRateLimiter()
    return _rate_limiter
