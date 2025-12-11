"""
Test Cornish-Fisher VaR Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validates Modified VaR calculation for crypto market conditions.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.domain.services.risk_calculator import RiskCalculatorService


class TestCornishFisherVaR:
    """Test suite for Modified VaR with Cornish-Fisher expansion."""
    
    @pytest.fixture
    def risk_calculator(self):
        """Create risk calculator instance."""
        return RiskCalculatorService(risk_free_rate=0.02)
    
    @pytest.fixture
    def normal_returns(self):
        """Generate normal distribution returns (baseline)."""
        np.random.seed(42)
        return pd.Series(np.random.normal(0.001, 0.02, 1000))
    
    @pytest.fixture
    def crypto_returns(self):
        """
        Generate crypto-like returns with:
        - Negative skew (left tail risk)
        - High kurtosis (fat tails)
        """
        np.random.seed(42)
        # Mix of normal + extreme events
        base = np.random.normal(0.001, 0.02, 1000)
        # Add fat tails (occasional extreme drops)
        extreme_events = np.random.choice([0, -0.1, -0.15], size=1000, p=[0.97, 0.02, 0.01])
        returns = base + extreme_events
        return pd.Series(returns)
    
    def test_modified_var_exists(self, risk_calculator, normal_returns):
        """Test that Modified VaR method exists and runs."""
        var_modified = risk_calculator.calculate_modified_var(
            normal_returns, 
            confidence_level=0.95
        )
        assert var_modified is not None
        assert isinstance(var_modified, float)
        assert var_modified < 0  # VaR should be negative (loss)
    
    def test_modified_var_handles_normal_distribution(self, risk_calculator, normal_returns):
        """
        For normal distribution, Modified VaR should be similar to Standard VaR.
        """
        var_standard = risk_calculator.calculate_var(
            normal_returns, 
            confidence_level=0.95, 
            method="parametric"
        )
        var_modified = risk_calculator.calculate_modified_var(
            normal_returns, 
            confidence_level=0.95
        )
        
        # For normal distribution, adjustment should be minimal (within 10%)
        difference_pct = abs(var_modified / var_standard - 1) * 100
        assert difference_pct < 10, f"Normal distribution adjustment too large: {difference_pct:.1f}%"
        
        print(f"\n📊 Normal Distribution:")
        print(f"   Standard VaR: {var_standard:.4f}")
        print(f"   Modified VaR: {var_modified:.4f}")
        print(f"   Difference: {difference_pct:.2f}%")
    
    def test_modified_var_adjusts_for_fat_tails(self, risk_calculator, crypto_returns):
        """
        For crypto-like returns with fat tails, Modified VaR should be 
        MORE NEGATIVE than Standard VaR (more conservative).
        """
        var_standard = risk_calculator.calculate_var(
            crypto_returns, 
            confidence_level=0.95, 
            method="parametric"
        )
        var_modified = risk_calculator.calculate_modified_var(
            crypto_returns, 
            confidence_level=0.95
        )
        
        # Modified VaR should be more negative (higher risk estimate)
        assert var_modified < var_standard, \
            f"Modified VaR should be more conservative: {var_modified} vs {var_standard}"
        
        # Calculate adjustment percentage
        adjustment_pct = (var_modified / var_standard - 1) * 100
        
        print(f"\n🔴 Crypto-like Distribution (Fat Tails):")
        print(f"   Standard VaR: {var_standard:.4f} ({var_standard*100:.2f}%)")
        print(f"   Modified VaR: {var_modified:.4f} ({var_modified*100:.2f}%)")
        print(f"   Adjustment: {adjustment_pct:+.1f}%")
        print(f"   ⚠️  Standard VaR UNDERESTIMATES risk by {-adjustment_pct:.1f}%!")
    
    def test_modified_var_confidence_levels(self, risk_calculator, crypto_returns):
        """Test Modified VaR at different confidence levels."""
        var_95 = risk_calculator.calculate_modified_var(crypto_returns, 0.95)
        var_99 = risk_calculator.calculate_modified_var(crypto_returns, 0.99)
        
        # 99% VaR should be more extreme than 95% VaR
        assert var_99 < var_95, "99% VaR should be more negative than 95% VaR"
        
        print(f"\n📊 Modified VaR at Different Confidence Levels:")
        print(f"   95% confidence: {var_95:.4f} ({var_95*100:.2f}%)")
        print(f"   99% confidence: {var_99:.4f} ({var_99*100:.2f}%)")
    
    def test_distribution_moments(self, risk_calculator, crypto_returns):
        """
        Test that crypto returns have expected distribution characteristics.
        """
        from scipy.stats import skew, kurtosis
        
        skewness = skew(crypto_returns.dropna())
        kurt = kurtosis(crypto_returns.dropna(), fisher=True)  # Excess kurtosis
        
        print(f"\n📈 Distribution Statistics:")
        print(f"   Skewness: {skewness:.3f}")
        print(f"   Excess Kurtosis: {kurt:.3f}")
        
        # Crypto should have negative skew (left tail risk)
        assert skewness < 0, "Crypto returns should have negative skew"
        
        # Crypto should have high kurtosis (fat tails)
        # Normal distribution has excess kurtosis = 0
        # Crypto typically has excess kurtosis > 3
        assert kurt > 0, "Crypto returns should have positive excess kurtosis"
        
        print(f"   ✅ Negative skew: Left tail risk present")
        print(f"   ✅ High kurtosis: Fat tails detected")
    
    def test_historical_bitcoin_scenario(self, risk_calculator):
        """
        Test with realistic Bitcoin return scenario.
        Simulates 2021 crash conditions.
        """
        # Simulate mixed conditions:
        # - Normal days: small gains/losses
        # - Flash crashes: -10% to -20% drops
        # - Mini-recoveries: +5% to +10% gains
        np.random.seed(123)
        
        returns = []
        for _ in range(365):  # 1 year
            rand = np.random.random()
            if rand < 0.90:  # 90% normal days
                returns.append(np.random.normal(0.002, 0.025))
            elif rand < 0.96:  # 6% crash days
                returns.append(np.random.uniform(-0.15, -0.08))
            else:  # 4% rally days
                returns.append(np.random.uniform(0.05, 0.12))
        
        returns = pd.Series(returns)
        
        var_standard = risk_calculator.calculate_var(returns, 0.95, "parametric")
        var_modified = risk_calculator.calculate_modified_var(returns, 0.95)
        var_historical = risk_calculator.calculate_var(returns, 0.95, "historical")
        
        print(f"\n🪙 Bitcoin Historical Scenario (2021-style):")
        print(f"   Standard VaR (Gaussian): {var_standard:.4f} ({var_standard*100:.2f}%)")
        print(f"   Modified VaR (Cornish-Fisher): {var_modified:.4f} ({var_modified*100:.2f}%)")
        print(f"   Historical VaR (Empirical): {var_historical:.4f} ({var_historical*100:.2f}%)")
        
        # Modified VaR should be closer to Historical VaR than Standard VaR
        error_standard = abs(var_standard - var_historical)
        error_modified = abs(var_modified - var_historical)
        
        print(f"\n   Accuracy comparison:")
        print(f"   Standard VaR error: {error_standard:.4f}")
        print(f"   Modified VaR error: {error_modified:.4f}")
        
        if error_modified < error_standard:
            print(f"   ✅ Modified VaR is MORE ACCURATE!")
    
    def test_insufficient_data_handling(self, risk_calculator):
        """Test that Modified VaR handles insufficient data gracefully."""
        small_sample = pd.Series([0.01, -0.02, 0.015])  # Only 3 observations
        
        with pytest.raises(Exception):  # Should raise RiskCalculationError
            risk_calculator.calculate_modified_var(small_sample, 0.95)
    
    def test_calculate_all_metrics_includes_modified_var(self, risk_calculator, crypto_returns):
        """
        Test that calculate_all_metrics includes Modified VaR in results.
        """
        metrics = risk_calculator.calculate_all_metrics(crypto_returns)
        
        assert metrics.var_95_modified is not None
        assert metrics.var_99_modified is not None
        assert metrics.skewness is not None
        assert metrics.kurtosis is not None
        
        print(f"\n📊 Complete Risk Metrics:")
        print(f"   Standard VaR 95%: {metrics.var_95:.4f}")
        print(f"   Modified VaR 95%: {metrics.var_95_modified:.4f}")
        print(f"   Standard VaR 99%: {metrics.var_99:.4f}")
        print(f"   Modified VaR 99%: {metrics.var_99_modified:.4f}")
        print(f"   Skewness: {metrics.skewness:.3f}")
        print(f"   Kurtosis: {metrics.kurtosis:.3f}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
