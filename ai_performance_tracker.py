"""
AI Performance Tracker
Tracks AI psychology analyzer performance and learns from failures
Helps improve AI prompts and weighting over time
"""

import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIPerformanceTracker:
    """
    Tracks AI psychology analyzer performance and learns from failures
    Adjusts AI confidence weighting based on historical accuracy
    """
    
    def __init__(self, performance_file='ai_performance.json'):
        self.performance_file = performance_file
        self.performance_data = self._load_performance()
        
    def _load_performance(self):
        """Load AI performance tracking data"""
        if os.path.exists(self.performance_file):
            try:
                with open(self.performance_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load AI performance data: {e}")
        
        # Initialize with defaults
        return {
            'total_trades': 0,
            'emotion_driven_trades': 0,
            'emotion_correct': 0,
            'emotion_incorrect': 0,
            'ai_confidence_weight': 1.0,  # Multiplier for AI psychology impact
            'failure_patterns': {
                'extreme_fear_wrong': 0,
                'extreme_greed_wrong': 0,
                'panic_wrong': 0,
                'euphoria_wrong': 0,
                'uncertainty_wrong': 0,
                'contrarian_failed': 0,
                'follow_momentum_failed': 0
            },
            'success_patterns': {
                'extreme_fear_correct': 0,
                'extreme_greed_correct': 0,
                'panic_correct': 0,
                'euphoria_correct': 0,
                'uncertainty_correct': 0,
                'contrarian_success': 0,
                'follow_momentum_success': 0
            },
            'prompt_adjustments': [],
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_performance(self):
        """Save performance data to disk"""
        try:
            self.performance_data['last_updated'] = datetime.now().isoformat()
            with open(self.performance_file, 'w') as f:
                json.dump(self.performance_data, f, indent=2)
            logger.info("AI performance data saved")
        except Exception as e:
            logger.error(f"Could not save AI performance data: {e}")
    
    def record_trade_with_psychology(self, trade_data, psychology_data):
        """
        Record a trade that was influenced by psychology analysis
        
        Args:
            trade_data: Dict with trade details (symbol, direction, entry_price, etc.)
            psychology_data: Dict with psychology analysis (emotion, fear_greed_index, etc.)
        """
        self.performance_data['total_trades'] += 1
        
        # Check if this was an emotion-driven trade (high irrationality)
        irrationality = psychology_data.get('irrationality_score', 0)
        if irrationality > 0.5:
            self.performance_data['emotion_driven_trades'] += 1
        
        # Store for later evaluation
        trade_record = {
            'timestamp': trade_data.get('timestamp', datetime.now().isoformat()),
            'symbol': trade_data['symbol'],
            'direction': trade_data['direction'],
            'entry_price': trade_data['entry_price'],
            'stop_price': trade_data['stop_price'],
            'target_price': trade_data['target_price'],
            'psychology': {
                'emotion': psychology_data.get('dominant_emotion'),
                'fear_greed_index': psychology_data.get('fear_greed_index'),
                'irrationality_score': irrationality,
                'recommendation': psychology_data.get('trading_recommendation'),
                'key_factors': psychology_data.get('key_factors', [])
            },
            'status': 'pending'
        }
        
        # Add to pending trades
        if 'pending_trades' not in self.performance_data:
            self.performance_data['pending_trades'] = []
        self.performance_data['pending_trades'].append(trade_record)
        
        self._save_performance()
    
    def evaluate_trade_outcome(self, trade_data, outcome_data, failure_type):
        """
        Evaluate trade outcome and determine if AI psychology was correct
        
        Args:
            trade_data: Original trade data with psychology
            outcome_data: Trade outcome (win/loss, actual price movement)
            failure_type: 'analytical', 'emotional', or 'mixed'
        
        Returns:
            Dict with analysis and suggested improvements
        """
        psychology = trade_data.get('psychology', {})
        irrationality = psychology.get('irrationality_score', 0)
        
        # Only evaluate if it was an emotion-driven trade
        if irrationality < 0.4:
            return {'type': 'low_emotion', 'analysis': 'Trade not significantly influenced by psychology'}
        
        was_correct = outcome_data.get('won', False)
        emotion = psychology.get('emotion')
        recommendation = psychology.get('recommendation')
        fear_greed = psychology.get('fear_greed_index', 0)
        
        analysis = {
            'was_correct': was_correct,
            'failure_type': failure_type,
            'emotion': emotion,
            'recommendation': recommendation,
            'improvements': []
        }
        
        # Update counters
        if failure_type == 'emotional':
            if was_correct:
                self.performance_data['emotion_correct'] += 1
                
                # Track successful patterns
                if abs(fear_greed) > 0.7:
                    if fear_greed < 0:
                        self.performance_data['success_patterns']['extreme_fear_correct'] += 1
                    else:
                        self.performance_data['success_patterns']['extreme_greed_correct'] += 1
                
                if emotion in ['panic', 'euphoria']:
                    self.performance_data['success_patterns'][f'{emotion}_correct'] += 1
                
                if recommendation == 'contrarian':
                    self.performance_data['success_patterns']['contrarian_success'] += 1
                elif recommendation == 'follow_momentum':
                    self.performance_data['success_patterns']['follow_momentum_success'] += 1
                    
            else:
                self.performance_data['emotion_incorrect'] += 1
                
                # Track failure patterns
                if abs(fear_greed) > 0.7:
                    if fear_greed < 0:
                        self.performance_data['failure_patterns']['extreme_fear_wrong'] += 1
                        analysis['improvements'].append('AI overestimated buying opportunity in fear')
                    else:
                        self.performance_data['failure_patterns']['extreme_greed_wrong'] += 1
                        analysis['improvements'].append('AI overestimated selling opportunity in greed')
                
                if emotion == 'panic':
                    self.performance_data['failure_patterns']['panic_wrong'] += 1
                    analysis['improvements'].append('AI misjudged panic intensity or market reaction')
                elif emotion == 'euphoria':
                    self.performance_data['failure_patterns']['euphoria_wrong'] += 1
                    analysis['improvements'].append('AI misjudged euphoria unsustainability')
                elif emotion == 'uncertainty':
                    self.performance_data['failure_patterns']['uncertainty_wrong'] += 1
                    analysis['improvements'].append('Uncertainty assessment needs refinement')
                
                if recommendation == 'contrarian':
                    self.performance_data['failure_patterns']['contrarian_failed'] += 1
                    analysis['improvements'].append('Contrarian call was premature or wrong')
                elif recommendation == 'follow_momentum':
                    self.performance_data['failure_patterns']['follow_momentum_failed'] += 1
                    analysis['improvements'].append('Momentum following led to late entry')
        
        # Adjust AI confidence weight based on performance
        self._adjust_confidence_weight()
        
        # Generate prompt improvement suggestions
        if not was_correct and failure_type == 'emotional':
            prompt_improvement = self._generate_prompt_improvement(psychology, outcome_data)
            if prompt_improvement:
                analysis['prompt_improvement'] = prompt_improvement
                self.performance_data['prompt_adjustments'].append({
                    'timestamp': datetime.now().isoformat(),
                    'improvement': prompt_improvement
                })
        
        self._save_performance()
        return analysis
    
    def _adjust_confidence_weight(self):
        """Adjust AI confidence weight based on success rate"""
        emotion_correct = self.performance_data['emotion_correct']
        emotion_incorrect = self.performance_data['emotion_incorrect']
        
        if emotion_correct + emotion_incorrect < 5:
            # Not enough data yet
            return
        
        success_rate = emotion_correct / (emotion_correct + emotion_incorrect)
        
        # Adjust weight based on success rate
        if success_rate > 0.65:
            # AI is doing well, increase trust
            self.performance_data['ai_confidence_weight'] = min(1.5, 
                self.performance_data['ai_confidence_weight'] * 1.05)
            logger.info(f"AI confidence weight increased to {self.performance_data['ai_confidence_weight']:.2f} (success: {success_rate:.1%})")
        elif success_rate < 0.45:
            # AI is struggling, reduce trust
            self.performance_data['ai_confidence_weight'] = max(0.5,
                self.performance_data['ai_confidence_weight'] * 0.95)
            logger.info(f"AI confidence weight reduced to {self.performance_data['ai_confidence_weight']:.2f} (success: {success_rate:.1%})")
        else:
            # Performance is acceptable, minor adjustments
            target_weight = 0.8 + (success_rate - 0.45) * 2  # Scale from 0.8 to 1.2
            current = self.performance_data['ai_confidence_weight']
            self.performance_data['ai_confidence_weight'] = current * 0.9 + target_weight * 0.1
            
    def _generate_prompt_improvement(self, psychology, outcome):
        """Generate suggestions for improving AI prompts based on failure"""
        improvements = []
        
        emotion = psychology.get('emotion')
        fear_greed = psychology.get('fear_greed_index', 0)
        
        # Analyze what went wrong
        if abs(fear_greed) > 0.8:
            improvements.append("Consider adding: 'Check if extreme emotion is backed by fundamentals or purely speculative'")
        
        if emotion == 'panic' and not outcome.get('won'):
            improvements.append("Add to prompt: 'Assess if panic selling has reached capitulation or just beginning'")
        
        if emotion == 'euphoria' and not outcome.get('won'):
            improvements.append("Add to prompt: 'Evaluate if euphoria is backed by sustainable trends or FOMO'")
        
        # Check key factors
        factors = psychology.get('key_factors', [])
        if 'contradiction' in str(factors).lower():
            improvements.append("Improve contradiction detection: 'Weigh contradiction severity and market's ability to rationalize'")
        
        return improvements
    
    def get_confidence_weight(self):
        """Get current AI confidence weight"""
        return self.performance_data.get('ai_confidence_weight', 1.0)
    
    def get_statistics(self):
        """Get AI performance statistics"""
        emotion_correct = self.performance_data['emotion_correct']
        emotion_incorrect = self.performance_data['emotion_incorrect']
        total_emotion = emotion_correct + emotion_incorrect
        
        if total_emotion > 0:
            success_rate = emotion_correct / total_emotion
        else:
            success_rate = 0.0
        
        return {
            'total_trades': self.performance_data['total_trades'],
            'emotion_driven_trades': self.performance_data['emotion_driven_trades'],
            'emotion_success_rate': success_rate,
            'ai_confidence_weight': self.performance_data['ai_confidence_weight'],
            'failure_patterns': self.performance_data['failure_patterns'],
            'success_patterns': self.performance_data['success_patterns']
        }
    
    def print_statistics(self):
        """Print AI performance statistics"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("AI PSYCHOLOGY ANALYZER PERFORMANCE")
        print("="*60)
        print(f"Total trades analyzed: {stats['total_trades']}")
        print(f"Emotion-driven trades: {stats['emotion_driven_trades']}")
        
        if stats['emotion_driven_trades'] > 0:
            emotion_correct = self.performance_data['emotion_correct']
            emotion_incorrect = self.performance_data['emotion_incorrect']
            total = emotion_correct + emotion_incorrect
            
            if total > 0:
                print(f"Success rate: {stats['emotion_success_rate']:.1%} ({emotion_correct}/{total})")
                print(f"Current AI confidence weight: {stats['ai_confidence_weight']:.2f}")
                
                print("\nSuccess Patterns:")
                for pattern, count in stats['success_patterns'].items():
                    if count > 0:
                        print(f"  {pattern.replace('_', ' ').title()}: {count}")
                
                print("\nFailure Patterns:")
                for pattern, count in stats['failure_patterns'].items():
                    if count > 0:
                        print(f"  {pattern.replace('_', ' ').title()}: {count}")
                
                # Show recent prompt improvements
                if self.performance_data.get('prompt_adjustments'):
                    print("\nRecent Prompt Improvements:")
                    for adj in self.performance_data['prompt_adjustments'][-3:]:
                        print(f"  - {adj['improvement'][0] if adj['improvement'] else 'N/A'}")
        else:
            print("No emotion-driven trades yet")
        
        print("="*60 + "\n")


# Global instance
_ai_performance_tracker = None

def get_ai_performance_tracker():
    """Get global AI performance tracker instance"""
    global _ai_performance_tracker
    if _ai_performance_tracker is None:
        _ai_performance_tracker = AIPerformanceTracker()
    return _ai_performance_tracker
