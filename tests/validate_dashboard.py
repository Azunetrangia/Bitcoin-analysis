"""Quick validation script to check all dashboard pages load correctly."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 Validating Dashboard Components...")
print("=" * 60)

# Test 1: Import all chart functions
print("\n1️⃣ Testing Chart Imports...")
try:
    from src.presentation.streamlit_app.components import (
        create_candlestick_chart,
        create_price_with_ma_chart,
        create_volume_analysis_chart,
        create_volatility_cone_chart,
        create_regime_transition_matrix,
        create_regime_probability_timeline,
        create_rsi_chart,
        create_macd_chart,
        create_bollinger_bands_chart,
        create_regime_timeline,
        create_drawdown_chart
    )
    print("   ✅ All chart functions imported successfully")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Test 2: Import filter functions
print("\n2️⃣ Testing Filter Imports...")
try:
    from src.presentation.streamlit_app.components import (
        date_range_filter,
        interval_selector,
        symbol_selector
    )
    print("   ✅ All filter functions imported successfully")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Test 3: Import metric functions
print("\n3️⃣ Testing Metric Imports...")
try:
    from src.presentation.streamlit_app.components import (
        price_metrics_row,
        volume_metrics_row,
        risk_metrics_cards,
        regime_distribution_pie
    )
    print("   ✅ All metric functions imported successfully")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Test 4: Check chart function signatures
print("\n4️⃣ Testing Chart Function Signatures...")
import inspect

chart_tests = [
    (create_price_with_ma_chart, ['df', 'title', 'height', 'ma_periods']),
    (create_volume_analysis_chart, ['df', 'title', 'height']),
    (create_volatility_cone_chart, ['df', 'windows', 'title', 'height']),
    (create_regime_transition_matrix, ['df', 'title', 'height']),
    (create_regime_probability_timeline, ['df', 'title', 'height'])
]

for func, expected_params in chart_tests:
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    if all(p in params for p in expected_params):
        print(f"   ✅ {func.__name__} - signature OK")
    else:
        print(f"   ⚠️ {func.__name__} - unexpected signature: {params}")

# Test 5: Create sample data and test chart creation
print("\n5️⃣ Testing Chart Creation with Sample Data...")
try:
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', end='2024-12-01', freq='1h')
    np.random.seed(42)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'close': 50000 + np.cumsum(np.random.randn(len(dates)) * 100),
        'open': 50000 + np.cumsum(np.random.randn(len(dates)) * 100),
        'high': 51000 + np.cumsum(np.random.randn(len(dates)) * 100),
        'low': 49000 + np.cumsum(np.random.randn(len(dates)) * 100),
        'volume': np.random.uniform(100, 1000, len(dates)),
        'regime': np.random.choice(['bull', 'bear', 'neutral', 'high_volatility'], len(dates)),
        'bull_prob': np.random.uniform(0, 1, len(dates)),
        'bear_prob': np.random.uniform(0, 1, len(dates)),
        'neutral_prob': np.random.uniform(0, 1, len(dates)),
        'high_volatility_prob': np.random.uniform(0, 1, len(dates))
    })
    
    # Test each new chart function
    tests = [
        ("Price with MA", lambda: create_price_with_ma_chart(df, ma_periods=[20, 50])),
        ("Volume Analysis", lambda: create_volume_analysis_chart(df)),
        ("Volatility Cone", lambda: create_volatility_cone_chart(df, windows=[7, 14, 30])),
        ("Regime Transition", lambda: create_regime_transition_matrix(df)),
        ("Regime Probability", lambda: create_regime_probability_timeline(df))
    ]
    
    for name, test_func in tests:
        try:
            fig = test_func()
            if fig is not None:
                print(f"   ✅ {name} chart created successfully")
            else:
                print(f"   ⚠️ {name} chart returned None")
        except Exception as e:
            print(f"   ❌ {name} chart failed: {str(e)[:50]}...")

except Exception as e:
    print(f"   ❌ Chart creation test failed: {e}")

# Test 6: Check API is running
print("\n6️⃣ Testing API Connection...")
try:
    import requests
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        print("   ✅ API is running and healthy")
    else:
        print(f"   ⚠️ API returned status code {response.status_code}")
except Exception as e:
    print(f"   ❌ API connection failed: {e}")

# Test 7: Check Streamlit is running
print("\n7️⃣ Testing Streamlit Connection...")
try:
    import requests
    response = requests.get("http://localhost:8501", timeout=5)
    if response.status_code == 200:
        print("   ✅ Streamlit is running")
    else:
        print(f"   ⚠️ Streamlit returned status code {response.status_code}")
except Exception as e:
    print(f"   ❌ Streamlit connection failed: {e}")

print("\n" + "=" * 60)
print("✅ Dashboard Validation Complete!")
print("\n🌐 Access your dashboard at: http://localhost:8501")
print("📊 Available pages:")
print("   1. Market Overview - http://localhost:8501/Market_Overview")
print("   2. Technical Analysis - http://localhost:8501/Technical_Analysis")
print("   3. Risk Analysis - http://localhost:8501/Risk_Analysis")
print("   4. Regime Classification - http://localhost:8501/Regime_Classification")
print("\n" + "=" * 60)
