"""
Advanced Risk Management System
Implements Kelly Criterion, Regime Detection, Correlation Filtering, and Sharpe Optimization
Inspired by Renaissance Technologies and top quantitative trading firms
"""

import os
import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

# Configuration
KELLY_CRITERION_ENABLED = os.getenv('KELLY_CRITERION_ENABLED', 'true').lower() == 'true'
KELLY_FRACTION = float(os.getenv('KELLY_FRACTION', '0.5'))  # Half-Kelly for safety
REGIME_DETECTION_ENABLED = os.getenv('REGIME_DETECTION_ENABLED', 'true').lower() == 'true'
CORRELATION_FILTER_ENABLED = os.getenv('CORRELATION_FILTER_ENABLED', 'true').lower() == 'true'
MAX_CORRELATION_EXPOSURE = float(os.getenv('MAX_CORRELATION_EXPOSURE', '2.0'))
SHARPE_TRACKING_ENABLED = os.getenv('SHARPE_TRACKING_ENABLED', 'true').lower() == 'true'

class AdvancedRiskManager:
    """Advanced risk management with Kelly Criterion, regime detection, and correlation filtering"""
    
    def __init__(self, history_file='advanced_risk_data.json'):
        self.history_file = history_file
        self.trade_history = deque(maxlen=1000)
        self.correlation_matrix = {}
        self.sharpe_ratios = {
            'technical': deque(maxlen=30),
            'sentiment': deque(maxlen=30),
            'psychology': deque(maxlen=30),
            'ml': deque(maxlen=30)
        }
        self.regime_history = deque(maxlen=100)
        self.open_positions = {}  # symbol -> position_data
        self.load_data()
    
    def load_data(self):
        """Load historical risk data"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.trade_history = deque(data.get('trade_history', [])[-1000:], maxlen=1000)
                    self.correlation_matrix = data.get('correlation_matrix', {})
                    self.open_positions = data.get('open_positions', {})
                    logger.info("Advanced risk data loaded")
        except Exception as e:
            logger.warning(f"Could not load advanced risk data: {e}")
    
    def save_data(self):
        """Save risk data"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump({
                    'trade_history': list(self.trade_history),
                    'correlation_matrix': self.correlation_matrix,
                    'open_positions': self.open_positions,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save advanced risk data: {e}")
    
    def calculate_kelly_fraction(self, win_probability, win_loss_ratio, ml_confidence=0.5):
        """
        Calculate Kelly Criterion position size
        f* = (p*b - q) / b
        where p = win probability, q = loss probability (1-p), b = odds (win/loss ratio)
        """
        if not KELLY_CRITERION_ENABLED:
            return 0.02  # Default 2% position size
        
        # Adjust win probability based on ML confidence
        adjusted_win_prob = win_probability * (0.5 + ml_confidence * 0.5)
        adjusted_win_prob = max(0.1, min(0.9, adjusted_win_prob))  # Clamp
        
        loss_prob = 1 - adjusted_win_prob
        
        if win_loss_ratio <= 0 or adjusted_win_prob <= 0:
            return 0.01  # Minimal position
        
        # Kelly formula
        kelly = (adjusted_win_prob * win_loss_ratio - loss_prob) / win_loss_ratio
        
        # Apply fractional Kelly for safety (typically 0.5 = half-Kelly)
        fractional_kelly = kelly * KELLY_FRACTION
        
        # Limit to maximum 25% of capital for single position
        position_size = max(0.01, min(0.25, fractional_kelly))
        
        return position_size
    
    def detect_market_regime(self, market_data):
        """
        Detect current market regime: trending, ranging, or volatile
        Returns: {'regime': 'trending'|'ranging'|'volatile', 'confidence': 0.0-1.0}
        """
        if not REGIME_DETECTION_ENABLED:
            return {'regime': 'neutral', 'confidence': 0.5}
        
        try:
            volatility = market_data.get('volatility_hourly', 0.01)
            adx = market_data.get('adx', 25)
            atr_pct = market_data.get('atr_pct', 0.005)
            
            # Calculate trend consistency (how many indicators agree on direction)
            trend_signals = [
                market_data.get('macd_signal', 0),
                market_data.get('trend_signal', 0),
                market_data.get('sar_signal', 0),
                market_data.get('adx_signal', 0)
            ]
            trend_agreement = abs(sum(trend_signals)) / len(trend_signals)
            
            # Volatility percentile (compared to recent history)
            recent_vols = [t.get('volatility', 0.01) for t in list(self.trade_history)[-30:]]
            if recent_vols:
                vol_percentile = sum(1 for v in recent_vols if v < volatility) / len(recent_vols)
            else:
                vol_percentile = 0.5
            
            # Decision logic
            if vol_percentile > 0.8 or volatility > 0.03:
                regime = 'volatile'
                confidence = vol_percentile
            elif adx > 25 and trend_agreement > 0.6:
                regime = 'trending'
                confidence = min(adx / 50, 1.0) * trend_agreement
            elif adx < 20 and trend_agreement < 0.4:
                regime = 'ranging'
                confidence = (1 - adx / 50) * (1 - trend_agreement)
            else:
                regime = 'neutral'
                confidence = 0.5
            
            result = {'regime': regime, 'confidence': confidence}
            self.regime_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Regime detection error: {e}")
            return {'regime': 'neutral', 'confidence': 0.5}
    
    def calculate_correlation(self, symbol1, symbol2, lookback_days=30):
        """Calculate correlation between two symbols"""
        # Simplified correlation based on currency base/quote
        # In production, would use actual price correlation
        
        # Extract base currencies
        base1 = symbol1[:3] if len(symbol1) >= 6 else symbol1
        base2 = symbol2[:3] if len(symbol2) >= 6 else symbol2
        quote1 = symbol1[3:6] if len(symbol1) >= 6 else ''
        quote2 = symbol2[3:6] if len(symbol2) >= 6 else ''
        
        # High correlation if same base or quote currency
        if base1 == base2 or quote1 == quote2:
            return 0.8
        elif base1 == quote2 or base2 == quote1:
            return -0.8  # Inverse correlation
        else:
            return 0.2  # Low correlation
    
    def check_correlation_limits(self, new_symbol, new_position_size):
        """
        Check if adding new position would exceed correlation limits
        Returns: (can_trade: bool, reason: str, max_allowed_size: float)
        """
        if not CORRELATION_FILTER_ENABLED:
            return True, "OK", new_position_size
        
        if not self.open_positions:
            return True, "OK", new_position_size
        
        # Calculate exposure to correlated assets
        total_correlated_exposure = 0
        
        for open_symbol, position in self.open_positions.items():
            correlation = self.calculate_correlation(new_symbol, open_symbol)
            if abs(correlation) > 0.5:  # Significant correlation
                # Weight by correlation strength
                total_correlated_exposure += position['size'] * abs(correlation)
        
        # Check if adding new position exceeds limit
        max_allowed_exposure = new_position_size * MAX_CORRELATION_EXPOSURE
        new_total_exposure = total_correlated_exposure + new_position_size
        
        if new_total_exposure > max_allowed_exposure:
            # Calculate reduced position size that fits within limits
            max_allowed_size = max(0.01, max_allowed_exposure - total_correlated_exposure)
            return False, f"Correlation limit: {new_total_exposure:.2f} > {max_allowed_exposure:.2f}", max_allowed_size
        
        return True, "OK", new_position_size
    
    def calculate_sharpe_ratio(self, returns):
        """Calculate Sharpe ratio from return series"""
        if len(returns) < 5:
            return 0.0
        
        returns_array = np.array(returns)
        if np.std(returns_array) == 0:
            return 0.0
        
        # Annualized Sharpe (assuming hourly returns)
        sharpe = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252 * 24)
        return sharpe
    
    def update_sharpe_tracking(self, trade_result):
        """Update Sharpe ratios for different strategy components"""
        if not SHARPE_TRACKING_ENABLED:
            return
        
        # Extract component returns
        if trade_result.get('outcome') == 'win':
            ret = trade_result.get('return', 0.0)
        else:
            ret = -abs(trade_result.get('return', 0.0))
        
        # Track by component contribution
        if trade_result.get('technical_score', 0) > 0.5:
            self.sharpe_ratios['technical'].append(ret)
        if trade_result.get('sentiment_score', 0) != 0:
            self.sharpe_ratios['sentiment'].append(ret)
        if trade_result.get('psychology_score', 0) > 0.4:
            self.sharpe_ratios['psychology'].append(ret)
        if trade_result.get('ml_used', False):
            self.sharpe_ratios['ml'].append(ret)
    
    def get_component_weights(self):
        """Get dynamic weights for strategy components based on Sharpe ratios"""
        if not SHARPE_TRACKING_ENABLED:
            return {'technical': 1.0, 'sentiment': 1.0, 'psychology': 1.0, 'ml': 1.0}
        
        weights = {}
        sharpe_scores = {}
        
        for component, returns in self.sharpe_ratios.items():
            if len(returns) >= 10:
                sharpe = self.calculate_sharpe_ratio(list(returns))
                sharpe_scores[component] = sharpe
                
                # Convert Sharpe to weight (0.5 to 1.5 range)
                if sharpe > 1.0:
                    weights[component] = min(1.5, 1.0 + sharpe * 0.25)
                elif sharpe < 0:
                    weights[component] = max(0.5, 1.0 + sharpe * 0.5)
                else:
                    weights[component] = 1.0
            else:
                weights[component] = 1.0  # Default weight
        
        return weights
    
    def adjust_strategy_for_regime(self, regime_info, trade_plan):
        """Adjust trading strategy based on market regime"""
        regime = regime_info['regime']
        confidence = regime_info['confidence']
        
        if regime == 'volatile':
            # Reduce position size, widen stops, avoid trades if very volatile
            trade_plan['position_size'] *= 0.5
            trade_plan['stop_loss_multiplier'] = trade_plan.get('stop_loss_multiplier', 1.0) * 1.5
            trade_plan['regime_note'] = f"Volatile market (conf: {confidence:.2f}): 50% size, 50% wider stops"
            
        elif regime == 'trending':
            # Follow trends, tighter stops
            trade_plan['stop_loss_multiplier'] = trade_plan.get('stop_loss_multiplier', 1.0) * 0.9
            trade_plan['trend_boost'] = 1.2  # Boost trend-following signals
            trade_plan['regime_note'] = f"Trending market (conf: {confidence:.2f}): Follow momentum, tighter stops"
            
        elif regime == 'ranging':
            # Mean reversion, use support/resistance
            trade_plan['mean_reversion_boost'] = 1.3
            trade_plan['regime_note'] = f"Ranging market (conf: {confidence:.2f}): Mean reversion focus"
        
        return trade_plan
    
    def record_trade(self, trade_data):
        """Record trade for history tracking"""
        self.trade_history.append(trade_data)
        
        # Update open positions
        if trade_data.get('action') == 'open':
            self.open_positions[trade_data['symbol']] = {
                'size': trade_data.get('position_size', 0.02),
                'entry_time': datetime.now().isoformat(),
                'entry_price': trade_data.get('price', 0)
            }
        elif trade_data.get('action') == 'close':
            if trade_data['symbol'] in self.open_positions:
                del self.open_positions[trade_data['symbol']]
        
        # Update Sharpe tracking
        if trade_data.get('outcome'):
            self.update_sharpe_tracking(trade_data)
        
        self.save_data()
    
    def get_statistics(self):
        """Get risk management statistics"""
        stats = {
            'kelly_criterion_enabled': KELLY_CRITERION_ENABLED,
            'regime_detection_enabled': REGIME_DETECTION_ENABLED,
            'correlation_filter_enabled': CORRELATION_FILTER_ENABLED,
            'sharpe_tracking_enabled': SHARPE_TRACKING_ENABLED,
            'open_positions': len(self.open_positions),
            'trades_tracked': len(self.trade_history)
        }
        
        if REGIME_DETECTION_ENABLED and self.regime_history:
            recent_regime = self.regime_history[-1]
            stats['current_regime'] = recent_regime
        
        if SHARPE_TRACKING_ENABLED:
            component_weights = self.get_component_weights()
            stats['component_weights'] = component_weights
            
            sharpe_scores = {}
            for component, returns in self.sharpe_ratios.items():
                if len(returns) >= 10:
                    sharpe_scores[component] = self.calculate_sharpe_ratio(list(returns))
            stats['sharpe_ratios'] = sharpe_scores
        
        # Calculate win rate for Kelly Criterion
        if len(self.trade_history) >= 10:
            wins = sum(1 for t in self.trade_history if t.get('outcome') == 'win')
            stats['win_rate'] = wins / len(self.trade_history)
            
            # Calculate average win/loss ratio
            win_returns = [t.get('return', 0) for t in self.trade_history if t.get('outcome') == 'win']
            loss_returns = [abs(t.get('return', 0)) for t in self.trade_history if t.get('outcome') == 'loss']
            if win_returns and loss_returns:
                stats['win_loss_ratio'] = np.mean(win_returns) / np.mean(loss_returns)
        
        return stats


# Singleton instance
_risk_manager = None

def get_risk_manager():
    """Get or create risk manager instance"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = AdvancedRiskManager()
    return _risk_manager
