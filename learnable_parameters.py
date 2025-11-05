"""
Learnable Parameters System
Manages trading parameters that adapt based on historical performance
Replaces hardcoded values with ML/AI-learned optimal values
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)

class LearnableParameters:
    """Manages parameters that learn from trading history"""
    
    def __init__(self, params_file='learnable_params.json'):
        self.params_file = params_file
        
        # Research-based default values (can be overridden by learning)
        self.defaults = {
            # Kelly Criterion (Thorp, 1961 - optimal betting)
            'kelly_fraction': 0.5,  # Half-Kelly for safety (MacLean et al., 2010)
            'min_position_size': 0.01,
            'max_position_size': 0.25,
            
            # Regime Detection (Wilder's ADX research, 1978)
            'adx_trending_threshold': 25,  # Standard threshold for strong trend
            'adx_ranging_threshold': 20,   # Standard threshold for weak trend
            'volatility_high_percentile': 0.8,
            'volatility_threshold': 0.03,
            'trend_agreement_trending': 0.6,
            'trend_agreement_ranging': 0.4,
            
            # Correlation (Modern Portfolio Theory, Markowitz)
            'correlation_threshold': 0.5,  # Moderate correlation cutoff
            'max_correlation_exposure': 2.0,
            
            # Sharpe Optimization (Sharpe, 1966)
            'sharpe_good_threshold': 1.0,  # Good risk-adjusted return
            'sharpe_weight_boost': 1.5,
            'sharpe_weight_reduce': 0.5,
            'sharpe_neutral_weight': 1.0,
            
            # Stop Loss Adjustments (volatility-based)
            'volatile_size_multiplier': 0.5,
            'volatile_stop_multiplier': 1.5,
            'trending_stop_multiplier': 0.9,
            'ranging_boost': 1.3,
            'trending_boost': 1.2,
            
            # Psychology Analysis
            'psychology_display_threshold': 0.4,
            'psychology_irrationality_threshold': 0.6,
            
            # ML Confidence
            'ml_confidence_factor': 0.5,
            'ml_confidence_min': 0.1,
            'ml_confidence_max': 0.9,
            
            # ATR Multipliers
            'atr_stop_loss_multiplier': 2.0,
            'atr_take_profit_multiplier': 3.0,
            'atr_volatility_factor': 1.0,
        }
        
        # Learned parameters (start with defaults)
        self.params = self.defaults.copy()
        
        # Learning history
        self.param_history = deque(maxlen=100)
        self.performance_by_params = {}
        
        self.load_params()
    
    def load_params(self):
        """Load learned parameters from disk"""
        try:
            if os.path.exists(self.params_file):
                with open(self.params_file, 'r') as f:
                    data = json.load(f)
                    self.params.update(data.get('params', {}))
                    self.param_history = deque(data.get('history', [])[-100:], maxlen=100)
                    logger.info(f"Loaded {len(self.params)} learned parameters")
        except Exception as e:
            logger.warning(f"Could not load learned parameters: {e}")
    
    def save_params(self):
        """Save learned parameters to disk"""
        try:
            with open(self.params_file, 'w') as f:
                json.dump({
                    'params': self.params,
                    'history': list(self.param_history),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save learned parameters: {e}")
    
    def get(self, param_name, default=None):
        """Get parameter value (learned or default)"""
        if default is None:
            default = self.defaults.get(param_name)
        return self.params.get(param_name, default)
    
    def update_from_trades(self, recent_trades):
        """Learn optimal parameters from recent trading history"""
        if len(recent_trades) < 30:
            return  # Need sufficient data
        
        try:
            # Calculate win rate for Kelly optimization
            wins = [t for t in recent_trades if t.get('outcome') == 'win']
            win_rate = len(wins) / len(recent_trades)
            
            avg_win = np.mean([t.get('return', 0) for t in wins]) if wins else 0
            losses = [t for t in recent_trades if t.get('outcome') == 'loss']
            avg_loss = np.mean([abs(t.get('return', 0)) for t in losses]) if losses else 0.01
            
            # Learn optimal Kelly fraction
            if avg_loss > 0:
                win_loss_ratio = avg_win / avg_loss
                optimal_kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
                # Adjust conservatively (move 20% toward optimal)
                current_kelly = self.params['kelly_fraction']
                target_kelly = current_kelly * 0.8 + optimal_kelly * 0.5 * 0.2
                self.params['kelly_fraction'] = np.clip(target_kelly, 0.3, 0.7)
            
            # Learn regime detection thresholds
            regime_trades = {}
            for t in recent_trades:
                regime = t.get('regime', 'neutral')
                if regime not in regime_trades:
                    regime_trades[regime] = {'wins': 0, 'total': 0}
                regime_trades[regime]['total'] += 1
                if t.get('outcome') == 'win':
                    regime_trades[regime]['wins'] += 1
            
            # Adjust ADX thresholds based on regime performance
            if 'trending' in regime_trades and regime_trades['trending']['total'] > 5:
                trending_win_rate = regime_trades['trending']['wins'] / regime_trades['trending']['total']
                if trending_win_rate < 0.4:  # Poor performance in trending
                    # Be more selective (increase threshold)
                    self.params['adx_trending_threshold'] = min(35, self.params['adx_trending_threshold'] + 1)
                elif trending_win_rate > 0.6:  # Good performance
                    # Be more aggressive (decrease threshold)
                    self.params['adx_trending_threshold'] = max(15, self.params['adx_trending_threshold'] - 1)
            
            # Learn correlation threshold
            correlated_losses = [t for t in recent_trades 
                                if t.get('correlation_warning') and t.get('outcome') == 'loss']
            if len(correlated_losses) > len(recent_trades) * 0.2:  # >20% correlated losses
                # Tighten correlation filter
                self.params['correlation_threshold'] = max(0.3, self.params['correlation_threshold'] - 0.05)
            
            # Learn psychology thresholds
            psychology_trades = [t for t in recent_trades if t.get('irrationality', 0) > 0.5]
            if psychology_trades:
                high_ir_wins = [t for t in psychology_trades if t.get('outcome') == 'win']
                if len(psychology_trades) > 5:
                    high_ir_win_rate = len(high_ir_wins) / len(psychology_trades)
                    # Adjust irrationality threshold
                    if high_ir_win_rate > 0.6:
                        # Good at high irrationality, lower threshold
                        self.params['psychology_irrationality_threshold'] = max(0.4, 
                            self.params['psychology_irrationality_threshold'] - 0.05)
                    elif high_ir_win_rate < 0.4:
                        # Poor at high irrationality, raise threshold
                        self.params['psychology_irrationality_threshold'] = min(0.8,
                            self.params['psychology_irrationality_threshold'] + 0.05)
            
            # Learn volatility multipliers
            volatile_trades = [t for t in recent_trades if t.get('regime') == 'volatile']
            if volatile_trades and len(volatile_trades) > 5:
                volatile_losses = [t for t in volatile_trades if t.get('outcome') == 'loss']
                volatile_loss_rate = len(volatile_losses) / len(volatile_trades)
                if volatile_loss_rate > 0.6:  # High loss rate in volatile markets
                    # Reduce size more aggressively
                    self.params['volatile_size_multiplier'] = max(0.3, 
                        self.params['volatile_size_multiplier'] - 0.05)
                    # Widen stops more
                    self.params['volatile_stop_multiplier'] = min(2.0,
                        self.params['volatile_stop_multiplier'] + 0.1)
            
            # Record parameter update
            self.param_history.append({
                'timestamp': datetime.now().isoformat(),
                'win_rate': win_rate,
                'params_snapshot': self.params.copy()
            })
            
            self.save_params()
            logger.info(f"Parameters updated from {len(recent_trades)} trades. Win rate: {win_rate:.2%}")
            
        except Exception as e:
            logger.error(f"Error updating parameters: {e}")
    
    def get_all(self):
        """Get all current parameters"""
        return self.params.copy()
    
    def reset_to_defaults(self):
        """Reset all parameters to research-based defaults"""
        self.params = self.defaults.copy()
        self.save_params()
        logger.info("Parameters reset to defaults")

# Singleton instance
_params_instance = None

def get_learnable_params():
    """Get singleton instance of learnable parameters"""
    global _params_instance
    if _params_instance is None:
        _params_instance = LearnableParameters()
    return _params_instance
