# AI Suggestion: Refactoring of an existing system that has been exposed to external modules would involve identifying which dependencies the module 'Code.BackTester' is dependent upon (i.e., what it depends). The issue with circular dependency cycles often occurs when a class relies on another, and then needs functionality from both at different times or in various states of operation - causing issues if one cannot operate independently without interfering directly to each otherâ€™s operations which violates the principles behind object-oriented programming.
 
Considering these points:
1) The dependency is with a third party library 'pyalgotrade'. This could be refactored into its own module, e.g., `Code` and then referred back in to use pyAlgotraded's functionalities within the new codebase (since it does not seem necessary).  
2) If we consider only this external dependency as a 'data provider', letâ€™s move away from using that object inside of our module â€˜code.backtester'. We could remove references to pyAlgotrade, and if future updates in the other modules are required - it would be easier for them too by removing these dependencies directly within backtest code itself rather than being pulled into every function or method calls at runtime as they did before (this is a common approach called dependency injection).
3) For maintenance purposes: By moving functionality to its own module, we make the system modular and maintainable. This will help prevent changes in one part of your project from affecting others due to dependencies on external modules/libraries that were changed during those updates or additions (efficiency), thus providing a balance between modifying only our codebase while keeping functionalities organized as intended, which is good practice for maintaining software quality and system integrity.
4) In terms of decoupling components: By doing so we ensure loose coupling among modules i.e., each module operates on the data it has been given to process (the Data Provider). This will allow us more flexibility in design choices due to easier modifications, changes or additions if required at any point downstream from our backtester codebase e.g adding new strategies/techniques as per requirement and maintaining this system can be accomplished easily without much work of re-factoring the existing components around those modules' updates (improved modularity).
  
In conclusion, a refactored module 'Code.backtester', considering only pyAlgotrade dependency while keeping other dependencies for future additions or maintenance purposes makes sense and is also more maintainable with decoupling in mind due to ease of modifications downstream from the backtest codebase itself using Python's import mechanism allows easy modification without extensive work done on related modules.
from Code.backtest_engine import fetch_all_data
from Code.backtest_engine import final_portfolio_value
from Code.backtest_engine import performance_metrics
from Code.backtester import BacktestRunner
from Code.backtester import ClassicBacktester
from Code.stocktwits_sentiment_analyzer import run
from core.config.config_manager import get
from core.indicators.custom_indicators import close
from core.indicators.main_indicators import apply_all_indicators
from core.indicators.trend_indicators import apply
from core.strategies.base_strategy import BaseStrategy
from core.strategies.base_strategy import __init__
from data_fetchers.main_data_fetcher import DataOrchestrator
from data_processing.Technical_Indicators.indicator_unifier import AllIndicatorsUnifier
from datetime import datetime
from strategies.macd_crossover import next
from strategies.registry import STRATEGY_REGISTRY
from typing import Dict, List
import asyncio
import backtrader as bt
import logging
import numpy as np
import pandas as pd

"""
File: backtester.py
Location: src/Utilities/strategies

Description:
    A modular backtesting engine for trading strategies.

    - Fetches data via DataOrchestrator (no inline data fetch).
    - Optionally applies all technical indicators via AllIndicatorsUnifier.
    - Supports any strategy class registered in STRATEGY_REGISTRY.
    - Provides a simple ClassicBacktester for row-by-row trading logic.
    - Can be imported and tested without a main entry block.
"""

# Updated imports reflecting new project structure

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BaseStrategy(bt.Strategy):
    """
    Base class for any trading strategy in Backtrader.
    
    Subclasses must implement `next()` for the main trading logic.
    """
    def __init__(self):
        self.data = None
        self.current_index = 0
        self.finished = False
        self.position = 0
        self.balance = 10000.0  # Default starting balance
        self.trade_log = []

    def next(self):
        """Iterates to the next candle or timepoint."""
        if self.current_index >= len(self.data):
            self.finished = True
            return

        row = self.data.iloc[self.current_index]
        signal = self.generate_signal(row)
        self._execute_trade(signal, row)
        self.current_index += 1
        return signal
    
    def _execute_trade(self, signal, row):
        """
        Execute a trade based on the generated signal.
        
        Args:
            signal: Generated trading signal (1 for buy, -1 for sell, 0 for hold)
            row: Current data row
        """
        price = row.get("Close", 0)
        date = row.get("Date", self.current_index)
        
        if signal == 1 and self.position == 0:  # Buy signal
            shares = int(self.balance // price)
            if shares > 0:
                self.balance -= shares * price
                self.position += shares
                self.trade_log.append(("BUY", date, price, shares))
                logging.info(f"BUY on {date}: {shares} shares at {price}")
        elif signal == -1 and self.position > 0:  # Sell signal
            self.balance += self.position * price
            self.trade_log.append(("SELL", date, price, self.position))
            logging.info(f"SELL on {date}: {self.position} shares at {price}")
            self.position = 0
    
    def generate_signal(self, row):
        """
        Generate trading signal based on the current row data.
        Subclasses must implement this method.
        
        Args:
            row: Current data row
            
        Returns:
            int: Signal value (1 for buy, -1 for sell, 0 for hold)
        """
        raise NotImplementedError("Subclasses must implement the 'generate_signal()' method.")
    
    def get_performance(self):
        """
        Calculate strategy performance metrics.
        
        Returns:
            dict: Performance metrics
        """
        final_value = self.balance
        if self.position > 0 and not self.data.empty:
            final_value += self.position * self.data["Close"].iloc[-1]
            
        initial_balance = 10000.0  # Default initial balance
        total_return = ((final_value - initial_balance) / initial_balance) * 100
        
        return {
            "initial_balance": initial_balance,
            "final_value": final_value,
            "total_return_pct": total_return,
            "num_trades": len(self.trade_log)
        }


class ClassicBacktester:
    """
    A simple row-by-row backtester that uses 'Buy_Signal'/'Sell_Signal'
    columns from a DataFrame to log trades.
    """

    def __init__(self, df: pd.DataFrame, initial_balance: float = 10000.0):
        self.df = df.copy()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = 0
        self.trade_log: List[tuple] = []

    def run(self):
        """
        Simulates a backtest by scanning row-by-row for Buy_Signal or Sell_Signal.
        """
        for i in range(len(self.df)):
            price = self.df["Close"].iloc[i]
            date = self.df["Date"].iloc[i]
            if self.df.get("Buy_Signal", pd.Series([False]*len(self.df))).iloc[i]:
                shares = int(self.balance // price)
                if shares > 0:
                    self.balance -= shares * price
                    self.position += shares
                    self.trade_log.append(("BUY", date, price, shares))
                    logging.info(f"BUY on {date}: {shares} shares at {price}")
            elif self.df.get("Sell_Signal", pd.Series([False]*len(self.df))).iloc[i] and self.position > 0:
                self.balance += self.position * price
                self.trade_log.append(("SELL", date, price, self.position))
                logging.info(f"SELL on {date}: {self.position} shares at {price}")
                self.position = 0

    def final_portfolio_value(self) -> float:
        """
        Returns the final portfolio value = cash + (shares * latest close).
        """
        return self.balance + (self.position * self.df["Close"].iloc[-1])

    def performance_metrics(self) -> dict:
        """
        Basic performance metrics:
         - final portfolio value
         - total return in percentage
        """
        final_value = self.final_portfolio_value()
        total_return = ((final_value - self.initial_balance) / self.initial_balance) * 100
        return {"final_value": final_value, "total_return_pct": total_return}


class BacktestRunner:
    """
    Main backtesting engine that:
    - Fetches data from DataOrchestrator (async).
    - (Optionally) applies AllIndicatorsUnifier for full indicator coverage.
    - Runs a registered strategy in Backtrader.
    - Returns performance metrics using either Backtrader logs or the ClassicBacktester.
    """

    def __init__(
        self,
        strategy_name: str,
        initial_balance: float = 10000.0,
        apply_unifier: bool = False
    ):
        """
        Args:
            strategy_name (str): The name of a registered strategy.
            initial_balance (float): Starting capital for the performance evaluation.
            apply_unifier (bool): If True, applies AllIndicatorsUnifier to the DataFrame.
        """
        if strategy_name not in STRATEGY_REGISTRY:
            raise ValueError(f"Strategy '{strategy_name}' not found in registry.")
        self.strategy_class = STRATEGY_REGISTRY[strategy_name]
        self.initial_balance = initial_balance
        self.apply_unifier = apply_unifier
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_orchestrator = DataOrchestrator()

    async def fetch_data(self, symbol: str, start_date: str, end_date: str, interval: str) -> pd.DataFrame:
        """
        Fetches and unifies data for a single symbol using DataOrchestrator.
        
        Returns:
            A single combined DataFrame sorted by "Date".
        """
        result_map = await self.data_orchestrator.fetch_all_data([symbol], start_date, end_date, interval)
        symbol_map = result_map.get(symbol, {})
        sources = [df for df in symbol_map.values() if not df.empty]
        if not sources:
            self.logger.warning(f"No data sources available for {symbol}.")
            return pd.DataFrame()

        combined = pd.concat(sources, ignore_index=True)
        combined.drop_duplicates(subset=["Date"], inplace=True)
        combined.sort_values(by="Date", inplace=True)
        return combined

    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str
    ) -> dict:
        """
        Runs the backtest for a single symbol and returns performance metrics.

        Steps:
          1) Asynchronously fetch data.
          2) Optionally apply AllIndicatorsUnifier.
          3) Feed data into Backtrader with the chosen strategy.
          4) Evaluate performance using ClassicBacktester.
        """
        loop = asyncio.get_event_loop()
        df = loop.run_until_complete(self.fetch_data(symbol, start_date, end_date, interval))

        if df.empty:
            self.logger.error(f"Empty DataFrame for symbol {symbol}. Cannot backtest.")
            return {"error": "no_data"}

        # Optionally apply unifier for full indicator coverage
        if self.apply_unifier:
            unifier = AllIndicatorsUnifier(config_manager=None, logger=self.logger, use_csv=False)
            df = unifier.apply_all_indicators(df)

        # Prepare DataFrame for Backtrader: ensure 'Date' and 'Close' columns are set up correctly
        df["datetime"] = pd.to_datetime(df["Date"])
        df.set_index("datetime", inplace=True, drop=True)
        df.dropna(subset=["Close"], inplace=True)

        datafeed = bt.feeds.PandasData(dataname=df)

        # Backtrader setup: add strategy and datafeed to Cerebro
        cerebro = bt.Cerebro()
        cerebro.addstrategy(self.strategy_class)
        cerebro.adddata(datafeed)
        cerebro.run()  # Execute the strategy

        # Evaluate performance using a classic row-by-row approach
        backtester = ClassicBacktester(df, initial_balance=self.initial_balance)
        backtester.run()
        metrics = backtester.performance_metrics()
        self.logger.info(f"Performance for {symbol}: {metrics}")
        return metrics


# Example usage:
# To use this module, first register your strategy in the registry (e.g., via a decorator)
# Then, you can run a backtest as follows:
#
# from src.strategies.backtester import BacktestRunner
# runner = BacktestRunner(strategy_name="RSI_MACD", apply_unifier=True)
# results = runner.run(symbol="AAPL", start_date="2020-01-01", end_date="2020-12-31", interval="1d")
# print(results)
