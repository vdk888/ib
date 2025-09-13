#!/usr/bin/env python3
"""
Configuration file for Uncle Stock Portfolio system
"""

# Portfolio Targeting Configuration
MAX_RANKED_STOCKS = 30  # Only top N ranked stocks get allocation, others get 0%

# Allocation Configuration
MAX_ALLOCATION = 0.10  # 10% - allocation for rank 1 stock
MIN_ALLOCATION = 0.01  # 1% - allocation for worst ranked stock (rank MAX_RANKED_STOCKS)