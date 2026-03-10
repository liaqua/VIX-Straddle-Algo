#VVIX-Based Energy Pairs Trading Strategy
An automated trading algorithm that uses volatility-of-volatility signals to execute pairs trades in energy commodity ETFs.
Strategy Overview
This algorithm monitors the CBOE VVIX index (volatility of VIX) to generate trading signals for a long/short position in energy ETFs:

Long: UGA (United States Gasoline Fund)
Short: USO (United States Oil Fund)

Signal Logic
Entry Conditions (both must be met):

VVIX z-score > 1.5 (20-day rolling window)
Current day is Thursday or Friday

Exit Conditions:

VVIX z-score < 0.5

Technical Implementation

Data Source: Yahoo Finance API for historical VVIX data
Execution: Alpaca Trading API (paper trading)
Position Sizing: Fixed 10 shares per leg
Order Type: Market orders, day duration

Libraries Used

pandas - Data manipulation and rolling statistics
numpy - Numerical computations
yfinance - Market data retrieval
alpaca-py - Trade execution

Files

strategy.py - Main strategy logic and execution

Risk Disclosure
This is an experimental algorithmic trading strategy for educational purposes only. Past performance does not guarantee future results. Trading involves substantial risk of loss.
