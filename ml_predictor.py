"""
Machine Learning Predictor for Forex Trading
Uses scikit-learn to predict trade outcomes based on technical indicators
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
import joblib
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLTradingPredictor:
    """Machine learning predictor for trading decisions"""
    
    # Class constants for feature extraction
    SUPPORT_DISTANCE_MULTIPLIER = 0.98
    RESISTANCE_DISTANCE_MULTIPLIER = 1.02
    
    def __init__(self, model_path='ml_model.pkl', scaler_path='ml_scaler.pkl'):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'sentiment', 'news_count', 'rsi_signal', 'macd_signal', 'bb_signal',
            'trend_signal', 'advanced_candle_signal', 'obv_signal', 'fvg_signal',
            'vwap_signal', 'stoch_signal', 'cci_signal', 'hurst_signal',
            'adx_signal', 'williams_r_signal', 'sar_signal', 'volatility',
            'atr_pct', 'distance_to_support', 'distance_to_resistance',
            'distance_to_pivot', 'llm_confidence', 'llm_market_impact'
        ]
        self.min_training_samples = 50
        self.load_model()
    
    def load_model(self):
        """Load trained model and scaler from disk"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("ML model and scaler loaded successfully")
                return True
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
        return False
    
    def save_model(self):
        """Save trained model and scaler to disk"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("ML model and scaler saved successfully")
            return True
        except Exception as e:
            logger.error(f"Could not save model: {e}")
            return False
    
    def extract_features(self, trade_data):
        """Extract features from trade data for ML prediction"""
        features = []
        
        # Sentiment features
        features.append(trade_data.get('avg_sentiment', 0.0))
        features.append(trade_data.get('news_count', 0))
        
        # Technical indicator signals
        features.append(trade_data.get('rsi_signal', 0))
        features.append(trade_data.get('macd_signal', 0))
        features.append(trade_data.get('bb_signal', 0))
        features.append(trade_data.get('trend_signal', 0))
        features.append(trade_data.get('advanced_candle_signal', 0))
        features.append(trade_data.get('obv_signal', 0))
        features.append(trade_data.get('fvg_signal', 0))
        features.append(trade_data.get('vwap_signal', 0))
        features.append(trade_data.get('stoch_signal', 0))
        features.append(trade_data.get('cci_signal', 0))
        features.append(trade_data.get('hurst_signal', 0))
        features.append(trade_data.get('adx_signal', 0))
        features.append(trade_data.get('williams_r_signal', 0))
        features.append(trade_data.get('sar_signal', 0))
        
        # Market conditions
        features.append(trade_data.get('volatility_hourly', 0.01))
        features.append(trade_data.get('atr_pct', 0.005))
        
        # Price position relative to key levels
        price = trade_data.get('price', 1.0)
        support = trade_data.get('support', price * self.SUPPORT_DISTANCE_MULTIPLIER)
        resistance = trade_data.get('resistance', price * self.RESISTANCE_DISTANCE_MULTIPLIER)
        pivot = trade_data.get('pivot', price)
        
        features.append((price - support) / price if price > 0 else 0)
        features.append((resistance - price) / price if price > 0 else 0)
        features.append((price - pivot) / price if price > 0 else 0)
        
        # LLM features (if available)
        features.append(trade_data.get('llm_confidence', 0.0))
        
        # Convert market impact to numerical: high=1.0, medium=0.5, low=0.0
        llm_analysis = trade_data.get('llm_analysis', {})
        market_impact = llm_analysis.get('market_impact', 'low') if llm_analysis else 'low'
        impact_value = {'high': 1.0, 'medium': 0.5, 'low': 0.0}.get(market_impact, 0.0)
        features.append(impact_value)
        
        return np.array(features).reshape(1, -1)
    
    def prepare_training_data(self, trade_log_file='trade_log.json'):
        """Prepare training data from historical trades"""
        if not os.path.exists(trade_log_file):
            logger.warning(f"Trade log file {trade_log_file} not found")
            return None, None
        
        with open(trade_log_file, 'r') as f:
            trades = json.load(f)
        
        if len(trades) < self.min_training_samples:
            logger.warning(f"Not enough trades for training: {len(trades)} < {self.min_training_samples}")
            return None, None
        
        X = []
        y = []
        
        for trade in trades:
            # Skip open trades
            if trade.get('status') == 'open':
                continue
            
            # Extract features
            features = self.extract_features(trade)
            X.append(features[0])
            
            # Label: 1 for win, 0 for loss
            label = 1 if trade.get('status') == 'win' else 0
            y.append(label)
        
        if len(X) < self.min_training_samples:
            logger.warning(f"Not enough completed trades: {len(X)} < {self.min_training_samples}")
            return None, None
        
        return np.array(X), np.array(y)
    
    def train(self, trade_log_file='trade_log.json'):
        """Train the ML model on historical trades"""
        X, y = self.prepare_training_data(trade_log_file)
        
        if X is None or y is None:
            logger.warning("Cannot train model: insufficient data")
            return False
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, 
            stratify=y if len(np.unique(y)) > 1 and min(np.bincount(y)) > 1 else None
        )
        
        # Train ensemble model (Random Forest + Gradient Boosting)
        rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced')
        gb = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
        
        # Use cross-validation to select best model
        cv_folds = max(2, min(5, len(X_train) // 10))
        rf_scores = cross_val_score(rf, X_train, y_train, cv=cv_folds, scoring='accuracy')
        gb_scores = cross_val_score(gb, X_train, y_train, cv=cv_folds, scoring='accuracy')
        
        logger.info(f"Random Forest CV score: {rf_scores.mean():.3f} (+/- {rf_scores.std():.3f})")
        logger.info(f"Gradient Boosting CV score: {gb_scores.mean():.3f} (+/- {gb_scores.std():.3f})")
        
        # Select best model
        if rf_scores.mean() > gb_scores.mean():
            self.model = rf
            logger.info("Selected Random Forest as primary model")
        else:
            self.model = gb
            logger.info("Selected Gradient Boosting as primary model")
        
        # Train on full training set
        self.model.fit(X_train, y_train)
        
        # Evaluate on test set
        test_score = self.model.score(X_test, y_test)
        logger.info(f"Test accuracy: {test_score:.3f}")
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            feature_importance = sorted(zip(self.feature_names, importances), key=lambda x: x[1], reverse=True)
            logger.info("Top 5 most important features:")
            for name, importance in feature_importance[:5]:
                logger.info(f"  {name}: {importance:.3f}")
        
        # Save model
        self.save_model()
        
        return True
    
    def predict(self, trade_data):
        """Predict trade outcome probability"""
        if self.model is None:
            logger.warning("Model not trained yet. Attempting to train...")
            if not self.train():
                logger.warning("Cannot make prediction: model not available")
                return 0.5  # Neutral prediction
        
        try:
            # Extract and scale features
            features = self.extract_features(trade_data)
            features_scaled = self.scaler.transform(features)
            
            # Predict probability of winning trade
            prob = self.model.predict_proba(features_scaled)[0][1]
            
            return prob
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 0.5  # Neutral prediction on error
    
    def predict_with_confidence(self, trade_data):
        """Predict with confidence score"""
        prob = self.predict(trade_data)
        
        # Confidence is distance from 0.5 (neutral)
        confidence = abs(prob - 0.5) * 2
        
        return prob, confidence
    
    def should_trade(self, trade_data, min_confidence=0.6, min_probability=0.55):
        """Determine if trade should be taken based on ML prediction"""
        prob, confidence = self.predict_with_confidence(trade_data)
        
        # Trade only if:
        # 1. Probability of success is above threshold
        # 2. Model is confident in prediction
        should_trade = prob >= min_probability and confidence >= min_confidence
        
        return should_trade, prob, confidence


# Global ML predictor instance
_ml_predictor = None

def get_ml_predictor():
    """Get or create global ML predictor instance"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLTradingPredictor()
    return _ml_predictor
