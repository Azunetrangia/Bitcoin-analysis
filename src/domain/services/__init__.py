"""
Domain Services
~~~~~~~~~~~~~~~

Business logic that doesn't naturally fit within entities.

Services:
- RegimeClassifier: GMM + HMM for market regime classification
- TechnicalAnalysis: Calculate technical indicators
- RiskCalculator: Compute VaR, ES, Sharpe, Sortino ratios
- VolatilityForecaster: GARCH models for volatility prediction
- InvestmentAdvisor: Multi-factor investment decision engine
"""

from src.domain.services.technical_analysis import TechnicalAnalysisService
from src.domain.services.risk_calculator import RiskCalculatorService
from src.domain.services.regime_classifier import RegimeClassifierService
from src.domain.services.investment_advisor import InvestmentAdvisorService

__all__ = [
    "TechnicalAnalysisService",
    "RiskCalculatorService",
    "RegimeClassifierService",
    "InvestmentAdvisorService",
]
