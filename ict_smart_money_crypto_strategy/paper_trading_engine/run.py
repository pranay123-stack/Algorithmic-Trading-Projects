#!/usr/bin/env python3
"""
Main runner script for ICT Smart Money Crypto Paper Trading Engine

This script provides a simple entry point to run the trading engine
without needing to use the -m flag.

Usage:
    python run.py
    python run.py --symbol BTC/USDT --timeframe 1h
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == '__main__':
    # Import and execute the paper trader module
    import runpy
    runpy.run_module('src.core_trading_strategy.paper_trader', run_name='__main__')
