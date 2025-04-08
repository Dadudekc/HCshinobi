import pytest
import pandas as pd
import numpy as np
from core.indicators.trend_indicators import ADXIndicator

def test_adx_basic_calculation():
    """Test basic ADX calculation with known values."""
    # Create test data with known price movements
    data = pd.DataFrame({
        'high': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        'low': [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        'close': [9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5]
    })
    
    # Initialize ADX with standard parameters
    adx = ADXIndicator(period=5)  # Small period for testing
    result = adx.calculate(data)
    
    # Check that all required columns are present
    assert 'adx' in result.columns
    assert 'plus_di' in result.columns
    assert 'minus_di' in result.columns
    
    # Check that the result has the same length as input
    assert len(result) == len(data)
    
    # Check that there are no NaN values after warmup period
    assert not result.iloc[5:].isna().any().any()
    
    # ADX should be between 0 and 100
    valid_adx = result['adx'].dropna()
    assert (valid_adx >= 0).all() and (valid_adx <= 100).all()
    
    # DI+ and DI- should be between 0 and 100
    assert (result['plus_di'].dropna() >= 0).all() and (result['plus_di'].dropna() <= 100).all()
    assert (result['minus_di'].dropna() >= 0).all() and (result['minus_di'].dropna() <= 100).all()

def test_adx_edge_cases():
    """Test ADX calculation with edge cases."""
    # Test with insufficient data
    data = pd.DataFrame({
        'high': [10, 11],
        'low': [9, 10],
        'close': [9.5, 10.5]
    })
    adx = ADXIndicator(period=14)
    result = adx.calculate(data)
    
    # Should return DataFrame with NaN values
    adx_columns = ['adx', 'plus_di', 'minus_di']
    assert result[adx_columns].isna().all().all()
    
    # Test with constant values
    data = pd.DataFrame({
        'high': [10] * 20,
        'low': [10] * 20,
        'close': [10] * 20
    })
    result = adx.calculate(data)
    
    # For constant values, ADX should approach 0 after warmup period
    warmup_period = 14  # Default ADX period
    assert (result['adx'].iloc[warmup_period:] < 5).all()  # Very low ADX indicates no trend

def test_adx_parameter_validation():
    """Test ADX parameter validation."""
    # Test invalid parameters
    with pytest.raises(ValueError):
        ADXIndicator(period=0)  # Period must be positive
    
    with pytest.raises(ValueError):
        ADXIndicator(period=-1)  # Period must be positive
    
    # Test valid parameters
    adx = ADXIndicator(period=14)
    assert adx.period == 14

def test_adx_performance():
    """Test ADX calculation performance with large dataset."""
    # Create large dataset with random price movements
    size = 10000
    data = pd.DataFrame({
        'high': np.random.rand(size) * 100 + 100,
        'low': np.random.rand(size) * 100 + 50,
        'close': np.random.rand(size) * 100 + 75
    })
    # Ensure low is always lower than high
    data['low'] = data[['high', 'low']].min(axis=1)
    data['high'] = data[['high', 'low']].max(axis=1)
    data['close'] = data[['high', 'low']].mean(axis=1)
    
    adx = ADXIndicator(period=14)
    
    # Time the calculation
    import time
    start_time = time.time()
    result = adx.calculate(data)
    end_time = time.time()
    
    # Check that calculation completes in reasonable time
    assert end_time - start_time < 1.0  # Should complete in less than 1 second
    
    # Verify results
    assert len(result) == len(data)
    assert not result.iloc[14:].isna().any().any()  # No NaN values after warmup period

def test_adx_trend_detection():
    """Test ADX trend detection capabilities."""
    # Create strong uptrend data
    size = 50
    uptrend = pd.DataFrame({
        'high': [100 + i * 2 for i in range(size)],
        'low': [99 + i * 2 for i in range(size)],
        'close': [99.5 + i * 2 for i in range(size)]
    })
    
    adx = ADXIndicator(period=14)
    result = adx.calculate(uptrend)
    
    # In strong uptrend:
    # - ADX should be high (> 25 indicates strong trend)
    # - DI+ should be greater than DI-
    assert (result['adx'].iloc[-1] > 25)
    assert (result['plus_di'].iloc[-1] > result['minus_di'].iloc[-1])
    
    # Create strong downtrend data
    downtrend = pd.DataFrame({
        'high': [200 - i * 2 for i in range(size)],
        'low': [199 - i * 2 for i in range(size)],
        'close': [199.5 - i * 2 for i in range(size)]
    })
    
    result = adx.calculate(downtrend)
    
    # In strong downtrend:
    # - ADX should be high (> 25 indicates strong trend)
    # - DI- should be greater than DI+
    assert (result['adx'].iloc[-1] > 25)
    assert (result['minus_di'].iloc[-1] > result['plus_di'].iloc[-1])
    
    # Create sideways market data
    np.random.seed(42)  # Set seed for reproducibility
    noise = np.random.uniform(-0.05, 0.05, size)
    sideways = pd.DataFrame({
        'high': [100 + n for n in noise],
        'low': [99.5 + n for n in noise],
        'close': [99.75 + n for n in noise]
    })
    
    result = adx.calculate(sideways)
    
    # In sideways market:
    # - ADX should be low (< 40 indicates no trend)
    # - DI+ and DI- should be close to each other
    assert (result['adx'].iloc[-1] < 40)
    assert abs(result['plus_di'].iloc[-1] - result['minus_di'].iloc[-1]) < 5 

def test_adx_signal_interpretation():
    """Test ADX signal interpretation for different market conditions."""
    # Create test data for different market conditions
    periods = 100
    index = pd.date_range(start='2020-01-01', periods=periods, freq='D')
    
    # Strong uptrend
    uptrend_data = pd.DataFrame({
        'high': [100 + i for i in range(periods)],
        'low': [99 + i for i in range(periods)],
        'close': [99.5 + i for i in range(periods)]
    }, index=index)
    
    # Strong downtrend
    downtrend_data = pd.DataFrame({
        'high': [100 - i for i in range(periods)],
        'low': [99 - i for i in range(periods)],
        'close': [99.5 - i for i in range(periods)]
    }, index=index)
    
    # Sideways market
    sideways_data = pd.DataFrame({
        'high': [100 + np.sin(i/10) * 0.5 for i in range(periods)],
        'low': [99 + np.sin(i/10) * 0.5 for i in range(periods)],
        'close': [99.5 + np.sin(i/10) * 0.5 for i in range(periods)]
    }, index=index)
    
    # Moderate trend
    moderate_data = pd.DataFrame({
        'high': [100 + i * 0.1 + np.random.normal(0, 0.05) for i in range(periods)],
        'low': [99 + i * 0.1 + np.random.normal(0, 0.05) for i in range(periods)],
        'close': [99.5 + i * 0.1 + np.random.normal(0, 0.05) for i in range(periods)]
    }, index=index)
    
    # Constant values
    constant_data = pd.DataFrame({
        'high': [100] * periods,
        'low': [100] * periods,
        'close': [100] * periods
    }, index=index)
    
    # Initialize ADX indicator
    adx = ADXIndicator(period=14)
    
    # Test each market condition
    for data, condition in [
        (uptrend_data, 'strong uptrend'),
        (downtrend_data, 'strong downtrend'),
        (sideways_data, 'sideways market'),
        (moderate_data, 'moderate trend'),
        (constant_data, 'constant values')
    ]:
        result = adx.calculate(data)
        
        # Debug logging
        print(f"\n{condition}:")
        print(f"ADX: {result['adx'].iloc[-1]:.2f}")
        print(f"DI+: {result['plus_di'].iloc[-1]:.2f}")
        print(f"DI-: {result['minus_di'].iloc[-1]:.2f}")
        
        # Verify trend strength
        if condition == 'strong uptrend' or condition == 'strong downtrend':
            assert result['trend_strength'].iloc[-1] == 'strong_trend'
            if condition == 'strong uptrend':
                assert result['trend_direction'].iloc[-1] == 'uptrend'
            else:
                assert result['trend_direction'].iloc[-1] == 'downtrend'
        elif condition == 'sideways market':
            assert result['trend_strength'].iloc[-1] == 'weak_trend'
            assert result['trend_direction'].iloc[-1] == 'sideways'
        elif condition == 'moderate trend':
            assert result['trend_strength'].iloc[-1] == 'moderate_trend'
        elif condition == 'constant values':
            assert result['trend_strength'].iloc[-1] == 'no_trend'
            assert result['trend_direction'].iloc[-1] == 'sideways' 