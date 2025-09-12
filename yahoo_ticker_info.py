#!/usr/bin/env python3
"""
Get Yahoo Finance info for specific tickers
"""

import yfinance as yf
import pandas as pd

def get_ticker_info():
    tickers = [
        "6420.T",    # Fukushima Industries Corp 
        "6490.T",    # Nippon Pillar Packing Co Ltd
        "4055.T",    # T&S inc.
        "9564.T",    # FCE Holdings Inc.
        "ADMCM.HE",  # Admicom Oyj
        "6037.T",    # Firstlogic Inc
        "MLHOT.PA",  # Hotelim Société Anonyme
        "2331.T",    # Sohgo Security Services Co Ltd
        "PROF.AT",   # Profile Systems & Software SA
        "FLEXO.AT",  # Flexopack Societe Anonyme
        "OR.PA",     # L'Oréal S.A.
        "3663.T",    # ArtSpark Holdings Inc
        "2154.T",    # BeNextYumeshin Group Co
        "3661.T"     # M-up Inc
    ]
    
    print("Fetching Yahoo Finance data for tickers...")
    print("="*80)
    
    for ticker in tickers:
        print(f"\n{ticker}:")
        print("-" * 40)
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get basic info
            name = info.get('longName', info.get('shortName', 'N/A'))
            sector = info.get('sector', 'N/A')
            industry = info.get('industry', 'N/A')
            country = info.get('country', 'N/A')
            currency = info.get('currency', 'N/A')
            exchange = info.get('exchange', 'N/A')
            
            # Get price info
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
            market_cap = info.get('marketCap', 'N/A')
            
            # Format market cap
            if market_cap != 'N/A' and market_cap:
                if market_cap >= 1e9:
                    market_cap_str = f"{market_cap/1e9:.1f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"{market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"{market_cap:,.0f}"
            else:
                market_cap_str = "N/A"
            
            print(f"Name: {name}")
            print(f"Country: {country}")
            print(f"Currency: {currency}")
            print(f"Exchange: {exchange}")
            print(f"Sector: {sector}")
            print(f"Industry: {industry}")
            print(f"Current Price: {current_price} {currency}")
            print(f"Market Cap: {market_cap_str} {currency}")
            
            # Check if data exists
            if name == 'N/A':
                print("⚠️  Limited data available - ticker might be delisted or incorrect")
                
        except Exception as e:
            print(f"❌ Error fetching data: {str(e)}")
            print("Ticker might be delisted, incorrect, or not available on Yahoo Finance")
    
    print("\n" + "="*80)
    print("Yahoo Finance data fetch complete")

if __name__ == "__main__":
    get_ticker_info()