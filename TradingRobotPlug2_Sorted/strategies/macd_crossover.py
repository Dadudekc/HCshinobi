#!/usr/bin/env python3
"""
MACD Crossover Strategy

This module implements a MACD crossover strategy for backtesting using Backtrader.
It fetches historical data through DataOrchestrator and calculates MACD indicators
to generate trading signals.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse
import asyncio
import logging
import os

import backtrader as bt
import numpy as np
import pandas as pd

# Internal imports
from strategies.macd_strategy import StandardMACDStrategy
from data_processing.Technical_Indicators.indicator_aggregator import MACD

# Third-party data fetching and evaluation
from src.data_fetchers.main_data_fetcher import DataOrchestrator
from evaluation.metrics import calculate_performance
from evaluation.visualization import plot_backtest_results

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class MACDCrossoverStrategy(bt.Strategy):
    """
    A Backtrader strategy implementation that uses MACD crossover signals.
    Buys when MACD crosses above signal line, sells when it crosses below.
    """

    params = (("fast", 12), ("slow", 26), ("signal", 9))

    def __init__(self):
        """
        Initialize the Backtrader strategy with MACD indicators.
        """
        # Calculate MACD indicators
        self.macd, self.signal, _ = MACD(self.data.close,
                                       self.params.fast,
                                       self.params.slow,
                                       self.params.signal)
        # Add crossover indicator
        self.crossover = bt.indicators.CrossOver(self.macd, self.signal)

    def next(self):
        """
        Execute trading logic for each bar.
        Buy when MACD crosses above signal line, sell when it crosses below.
        """
        if not self.position:  # Not in the market
            if self.crossover > 0:  # MACD crosses above signal line
                self.buy()
        else:  # In the market
            if self.crossover < 0:  # MACD crosses below signal line
                self.close()  # Close the position


async def fetch_symbol_data(symbol: str, start_date: str, end_date: str, interval: str) -> pd.DataFrame:
    """
    Asynchronously fetches data for a single symbol from DataOrchestrator,
    unifies all sources, sorts them by 'Date', and returns one combined DataFrame.

    Args:
        symbol: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Data interval (e.g., "1d", "1Day")

    Returns:
        Combined historical data for the symbol
    """
    orchestrator = DataOrchestrator()
    symbol_map = await orchestrator.fetch_all_data([symbol], start_date, end_date, interval=interval)
    
    # Extract data for this symbol
    data_dict = symbol_map.get(symbol, {})
    sources = [df for df in data_dict.values() if not df.empty]
    
    if not sources:
        logger.error(f"No data fetched for {symbol} from any source.")
        return pd.DataFrame()

    # Combine data from all sources
    combined = pd.concat(sources, ignore_index=True)
    combined.drop_duplicates(subset=["Date"], inplace=True)
    combined.sort_values(by="Date", inplace=True)
    
    return combined


def run_backtest(symbol: str, start_date: str, end_date: str, timeframe: str, output_file: str):
    """
    Run a MACD crossover backtest using Backtrader.
    
    Steps:
    1) Fetch data from DataOrchestrator or load from cache
    2) Convert data to Backtrader feed
    3) Run the MACD crossover strategy
    4) Evaluate performance and visualize results
    
    Args:
        symbol: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        timeframe: Data timeframe (e.g., "1d")
        output_file: Path to cache the fetched data
    """
    # Check if data is cached
    if os.path.exists(output_file):
        logger.info(f"Loading cached data from {output_file}")
        df = pd.read_csv(output_file)
    else:
        logger.info(f"Fetching data for {symbol} from {start_date} to {end_date} ...")
        loop = asyncio.get_event_loop()
        df = loop.run_until_complete(fetch_symbol_data(symbol, start_date, end_date, timeframe))
        
        if df.empty:
            logger.error("Data fetch failed, cannot proceed with backtest.")
            return
            
        # Cache the data
        df.to_csv(output_file, index=False)
        logger.info(f"Data saved to {output_file}")

    # Prepare data for Backtrader
    if "Date" in df.columns:
        df["datetime"] = pd.to_datetime(df["Date"])
    else:
        logger.warning("No 'Date' column found; expecting 'datetime'.")
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    df.set_index("datetime", inplace=True)
    df.dropna(subset=["Close"], inplace=True)

    # Create Backtrader feed
    data_feed = bt.feeds.PandasData(dataname=df)

    # Run backtest
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MACDCrossoverStrategy)
    cerebro.adddata(data_feed)
    cerebro.run()

    # Calculate performance metrics
    perf = calculate_performance(df)
    logger.info(f"Performance: {perf}")

    # Generate and show visualization
    plot_backtest_results(df, symbol, timeframe)
    
    # Also calculate signals using our StandardMACDStrategy implementation
    macd_strategy = StandardMACDStrategy()
    if "Close" in df.columns:
        signals = macd_strategy.generate_signals(df["Close"])
        logger.info(f"Generated {signals['buy_signal'].sum()} buy signals and {signals['sell_signal'].sum()} sell signals")
    else:
        logger.warning("No 'Close' column found, cannot calculate MACD signals")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MACD Crossover Backtest using DataOrchestrator + Backtrader.")
    parser.add_argument("--symbol", type=str, required=True, help="Stock symbol (e.g., AAPL)")
    parser.add_argument("--start_date", type=str, default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default=datetime.today().strftime('%Y-%m-%d'), help="End date (YYYY-MM-DD)")
    parser.add_argument("--timeframe", type=str, default="1d", help="Data timeframe (e.g., 1d, 1Day)")
    parser.add_argument("--output_file", type=str, default="data.csv", help="Where to cache the fetched CSV data")

    args = parser.parse_args()
    run_backtest(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        timeframe=args.timeframe,
        output_file=args.output_file
    )
