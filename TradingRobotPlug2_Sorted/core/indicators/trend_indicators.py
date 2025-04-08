"""
Trend indicators for technical analysis.
"""

from typing import Union, Optional, Dict, Any, List
import numpy as np
import pandas as pd
import logging

from .indicator_interface import IndicatorInterface
from .base import BaseIndicator

def sma(data: Union[pd.Series, np.ndarray], window: int) -> np.ndarray:
    """
    Calculate Simple Moving Average.
    
    Args:
        data: Input data series
        window: Window size for the moving average
        
    Returns:
        numpy.ndarray: Simple moving average values
    """
    if isinstance(data, pd.Series):
        data = data.values
        
    if len(data) < window:
        return np.full(len(data), np.nan)
        
    # Calculate SMA using rolling window
    result = np.full(len(data), np.nan)
    for i in range(window - 1, len(data)):
        result[i] = np.mean(data[i - window + 1:i + 1])
    return result

def ema(data: Union[pd.Series, np.ndarray], window: int, 
        adjust: bool = True) -> np.ndarray:
    """
    Calculate Exponential Moving Average.
    
    Args:
        data: Input data series
        window: Window size for the moving average
        adjust: Whether to adjust the weights
        
    Returns:
        numpy.ndarray: Exponential moving average values
    """
    if isinstance(data, pd.Series):
        data = data.values
        
    if len(data) < window:
        return np.full(len(data), np.nan)
        
    # Calculate EMA using rolling window
    alpha = 2 / (window + 1)
    result = np.full(len(data), np.nan)
    result[window - 1] = np.mean(data[:window])  # Initialize with SMA
    
    for i in range(window, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        
    return result

def wma(data: Union[pd.Series, np.ndarray], window: int) -> np.ndarray:
    """
    Calculate Weighted Moving Average.
    
    Args:
        data: Input data series
        window: Window size for the moving average
        
    Returns:
        numpy.ndarray: Weighted moving average values
    """
    if isinstance(data, pd.Series):
        data = data.values
        
    if len(data) < window:
        return np.full(len(data), np.nan)
        
    # Calculate weights
    weights = np.arange(1, window + 1)
    weights = weights / weights.sum()
    
    # Calculate WMA using rolling window
    result = np.full(len(data), np.nan)
    for i in range(window - 1, len(data)):
        result[i] = np.sum(data[i - window + 1:i + 1] * weights)
    return result

def hma(data: Union[pd.Series, np.ndarray], window: int) -> np.ndarray:
    """
    Calculate Hull Moving Average.
    
    Args:
        data: Input data series
        window: Window size for the moving average
        
    Returns:
        numpy.ndarray: Hull moving average values
    """
    if isinstance(data, pd.Series):
        data = data.values
        
    if len(data) < window:
        return np.full(len(data), np.nan)
        
    # Calculate WMA with half the window
    half_window = int(window / 2)
    wma_half = wma(data, half_window)
    
    # Calculate WMA with full window
    wma_full = wma(data, window)
    
    # Calculate HMA
    sqrt_window = int(np.sqrt(window))
    result = np.full(len(data), np.nan)
    
    # Calculate 2 * WMA(n/2) - WMA(n)
    temp = 2 * wma_half - wma_full
    
    # Calculate final HMA
    for i in range(sqrt_window - 1, len(data)):
        if i - sqrt_window + 1 >= 0:  # Ensure we have enough data
            result[i] = np.sum(temp[i - sqrt_window + 1:i + 1] * np.arange(1, sqrt_window + 1)) / np.sum(np.arange(1, sqrt_window + 1))
            
    return result

def vwma(data: pd.DataFrame, price_col: str = 'close', 
         volume_col: str = 'volume', window: int = 20) -> np.ndarray:
    """
    Calculate Volume Weighted Moving Average.
    
    Args:
        data: DataFrame containing price and volume data
        price_col: Name of the price column
        volume_col: Name of the volume column
        window: Window size for the moving average
        
    Returns:
        numpy.ndarray: Volume weighted moving average values
    """
    if len(data) < window:
        return np.full(len(data), np.nan)
        
    price = data[price_col].values
    volume = data[volume_col].values
    
    # Calculate VWMA using rolling window
    result = np.full(len(data), np.nan)
    for i in range(window - 1, len(data)):
        window_prices = price[i - window + 1:i + 1]
        window_volumes = volume[i - window + 1:i + 1]
        result[i] = np.sum(window_prices * window_volumes) / np.sum(window_volumes)
        
    return result

class TrendIndicator(BaseIndicator):
    """Base class for trend indicators."""
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        super().__init__(name, logger)
        
    def get_required_columns(self) -> List[str]:
        return ['close', 'high', 'low']
        
    def get_output_columns(self) -> List[str]:
        return [f'{self.name}_trend']

class MovingAverageIndicator(TrendIndicator):
    """Moving Average indicator."""
    
    def __init__(self, window: int = 20, ma_type: str = 'SMA', logger: Optional[logging.Logger] = None):
        super().__init__(f'{ma_type}_{window}', logger)
        self.window = window
        self.ma_type = ma_type
        
    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate moving average."""
        result = df.copy()
        
        if self.ma_type == 'SMA':
            result[self.get_output_columns()[0]] = sma(df['close'], self.window)
        elif self.ma_type == 'EMA':
            result[self.get_output_columns()[0]] = ema(df['close'], self.window)
        elif self.ma_type == 'WMA':
            result[self.get_output_columns()[0]] = wma(df['close'], self.window)
        elif self.ma_type == 'HMA':
            result[self.get_output_columns()[0]] = hma(df['close'], self.window)
        elif self.ma_type == 'VWMA':
            result[self.get_output_columns()[0]] = vwma(df['close'], df['volume'], self.window)
        else:
            raise ValueError(f"Unknown MA type: {self.ma_type}")
            
        return result
        
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters."""
        if 'window' not in params:
            return False
        if not isinstance(params['window'], int) or params['window'] <= 0:
            return False
        if 'ma_type' not in params:
            return False
        if params['ma_type'] not in ['SMA', 'EMA', 'WMA', 'HMA', 'VWMA']:
            return False
        return True
        
    def get_required_parameters(self) -> List[str]:
        return ['window', 'ma_type']

class MACDIndicator(TrendIndicator):
    """Moving Average Convergence Divergence (MACD) indicator."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize MACD indicator.
        
        Args:
            fast_period: Period for fast EMA
            slow_period: Period for slow EMA
            signal_period: Period for signal line EMA
        """
        if fast_period >= slow_period:
            raise ValueError("Fast period must be less than slow period")
        if fast_period <= 0 or slow_period <= 0 or signal_period <= 0:
            raise ValueError("All periods must be positive")
            
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self._cache: Dict[str, pd.Series] = {}
        
    def get_parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """Get parameter information for the indicator."""
        return {
            'fast_period': {
                'type': 'int',
                'min': 1,
                'max': self.slow_period - 1,
                'description': 'Period for fast EMA calculation'
            },
            'slow_period': {
                'type': 'int',
                'min': self.fast_period + 1,
                'max': 100,
                'description': 'Period for slow EMA calculation'
            },
            'signal_period': {
                'type': 'int',
                'min': 1,
                'max': 50,
                'description': 'Period for signal line EMA calculation'
            }
        }
        
    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate EMA with caching."""
        cache_key = f"ema_{period}_{series.name}"
        if cache_key not in self._cache:
            self._cache[cache_key] = series.ewm(span=period, adjust=False).mean()
        return self._cache[cache_key]
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD indicator.
        
        Args:
            df: DataFrame with 'close' column
            
        Returns:
            DataFrame with MACD line, signal line, and histogram
        """
        result = df.copy()
        
        # Check if we have enough data
        min_periods = max(self.fast_period, self.slow_period, self.signal_period)
        if len(df) < min_periods:
            # Return DataFrame with NaN values
            result['macd_line'] = np.nan
            result['signal_line'] = np.nan
            result['macd_histogram'] = np.nan
            return result
        
        # Calculate fast and slow EMAs using cached method
        fast_ema = self._calculate_ema(df['close'], self.fast_period)
        slow_ema = self._calculate_ema(df['close'], self.slow_period)
        
        # Calculate MACD line (fast EMA - slow EMA)
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line (EMA of MACD line)
        signal_line = self._calculate_ema(macd_line, self.signal_period)
        
        # Calculate MACD histogram (MACD line - signal line)
        macd_histogram = macd_line - signal_line
        
        # Add results to DataFrame
        result['macd_line'] = macd_line
        result['signal_line'] = signal_line
        result['macd_histogram'] = macd_histogram
        
        # Clear cache after calculation
        self._cache.clear()
        
        return result
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get indicator parameters."""
        return {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'signal_period': self.signal_period
        }
    
    def get_output_columns(self) -> list:
        """Get list of output column names."""
        return ['macd_line', 'signal_line', 'macd_histogram']

class ADXIndicator(TrendIndicator):
    """Average Directional Index (ADX) indicator."""

    def __init__(self, period: int = 14):
        """Initialize ADX indicator.
        
        Args:
            period (int, optional): Period for ADX calculation. Defaults to 14.
        """
        if period < 2:
            raise ValueError("Period must be greater than or equal to 2")
        self.period = period

    def _calculate_true_range(self, data: pd.DataFrame) -> pd.Series:
        """Calculate True Range.
        
        Args:
            data (pd.DataFrame): DataFrame with high, low, close columns
            
        Returns:
            pd.Series: True Range values
        """
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        return ranges.max(axis=1)

    def _calculate_plus_dm(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Plus Directional Movement.
        
        Args:
            data (pd.DataFrame): DataFrame with high, low columns
            
        Returns:
            pd.Series: Plus DM values
        """
        up_move = data['high'] - data['high'].shift(1)
        down_move = data['low'].shift(1) - data['low']
        return pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=data.index)

    def _calculate_minus_dm(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Minus Directional Movement.
        
        Args:
            data (pd.DataFrame): DataFrame with high, low columns
            
        Returns:
            pd.Series: Minus DM values
        """
        up_move = data['high'] - data['high'].shift(1)
        down_move = data['low'].shift(1) - data['low']
        return pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=data.index)

    def _smooth_values(self, series: Union[pd.Series, np.ndarray]) -> pd.Series:
        """Smooth values using Wilder's smoothing method.
        
        Args:
            series (Union[pd.Series, np.ndarray]): Series or array to smooth
            
        Returns:
            pd.Series: Smoothed values
        """
        if isinstance(series, np.ndarray):
            series = pd.Series(series)
        return series.ewm(alpha=1/self.period, adjust=False).mean()

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate ADX indicator.
        
        Args:
            data (pd.DataFrame): DataFrame with high, low, close columns
            
        Returns:
            pd.DataFrame: DataFrame with ADX indicator columns
        """
        # Check for constant values
        if (data['high'] == data['low']).all() and (data['low'] == data['close']).all():
            result = pd.DataFrame(index=data.index)
            result['adx'] = 0.0
            result['plus_di'] = 0.0
            result['minus_di'] = 0.0
            result['trend_strength'] = 'no_trend'
            result['trend_direction'] = 'sideways'
            return result

        result = pd.DataFrame(index=data.index)
        
        # Calculate True Range and Directional Movement
        tr = self._calculate_true_range(data)
        plus_dm = self._calculate_plus_dm(data)
        minus_dm = self._calculate_minus_dm(data)
        
        # Smooth TR and DM values
        smoothed_tr = self._smooth_values(tr)
        smoothed_plus_dm = self._smooth_values(plus_dm)
        smoothed_minus_dm = self._smooth_values(minus_dm)
        
        # Calculate +DI and -DI
        result['plus_di'] = (smoothed_plus_dm / smoothed_tr) * 100
        result['minus_di'] = (smoothed_minus_dm / smoothed_tr) * 100
        
        # Calculate DX
        di_sum = result['plus_di'] + result['minus_di']
        di_diff = abs(result['plus_di'] - result['minus_di'])
        dx = (di_diff / di_sum) * 100
        
        # Calculate ADX
        result['adx'] = self._smooth_values(dx)
        
        # Set initial values to NaN for proper warmup
        warmup_period = self.period - 1
        result.iloc[:warmup_period] = np.nan
        
        # Interpret trend strength and direction
        result['trend_strength'] = self._interpret_trend_strength(result['adx'], result)
        result['trend_direction'] = self._interpret_trend_direction(result['plus_di'], result['minus_di'])
        
        return result

    def _interpret_trend_strength(self, adx: pd.Series, result: pd.DataFrame) -> pd.Series:
        """Interpret ADX values into trend strength categories.
        
        Args:
            adx (pd.Series): ADX values
            result (pd.DataFrame): DataFrame with DI values
            
        Returns:
            pd.Series: Trend strength categories
        """
        # Calculate DI difference
        di_diff = abs(result['plus_di'] - result['minus_di'])
        
        # Convert adx and di_diff to float values for comparison
        adx_values = adx.astype(float)
        di_diff_values = di_diff.astype(float)
        
        # Initialize result series with 'no_trend'
        trend_strength = pd.Series('no_trend', index=adx.index)
        
        # Update trend strength based on conditions
        # Weak trend: Low ADX or small DI difference
        mask = (adx_values < 20) | (di_diff_values < 5)
        trend_strength[mask] = 'weak_trend'
        
        # Moderate trend: Medium ADX and significant DI difference
        mask = ((adx_values >= 20) & (adx_values < 40) & (di_diff_values >= 5)) | \
               ((adx_values >= 40) & (di_diff_values >= 5) & (di_diff_values < 15))
        trend_strength[mask] = 'moderate_trend'
        
        # Strong trend: High ADX and large DI difference
        mask = (adx_values >= 40) & (di_diff_values >= 15)
        trend_strength[mask] = 'strong_trend'
        
        return trend_strength

    def _interpret_trend_direction(self, plus_di: pd.Series, minus_di: pd.Series) -> pd.Series:
        """Interpret trend direction based on DI values.
        
        Args:
            plus_di (pd.Series): +DI values
            minus_di (pd.Series): -DI values
            
        Returns:
            pd.Series: Trend direction categories
        """
        # Convert DI values to float for comparison
        plus_di_values = plus_di.astype(float)
        minus_di_values = minus_di.astype(float)
        
        # Calculate DI difference
        di_diff = abs(plus_di_values - minus_di_values)
        
        # Initialize result series with 'sideways'
        trend_direction = pd.Series('sideways', index=plus_di.index)
        
        # Update trend direction based on DI comparison
        # Only consider it a trend if the DI difference is significant
        mask = (di_diff >= 3) & (plus_di_values > minus_di_values)
        trend_direction[mask] = 'uptrend'
        
        mask = (di_diff >= 3) & (minus_di_values > plus_di_values)
        trend_direction[mask] = 'downtrend'
        
        return trend_direction

    def get_parameter_info(self) -> Dict[str, Any]:
        """Get information about the indicator's parameters.
        
        Returns:
            Dict[str, Any]: Dictionary containing parameter information
        """
        return {
            'period': {
                'type': 'int',
                'min': 2,
                'max': 100,
                'default': 14,
                'description': 'Period for ADX calculation'
            }
        }

class TrendIndicators:
    """Collection of trend indicators."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.indicators = {
            'ma': MovingAverageIndicator(window=20, ma_type='SMA', logger=logger),
            'macd': MACDIndicator(fast_period=12, slow_period=26, signal_period=9, logger=logger),
            'adx': ADXIndicator(period=14, logger=logger)
        }
        
    def apply(self, df: pd.DataFrame, indicators: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Apply trend indicators to the DataFrame.
        
        Args:
            df: Input DataFrame
            indicators: List of indicator names to apply. If None, all indicators are applied.
            
        Returns:
            DataFrame with added indicator columns
        """
        if indicators is None:
            indicators = list(self.indicators.keys())
            
        # Create a copy of the DataFrame to avoid modifying the original
        result = df.copy()
        
        for indicator_name in indicators:
            if indicator_name not in self.indicators:
                self.logger.warning(f"Unknown indicator: {indicator_name}")
                continue
                
            try:
                result = self.indicators[indicator_name].apply(result)
            except Exception as e:
                self.logger.error(f"Error applying {indicator_name}: {str(e)}")
                
        return result
