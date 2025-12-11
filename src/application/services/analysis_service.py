"""
Analysis Service
~~~~~~~~~~~~~~~~

Application service for market analysis operations.

Responsibilities:
- Calculate technical indicators
- Perform risk analysis
- Classify market regimes
- Provide analysis results

This service orchestrates domain services.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from src.domain.models.market_data import MarketData
from src.domain.services.technical_analysis import TechnicalAnalysisService
from src.domain.services.risk_calculator import RiskCalculatorService
from src.domain.services.regime_classifier import RegimeClassifierService
from src.application.services.market_data_service import MarketDataService
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class AnalysisService:
    """
    Service for market analysis operations.
    
    Orchestrates:
    - Technical Analysis
    - Risk Calculations
    - Regime Classification
    """
    
    def __init__(
        self,
        market_data_service: MarketDataService,
        ta_service: Optional[TechnicalAnalysisService] = None,
        risk_service: Optional[RiskCalculatorService] = None,
        regime_service: Optional[RegimeClassifierService] = None
    ):
        """
        Initialize analysis service.
        
        Args:
            market_data_service: Market data service
            ta_service: Technical analysis service (creates default if None)
            risk_service: Risk calculator service (creates default if None)
            regime_service: Regime classifier service (creates default if None)
        """
        self.market_data_service = market_data_service
        self.ta_service = ta_service or TechnicalAnalysisService()
        self.risk_service = risk_service or RiskCalculatorService()
        self.regime_service = regime_service or RegimeClassifierService()
        
        logger.info("✅ Analysis Service initialized")
    
    def analyze_full_report(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """
        Generate complete analysis report.
        
        Includes:
        - Technical indicators
        - Risk metrics
        - Regime classification
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            Dictionary with complete analysis
            
        Example:
            >>> service = AnalysisService(market_data_service)
            >>> report = service.analyze_full_report(
            ...     'btcusdt', '1h',
            ...     datetime(2024, 1, 1),
            ...     datetime(2024, 12, 31)
            ... )
            >>> print(report['regime']['current_regime'])
        """
        logger.info(
            "📊 Generating full analysis report",
            symbol=symbol,
            interval=interval
        )
        
        # Get market data
        df = self.market_data_service.get_data_as_dataframe(
            symbol, interval, start, end
        )
        
        if df.empty:
            logger.warning("⚠️ No data available")
            return {
                "symbol": symbol,
                "interval": interval,
                "error": "No data available"
            }
        
        # Calculate technical indicators
        df_with_indicators = self.ta_service.calculate_all_indicators(df)
        
        # Calculate risk metrics
        risk_metrics = self.risk_service.calculate_all_metrics(df['close'])
        
        # Classify regime
        regime_features = self.ta_service.extract_features_for_regime_classification(
            df_with_indicators
        )
        
        # Train regime classifier if not fitted
        if not hasattr(self.regime_service, 'is_fitted') or not self.regime_service.is_fitted:
            logger.info("🔧 Training regime classifier...")
            self.regime_service.fit(regime_features)
        
        # Classify current regime
        current_regime = self.regime_service.classify_latest(regime_features)
        regime_probs = self.regime_service.predict_proba(regime_features)
        
        # Detect regime transitions
        regime_history = self.regime_service.classify(regime_features)
        transitions = self.regime_service.detect_transitions(regime_history)
        
        report = {
            "symbol": symbol,
            "interval": interval,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "num_candles": len(df)
            },
            "latest_price": {
                "timestamp": df["timestamp"].iloc[-1].isoformat(),
                "open": float(df["open"].iloc[-1]),
                "high": float(df["high"].iloc[-1]),
                "low": float(df["low"].iloc[-1]),
                "close": float(df["close"].iloc[-1]),
                "volume": float(df["volume"].iloc[-1])
            },
            "technical_indicators": self._get_latest_indicators(df_with_indicators),
            "risk_metrics": risk_metrics,
            "regime": {
                "current_regime": current_regime.regime.value,  # Get enum value
                "confidence": current_regime.confidence,
                "regime_probabilities": {
                    regime.value: prob 
                    for regime, prob in current_regime.probabilities.items()
                },
                "num_transitions": len(transitions),
                "recent_transitions": transitions[-5:] if len(transitions) > 0 else []
            }
        }
        
        logger.info(
            "✅ Analysis report generated",
            current_regime=current_regime.regime.value,
            var_95=risk_metrics.var_95,
            sharpe=risk_metrics.sharpe_ratio
        )
        
        return report
    
    def analyze_technical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Calculate technical indicators only.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            DataFrame with OHLCV + indicators
        """
        logger.info(
            "📈 Calculating technical indicators",
            symbol=symbol,
            interval=interval
        )
        
        df = self.market_data_service.get_data_as_dataframe(
            symbol, interval, start, end
        )
        
        if df.empty:
            logger.warning("⚠️ No data available")
            return pd.DataFrame()
        
        df_with_indicators = self.ta_service.calculate_all_indicators(df)
        
        logger.info(
            f"✅ Calculated indicators for {len(df_with_indicators)} candles"
        )
        
        return df_with_indicators
    
    def analyze_risk(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        confidence_level: float = 0.95
    ) -> Dict[str, float]:
        """
        Calculate risk metrics only.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            confidence_level: Confidence level for VaR/ES
            
        Returns:
            Dictionary with risk metrics
        """
        logger.info(
            "⚠️ Calculating risk metrics",
            symbol=symbol,
            interval=interval
        )
        
        df = self.market_data_service.get_data_as_dataframe(
            symbol, interval, start, end
        )
        
        if df.empty:
            logger.warning("⚠️ No data available")
            return {}
        
        risk_metrics = self.risk_service.calculate_all_metrics(
            df['close'],
            confidence_levels=[confidence_level]
        )
        
        logger.info(
            "✅ Risk metrics calculated",
            var=risk_metrics.var_95,
            sharpe=risk_metrics.sharpe_ratio
        )
        
        return risk_metrics
    
    def classify_regimes(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        retrain: bool = False
    ) -> Dict[str, Any]:
        """
        Classify market regimes.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            retrain: If True, retrain classifier
            
        Returns:
            Dictionary with regime info
        """
        logger.info(
            "🎯 Classifying market regimes",
            symbol=symbol,
            interval=interval
        )
        
        # Get data with indicators
        df = self.analyze_technical(symbol, interval, start, end)
        
        if df.empty:
            logger.warning("⚠️ No data available")
            return {}
        
        # Extract features
        features = self.ta_service.extract_features_for_regime_classification(df)
        
        # Train or use existing model
        if retrain or not hasattr(self.regime_service, 'is_fitted') or not self.regime_service.is_fitted:
            logger.info("🔧 Training regime classifier...")
            self.regime_service.fit(features)
        
        # Classify all periods
        regimes = self.regime_service.classify(features)
        probabilities = self.regime_service.predict_proba(features)
        
        # Get current regime
        current_regime = regimes[-1]
        current_probs = probabilities[-1]
        
        # Detect transitions
        transitions = self.regime_service.detect_transitions(regimes)
        
        result = {
            "symbol": symbol,
            "interval": interval,
            "current_regime": int(current_regime),
            "current_regime_name": self._get_regime_name(current_regime),
            "regime_probabilities": {
                f"regime_{i}": float(prob)
                for i, prob in enumerate(current_probs)
            },
            "regime_history": [int(r) for r in regimes],
            "num_transitions": len(transitions),
            "transitions": transitions,
            "regime_distribution": {
                f"regime_{i}": int((regimes == i).sum())
                for i in range(4)
            }
        }
        
        logger.info(
            "✅ Regime classification complete",
            current_regime=current_regime,
            num_transitions=len(transitions)
        )
        
        return result
    
    def get_regime_stats(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Get statistics for each regime.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            DataFrame with regime statistics
        """
        # Get regimes
        regime_info = self.classify_regimes(symbol, interval, start, end)
        
        if not regime_info:
            return pd.DataFrame()
        
        # Get price data
        df = self.market_data_service.get_data_as_dataframe(
            symbol, interval, start, end
        )
        
        # Add regimes to dataframe
        df["regime"] = regime_info["regime_history"]
        
        # Calculate returns
        df["returns"] = df["close"].pct_change()
        
        # Group by regime and calculate stats
        stats = df.groupby("regime").agg({
            "close": ["count", "mean"],
            "returns": ["mean", "std"],
            "volume": "mean"
        }).reset_index()
        
        stats.columns = [
            "regime",
            "count",
            "avg_price",
            "avg_return",
            "volatility",
            "avg_volume"
        ]
        
        stats["regime_name"] = stats["regime"].apply(self._get_regime_name)
        
        return stats
    
    # ==================== Helper Methods ====================
    
    def _get_latest_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract latest values of all indicators."""
        latest = df.iloc[-1]
        
        indicators = {}
        
        # Price-based
        if "rsi" in df.columns:
            indicators["rsi"] = float(latest["rsi"])
        
        # MACD
        if "macd" in df.columns:
            indicators["macd"] = float(latest["macd"])
            indicators["macd_signal"] = float(latest["macd_signal"])
            indicators["macd_histogram"] = float(latest["macd_histogram"])
        
        # Bollinger Bands
        if "bb_upper" in df.columns:
            indicators["bb_upper"] = float(latest["bb_upper"])
            indicators["bb_middle"] = float(latest["bb_middle"])
            indicators["bb_lower"] = float(latest["bb_lower"])
            indicators["bb_width"] = float(latest["bb_bandwidth"])
        
        # ATR
        if "atr" in df.columns:
            indicators["atr"] = float(latest["atr"])
        
        # Moving Averages
        if "sma_20" in df.columns:
            indicators["sma_20"] = float(latest["sma_20"])
            indicators["ema_20"] = float(latest["ema_20"])
        
        return indicators
    
    def _get_regime_name(self, regime: int) -> str:
        """Get human-readable regime name."""
        regime_names = {
            0: "Low Volatility Bullish",
            1: "High Volatility Bullish",
            2: "Low Volatility Bearish",
            3: "High Volatility Bearish"
        }
        return regime_names.get(regime, f"Unknown ({regime})")
