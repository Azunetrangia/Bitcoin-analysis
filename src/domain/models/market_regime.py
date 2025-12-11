"""
Market Regime Model
~~~~~~~~~~~~~~~~~~~

Domain model for market regime classification results.

Regimes:
- BULL: Upward trending market
- BEAR: Downward trending market
- NEUTRAL: Sideways/ranging market
- HIGH_VOLATILITY: High volatility regime (regardless of direction)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict


class RegimeType(Enum):
    """Market regime types."""
    
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    HIGH_VOLATILITY = "high_volatility"
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> "RegimeType":
        """
        Create RegimeType from string.
        
        Args:
            value: Regime name (case-insensitive)
            
        Returns:
            RegimeType enum
            
        Raises:
            ValueError: If invalid regime name
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = [e.value for e in cls]
            raise ValueError(f"Invalid regime: {value}. Valid options: {valid_values}")


@dataclass(frozen=True)
class MarketRegime:
    """
    Immutable domain model for market regime classification.
    
    Attributes:
        timestamp: Timestamp of classification
        regime: Classified regime type
        confidence: Classification confidence (0-1)
        probabilities: Probability distribution over all regimes
        features: Feature values used for classification
    """
    
    timestamp: datetime
    regime: RegimeType
    confidence: float
    probabilities: Dict[RegimeType, float]
    features: Dict[str, float] | None = None
    
    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
        
        prob_sum = sum(self.probabilities.values())
        if not 0.99 <= prob_sum <= 1.01:  # Allow small floating-point errors
            raise ValueError(f"Probabilities must sum to 1.0, got {prob_sum}")
    
    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """
        Check if classification has high confidence.
        
        Args:
            threshold: Confidence threshold (default 0.7)
            
        Returns:
            True if confidence >= threshold
        """
        return self.confidence >= threshold
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "regime": self.regime.value,
            "confidence": self.confidence,
            "probabilities": {k.value: v for k, v in self.probabilities.items()},
            "features": self.features,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MarketRegime":
        """Create MarketRegime from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            regime=RegimeType.from_string(data["regime"]),
            confidence=data["confidence"],
            probabilities={
                RegimeType.from_string(k): v
                for k, v in data["probabilities"].items()
            },
            features=data.get("features"),
        )


@dataclass
class RegimeTransition:
    """
    Represents a transition between market regimes.
    
    Useful for analyzing regime stability and transition patterns.
    """
    
    from_regime: RegimeType
    to_regime: RegimeType
    timestamp: datetime
    duration: float  # Duration in hours of previous regime
    
    def is_significant(self) -> bool:
        """
        Check if this is a significant regime change.
        
        Returns:
            True if regimes are different
        """
        return self.from_regime != self.to_regime
    
    def transition_name(self) -> str:
        """
        Get human-readable transition name.
        
        Returns:
            Transition description (e.g., "Bull → Bear")
        """
        return f"{self.from_regime.value.title()} → {self.to_regime.value.title()}"
