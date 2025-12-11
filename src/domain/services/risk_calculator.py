"""
Risk Calculator Service
~~~~~~~~~~~~~~~~~~~~~~~

Domain service for calculating portfolio risk metrics.

This service implements standard risk management formulas
used in quantitative finance.

Metrics:
- Value at Risk (VaR): Historical and Parametric methods
- Expected Shortfall (Conditional VaR)
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Volatility (annualized)
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import skew, kurtosis
from datetime import datetime
from typing import Dict, Literal, Optional
from src.domain.models.risk_metrics import RiskMetrics
from src.shared.exceptions.custom_exceptions import RiskCalculationError
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class RiskCalculatorService:
    """
    Domain service for risk metric calculations.
    
    This service is stateless and contains pure calculation logic.
    All formulas follow industry-standard risk management practices.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize Risk Calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 0.02 = 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: Literal["historical", "parametric"] = "historical"
    ) -> float:
        """
        Calculate Value at Risk (VaR).
        
        VaR answers: "What is the maximum loss I can expect with X% confidence?"
        
        Args:
            returns: Return series (not prices!)
            confidence_level: Confidence level (0.95 = 95%, 0.99 = 99%)
            method: 
                - 'historical': Use empirical distribution
                - 'parametric': Assume normal distribution
                
        Returns:
            VaR as negative decimal (e.g., -0.05 = 5% loss)
            
        Raises:
            RiskCalculationError: If calculation fails
            
        Example:
            VaR(95%) = -0.03 means "95% confident we won't lose more than 3% in a day"
        """
        try:
            if len(returns) < 30:
                raise RiskCalculationError(
                    "Insufficient data for VaR calculation (need at least 30 observations)"
                )
            
            if method == "historical":
                # Historical VaR: Use empirical quantile
                var = np.percentile(returns.dropna(), (1 - confidence_level) * 100)
                
            elif method == "parametric":
                # Parametric VaR: Assume normal distribution
                mean = returns.mean()
                std = returns.std()
                z_score = stats.norm.ppf(1 - confidence_level)
                var = mean + z_score * std
                
            else:
                raise ValueError(f"Unknown method: {method}")
            
            logger.debug(
                f"VaR calculated",
                confidence=confidence_level,
                method=method,
                var=var
            )
            
            return float(var)
            
        except Exception as e:
            raise RiskCalculationError(
                f"VaR calculation failed: {str(e)}",
                details={
                    "confidence_level": confidence_level,
                    "method": method,
                    "data_length": len(returns)
                }
            )
    
    def calculate_modified_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        Calculate Modified VaR using Cornish-Fisher expansion.
        
        This method adjusts for skewness and kurtosis in the return distribution,
        providing more accurate risk estimates for non-normal distributions like crypto.
        
        Traditional VaR assumes normal distribution, which UNDERESTIMATES tail risk
        in crypto markets that have fat tails (leptokurtosis) and negative skew.
        
        Args:
            returns: Return series
            confidence_level: Confidence level (0.95 = 95%, 0.99 = 99%)
            
        Returns:
            Modified VaR as negative decimal
            
        Formula (Cornish-Fisher Expansion):
            z_CF = z_c + (1/6)(z_c^2 - 1)S + (1/24)(z_c^3 - 3*z_c)(K-3) 
                   - (1/36)(2*z_c^3 - 5*z_c)S^2
            
            Where:
            - z_c: Critical value from standard normal distribution
            - S: Skewness
            - K: Excess Kurtosis
            
        Why This Matters:
            - Negative skew → Higher VaR (more left-tail risk)
            - High kurtosis → Higher VaR (fatter tails, more extreme events)
            - Crypto has both! → Standard VaR is dangerously optimistic
            
        Example:
            Standard VaR(95%) = -2.5%  (assumes normal)
            Modified VaR(95%) = -4.2%  (accounts for fat tails)
            
        References:
            - Cornish & Fisher (1937): "Moments and Cumulants in the Specification of Distributions"
            - JPMorgan (1996): "RiskMetrics Technical Document"
        """
        try:
            if len(returns) < 30:
                raise RiskCalculationError(
                    "Insufficient data for Modified VaR (need at least 30 observations)"
                )
            
            # Calculate distribution moments
            mu = returns.mean()
            sigma = returns.std()
            S = skew(returns.dropna())  # Skewness
            K = kurtosis(returns.dropna(), fisher=True)  # Excess kurtosis (Fisher's definition)
            
            # Standard normal critical value
            z_c = stats.norm.ppf(1 - confidence_level)
            
            # Cornish-Fisher expansion for adjusted z-score
            z_cf = (
                z_c
                + (1/6) * (z_c**2 - 1) * S
                + (1/24) * (z_c**3 - 3*z_c) * K
                - (1/36) * (2*z_c**3 - 5*z_c) * S**2
            )
            
            # Modified VaR
            var_modified = mu + z_cf * sigma
            
            # Standard VaR for comparison
            var_standard = mu + z_c * sigma
            
            logger.info(
                f"📊 Modified VaR calculated",
                confidence=confidence_level,
                skewness=round(S, 3),
                kurtosis=round(K, 3),
                var_standard=round(var_standard, 5),
                var_modified=round(var_modified, 5),
                adjustment_pct=round((var_modified / var_standard - 1) * 100, 1)
            )
            
            return float(var_modified)
            
        except Exception as e:
            raise RiskCalculationError(
                f"Modified VaR calculation failed: {str(e)}",
                details={
                    "confidence_level": confidence_level,
                    "data_length": len(returns)
                }
            )
    
    def calculate_expected_shortfall(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        Calculate Expected Shortfall (ES), also called Conditional VaR (CVaR).
        
        ES answers: "If I experience a loss beyond VaR, what's the average loss?"
        
        ES is a more conservative risk measure than VaR because it considers
        the tail risk (extreme losses).
        
        Args:
            returns: Return series
            confidence_level: Confidence level (0.95 = 95%)
            
        Returns:
            Expected Shortfall as negative decimal
            
        Example:
            ES(95%) = -0.07 means "If we exceed the 95% VaR threshold,
            the average loss is 7%"
        """
        try:
            if len(returns) < 30:
                raise RiskCalculationError(
                    "Insufficient data for ES calculation (need at least 30 observations)"
                )
            
            # Get VaR threshold
            var_threshold = self.calculate_var(returns, confidence_level, method="historical")
            
            # Expected Shortfall = average of returns below VaR
            tail_returns = returns[returns <= var_threshold]
            
            if len(tail_returns) == 0:
                # No observations in tail (very rare)
                es = var_threshold
            else:
                es = tail_returns.mean()
            
            logger.debug(
                f"Expected Shortfall calculated",
                confidence=confidence_level,
                es=es,
                tail_observations=len(tail_returns)
            )
            
            return float(es)
            
        except Exception as e:
            raise RiskCalculationError(
                f"Expected Shortfall calculation failed: {str(e)}",
                details={"confidence_level": confidence_level}
            )
    
    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 365
    ) -> float:
        """
        Calculate Sharpe Ratio (annualized).
        
        Sharpe Ratio measures risk-adjusted return:
        (Return - Risk-Free Rate) / Volatility
        
        Higher Sharpe = Better risk-adjusted performance
        - Sharpe > 1.0: Good
        - Sharpe > 2.0: Very good
        - Sharpe > 3.0: Excellent
        
        Args:
            returns: Daily return series
            periods_per_year: 365 for daily, 8760 for hourly, 252 for trading days
            
        Returns:
            Annualized Sharpe Ratio
            
        Formula:
            Sharpe = (mean_return - risk_free_rate) / std_dev * sqrt(periods_per_year)
        """
        try:
            if len(returns) < 30:
                raise RiskCalculationError(
                    "Insufficient data for Sharpe calculation (need at least 30 observations)"
                )
            
            # Annualized return
            mean_return = returns.mean() * periods_per_year
            
            # Annualized volatility
            volatility = returns.std() * np.sqrt(periods_per_year)
            
            # Sharpe Ratio
            if volatility == 0:
                sharpe = 0.0
            else:
                sharpe = (mean_return - self.risk_free_rate) / volatility
            
            logger.debug(
                f"Sharpe Ratio calculated",
                sharpe=sharpe,
                mean_return=mean_return,
                volatility=volatility
            )
            
            return float(sharpe)
            
        except Exception as e:
            raise RiskCalculationError(
                f"Sharpe Ratio calculation failed: {str(e)}",
                details={"periods_per_year": periods_per_year}
            )
    
    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 365
    ) -> float:
        """
        Calculate Sortino Ratio (annualized).
        
        Similar to Sharpe, but only penalizes downside volatility.
        This is more realistic because upside volatility is desirable.
        
        Args:
            returns: Daily return series
            periods_per_year: 365 for daily, 8760 for hourly
            
        Returns:
            Annualized Sortino Ratio
            
        Formula:
            Sortino = (mean_return - risk_free_rate) / downside_deviation
        """
        try:
            if len(returns) < 30:
                raise RiskCalculationError(
                    "Insufficient data for Sortino calculation (need at least 30 observations)"
                )
            
            # Annualized return
            mean_return = returns.mean() * periods_per_year
            
            # Downside deviation (only negative returns)
            negative_returns = returns[returns < 0]
            
            if len(negative_returns) == 0:
                # No negative returns (unrealistic but handle it)
                downside_deviation = 0.0
            else:
                downside_deviation = negative_returns.std() * np.sqrt(periods_per_year)
            
            # Sortino Ratio
            if downside_deviation == 0:
                sortino = 0.0
            else:
                sortino = (mean_return - self.risk_free_rate) / downside_deviation
            
            logger.debug(
                f"Sortino Ratio calculated",
                sortino=sortino,
                downside_deviation=downside_deviation
            )
            
            return float(sortino)
            
        except Exception as e:
            raise RiskCalculationError(
                f"Sortino Ratio calculation failed: {str(e)}"
            )
    
    def calculate_max_drawdown(self, prices: pd.Series) -> float:
        """
        Calculate Maximum Drawdown.
        
        Max Drawdown measures the largest peak-to-trough decline.
        
        Args:
            prices: Price series (not returns!)
            
        Returns:
            Max drawdown as negative decimal (e.g., -0.25 = 25% drawdown)
            
        Formula:
            Drawdown = (Price - Peak Price) / Peak Price
            Max Drawdown = min(all drawdowns)
            
        Example:
            Price goes from $100 → $150 (peak) → $100
            Max Drawdown = (100 - 150) / 150 = -0.333 = 33.3%
        """
        try:
            if len(prices) < 2:
                raise RiskCalculationError(
                    "Insufficient data for drawdown calculation (need at least 2 observations)"
                )
            
            # Calculate cumulative maximum (rolling peak)
            cumulative_max = prices.expanding().max()
            
            # Calculate drawdown from peak
            drawdown = (prices - cumulative_max) / cumulative_max
            
            # Maximum drawdown (most negative value)
            max_dd = drawdown.min()
            
            logger.debug(f"Max Drawdown calculated", max_dd=max_dd)
            
            return float(max_dd)
            
        except Exception as e:
            raise RiskCalculationError(
                f"Max Drawdown calculation failed: {str(e)}"
            )
    
    def calculate_all_metrics(
        self,
        prices: pd.Series,
        returns: pd.Series | None = None,
        confidence_levels: list[float] = [0.95, 0.99],
        periods_per_year: int = 365
    ) -> RiskMetrics:
        """
        Calculate all risk metrics at once.
        
        Args:
            prices: Price series
            returns: Return series (if None, calculated from prices)
            confidence_levels: List of confidence levels for VaR/ES
            periods_per_year: For annualization (365=daily, 8760=hourly)
            
        Returns:
            RiskMetrics domain model
            
        Example:
            >>> calc = RiskCalculatorService(risk_free_rate=0.02)
            >>> metrics = calc.calculate_all_metrics(df['close'])
            >>> print(f"VaR 95%: {metrics.var_95_percent():.2f}%")
        """
        try:
            # Calculate returns if not provided
            if returns is None:
                returns = prices.pct_change().dropna()
            
            # Calculate all metrics
            var_95 = self.calculate_var(returns, confidence_level=0.95)
            var_99 = self.calculate_var(returns, confidence_level=0.99)
            
            # NEW: Modified VaR with Cornish-Fisher adjustment
            var_95_modified = self.calculate_modified_var(returns, confidence_level=0.95)
            var_99_modified = self.calculate_modified_var(returns, confidence_level=0.99)
            
            es_95 = self.calculate_expected_shortfall(returns, confidence_level=0.95)
            es_99 = self.calculate_expected_shortfall(returns, confidence_level=0.99)
            
            sharpe = self.calculate_sharpe_ratio(returns, periods_per_year)
            sortino = self.calculate_sortino_ratio(returns, periods_per_year)
            
            max_dd = self.calculate_max_drawdown(prices)
            
            # Volatility (annualized)
            volatility = returns.std() * np.sqrt(periods_per_year)
            
            # Mean return (daily)
            mean_return = returns.mean()
            
            # Distribution moments
            skewness = skew(returns.dropna())
            kurt = kurtosis(returns.dropna(), fisher=True)
            
            # Create RiskMetrics domain model
            metrics = RiskMetrics(
                timestamp=datetime.utcnow(),
                var_95=var_95,
                var_99=var_99,
                expected_shortfall_95=es_95,
                expected_shortfall_99=es_99,
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
                max_drawdown=max_dd,
                volatility=float(volatility),
                mean_return=float(mean_return),
                var_95_modified=var_95_modified,
                var_99_modified=var_99_modified,
                skewness=float(skewness),
                kurtosis=float(kurt),
            )
            
            logger.info(
                f"✅ All risk metrics calculated",
                sharpe=sharpe,
                max_dd=max_dd,
                var_95_standard=var_95,
                var_95_modified=var_95_modified,
                skewness=round(skewness, 2),
                kurtosis=round(kurt, 2)
            )
            
            return metrics
            
        except Exception as e:
            raise RiskCalculationError(
                f"Batch risk calculation failed: {str(e)}",
                details={"data_length": len(prices)}
            )
    
    def calculate_rolling_metrics(
        self,
        prices: pd.Series,
        window: int = 30,
        confidence_level: float = 0.95
    ) -> pd.DataFrame:
        """
        Calculate rolling risk metrics over time.
        
        Useful for visualizing how risk evolves.
        
        Args:
            prices: Price series
            window: Rolling window size (e.g., 30 days)
            confidence_level: For VaR/ES
            
        Returns:
            DataFrame with rolling metrics:
            - rolling_var: Rolling VaR
            - rolling_volatility: Rolling volatility
            - rolling_sharpe: Rolling Sharpe Ratio
            
        Example:
            >>> calc = RiskCalculatorService()
            >>> rolling = calc.calculate_rolling_metrics(df['close'], window=30)
            >>> rolling[['rolling_var', 'rolling_sharpe']].plot()
        """
        try:
            returns = prices.pct_change().dropna()
            
            result = pd.DataFrame(index=prices.index)
            
            # Rolling VaR
            result["rolling_var"] = returns.rolling(window).apply(
                lambda x: self.calculate_var(x, confidence_level, method="historical"),
                raw=False
            )
            
            # Rolling volatility (annualized)
            result["rolling_volatility"] = returns.rolling(window).std() * np.sqrt(365)
            
            # Rolling Sharpe
            result["rolling_sharpe"] = returns.rolling(window).apply(
                lambda x: self.calculate_sharpe_ratio(x, periods_per_year=365),
                raw=False
            )
            
            logger.info(
                f"✅ Rolling metrics calculated",
                window=window,
                metrics=len(result.columns)
            )
            
            return result
            
        except Exception as e:
            raise RiskCalculationError(
                f"Rolling metrics calculation failed: {str(e)}",
                details={"window": window}
            )
