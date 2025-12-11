"""
Risk Metrics Model
~~~~~~~~~~~~~~~~~~

Domain model for risk analytics calculations.

Metrics:
- Value at Risk (VaR)
- Expected Shortfall (Conditional VaR)
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass(frozen=True)
class RiskMetrics:
    """
    Immutable domain model for portfolio risk metrics.
    
    Attributes:
        timestamp: Calculation timestamp
        var_95: Value at Risk at 95% confidence (daily)
        var_99: Value at Risk at 99% confidence (daily)
        expected_shortfall_95: Expected Shortfall (CVaR) at 95%
        expected_shortfall_99: Expected Shortfall (CVaR) at 99%
        sharpe_ratio: Sharpe Ratio (annualized)
        sortino_ratio: Sortino Ratio (annualized)
        max_drawdown: Maximum Drawdown (decimal, e.g., 0.25 = 25%)
        volatility: Annualized volatility (standard deviation)
        mean_return: Mean daily return
        var_95_modified: Modified VaR using Cornish-Fisher expansion (NEW)
        var_99_modified: Modified VaR at 99% confidence (NEW)
        skewness: Distribution skewness (NEW)
        kurtosis: Distribution kurtosis (NEW)
    """
    
    timestamp: datetime
    var_95: float  # 1-day VaR at 95% confidence (standard)
    var_99: float  # 1-day VaR at 99% confidence (standard)
    expected_shortfall_95: float  # ES at 95%
    expected_shortfall_99: float  # ES at 99%
    sharpe_ratio: float  # Annualized Sharpe
    sortino_ratio: float  # Annualized Sortino
    max_drawdown: float  # Decimal (0.25 = 25% drawdown)
    volatility: float  # Annualized volatility
    mean_return: float  # Mean daily return
    var_95_modified: float = None  # Modified VaR (Cornish-Fisher)
    var_99_modified: float = None  # Modified VaR at 99%
    skewness: float = None  # Distribution skewness
    kurtosis: float = None  # Excess kurtosis
    
    def __post_init__(self) -> None:
        """Validate metrics after initialization."""
        # VaR and ES should be negative (losses)
        if self.var_95 > 0 or self.var_99 > 0:
            # Allow small positive values due to floating-point errors
            if self.var_95 > 0.0001 or self.var_99 > 0.0001:
                raise ValueError("VaR should be negative (representing potential losses)")
        
        if self.expected_shortfall_95 > 0 or self.expected_shortfall_99 > 0:
            if self.expected_shortfall_95 > 0.0001 or self.expected_shortfall_99 > 0.0001:
                raise ValueError("Expected Shortfall should be negative")
        
        # Volatility should be positive
        if self.volatility < 0:
            raise ValueError("Volatility must be non-negative")
        
        # Max drawdown should be non-positive (0 = no drawdown)
        if self.max_drawdown > 0:
            raise ValueError("Max drawdown should be <= 0 (e.g., -0.25 for 25% drawdown)")
    
    def var_95_percent(self) -> float:
        """Get VaR 95% as percentage."""
        return self.var_95 * 100
    
    def var_99_percent(self) -> float:
        """Get VaR 99% as percentage."""
        return self.var_99 * 100
    
    def es_95_percent(self) -> float:
        """Get Expected Shortfall 95% as percentage."""
        return self.expected_shortfall_95 * 100
    
    def es_99_percent(self) -> float:
        """Get Expected Shortfall 99% as percentage."""
        return self.expected_shortfall_99 * 100
    
    def max_drawdown_percent(self) -> float:
        """Get maximum drawdown as percentage."""
        return self.max_drawdown * 100
    
    def risk_adjusted_return(self) -> float:
        """
        Calculate risk-adjusted return (Sharpe * sqrt(volatility)).
        
        Returns:
            Risk-adjusted annual return
        """
        return self.sharpe_ratio * (self.volatility ** 0.5)
    
    def is_high_risk(self, threshold: float = 0.5) -> bool:
        """
        Check if portfolio is in high-risk state.
        
        Args:
            threshold: Annualized volatility threshold
            
        Returns:
            True if volatility > threshold
        """
        return self.volatility > threshold
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "var_95": self.var_95,
            "var_99": self.var_99,
            "expected_shortfall_95": self.expected_shortfall_95,
            "expected_shortfall_99": self.expected_shortfall_99,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "volatility": self.volatility,
            "mean_return": self.mean_return,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RiskMetrics":
        """Create RiskMetrics from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class VolatilityForecast:
    """
    Domain model for volatility forecasting (GARCH output).
    
    Attributes:
        timestamp: Forecast timestamp
        forecast_horizon: Number of periods ahead (e.g., 24 for 24 hours)
        forecasted_volatility: Forecasted volatility values
        confidence_interval: (lower_bound, upper_bound) tuple
    """
    
    timestamp: datetime
    forecast_horizon: int
    forecasted_volatility: list[float]
    confidence_interval: tuple[list[float], list[float]]  # (lower, upper)
    
    def get_point_forecast(self, horizon: int) -> float:
        """
        Get volatility forecast at specific horizon.
        
        Args:
            horizon: Forecast step (0 = next period, 1 = 2 periods ahead, etc.)
            
        Returns:
            Forecasted volatility
            
        Raises:
            IndexError: If horizon exceeds forecast_horizon
        """
        return self.forecasted_volatility[horizon]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "forecast_horizon": self.forecast_horizon,
            "forecasted_volatility": self.forecasted_volatility,
            "confidence_interval": {
                "lower": self.confidence_interval[0],
                "upper": self.confidence_interval[1],
            },
        }
