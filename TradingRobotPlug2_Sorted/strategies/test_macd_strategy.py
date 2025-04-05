#!/usr/bin/env python3
"""
Test for MACD Strategy

This script tests the MACD strategy implementation with a simple example.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from strategies.macd_strategy import StandardMACDStrategy

def test_macd_strategy():
    """Test the MACD strategy with sample data."""
    # Generate sample price data (trending up then down)
    x = np.linspace(0, 4*np.pi, 200)
    prices = 100 + 20 * np.sin(x) + np.linspace(0, 40, 200)
    
    # Create the strategy
    macd_strategy = StandardMACDStrategy()
    
    # Generate signals
    signals_df = macd_strategy.generate_signals(prices)
    
    # Print summary
    buy_signals = signals_df['buy_signal'].sum()
    sell_signals = signals_df['sell_signal'].sum()
    print(f"Generated {buy_signals} buy signals and {sell_signals} sell signals")
    
    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Price plot
    ax1.plot(signals_df['price'], label='Price')
    ax1.scatter(signals_df.index[signals_df['buy_signal']], 
                signals_df.loc[signals_df['buy_signal'], 'price'], 
                color='green', marker='^', s=100, label='Buy')
    ax1.scatter(signals_df.index[signals_df['sell_signal']], 
                signals_df.loc[signals_df['sell_signal'], 'price'], 
                color='red', marker='v', s=100, label='Sell')
    ax1.set_title('Price with Buy/Sell Signals')
    ax1.legend()
    
    # MACD plot
    ax2.plot(signals_df['macd'], label='MACD')
    ax2.plot(signals_df['signal'], label='Signal')
    ax2.bar(signals_df.index, signals_df['histogram'], color='gray', alpha=0.3, label='Histogram')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.2)
    ax2.set_title('MACD Indicator')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('macd_test_plot.png')
    print("Plot saved as 'macd_test_plot.png'")

    return signals_df

if __name__ == "__main__":
    test_macd_strategy() 