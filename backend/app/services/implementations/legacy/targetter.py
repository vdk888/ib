#!/usr/bin/env python3
"""
Targetter for Uncle Stock screener portfolios
Calculates final stock allocations based on:
1. Screener allocation from portfolio optimizer
2. Individual stock performance ranking within each screener (180d price change)
3. Linear allocation within screener (best: 10%, worst: 1%)
"""

import json
import os
from typing import Dict, List, Any, Tuple

# Import settings from the new configuration system
from ....core.config import settings

# Extract constants from settings for backward compatibility
MAX_RANKED_STOCKS = settings.portfolio.max_ranked_stocks
MAX_ALLOCATION = settings.portfolio.max_allocation
MIN_ALLOCATION = settings.portfolio.min_allocation

def load_universe_data() -> Dict[str, Any]:
    """Load universe.json data"""
    universe_path = "data/universe.json"
    if not os.path.exists(universe_path):
        raise FileNotFoundError("universe.json not found - run previous steps first")
    
    with open(universe_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_screener_allocations(universe_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract screener allocations from portfolio optimization results
    
    Returns:
        Dict with screener keys and their target allocations
    """
    portfolio_opt = universe_data.get('metadata', {}).get('portfolio_optimization', {})
    optimal_allocations = portfolio_opt.get('optimal_allocations', {})
    
    if not optimal_allocations:
        raise ValueError("No portfolio optimization results found - run portfolio optimizer first")
    
    print(f"+ Found screener allocations:")
    for screener, allocation in optimal_allocations.items():
        print(f"  {screener}: {allocation*100:.2f}%")
    
    return optimal_allocations

def parse_180d_change(price_change_str: str) -> float:
    """
    Parse price_180d_change string to float
    
    Args:
        price_change_str: String like "12.45%" or "-5.23%"
        
    Returns:
        Float value (e.g., 12.45 or -5.23)
    """
    try:
        # Remove % sign and convert to float
        return float(price_change_str.replace('%', ''))
    except (ValueError, AttributeError):
        return 0.0  # Default to 0 if parsing fails

def rank_stocks_in_screener(stocks: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int, float]]:
    """
    Rank stocks within a screener by 180d price change performance
    
    Args:
        stocks: List of stock dictionaries
        
    Returns:
        List of tuples: (stock_dict, rank, performance)
        Rank 1 = best performing, highest rank number = worst performing
    """
    # Extract performance and create (stock, performance) pairs
    stock_performance = []
    for stock in stocks:
        performance = parse_180d_change(stock.get('price_180d_change', '0%'))
        stock_performance.append((stock, performance))
    
    # Sort by performance descending (best first)
    stock_performance.sort(key=lambda x: x[1], reverse=True)
    
    # Add ranks (1 = best, n = worst)
    ranked_stocks = []
    for rank, (stock, performance) in enumerate(stock_performance, 1):
        ranked_stocks.append((stock, rank, performance))
    
    return ranked_stocks

def calculate_pocket_allocation(rank: int, total_stocks: int) -> float:
    """
    Calculate pocket allocation within screener based on rank
    Only top MAX_RANKED_STOCKS get allocation: Rank 1 gets MAX_ALLOCATION%, rank MAX_RANKED_STOCKS gets MIN_ALLOCATION%
    Ranks beyond MAX_RANKED_STOCKS get 0%

    Args:
        rank: Stock rank (1 = best)
        total_stocks: Total number of stocks in screener

    Returns:
        Pocket allocation percentage (0.00 to MAX_ALLOCATION)
    """
    # Stocks ranked beyond MAX_RANKED_STOCKS get 0% allocation
    if rank > MAX_RANKED_STOCKS:
        return 0.0

    # Single stock in top MAX_RANKED_STOCKS gets max allocation
    if total_stocks == 1 or MAX_RANKED_STOCKS == 1:
        return MAX_ALLOCATION

    # Linear interpolation from MAX_ALLOCATION (rank 1) to MIN_ALLOCATION (rank MAX_RANKED_STOCKS)
    # Use min(MAX_RANKED_STOCKS, total_stocks) to handle cases where screener has fewer stocks than MAX_RANKED_STOCKS
    effective_max_rank = min(MAX_RANKED_STOCKS, total_stocks)

    if effective_max_rank == 1:
        return MAX_ALLOCATION

    # Calculate allocation: best gets MAX_ALLOCATION, worst ranked stock gets MIN_ALLOCATION
    allocation = MAX_ALLOCATION - ((rank - 1) / (effective_max_rank - 1)) * (MAX_ALLOCATION - MIN_ALLOCATION)

    return allocation

def calculate_final_allocations(universe_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate final allocations for all stocks
    
    Returns:
        Dict with stock tickers as keys and allocation data as values
    """
    # Get screener allocations from optimizer
    screener_allocations = extract_screener_allocations(universe_data)
    
    final_allocations = {}
    
    print(f"\n{'='*60}")
    print("CALCULATING FINAL STOCK ALLOCATIONS")
    print(f"{'='*60}")
    
    # Process each screener
    for screen_key, screen_data in universe_data.get('screens', {}).items():
        screen_name = screen_data.get('name', screen_key)
        stocks = screen_data.get('stocks', [])
        
        if not stocks:
            print(f"\nX {screen_name}: No stocks found")
            continue
        
        # Get screener allocation (handle different key formats)
        screener_target = 0.0
        for alloc_key, alloc_value in screener_allocations.items():
            if alloc_key == screen_key or alloc_key.replace('_', ' ').lower() == screen_name.lower():
                screener_target = alloc_value
                break
        
        print(f"\n{screen_name} (Target: {screener_target*100:.2f}%):")
        print(f"  Processing {len(stocks)} stocks...")
        
        # Rank stocks by 180d performance
        ranked_stocks = rank_stocks_in_screener(stocks)
        
        # Calculate allocations for each stock
        for stock, rank, performance in ranked_stocks:
            ticker = stock.get('ticker', 'UNKNOWN')
            
            # Calculate pocket allocation within screener
            pocket_allocation = calculate_pocket_allocation(rank, len(stocks))
            
            # Calculate final allocation
            final_allocation = screener_target * pocket_allocation
            
            # Store allocation data
            final_allocations[ticker] = {
                'ticker': ticker,
                'screener': screen_name,
                'rank': rank,
                'performance_180d': performance,
                'pocket_allocation': pocket_allocation,
                'screener_target': screener_target,
                'final_allocation': final_allocation
            }
            
            print(f"  {rank:2d}. {ticker:<12} | {performance:+6.2f}% | Pocket: {pocket_allocation*100:4.1f}% | Final: {final_allocation*100:5.2f}%")
    
    return final_allocations

def update_universe_with_allocations(universe_data: Dict[str, Any], final_allocations: Dict[str, Dict[str, Any]]) -> bool:
    """
    Update universe.json with final allocation data
    
    Args:
        universe_data: Universe data dictionary
        final_allocations: Final allocation data for each ticker
        
    Returns:
        bool: True if successful, False otherwise
    """
    updated_count = 0
    
    try:
        # Update stocks in screens
        for screen_key, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                ticker = stock.get('ticker')
                if ticker in final_allocations:
                    alloc_data = final_allocations[ticker]
                    
                    # Add new fields to stock
                    stock['rank'] = alloc_data['rank']
                    stock['allocation_target'] = alloc_data['pocket_allocation']
                    stock['screen_target'] = alloc_data['screener_target']
                    stock['final_target'] = alloc_data['final_allocation']
                    
                    updated_count += 1
        
        # Update stocks in all_stocks
        for ticker, stock in universe_data.get('all_stocks', {}).items():
            if ticker in final_allocations:
                alloc_data = final_allocations[ticker]
                
                # Add new fields to stock
                stock['rank'] = alloc_data['rank']
                stock['allocation_target'] = alloc_data['pocket_allocation']
                stock['screen_target'] = alloc_data['screener_target']
                stock['final_target'] = alloc_data['final_allocation']
        
        print(f"\n+ Updated {updated_count} stocks with allocation data")
        return True
        
    except Exception as e:
        print(f"X Error updating stocks with allocations: {e}")
        return False

def save_universe(universe_data: Dict[str, Any]) -> None:
    """Save updated universe data"""
    universe_path = "data/universe.json"
    with open(universe_path, 'w', encoding='utf-8') as f:
        json.dump(universe_data, f, indent=2, ensure_ascii=False)

def display_allocation_summary(final_allocations: Dict[str, Dict[str, Any]]) -> None:
    """Display summary of final allocations"""
    print(f"\n{'='*80}")
    print("FINAL ALLOCATION SUMMARY")
    print(f"{'='*80}")
    
    # Sort by final allocation descending
    sorted_allocations = sorted(final_allocations.items(), key=lambda x: x[1]['final_allocation'], reverse=True)
    
    print(f"{'Rank':<4} {'Ticker':<12} {'Screener':<15} {'180d Perf':<10} {'Pocket':<8} {'Final':<8}")
    print("-" * 80)
    
    total_allocation = 0.0
    for ticker, data in sorted_allocations:
        print(f"{data['rank']:<4} {ticker:<12} {data['screener'][:14]:<15} "
              f"{data['performance_180d']:+7.2f}% {data['pocket_allocation']*100:>6.1f}% {data['final_allocation']*100:>6.2f}%")
        total_allocation += data['final_allocation']
    
    print("-" * 80)
    print(f"{'TOTAL':<52} {total_allocation*100:>6.2f}%")
    
    # Display top 10 allocations
    print(f"\nTOP 10 FINAL ALLOCATIONS:")
    print("-" * 50)
    for i, (ticker, data) in enumerate(sorted_allocations[:10], 1):
        print(f"{i:2d}. {ticker:<12} {data['final_allocation']*100:>6.2f}% ({data['screener']}, Rank {data['rank']})")

def main():
    """Main targetter function"""
    print("Uncle Stock Portfolio Targetter")
    print("=" * 60)
    
    try:
        # Load universe data
        print("Loading universe data...")
        universe_data = load_universe_data()
        
        # Calculate final allocations
        final_allocations = calculate_final_allocations(universe_data)
        
        if not final_allocations:
            print("X No allocations calculated")
            return False
        
        # Display summary
        display_allocation_summary(final_allocations)
        
        # Update universe.json
        print(f"\nUpdating universe.json with allocation data...")
        success = update_universe_with_allocations(universe_data, final_allocations)
        
        if success:
            # Save updated data
            save_universe(universe_data)
            print("\n+ Portfolio targeting complete!")
            print("+ Results saved to universe.json")
            print("+ Each stock now has: rank, allocation_target, screen_target, final_target")
        else:
            print("\nX Failed to update universe.json with allocation data")
        
        return success
        
    except Exception as e:
        print(f"X Error in portfolio targetter: {e}")
        return False

if __name__ == "__main__":
    main()