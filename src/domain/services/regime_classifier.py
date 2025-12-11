"""
Regime Classifier Service
~~~~~~~~~~~~~~~~~~~~~~~~~

Domain service for market regime classification using:
- Gaussian Mixture Model (GMM) for soft clustering
- Hidden Markov Model (HMM) for temporal smoothing

This is the core analytical component of the system.

Regimes:
1. BULL: Upward trending, positive momentum
2. BEAR: Downward trending, negative momentum  
3. NEUTRAL: Sideways, low momentum
4. HIGH_VOLATILITY: High volatility regardless of direction
"""

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from hmmlearn import hmm
from typing import Dict, List, Tuple
from datetime import datetime

from src.domain.models.market_regime import MarketRegime, RegimeType, RegimeTransition
from src.domain.services.technical_analysis import TechnicalAnalysisService
from src.shared.exceptions.custom_exceptions import RegimeClassificationError
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class RegimeClassifierService:
    """
    Domain service for market regime classification.
    
    This service combines unsupervised learning (GMM) with temporal modeling (HMM)
    to classify market regimes with temporal consistency.
    
    Architecture:
    1. Extract features (returns, volatility, RSI, etc.)
    2. Fit GMM to identify distinct regimes
    3. Apply HMM to smooth regime transitions (prevent flickering)
    4. Map clusters to regime types based on characteristics
    """
    
    def __init__(
        self,
        n_regimes: int = 4,
        n_hmm_states: int = 4,
        random_state: int = 42
    ):
        """
        Initialize Regime Classifier.
        
        Args:
            n_regimes: Number of GMM clusters (default 4: Bull/Bear/Neutral/HighVol)
            n_hmm_states: Number of HMM states (default 4, same as GMM)
            random_state: Random seed for reproducibility
        """
        self.n_regimes = n_regimes
        self.n_hmm_states = n_hmm_states
        self.random_state = random_state
        
        # Models (will be fitted)
        self.gmm: GaussianMixture | None = None
        self.hmm_model: hmm.GaussianHMM | None = None
        self.scaler: StandardScaler = StandardScaler()
        
        # Feature engineering
        self.ta_service = TechnicalAnalysisService()
        
        # Cluster-to-regime mapping (learned after fitting)
        self.cluster_to_regime: Dict[int, RegimeType] | None = None
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features for regime classification.
        
        This delegates to TechnicalAnalysisService for consistency.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Feature DataFrame with columns:
            - returns, volatility, rsi, macd_histogram, atr_normalized, volume_change
        """
        return self.ta_service.extract_features_for_regime_classification(df)
    
    def fit(self, df: pd.DataFrame) -> "RegimeClassifierService":
        """
        Fit GMM and HMM models on historical data.
        
        This is a training step that must be run before classification.
        
        Args:
            df: OHLCV DataFrame with sufficient history (recommend 3+ years)
            
        Returns:
            Self (for method chaining)
            
        Raises:
            RegimeClassificationError: If fitting fails
            
        Example:
            >>> classifier = RegimeClassifierService()
            >>> classifier.fit(historical_df)
            >>> regime = classifier.classify_latest(new_df)
        """
        try:
            logger.info(f"🔧 Starting regime classifier training", rows=len(df))
            
            # 1. Extract features
            features = self.extract_features(df)
            
            if len(features) < 100:
                raise RegimeClassificationError(
                    f"Insufficient data for training (need 100+, got {len(features)})"
                )
            
            # 2. Standardize features
            features_scaled = self.scaler.fit_transform(features)
            
            # 3. Fit GMM
            logger.info(f"Training GMM with {self.n_regimes} components")
            self.gmm = GaussianMixture(
                n_components=self.n_regimes,
                covariance_type="full",  # Full covariance for flexibility
                random_state=self.random_state,
                max_iter=200,
                n_init=10,  # Try 10 different initializations
            )
            
            gmm_labels = self.gmm.fit_predict(features_scaled)
            
            # 4. Fit HMM for temporal smoothing
            logger.info(f"Training HMM with {self.n_hmm_states} states")
            self.hmm_model = hmm.GaussianHMM(
                n_components=self.n_hmm_states,
                covariance_type="full",
                random_state=self.random_state,
                n_iter=100,
            )
            
            # Reshape for HMM (expects 2D: [n_samples, n_features])
            self.hmm_model.fit(features_scaled)
            
            # 5. Learn cluster-to-regime mapping
            self.cluster_to_regime = self._map_clusters_to_regimes(
                features, gmm_labels
            )
            
            logger.info(
                f"✅ Regime classifier trained successfully",
                n_regimes=self.n_regimes,
                cluster_mapping=self.cluster_to_regime
            )
            
            return self
            
        except Exception as e:
            raise RegimeClassificationError(
                f"Regime classifier training failed: {str(e)}",
                details={"data_rows": len(df)}
            )
    
    def _map_clusters_to_regimes(
        self,
        features: pd.DataFrame,
        labels: np.ndarray
    ) -> Dict[int, RegimeType]:
        """
        Map GMM clusters to regime types based on feature characteristics.
        
        Heuristics:
        - High volatility + any returns → HIGH_VOLATILITY
        - Positive returns + low volatility → BULL
        - Negative returns + low volatility → BEAR
        - Low returns + low volatility → NEUTRAL
        
        Args:
            features: Feature DataFrame
            labels: GMM cluster labels
            
        Returns:
            Dictionary mapping cluster ID → RegimeType
        """
        cluster_stats = {}
        
        for cluster_id in range(self.n_regimes):
            mask = labels == cluster_id
            cluster_data = features[mask]
            
            # Calculate cluster characteristics
            avg_returns = cluster_data["returns"].mean()
            avg_volatility = cluster_data["volatility"].mean()
            avg_rsi = cluster_data["rsi"].mean()
            
            cluster_stats[cluster_id] = {
                "returns": avg_returns,
                "volatility": avg_volatility,
                "rsi": avg_rsi,
                "count": mask.sum(),
            }
        
        # Sort clusters by volatility (descending)
        sorted_clusters = sorted(
            cluster_stats.items(),
            key=lambda x: x[1]["volatility"],
            reverse=True
        )
        
        mapping = {}
        
        for i, (cluster_id, stats) in enumerate(sorted_clusters):
            if i == 0:
                # Highest volatility cluster
                mapping[cluster_id] = RegimeType.HIGH_VOLATILITY
                
            elif stats["returns"] > 0.001:  # Positive returns
                if cluster_id not in mapping:
                    mapping[cluster_id] = RegimeType.BULL
                    
            elif stats["returns"] < -0.001:  # Negative returns
                if cluster_id not in mapping:
                    mapping[cluster_id] = RegimeType.BEAR
                    
            else:  # Near-zero returns
                if cluster_id not in mapping:
                    mapping[cluster_id] = RegimeType.NEUTRAL
        
        # Ensure all clusters are mapped
        unmapped = set(range(self.n_regimes)) - set(mapping.keys())
        for cluster_id in unmapped:
            mapping[cluster_id] = RegimeType.NEUTRAL  # Default
        
        logger.debug(f"Cluster mapping created", mapping=mapping, stats=cluster_stats)
        
        return mapping
    
    def predict_proba(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict regime probabilities for each time step.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with probability columns for each regime
            
        Raises:
            RegimeClassificationError: If model not fitted
        """
        if self.gmm is None or self.hmm_model is None:
            raise RegimeClassificationError(
                "Model not fitted. Call fit() first."
            )
        
        try:
            # Extract and scale features
            features = self.extract_features(df)
            features_scaled = self.scaler.transform(features)
            
            # GMM probabilities
            gmm_proba = self.gmm.predict_proba(features_scaled)
            
            # HMM smoothing
            hmm_proba = self.hmm_model.predict_proba(features_scaled)
            
            # Combine (average of GMM and HMM)
            combined_proba = (gmm_proba + hmm_proba) / 2
            
            # Create DataFrame
            proba_df = pd.DataFrame(
                combined_proba,
                index=features.index,
                columns=[f"cluster_{i}" for i in range(self.n_regimes)]
            )
            
            # Map to regime probabilities
            regime_proba = pd.DataFrame(index=features.index)
            
            for cluster_id, regime in self.cluster_to_regime.items():
                col_name = f"prob_{regime.value}"
                if col_name not in regime_proba.columns:
                    regime_proba[col_name] = 0.0
                
                regime_proba[col_name] += proba_df[f"cluster_{cluster_id}"]
            
            return regime_proba
            
        except Exception as e:
            raise RegimeClassificationError(
                f"Probability prediction failed: {str(e)}",
                details={"data_rows": len(df)}
            )
    
    def classify(self, df: pd.DataFrame) -> List[MarketRegime]:
        """
        Classify market regime for each time step.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            List of MarketRegime objects
            
        Raises:
            RegimeClassificationError: If model not fitted
        """
        if self.cluster_to_regime is None:
            raise RegimeClassificationError(
                "Model not fitted. Call fit() first."
            )
        
        try:
            # Get probabilities
            proba_df = self.predict_proba(df)
            
            # Extract features for context
            features = self.extract_features(df)
            
            # Classify each time step
            regimes = []
            
            for timestamp, probs in proba_df.iterrows():
                # Get regime with highest probability
                regime_probs = {
                    RegimeType.BULL: probs.get("prob_bull", 0.0),
                    RegimeType.BEAR: probs.get("prob_bear", 0.0),
                    RegimeType.NEUTRAL: probs.get("prob_neutral", 0.0),
                    RegimeType.HIGH_VOLATILITY: probs.get("prob_high_volatility", 0.0),
                }
                
                best_regime = max(regime_probs, key=regime_probs.get)
                confidence = regime_probs[best_regime]
                
                # Get features for this timestamp
                feature_values = None
                if timestamp in features.index:
                    feature_values = features.loc[timestamp].to_dict()
                
                regime = MarketRegime(
                    timestamp=timestamp,
                    regime=best_regime,
                    confidence=float(confidence),
                    probabilities=regime_probs,
                    features=feature_values,
                )
                
                regimes.append(regime)
            
            logger.info(f"✅ Classified {len(regimes)} time steps")
            
            return regimes
            
        except Exception as e:
            raise RegimeClassificationError(
                f"Classification failed: {str(e)}",
                details={"data_rows": len(df)}
            )
    
    def classify_latest(self, df: pd.DataFrame) -> MarketRegime:
        """
        Classify the most recent market regime.
        
        Args:
            df: OHLCV DataFrame (last row is most recent)
            
        Returns:
            MarketRegime for latest timestamp
        """
        regimes = self.classify(df)
        return regimes[-1]  # Return last (most recent)
    
    def detect_transitions(
        self,
        regimes: List[MarketRegime]
    ) -> List[RegimeTransition]:
        """
        Detect regime transitions from a regime sequence.
        
        Args:
            regimes: List of MarketRegime objects (time-ordered)
            
        Returns:
            List of RegimeTransition objects
            
        Example:
            >>> regimes = classifier.classify(df)
            >>> transitions = classifier.detect_transitions(regimes)
            >>> for t in transitions:
            >>>     if t.is_significant():
            >>>         print(f"{t.transition_name()} at {t.timestamp}")
        """
        transitions = []
        
        for i in range(1, len(regimes)):
            prev_regime = regimes[i - 1]
            curr_regime = regimes[i]
            
            if prev_regime.regime != curr_regime.regime:
                # Calculate duration of previous regime (in hours)
                # Handle both datetime and numeric timestamps
                if isinstance(curr_regime.timestamp, (int, float)):
                    # Numeric timestamp (e.g., index position)
                    duration = float(curr_regime.timestamp - prev_regime.timestamp)
                else:
                    # Datetime timestamp
                    duration = (curr_regime.timestamp - prev_regime.timestamp).total_seconds() / 3600
                
                transition = RegimeTransition(
                    from_regime=prev_regime.regime,
                    to_regime=curr_regime.regime,
                    timestamp=curr_regime.timestamp,
                    duration=duration,
                )
                
                transitions.append(transition)
        
        logger.debug(f"Detected {len(transitions)} regime transitions")
        
        return transitions
