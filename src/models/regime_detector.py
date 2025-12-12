"""
HMM-based Market Regime Detection
Detects Bull, Bear, and Sideways market states using Hidden Markov Models
"""

import numpy as np
import pandas as pd
from hmmlearn import hmm
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Market regime detector using Gaussian HMM.
    
    States:
    - 0: Bear (negative returns, high volatility)
    - 1: Sideways (low volatility, range-bound)
    - 2: Bull (positive returns, moderate volatility)
    """
    
    def __init__(self, n_states=3, lookback_days=90):
        """
        Initialize regime detector.
        
        Args:
            n_states: Number of hidden states (default 3: Bear/Sideways/Bull)
            lookback_days: Days of history to use for training
        """
        self.n_states = n_states
        self.lookback_days = lookback_days
        self.model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type="diag",  # Changed from "full" to "diag" to prevent singular matrix
            n_iter=100,
            random_state=42
        )
        self.is_trained = False
        self.last_train_time = None
        self.state_labels = {0: "Bear", 1: "Sideways", 2: "Bull"}
        
    def prepare_features(self, df):
        """
        Prepare features for HMM from OHLCV data.
        
        Features:
        - Log returns
        - Volatility (ATR normalized)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            numpy array of shape (n_samples, n_features)
        """
        # Calculate log returns
        df = df.copy()
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # Calculate ATR (Average True Range) for volatility
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Normalize volatility by price
        df['volatility'] = df['atr'] / df['close']
        
        # Drop NaN values
        df = df.dropna()
        
        # Select features
        features = df[['log_return', 'volatility']].values
        
        return features, df.index
    
    def train(self, df):
        """
        Train HMM on historical data.
        
        Args:
            df: DataFrame with OHLCV data (at least lookback_days)
        """
        logger.info(f"Training HMM on {len(df)} candles...")
        
        # Prepare features
        features, _ = self.prepare_features(df)
        
        if len(features) < 50:
            logger.warning(f"Insufficient data for training: {len(features)} samples")
            return False
        
        try:
            # Fit model
            self.model.fit(features)
            self.is_trained = True
            self.last_train_time = datetime.now()
            
            # Log model parameters
            logger.info(f"Training complete. Model converged: {self.model.monitor_.converged}")
            logger.info(f"Mean returns by state: {self.model.means_[:, 0]}")
            logger.info(f"Mean volatility by state: {self.model.means_[:, 1]}")
            
            # Identify states based on mean returns
            self._identify_states()
            
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def _identify_states(self):
        """
        Identify which HMM state corresponds to Bull/Bear/Sideways
        based on mean returns and volatility.
        """
        means = self.model.means_[:, 0]  # Returns
        vols = self.model.means_[:, 1]   # Volatility
        
        # State with most negative return = Bear
        bear_idx = np.argmin(means)
        
        # State with most positive return = Bull
        bull_idx = np.argmax(means)
        
        # Remaining state = Sideways
        sideways_idx = [i for i in range(self.n_states) if i not in [bear_idx, bull_idx]][0]
        
        # Update labels
        self.state_labels = {
            bear_idx: "Bear",
            sideways_idx: "Sideways",
            bull_idx: "Bull"
        }
        
        logger.info(f"State mapping: {self.state_labels}")
    
    def predict_current_regime(self, df):
        """
        Predict current market regime.
        
        Args:
            df: DataFrame with recent OHLCV data
            
        Returns:
            dict with regime info:
            {
                'regime': 'Bull',
                'state': 2,
                'probability': 0.85,
                'all_probs': [0.05, 0.10, 0.85]
            }
        """
        if not self.is_trained:
            return {
                'regime': 'Unknown',
                'state': None,
                'probability': 0.0,
                'all_probs': [0.33, 0.33, 0.34],
                'error': 'Model not trained'
            }
        
        try:
            # Prepare features
            features, _ = self.prepare_features(df)
            
            if len(features) == 0:
                return {
                    'regime': 'Unknown',
                    'state': None,
                    'probability': 0.0,
                    'all_probs': [0.33, 0.33, 0.34],
                    'error': 'Insufficient data'
                }
            
            # Predict state sequence
            states = self.model.predict(features)
            current_state = states[-1]
            
            # Get probability distribution
            probs = self.model.predict_proba(features)
            current_probs = probs[-1]
            
            return {
                'regime': self.state_labels[current_state],
                'state': int(current_state),
                'probability': float(current_probs[current_state]),
                'all_probs': current_probs.tolist(),
                'confidence': 'high' if current_probs[current_state] > 0.7 else 'medium' if current_probs[current_state] > 0.5 else 'low'
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'regime': 'Error',
                'state': None,
                'probability': 0.0,
                'all_probs': [0.0, 0.0, 0.0],
                'error': str(e)
            }
    
    def should_retrain(self, hours=24):
        """
        Check if model should be retrained.
        
        Args:
            hours: Hours since last training
            
        Returns:
            bool
        """
        if not self.is_trained:
            return True
        
        if self.last_train_time is None:
            return True
        
        time_since_train = datetime.now() - self.last_train_time
        return time_since_train > timedelta(hours=hours)


def backtest_regime_detector(df, lookback_days=90):
    """
    Backtest regime detector on historical data.
    
    Args:
        df: DataFrame with OHLCV data
        lookback_days: Training window size
        
    Returns:
        DataFrame with regime predictions
    """
    detector = RegimeDetector(lookback_days=lookback_days)
    
    # Train on first lookback_days
    train_data = df.iloc[:lookback_days * 24]  # Assuming hourly data
    detector.train(train_data)
    
    # Predict on remaining data
    results = []
    for i in range(lookback_days * 24, len(df)):
        # Use sliding window for prediction
        window_data = df.iloc[i-100:i+1]  # Last 100 candles
        prediction = detector.predict_current_regime(window_data)
        
        results.append({
            'timestamp': df.iloc[i]['timestamp'],
            'close': df.iloc[i]['close'],
            'regime': prediction['regime'],
            'probability': prediction['probability']
        })
    
    return pd.DataFrame(results)


if __name__ == "__main__":
    # Test with sample data
    logging.basicConfig(level=logging.INFO)
    
    print("Regime Detector Module")
    print("=" * 50)
    print("Usage:")
    print("  detector = RegimeDetector()")
    print("  detector.train(historical_df)")
    print("  result = detector.predict_current_regime(recent_df)")
