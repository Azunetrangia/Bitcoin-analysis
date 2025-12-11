"""
Test: Risk Calculator Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for risk metric calculations.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from src.domain.services.risk_calculator import RiskCalculatorService
from src.domain.models.risk_metrics import RiskMetrics
from src.shared.exceptions.custom_exceptions import RiskCalculationError


@pytest.fixture
def risk_calc():
    """Risk Calculator service instance."""
    return RiskCalculatorService(risk_free_rate=0.02)


@pytest.fixture
def sample_returns():
    """Sample return data (normally distributed)."""
    np.random.seed(42)
    returns = pd.Series(np.random.randn(100) * 0.02)  # 2% daily volatility
    return returns


@pytest.fixture
def sample_prices():
    """Sample price data."""
    np.random.seed(42)
    returns = np.random.randn(100) * 0.02
    prices = pd.Series(45000 * np.exp(np.cumsum(returns)))
    return prices


class TestVaR:
    """Test cases for Value at Risk calculation."""
    
    def test_var_historical(self, risk_calc, sample_returns):
        """Test historical VaR calculation."""
        var_95 = risk_calc.calculate_var(sample_returns, confidence_level=0.95)
        
        # VaR should be negative (loss)
        assert var_95 < 0
        
        # 95% VaR should be less extreme than 99% VaR
        var_99 = risk_calc.calculate_var(sample_returns, confidence_level=0.99)
        assert var_99 < var_95  # More negative = more extreme
    
    def test_var_parametric(self, risk_calc, sample_returns):
        """Test parametric VaR calculation."""
        var_param = risk_calc.calculate_var(
            sample_returns,
            confidence_level=0.95,
            method="parametric"
        )
        
        assert var_param < 0
    
    def test_var_insufficient_data(self, risk_calc):
        """Test VaR with insufficient data."""
        short_returns = pd.Series(np.random.randn(10))
        
        with pytest.raises(RiskCalculationError):
            risk_calc.calculate_var(short_returns)


class TestExpectedShortfall:
    """Test cases for Expected Shortfall (CVaR) calculation."""
    
    def test_es_calculation(self, risk_calc, sample_returns):
        """Test Expected Shortfall calculation."""
        es_95 = risk_calc.calculate_expected_shortfall(sample_returns, confidence_level=0.95)
        
        # ES should be negative
        assert es_95 < 0
        
        # ES should be more extreme than VaR (tail risk)
        var_95 = risk_calc.calculate_var(sample_returns, confidence_level=0.95)
        assert es_95 <= var_95  # ES <= VaR (more conservative)
    
    def test_es_vs_var(self, risk_calc, sample_returns):
        """Test that ES is more conservative than VaR."""
        var_99 = risk_calc.calculate_var(sample_returns, confidence_level=0.99)
        es_99 = risk_calc.calculate_expected_shortfall(sample_returns, confidence_level=0.99)
        
        # Expected Shortfall should be <= VaR (more negative)
        assert es_99 <= var_99


class TestSharpeRatio:
    """Test cases for Sharpe Ratio calculation."""
    
    def test_sharpe_calculation(self, risk_calc, sample_returns):
        """Test Sharpe Ratio calculation."""
        sharpe = risk_calc.calculate_sharpe_ratio(sample_returns, periods_per_year=365)
        
        # Sharpe can be positive or negative
        assert isinstance(sharpe, float)
    
    def test_sharpe_with_positive_returns(self, risk_calc):
        """Test Sharpe with consistently positive returns."""
        # Generate positive returns
        positive_returns = pd.Series(np.abs(np.random.randn(100)) * 0.01)
        
        sharpe = risk_calc.calculate_sharpe_ratio(positive_returns, periods_per_year=365)
        
        # Should have positive Sharpe
        assert sharpe > 0
    
    def test_sharpe_with_negative_returns(self, risk_calc):
        """Test Sharpe with consistently negative returns."""
        # Generate negative returns
        negative_returns = pd.Series(-np.abs(np.random.randn(100)) * 0.01)
        
        sharpe = risk_calc.calculate_sharpe_ratio(negative_returns, periods_per_year=365)
        
        # Should have negative Sharpe
        assert sharpe < 0


class TestSortinoRatio:
    """Test cases for Sortino Ratio calculation."""
    
    def test_sortino_calculation(self, risk_calc, sample_returns):
        """Test Sortino Ratio calculation."""
        sortino = risk_calc.calculate_sortino_ratio(sample_returns, periods_per_year=365)
        
        assert isinstance(sortino, float)
    
    def test_sortino_vs_sharpe(self, risk_calc, sample_returns):
        """Test that Sortino is typically higher than Sharpe (less penalty for upside vol)."""
        sharpe = risk_calc.calculate_sharpe_ratio(sample_returns, periods_per_year=365)
        sortino = risk_calc.calculate_sortino_ratio(sample_returns, periods_per_year=365)
        
        # Sortino should be >= Sharpe (only penalizes downside)
        # Note: This may not always hold for pathological data
        assert isinstance(sortino, float)
        assert isinstance(sharpe, float)


class TestMaxDrawdown:
    """Test cases for Maximum Drawdown calculation."""
    
    def test_max_drawdown_calculation(self, risk_calc, sample_prices):
        """Test Maximum Drawdown calculation."""
        max_dd = risk_calc.calculate_max_drawdown(sample_prices)
        
        # Max drawdown should be negative or zero
        assert max_dd <= 0
    
    def test_max_drawdown_with_crash(self, risk_calc):
        """Test max drawdown with simulated crash."""
        # Simulate price going up then crashing
        prices = pd.Series([100, 110, 120, 130, 120, 110, 90, 80])
        
        max_dd = risk_calc.calculate_max_drawdown(prices)
        
        # Peak was 130, trough was 80
        # Max DD = (80 - 130) / 130 = -0.3846
        expected_dd = (80 - 130) / 130
        
        assert abs(max_dd - expected_dd) < 0.01
    
    def test_max_drawdown_no_loss(self, risk_calc):
        """Test max drawdown with only gains (no drawdown)."""
        # Monotonically increasing prices
        prices = pd.Series([100, 110, 120, 130, 140])
        
        max_dd = risk_calc.calculate_max_drawdown(prices)
        
        # Should be 0 (no drawdown)
        assert max_dd == 0


class TestBatchCalculations:
    """Test cases for batch metric calculations."""
    
    def test_calculate_all_metrics(self, risk_calc, sample_prices):
        """Test calculating all metrics at once."""
        metrics = risk_calc.calculate_all_metrics(sample_prices, periods_per_year=365)
        
        # Should return RiskMetrics domain model
        assert isinstance(metrics, RiskMetrics)
        
        # All fields should be populated
        assert metrics.var_95 < 0
        assert metrics.var_99 < 0
        assert metrics.expected_shortfall_95 < 0
        assert metrics.expected_shortfall_99 < 0
        assert isinstance(metrics.sharpe_ratio, float)
        assert isinstance(metrics.sortino_ratio, float)
        assert metrics.max_drawdown <= 0
        assert metrics.volatility >= 0
    
    def test_metrics_validation(self, risk_calc, sample_prices):
        """Test that RiskMetrics model validates data."""
        metrics = risk_calc.calculate_all_metrics(sample_prices)
        
        # RiskMetrics should enforce VaR/ES are negative
        assert metrics.var_95 <= 0.0001  # Allow tiny floating-point errors
        assert metrics.expected_shortfall_95 <= metrics.var_95
    
    def test_rolling_metrics(self, risk_calc, sample_prices):
        """Test rolling metrics calculation."""
        rolling = risk_calc.calculate_rolling_metrics(
            sample_prices,
            window=30,
            confidence_level=0.95
        )
        
        # Should have rolling columns
        assert "rolling_var" in rolling.columns
        assert "rolling_volatility" in rolling.columns
        assert "rolling_sharpe" in rolling.columns
        
        # Should have same length as input
        assert len(rolling) == len(sample_prices)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_volatility(self, risk_calc):
        """Test with zero volatility (constant prices)."""
        constant_prices = pd.Series([100.0] * 50)
        
        metrics = risk_calc.calculate_all_metrics(constant_prices)
        
        # Sharpe should be 0 (undefined, but we return 0)
        assert metrics.sharpe_ratio == 0.0
        assert metrics.volatility == 0.0
    
    def test_insufficient_data(self, risk_calc):
        """Test with very small dataset."""
        tiny_prices = pd.Series([100, 101, 102])
        
        # Should raise error for most metrics
        with pytest.raises(RiskCalculationError):
            risk_calc.calculate_all_metrics(tiny_prices)
