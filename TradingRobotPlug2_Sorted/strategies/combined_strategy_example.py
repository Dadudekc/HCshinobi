#!/usr/bin/env python3
"""
Combined Strategy Example

This script demonstrates how to combine RSI and MACD indicators
into a single trading strategy.
"""

import argparse
from datetime import datetime
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class IndicatorCalculator:
    """Helper class to calculate trading indicators"""
    
    @staticmethod
    def compute_rsi(prices, window=14):
        """
        Calculate the Relative Strength Index (RSI)
        
        Args:
            prices: Series of prices
            window: RSI window period
            
        Returns:
            Series with RSI values
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def compute_macd(prices, fast_period=12, slow_period=26, signal_period=9):
        """
        Calculate the MACD and signal line
        
        Args:
            prices: Series of prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
            
        Returns:
            Tuple of (MACD line, Signal line)
        """
        fast_ema = prices.ewm(span=fast_period, adjust=False).mean()
        slow_ema = prices.ewm(span=slow_period, adjust=False).mean()
        
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        return macd_line, signal_line


class RSIMACDCombinedStrategy:
    """
    A trading strategy that combines RSI and MACD signals.
    
    This strategy generates buy signals when:
    1. RSI is below the oversold threshold AND
    2. MACD line crosses above the signal line
    
    It generates sell signals when:
    1. RSI is above the overbought threshold OR
    2. MACD line crosses below the signal line
    """
    
    def __init__(self, df, rsi_window=14, macd_fast=12, macd_slow=26, macd_signal=9,
                 rsi_buy_threshold=30, rsi_sell_threshold=70, logger=None):
        """
        Initialize the strategy.
        
        Args:
            df: DataFrame containing stock price data with 'Close' prices
            rsi_window: RSI lookback period
            macd_fast: Fast period for MACD
            macd_slow: Slow period for MACD
            macd_signal: Signal line period for MACD
            rsi_buy_threshold: RSI level considered oversold
            rsi_sell_threshold: RSI level considered overbought
            logger: Optional logger instance
        """
        self.df = df.copy()
        self.rsi_window = rsi_window
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_buy_threshold = rsi_buy_threshold
        self.rsi_sell_threshold = rsi_sell_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        self.logger.info("RSIMACDCombinedStrategy initialized")
    
    def generate_signals(self):
        """
        Generate buy/sell signals based on RSI and MACD conditions.
        
        Returns:
            DataFrame with Buy_Signal and Sell_Signal columns
        """
        self.logger.info("Generating RSI and MACD indicators...")
        
        # Compute RSI
        self.df["RSI"] = IndicatorCalculator.compute_rsi(
            self.df["Close"], window=self.rsi_window
        )
        
        # Compute MACD
        self.df["MACD"], self.df["MACD_Signal"] = IndicatorCalculator.compute_macd(
            self.df["Close"], self.macd_fast, self.macd_slow, self.macd_signal
        )
        
        # Calculate MACD histogram and crossovers
        self.df["MACD_Histogram"] = self.df["MACD"] - self.df["MACD_Signal"]
        self.df["MACD_Crossover"] = np.where(
            (self.df["MACD"] > self.df["MACD_Signal"]) & 
            (self.df["MACD"].shift(1) <= self.df["MACD_Signal"].shift(1)),
            1, 0
        )
        self.df["MACD_Crossunder"] = np.where(
            (self.df["MACD"] < self.df["MACD_Signal"]) & 
            (self.df["MACD"].shift(1) >= self.df["MACD_Signal"].shift(1)),
            1, 0
        )
        
        self.logger.info("Applying combined RSI and MACD conditions...")
        
        # Buy signal: RSI is oversold AND MACD crosses above signal line
        self.df["Buy_Signal"] = (
            (self.df["RSI"] < self.rsi_buy_threshold) & 
            (self.df["MACD_Crossover"] == 1)
        )
        
        # Sell signal: RSI is overbought OR MACD crosses below signal line
        self.df["Sell_Signal"] = (
            (self.df["RSI"] > self.rsi_sell_threshold) | 
            (self.df["MACD_Crossunder"] == 1)
        )
        
        signal_count = {
            "buy": self.df["Buy_Signal"].sum(),
            "sell": self.df["Sell_Signal"].sum()
        }
        self.logger.info(f"Generated {signal_count['buy']} buy signals and {signal_count['sell']} sell signals")
        
        return self.df


def fetch_data(symbol, start_date, end_date):
    """
    Fetch historical data from Yahoo Finance.
    
    Args:
        symbol: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        DataFrame with historical price data
    """
    logger.info(f"Fetching data for {symbol} from {start_date} to {end_date}")
    
    try:
        data = yf.download(symbol, start=start_date, end=end_date)
        if data.empty:
            logger.error(f"No data found for {symbol}")
            return pd.DataFrame()
        
        data.reset_index(inplace=True)
        logger.info(f"Successfully fetched {len(data)} data points")
        return data
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return pd.DataFrame()


def run_backtest(symbol, start_date, end_date, rsi_window=14, macd_fast=12, 
                macd_slow=26, macd_signal=9, rsi_buy=30, rsi_sell=70):
    """
    Run a backtest using the combined RSI+MACD strategy.
    
    Args:
        symbol: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        rsi_window: RSI window period
        macd_fast: Fast period for MACD
        macd_slow: Slow period for MACD 
        macd_signal: Signal period for MACD
        rsi_buy: RSI buy threshold
        rsi_sell: RSI sell threshold
    """
    # Fetch historical data
    df = fetch_data(symbol, start_date, end_date)
    if df.empty:
        logger.error("Cannot run backtest with empty data")
        return
    
    # Create strategy instance
    strategy = RSIMACDCombinedStrategy(
        df=df,
        rsi_window=rsi_window,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        rsi_buy_threshold=rsi_buy,
        rsi_sell_threshold=rsi_sell,
        logger=logger
    )
    
    # Generate signals
    df_with_signals = strategy.generate_signals()
    
    # Run a simple backtest simulation
    initial_balance = 10000.0
    balance = initial_balance
    position = 0
    trade_log = []
    
    for i in range(len(df_with_signals)):
        price = df_with_signals["Close"].iloc[i]
        date = df_with_signals["Date"].iloc[i]
        
        # Buy signal
        if df_with_signals["Buy_Signal"].iloc[i] and position == 0:
            shares = int(balance // price)
            if shares > 0:
                balance -= shares * price
                position += shares
                trade_log.append(("BUY", date, price, shares))
                logger.info(f"BUY on {date}: {shares} shares at {price:.2f}")
        
        # Sell signal
        elif df_with_signals["Sell_Signal"].iloc[i] and position > 0:
            balance += position * price
            trade_log.append(("SELL", date, price, position))
            logger.info(f"SELL on {date}: {position} shares at {price:.2f}")
            position = 0
    
    # Calculate final portfolio value
    final_balance = balance + (position * df_with_signals["Close"].iloc[-1])
    total_return = ((final_balance - initial_balance) / initial_balance) * 100
    
    # Print performance metrics
    logger.info(f"Initial balance: ${initial_balance:.2f}")
    logger.info(f"Final balance: ${final_balance:.2f}")
    logger.info(f"Total return: {total_return:.2f}%")
    logger.info(f"Total trades: {len(trade_log)}")
    
    # Plot results
    plt.figure(figsize=(16, 12))
    
    # Price subplot with buy/sell signals
    plt.subplot(3, 1, 1)
    plt.plot(df_with_signals["Date"], df_with_signals["Close"], label="Price", alpha=0.5)
    
    # Plot buy signals
    buy_signals = df_with_signals[df_with_signals["Buy_Signal"]]
    plt.scatter(buy_signals["Date"], buy_signals["Close"], 
                marker='^', color='green', s=100, label='Buy Signal')
    
    # Plot sell signals
    sell_signals = df_with_signals[df_with_signals["Sell_Signal"]]
    plt.scatter(sell_signals["Date"], sell_signals["Close"], 
                marker='v', color='red', s=100, label='Sell Signal')
    
    plt.title(f"RSI+MACD Combined Strategy: {symbol}")
    plt.ylabel("Price ($)")
    plt.legend()
    plt.grid(True)
    
    # RSI subplot
    plt.subplot(3, 1, 2)
    plt.plot(df_with_signals["Date"], df_with_signals["RSI"], label='RSI', color='purple')
    plt.axhline(y=rsi_buy, color='green', linestyle='--', alpha=0.5, label=f'Oversold ({rsi_buy})')
    plt.axhline(y=rsi_sell, color='red', linestyle='--', alpha=0.5, label=f'Overbought ({rsi_sell})')
    plt.axhline(y=50, color='black', linestyle='-', alpha=0.2)
    plt.title("RSI Indicator")
    plt.ylabel("RSI Value")
    plt.ylim(0, 100)
    plt.legend()
    plt.grid(True)
    
    # MACD subplot
    plt.subplot(3, 1, 3)
    plt.plot(df_with_signals["Date"], df_with_signals["MACD"], label='MACD')
    plt.plot(df_with_signals["Date"], df_with_signals["MACD_Signal"], label='Signal Line')
    plt.bar(df_with_signals["Date"], df_with_signals["MACD_Histogram"], color='gray', alpha=0.3, label='Histogram')
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.2)
    plt.title("MACD Indicator")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(f"{symbol}_rsi_macd_combined.png")
    logger.info(f"Plot saved as {symbol}_rsi_macd_combined.png")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combined RSI+MACD Strategy Backtest")
    parser.add_argument("--symbol", type=str, default="AAPL", help="Stock symbol (e.g., AAPL)")
    parser.add_argument("--start_date", type=str, default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default=datetime.today().strftime('%Y-%m-%d'), help="End date (YYYY-MM-DD)")
    parser.add_argument("--rsi_window", type=int, default=14, help="RSI window period")
    parser.add_argument("--macd_fast", type=int, default=12, help="MACD fast period")
    parser.add_argument("--macd_slow", type=int, default=26, help="MACD slow period")
    parser.add_argument("--macd_signal", type=int, default=9, help="MACD signal period")
    parser.add_argument("--rsi_buy", type=int, default=30, help="RSI oversold threshold")
    parser.add_argument("--rsi_sell", type=int, default=70, help="RSI overbought threshold")
    
    args = parser.parse_args()
    run_backtest(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        rsi_window=args.rsi_window,
        macd_fast=args.macd_fast,
        macd_slow=args.macd_slow,
        macd_signal=args.macd_signal,
        rsi_buy=args.rsi_buy,
        rsi_sell=args.rsi_sell
    ) 