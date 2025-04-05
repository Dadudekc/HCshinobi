#!/usr/bin/env python3
"""
MACD Strategy Implementation

This module provides a concrete implementation of the MACD strategy interface.
"""

from typing import Tuple, List, Dict, Any, Optional, ClassVar, Union
import logging

import numpy as np
import pandas as pd

from strategies.macd_strategy_interface import MacdStrategy, PriceData

logger = logging.getLogger(__name__)

class StandardMACDStrategy(MacdStrategy):
    """
    Standard implementation of the MACD strategy.
    
    This class implements the MACD (Moving Average Convergence Divergence)
    strategy using exponential moving averages.
    """
    
    # Default parameters
    DEFAULT_FAST_PERIOD: ClassVar[int] = 12
    DEFAULT_SLOW_PERIOD: ClassVar[int] = 26
    DEFAULT_SIGNAL_PERIOD: ClassVar[int] = 9
    
    def __init__(self, fast_period: int = DEFAULT_FAST_PERIOD, 
                 slow_period: int = DEFAULT_SLOW_PERIOD, 
                 signal_period: int = DEFAULT_SIGNAL_PERIOD):
        """
        Initialize the MACD strategy with the specified parameters.
        
        Args:
            fast_period: Period for fast EMA
            slow_period: Period for slow EMA
            signal_period: Period for signal line
        """
        if fast_period >= slow_period:
            raise ValueError("Fast period must be smaller than slow period")
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.logger = logger
    
    @classmethod
    def create(cls, fast_period: int = DEFAULT_FAST_PERIOD, 
              slow_period: int = DEFAULT_SLOW_PERIOD, 
              signal_period: int = DEFAULT_SIGNAL_PERIOD) -> 'StandardMACDStrategy':
        """
        Factory method to create a new strategy instance.
        
        Args:
            fast_period: Period for fast EMA (default: 12)
            slow_period: Period for slow EMA (default: 26)
            signal_period: Period for signal line (default: 9)
            
        Returns:
            New StandardMACDStrategy instance
        """
        return cls(fast_period, slow_period, signal_period)
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate Exponential Moving Average (EMA).
        
        Args:
            data: Price data as numpy array
            period: EMA period
            
        Returns:
            EMA values as numpy array
        """
        ema = np.zeros_like(data)
        alpha = 2 / (period + 1)
        
        # Initialize EMA with SMA for the first period
        ema[:period] = np.nan
        if len(data) >= period:
            ema[period-1] = np.mean(data[:period])
            
            # Calculate EMA for remaining data
            for i in range(period, len(data)):
                ema[i] = data[i] * alpha + ema[i-1] * (1 - alpha)
                
        return ema
    
    def get_macd_value(self, prices: PriceData) -> Tuple[float, float, float]:
        """
        Compute the most recent MACD value, signal value, and histogram value.
        
        Args:
            prices: Price data
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        # Convert input to numpy array for calculation
        if isinstance(prices, pd.Series):
            price_array = prices.values
        else:
            price_array = np.array(prices)
        
        # Calculate fast and slow EMAs
        fast_ema = self._calculate_ema(price_array, self.fast_period)
        slow_ema = self._calculate_ema(price_array, self.slow_period)
        
        # Calculate MACD line (fast EMA - slow EMA)
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line (EMA of MACD line)
        signal_line = self._calculate_ema(macd_line, self.signal_period)
        
        # Calculate histogram (MACD line - signal line)
        histogram = macd_line - signal_line
        
        # Return the most recent values
        if len(macd_line) > 0 and not np.isnan(macd_line[-1]):
            return macd_line[-1], signal_line[-1], histogram[-1]
        else:
            return 0.0, 0.0, 0.0
    
    def calculate_macd_series(self, prices: PriceData) -> Dict[str, np.ndarray]:
        """
        Calculate MACD, signal, and histogram series for the entire price data.
        
        Args:
            prices: Price data
            
        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' arrays
        """
        # Convert input to numpy array for calculation
        if isinstance(prices, pd.Series):
            price_array = prices.values
        else:
            price_array = np.array(prices)
        
        # Calculate fast and slow EMAs
        fast_ema = self._calculate_ema(price_array, self.fast_period)
        slow_ema = self._calculate_ema(price_array, self.slow_period)
        
        # Calculate MACD line (fast EMA - slow EMA)
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line (EMA of MACD line)
        signal_line = self._calculate_ema(macd_line, self.signal_period)
        
        # Calculate histogram (MACD line - signal line)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def generate_signals(self, prices: PriceData) -> pd.DataFrame:
        """
        Generate buy/sell signals based on MACD crossovers.
        
        A buy signal is generated when the MACD line crosses above the signal line.
        A sell signal is generated when the MACD line crosses below the signal line.
        
        Args:
            prices: Price data
            
        Returns:
            DataFrame with columns for MACD values and buy/sell signals
        """
        # Convert input to Series if it's not already
        if not isinstance(prices, pd.Series):
            prices = pd.Series(prices)
        
        # Calculate MACD components
        macd_data = self.calculate_macd_series(prices)
        
        # Create DataFrame with results
        result = pd.DataFrame({
            'price': prices,
            'macd': macd_data['macd'],
            'signal': macd_data['signal'],
            'histogram': macd_data['histogram']
        })
        
        # Initialize signal columns
        result['buy_signal'] = False
        result['sell_signal'] = False
        
        # Generate crossover signals (excluding first rows with NaN values)
        valid_idx = result.index[~np.isnan(result['macd']) & ~np.isnan(result['signal'])]
        if len(valid_idx) > 1:
            # Find crossover points (current macd > signal but previous macd <= signal)
            for i in range(1, len(valid_idx)):
                curr_idx = valid_idx[i]
                prev_idx = valid_idx[i-1]
                
                # Buy signal: MACD crosses above signal
                if (result.loc[curr_idx, 'macd'] > result.loc[curr_idx, 'signal'] and 
                    result.loc[prev_idx, 'macd'] <= result.loc[prev_idx, 'signal']):
                    result.loc[curr_idx, 'buy_signal'] = True
                
                # Sell signal: MACD crosses below signal
                elif (result.loc[curr_idx, 'macd'] < result.loc[curr_idx, 'signal'] and 
                      result.loc[prev_idx, 'macd'] >= result.loc[prev_idx, 'signal']):
                    result.loc[curr_idx, 'sell_signal'] = True
        
        self.logger.debug(f"Generated signals: {result['buy_signal'].sum()} buys, {result['sell_signal'].sum()} sells")
        return result
    
    def __str__(self) -> str:
        return f"MACD({self.fast_period},{self.slow_period},{self.signal_period})" 