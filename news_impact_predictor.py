"""
AI-Powered News Impact Predictor
Uses machine learning to predict how current news will affect trading opportunities
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, cross_val_score
import joblib
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsImpactPredictor:
    """
    ML-based predictor for news impact on trading
    Learns from historical news and trade outcomes to predict future news impact
    """
    
    def __init__(self, model_path='news_impact_model.pkl', 
                 vectorizer_path='news_impact_vectorizer.pkl',
                 scaler_path='news_impact_scaler.pkl'):
        self.model_path = model_path
        self.vectorizer_path = vectorizer_path
        self.scaler_path = scaler_path
        self.model = None
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.scaler = StandardScaler()
        
        # High-impact keywords for forex trading
        self.high_impact_keywords = {
            'central_bank': ['fed', 'ecb', 'boj', 'boe', 'pboc', 'rba', 'rate decision', 'monetary policy'],
            'economic_data': ['gdp', 'employment', 'unemployment', 'nonfarm', 'payroll', 'inflation', 'cpi', 'ppi'],
            'crisis': ['crisis', 'emergency', 'collapse', 'default', 'bankrupt', 'crash'],
            'geopolitical': ['war', 'sanctions', 'trade war', 'tariff', 'conflict', 'election'],
            'market_event': ['brexit', 'stimulus', 'bailout', 'quantitative easing', 'tapering']
        }
        
        self.min_training_samples = 30
        self.load_model()
    
    def load_model(self):
        """Load trained model, vectorizer, and scaler from disk"""
        try:
            if (os.path.exists(self.model_path) and 
                os.path.exists(self.vectorizer_path) and 
                os.path.exists(self.scaler_path)):
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("News impact model loaded successfully")
                return True
        except Exception as e:
            logger.warning(f"Could not load news impact model: {e}")
        return False
    
    def save_model(self):
        """Save trained model, vectorizer, and scaler to disk"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("News impact model saved successfully")
            return True
        except Exception as e:
            logger.error(f"Could not save news impact model: {e}")
            return False
    
    def extract_news_features(self, news_articles):
        """
        Extract features from news articles for prediction
        
        Args:
            news_articles: List of dicts with 'title', 'description', 'source'
        
        Returns:
            Feature vector for prediction
        """
        if not news_articles:
            # Return neutral features if no news
            return np.zeros(100 + 5 + 2).reshape(1, -1)  # TF-IDF + category + count features
        
        # Combine all text
        texts = []
        for article in news_articles:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()
            texts.append(text)
        
        combined_text = ' '.join(texts)
        
        # TF-IDF features (100 dimensions)
        if hasattr(self.vectorizer, 'vocabulary_'):
            tfidf_features = self.vectorizer.transform([combined_text]).toarray()[0]
        else:
            # If not fitted yet, return zeros
            tfidf_features = np.zeros(100)
        
        # Category features (count of high-impact keywords)
        category_features = []
        for category, keywords in self.high_impact_keywords.items():
            count = sum(1 for keyword in keywords if keyword in combined_text)
            category_features.append(count)
        
        # Aggregate features
        news_count = len(news_articles)
        authoritative_count = sum(1 for a in news_articles 
                                   if any(word in a.get('source', '').lower() 
                                         for word in ['reuters', 'bloomberg', 'fed', 'ecb']))
        
        aggregate_features = [news_count, authoritative_count]
        
        # Combine all features
        all_features = np.concatenate([tfidf_features, category_features, aggregate_features])
        
        return all_features.reshape(1, -1)
    
    def categorize_news_impact(self, news_articles):
        """
        Categorize news impact based on keywords (rule-based fallback)
        
        Returns:
            impact_level: 'high', 'medium', 'low'
            impact_score: float between -1 and 1
            confidence: float between 0 and 1
        """
        if not news_articles:
            return 'low', 0.0, 0.5
        
        combined_text = ' '.join([
            f"{a.get('title', '')} {a.get('description', '')}".lower() 
            for a in news_articles
        ])
        
        # Count high-impact keywords by category
        impact_scores = {}
        for category, keywords in self.high_impact_keywords.items():
            count = sum(1 for keyword in keywords if keyword in combined_text)
            impact_scores[category] = count
        
        total_high_impact = sum(impact_scores.values())
        
        # Determine impact level
        if total_high_impact >= 3:
            impact_level = 'high'
            impact_score = 0.7
            confidence = 0.8
        elif total_high_impact >= 1:
            impact_level = 'medium'
            impact_score = 0.4
            confidence = 0.6
        else:
            impact_level = 'low'
            impact_score = 0.1
            confidence = 0.5
        
        # Check for negative keywords (bearish news)
        negative_keywords = ['crisis', 'collapse', 'default', 'bankrupt', 'crash', 'war', 'conflict']
        negative_count = sum(1 for keyword in negative_keywords if keyword in combined_text)
        
        if negative_count > 0:
            impact_score = -impact_score  # Make it negative for bearish impact
        
        return impact_level, impact_score, confidence
    
    def prepare_training_data(self, trade_log_file='trade_log.json'):
        """
        Prepare training data from historical trades with news context
        
        Expected trade log format:
        {
            'timestamp': '2024-01-01T10:00:00',
            'status': 'win' or 'loss' or 'loss_news_driven',
            'entry_news_count': 5,
            'entry_sentiment': 0.3,
            'news_articles': [...]  # Optional: saved news at entry
            'training_mode': True/False  # If True, exclude from training
        }
        """
        if not os.path.exists(trade_log_file):
            logger.warning(f"Trade log file {trade_log_file} not found")
            return None, None, None
        
        with open(trade_log_file, 'r') as f:
            trades = json.load(f)
        
        if len(trades) < self.min_training_samples:
            logger.warning(f"Not enough trades for news impact training: {len(trades)} < {self.min_training_samples}")
            return None, None, None
        
        # For now, we'll use simpler features since news articles aren't saved
        # We'll use entry_news_count and entry_sentiment as proxies
        X = []
        y = []
        texts = []
        excluded_training_mode = 0
        
        for trade in trades:
            status = trade.get('status', 'open')
            
            # Skip open trades
            if status == 'open':
                continue
            
            # Skip trades collected in training mode (psychology data invalid for news impact)
            if trade.get('training_mode', False):
                excluded_training_mode += 1
                continue
            
            # Create synthetic text from available data for training
            news_count = trade.get('entry_news_count', 0)
            sentiment = trade.get('entry_sentiment', 0)
            
            # Simple feature vector based on available data
            features = [
                news_count,
                abs(sentiment),
                sentiment * news_count,  # Interaction term
                1 if sentiment > 0 else 0,  # Positive sentiment flag
                1 if sentiment < 0 else 0,  # Negative sentiment flag
            ]
            
            # Pad to match expected feature count (100 TF-IDF + 5 category + 2 aggregate)
            features.extend([0] * (100 + 5 + 2 - len(features)))
            
            X.append(features)
            
            # Label: 1 if news-driven failure, 0 otherwise
            # This trains the model to predict when news will cause failures
            label = 1 if status == 'loss_news_driven' else 0
            y.append(label)
            
            # Collect text for future TF-IDF training (placeholder)
            texts.append(f"news_count_{news_count} sentiment_{sentiment}")
        
        if excluded_training_mode > 0:
            logger.info(f"Excluded {excluded_training_mode} trades collected in training mode (psychology not used for decisions)")
        
        if len(X) < self.min_training_samples:
            logger.warning(f"Not enough completed trades: {len(X)} < {self.min_training_samples}")
            return None, None, None
        
        return np.array(X), np.array(y), texts
    
    def train(self, trade_log_file='trade_log.json'):
        """Train the news impact model on historical trades"""
        X, y, texts = self.prepare_training_data(trade_log_file)
        
        if X is None or y is None:
            logger.warning("Cannot train news impact model: insufficient data")
            return False
        
        # Fit vectorizer on texts (for future use)
        try:
            self.vectorizer.fit(texts)
        except Exception as e:
            logger.warning(f"Could not fit vectorizer: {e}")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        if len(X) < 10:
            # Too small for split, use all data
            X_train, X_test = X_scaled, X_scaled
            y_train, y_test = y, y
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42,
                stratify=y if len(np.unique(y)) > 1 and min(np.bincount(y)) > 1 else None
            )
        
        # Train ensemble model
        rf = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=42, class_weight='balanced')
        gb = GradientBoostingClassifier(n_estimators=50, max_depth=4, random_state=42)
        
        # Use cross-validation to select best model
        cv_folds = max(2, min(5, len(X_train) // 10))
        try:
            rf_scores = cross_val_score(rf, X_train, y_train, cv=cv_folds, scoring='accuracy')
            gb_scores = cross_val_score(gb, X_train, y_train, cv=cv_folds, scoring='accuracy')
            
            logger.info(f"News Impact RF CV score: {rf_scores.mean():.3f} (+/- {rf_scores.std():.3f})")
            logger.info(f"News Impact GB CV score: {gb_scores.mean():.3f} (+/- {gb_scores.std():.3f})")
            
            # Select best model
            if rf_scores.mean() > gb_scores.mean():
                self.model = rf
                logger.info("Selected Random Forest for news impact prediction")
            else:
                self.model = gb
                logger.info("Selected Gradient Boosting for news impact prediction")
        except Exception as e:
            logger.warning(f"Cross-validation failed: {e}, using Random Forest")
            self.model = rf
        
        # Train on full training set
        self.model.fit(X_train, y_train)
        
        # Evaluate on test set
        if len(X_test) > 0:
            test_score = self.model.score(X_test, y_test)
            logger.info(f"News impact model test accuracy: {test_score:.3f}")
        
        # Save model
        self.save_model()
        
        return True
    
    def predict_news_impact(self, news_articles, symbol=None):
        """
        Predict the impact of current news on trading
        
        Args:
            news_articles: List of news article dicts
            symbol: Optional symbol to consider (future enhancement)
        
        Returns:
            dict with:
                - impact_level: 'high', 'medium', 'low'
                - impact_score: float -1 to 1 (negative = bearish, positive = bullish)
                - confidence: float 0 to 1
                - should_trade: bool
                - suggested_direction: 'long', 'short', or None (None = use technical analysis)
                - ml_prediction: float 0 to 1 (probability of news-driven failure)
                - reason: str explanation
        """
        # Rule-based categorization (always available)
        impact_level, impact_score, base_confidence = self.categorize_news_impact(news_articles)
        
        # ML-based prediction (if model is trained)
        ml_prediction = 0.5
        ml_confidence = base_confidence
        
        if self.model is not None:
            try:
                features = self.extract_news_features(news_articles)
                features_scaled = self.scaler.transform(features)
                
                # Predict probability of news-driven failure
                ml_prediction = self.model.predict_proba(features_scaled)[0][1]
                ml_confidence = abs(ml_prediction - 0.5) * 2
                
                logger.info(f"ML news impact prediction: {ml_prediction:.3f} (confidence: {ml_confidence:.3f})")
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}, using rule-based only")
        
        # Combine rule-based and ML predictions
        combined_confidence = (base_confidence + ml_confidence) / 2
        
        # Adjust impact score based on ML prediction
        if ml_prediction > 0.7:
            # High probability of news-driven failure -> reduce impact score
            impact_score *= 0.5
            impact_level = 'high' if impact_level == 'high' else 'medium'
        
        # Trading decision with directionality
        should_trade = True
        suggested_direction = None  # None = use technical analysis, 'long'/'short' = force direction
        reason = f"News impact: {impact_level} (score: {impact_score:.2f})"
        
        if impact_level == 'high':
            if abs(impact_score) > 0.5:
                # High impact news - use news direction instead of stopping
                if impact_score < -0.5:
                    # Bearish news - suggest shorting
                    suggested_direction = 'short'
                    reason = f"Bearish news impact (score: {impact_score:.2f}) - optimal shorting opportunity"
                elif impact_score > 0.5:
                    # Bullish news - suggest longing  
                    suggested_direction = 'long'
                    reason = f"Bullish news impact (score: {impact_score:.2f}) - optimal longing opportunity"
                else:
                    # Uncertain direction - stop trading
                    should_trade = False
                    reason = f"High news impact but uncertain direction (score: {impact_score:.2f}) - avoiding trade"
            else:
                # Medium-high impact but low score - use technical analysis
                reason = f"Medium-high news impact (score: {impact_score:.2f}) - using technical analysis"
        elif ml_prediction > 0.8:
            # ML predicts high probability of news-driven failure - stop trading
            should_trade = False
            reason = f"ML predicts high probability ({ml_prediction:.2f}) of news-driven failure"
        
        return {
            'impact_level': impact_level,
            'impact_score': impact_score,
            'confidence': combined_confidence,
            'should_trade': should_trade,
            'suggested_direction': suggested_direction,
            'ml_prediction': ml_prediction,
            'reason': reason
        }
    
    def classify_failure_type(self, trade_data, market_data, psychology_data=None):
        """
        Classify if trade failure was analytical or emotional/news-driven
        
        Args:
            trade_data: Dict with trade info (signals, sentiment, etc.)
            market_data: Current market data to compare with expectations
            psychology_data: Optional psychology analysis data
        
        Returns:
            Dict with:
                - failure_type: 'analytical', 'emotional', or 'mixed'
                - confidence: How confident we are in the classification
                - reason: Explanation
                - emotional_factors: List of emotional factors if applicable
                - analytical_factors: List of analytical factors if applicable
        """
        analytical_factors = []
        emotional_factors = []
        
        # Check if technical indicators failed
        direction = trade_data.get('direction')
        signals = {
            'rsi': trade_data.get('rsi_signal', 0),
            'macd': trade_data.get('macd_signal', 0),
            'bb': trade_data.get('bb_signal', 0),
            'trend': trade_data.get('trend_signal', 0),
            'stoch': trade_data.get('stoch_signal', 0),
            'cci': trade_data.get('cci_signal', 0),
            'adx': trade_data.get('adx_signal', 0),
        }
        
        # Count how many indicators agreed with trade direction
        if direction == 'long':
            agreeing_signals = sum(1 for s in signals.values() if s > 0)
        else:
            agreeing_signals = sum(1 for s in signals.values() if s < 0)
        
        total_signals = len(signals)
        agreement_rate = agreeing_signals / total_signals if total_signals > 0 else 0
        
        # If most indicators were wrong, it's analytical failure
        if agreement_rate < 0.3:
            analytical_factors.append(f"Low indicator agreement: {agreement_rate:.0%}")
        elif agreement_rate > 0.7:
            # Most indicators agreed but still failed - likely emotional override
            analytical_factors.append(f"Strong indicator agreement ({agreement_rate:.0%}) suggests technical setup was good")
        
        # Check sentiment/news factors
        sentiment = trade_data.get('entry_sentiment', 0) or trade_data.get('avg_sentiment', 0)
        news_count = trade_data.get('entry_news_count', 0) or trade_data.get('news_count', 0)
        
        if abs(sentiment) > 0.6 and news_count > 3:
            emotional_factors.append(f"Strong sentiment ({sentiment:.2f}) with high news volume ({news_count})")
        
        # Check psychology data if available
        if psychology_data:
            irrationality = psychology_data.get('irrationality_score', 0)
            fear_greed = psychology_data.get('fear_greed_index', 0)
            emotion = psychology_data.get('dominant_emotion', 'neutral')
            
            if irrationality > 0.6:
                emotional_factors.append(f"High irrationality detected: {irrationality:.2f}")
            
            if abs(fear_greed) > 0.7:
                emotion_type = 'extreme fear' if fear_greed < 0 else 'extreme greed'
                emotional_factors.append(f"{emotion_type.title()} dominated market")
            
            if emotion in ['panic', 'euphoria']:
                emotional_factors.append(f"{emotion.title()} emotion detected")
        
        # Check for news-driven volatility
        volatility = trade_data.get('volatility_hourly', 0)
        atr_pct = trade_data.get('atr_pct', 0)
        
        if volatility > 0.015 or atr_pct > 0.01:
            emotional_factors.append(f"High volatility suggests emotional/news-driven moves")
        
        # Classify based on factors
        emotional_score = len(emotional_factors)
        analytical_score = len(analytical_factors)
        
        if emotional_score > analytical_score * 2:
            failure_type = 'emotional'
            confidence = min(0.9, 0.5 + emotional_score * 0.1)
            reason = "Trade failure primarily due to emotional/news-driven market behavior"
        elif analytical_score > emotional_score * 2:
            failure_type = 'analytical'
            confidence = min(0.9, 0.5 + analytical_score * 0.1)
            reason = "Trade failure primarily due to incorrect technical analysis"
        else:
            failure_type = 'mixed'
            confidence = 0.6
            reason = "Trade failure due to combination of analytical and emotional factors"
        
        return {
            'failure_type': failure_type,
            'confidence': confidence,
            'reason': reason,
            'emotional_factors': emotional_factors,
            'analytical_factors': analytical_factors,
            'emotional_score': emotional_score,
            'analytical_score': analytical_score
        }


# Global news impact predictor instance
_news_impact_predictor = None

def get_news_impact_predictor():
    """Get or create global news impact predictor instance"""
    global _news_impact_predictor
    if _news_impact_predictor is None:
        _news_impact_predictor = NewsImpactPredictor()
    return _news_impact_predictor
