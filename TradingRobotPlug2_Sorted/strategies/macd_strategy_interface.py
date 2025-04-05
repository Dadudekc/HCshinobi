#!/usr/bin/env python3
"""
MACD Strategy Interface

This module defines the interface for MACD strategy implementations.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Union, Optional, TypeVar

import numpy as np
import pandas as pd

# Type aliases for clarity
PriceData = Union[List[float], np.ndarray, pd.Series]
T = TypeVar('T', bound='MacdStrategy')

class MacdStrategy(ABC):
    """
    Abstract base class for MACD strategy implementations.
    
    This interface defines the contract that all MACD strategy
    implementations must follow, ensuring consistency across
    different implementations.
    """
    
    @abstractmethod
    def get_macd_value(self, prices: PriceData) -> Tuple[float, float, float]:
        """
        Compute MACD line, signal line, and histogram from price data.
        
        Args:
            prices: List, array, or Series of price data
            
        Returns:
            Tuple containing (macd_line, signal_line, histogram)
        """
        pass
    
    @abstractmethod
    def generate_signals(self, prices: PriceData) -> pd.DataFrame:
        """
        Generate buy/sell signals based on MACD crossovers.
        
        Args:
            prices: List, array, or Series of price data
            
        Returns:
            DataFrame with columns for MACD values and buy/sell signals
        """
        pass
    
    @classmethod
    @abstractmethod
    def create(cls: type[T], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> T:
        """
        Factory method to create a new strategy instance with the specified parameters.
        
        Args:
            fast_period: Period for fast EMA (default: 12)
            slow_period: Period for slow EMA (default: 26)
            signal_period: Period for signal line (default: 9)
            
        Returns:
            New instance of the strategy
        """
        pass 