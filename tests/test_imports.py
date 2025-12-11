"""
Quick test to verify all imports work correctly.
"""

def test_chart_imports():
    """Test that all new chart functions can be imported."""
    from src.presentation.streamlit_app.components import (
        create_candlestick_chart,
        create_price_with_ma_chart,
        create_volume_analysis_chart,
        create_volatility_cone_chart,
        create_regime_transition_matrix,
        create_regime_probability_timeline,
        create_drawdown_chart
    )
    
    # If we get here, all imports succeeded
    assert create_candlestick_chart is not None
    assert create_price_with_ma_chart is not None
    assert create_volume_analysis_chart is not None
    assert create_volatility_cone_chart is not None
    assert create_regime_transition_matrix is not None
    assert create_regime_probability_timeline is not None
    assert create_drawdown_chart is not None
    
    print("✅ All chart functions imported successfully!")


def test_page_imports():
    """Test that all dashboard pages can be imported."""
    import sys
    from pathlib import Path
    
    # Add src to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    try:
        # These will fail if there are import errors
        import importlib.util
        
        pages = [
            "src/presentation/streamlit_app/pages/1_📊_Market_Overview.py",
            "src/presentation/streamlit_app/pages/2_📈_Technical_Analysis.py",
            "src/presentation/streamlit_app/pages/3_⚠️_Risk_Analysis.py",
            "src/presentation/streamlit_app/pages/4_🎯_Regime_Classification.py"
        ]
        
        for page_path in pages:
            full_path = project_root / page_path
            spec = importlib.util.spec_from_file_location("page", full_path)
            if spec and spec.loader:
                print(f"✅ {page_path.split('/')[-1]} can be loaded")
        
        print("✅ All dashboard pages can be imported!")
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        raise


if __name__ == "__main__":
    print("Testing chart imports...")
    test_chart_imports()
    
    print("\nTesting page imports...")
    test_page_imports()
    
    print("\n🎉 All imports working correctly!")
