"""
Trading strategies for technical and quantitative analysis.
"""

from strategies.macd_strategy_interface import MacdStrategy
from strategies.macd_strategy import StandardMACDStrategy
from strategies.macd_crossover import MACDCrossoverStrategy, run_backtest

__all__ = [
    'MacdStrategy',
    'StandardMACDStrategy',
    'MACDCrossoverStrategy',
    'run_backtest'
]



