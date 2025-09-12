#!/usr/bin/env python3
"""
History parser for Uncle Stock backtest results
Parses historical performance data from backtest CSV files and updates universe.json metadata
"""

import csv
import json
import os
from typing import Dict, List, Any
from config import UNCLE_STOCK_SCREENS

def parse_backtest_csv(csv_path: str, debug: bool = False) -> Dict[str, Any]:
    """
    Parse a backtest results CSV file to extract historical performance metrics
    
    Args:
        csv_path: Path to the backtest results CSV file
        
    Returns:
        Dict containing parsed performance metrics
    """
    if not os.path.exists(csv_path):
        return {"error": f"File not found: {csv_path}"}
    
    performance_data = {
        "metadata": {},
        "quarterly_performance": [],
        "statistics": {}
    }
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse metadata from the top section
        for line in lines[:13]:  # First 13 lines contain metadata
            if ',' in line and not line.startswith('sep='):
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    key = parts[0].strip('"')
                    value = parts[1].strip('"')
                    performance_data["metadata"][key] = value
        
        # Find the statistics headers (line 14)
        stats_line = None
        total_return_line = None
        yearly_return_line = None
        
        for i, line in enumerate(lines):
            if '"Return"' in line and '"Period SD"' in line:
                stats_line = i
                # Next lines should contain total return and yearly return
                if i + 1 < len(lines) and 'Total return' in lines[i + 1]:
                    total_return_line = i + 1
                if i + 2 < len(lines) and 'Yearly return' in lines[i + 2]:
                    yearly_return_line = i + 2
                break
        
        if stats_line is not None and total_return_line is not None and yearly_return_line is not None:
            # Parse statistics headers
            headers = [h.strip('"') for h in lines[stats_line].split(',')]
            
            # Parse total return data
            total_data = lines[total_return_line].split(',')
            yearly_data = lines[yearly_return_line].split(',')
            
            # Extract key statistics
            for i, header in enumerate(headers):
                if i < len(total_data) and i < len(yearly_data):
                    if header and header not in ['', ' ']:
                        performance_data["statistics"][f"{header}_total"] = total_data[i].strip('"')
                        performance_data["statistics"][f"{header}_yearly"] = yearly_data[i].strip('"')
        
        # Parse quarterly data by looking for "Quarter return" lines directly
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for Quarter return lines
            if 'Quarter return' in line:
                return_parts = line.split(',')
                if len(return_parts) >= 3:
                    # Extract data: First column is empty, second is "Quarter return", third is the return %
                    quarter_return = return_parts[2].strip('"')  # 3rd column has the return percentage
                    period_sd = return_parts[3].strip('"') if len(return_parts) > 3 else ""  # 4th column has SD
                    beta = return_parts[4].strip('"') if len(return_parts) > 4 else ""  # 5th column has beta
                    
                    # Find the corresponding quarter header (should be in previous lines)
                    quarter = ""
                    for j in range(i-1, max(i-5, -1), -1):  # Look back up to 5 lines
                        prev_line = lines[j].strip()
                        if ' Q' in prev_line and 'Stocks' in prev_line:
                            quarter = prev_line.split(',')[0].strip('"')
                            break
                    
                    if debug:
                        print(f"Found quarter: {quarter}, return: {quarter_return}, sd: {period_sd}")
                    
                    if quarter:  # Only add if we found a quarter
                        quarterly_entry = {
                            "quarter": quarter,
                            "return": quarter_return,
                            "period_sd": period_sd,
                            "beta": beta
                        }
                        
                        # Add benchmark return (usually last non-empty column)
                        for j in range(len(return_parts)-1, -1, -1):
                            benchmark = return_parts[j].strip('"')
                            if benchmark and benchmark != "" and "%" in benchmark and benchmark != quarter_return:
                                quarterly_entry["benchmark_return"] = benchmark
                                break
                        
                        performance_data["quarterly_performance"].append(quarterly_entry)
        
        return performance_data
        
    except Exception as e:
        return {"error": f"Error parsing CSV: {str(e)}"}

def get_all_backtest_data() -> Dict[str, Dict[str, Any]]:
    """
    Parse all backtest CSV files for configured screeners
    
    Returns:
        Dict with screener keys and their parsed performance data
    """
    all_data = {}
    
    for key, screen_name in UNCLE_STOCK_SCREENS.items():
        # Convert screen name to filename format
        safe_name = screen_name.replace(' ', '_').replace('/', '_')
        csv_path = f"data/files_exports/{safe_name}_backtest_results.csv"
        
        print(f"Parsing backtest data for {screen_name}...")
        performance_data = parse_backtest_csv(csv_path)
        
        if "error" in performance_data:
            print(f"X Error parsing {screen_name}: {performance_data['error']}")
        else:
            print(f"+ Parsed {len(performance_data['quarterly_performance'])} quarters for {screen_name}")
        
        all_data[key] = performance_data
    
    return all_data

def update_universe_with_history() -> bool:
    """
    Update universe.json with historical performance data in metadata section
    
    Returns:
        bool: True if successful, False otherwise
    """
    universe_path = "data/universe.json"
    
    if not os.path.exists(universe_path):
        print("X universe.json not found - run step 2 first")
        return False
    
    try:
        # Load existing universe data
        with open(universe_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)
        
        # Get all backtest data
        backtest_data = get_all_backtest_data()
        
        # Update metadata with historical performance
        if "metadata" not in universe_data:
            universe_data["metadata"] = {}
        
        universe_data["metadata"]["historical_performance"] = {}
        
        for key, performance_data in backtest_data.items():
            screen_name = UNCLE_STOCK_SCREENS[key]
            
            if "error" not in performance_data:
                # Add comprehensive performance metrics to metadata
                screen_performance = {
                    "screen_name": screen_name,
                    "backtest_metadata": performance_data["metadata"],
                    "key_statistics": {},
                    "quarterly_summary": {
                        "total_quarters": len(performance_data["quarterly_performance"]),
                        "avg_quarterly_return": None,
                        "quarterly_std": None
                    },
                    "quarterly_data": performance_data["quarterly_performance"]
                }
                
                # Extract key statistics
                stats = performance_data["statistics"]
                for stat_key, value in stats.items():
                    if "Return_yearly" in stat_key or "Period SD_yearly" in stat_key:
                        clean_key = stat_key.replace("_yearly", "").replace(" ", "_").lower()
                        screen_performance["key_statistics"][clean_key] = value
                
                # Calculate quarterly averages
                quarterly_returns = []
                quarterly_stds = []
                
                for quarter in performance_data["quarterly_performance"]:
                    try:
                        ret = quarter.get("return", "").replace("%", "")
                        if ret and ret != "":
                            quarterly_returns.append(float(ret))
                    except (ValueError, AttributeError):
                        pass
                    
                    try:
                        std = quarter.get("period_sd", "").replace("%", "")
                        if std and std != "":
                            quarterly_stds.append(float(std))
                    except (ValueError, AttributeError):
                        pass
                
                if quarterly_returns:
                    screen_performance["quarterly_summary"]["avg_quarterly_return"] = f"{sum(quarterly_returns)/len(quarterly_returns):.2f}%"
                
                if quarterly_stds:
                    screen_performance["quarterly_summary"]["quarterly_std"] = f"{sum(quarterly_stds)/len(quarterly_stds):.2f}%"
                
                universe_data["metadata"]["historical_performance"][key] = screen_performance
            else:
                universe_data["metadata"]["historical_performance"][key] = {
                    "screen_name": screen_name,
                    "error": performance_data["error"]
                }
        
        # Save updated universe data
        with open(universe_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2, ensure_ascii=False)
        
        print("+ Updated universe.json with historical performance data")
        return True
        
    except Exception as e:
        print(f"X Error updating universe.json: {e}")
        return False

def display_performance_summary():
    """Display a summary of the parsed performance data"""
    backtest_data = get_all_backtest_data()
    
    print("\n" + "="*60)
    print("HISTORICAL PERFORMANCE SUMMARY")
    print("="*60)
    
    for key, data in backtest_data.items():
        screen_name = UNCLE_STOCK_SCREENS[key]
        print(f"\n{screen_name}:")
        
        if "error" in data:
            print(f"  X Error: {data['error']}")
            continue
        
        # Display key metadata
        metadata = data.get("metadata", {})
        print(f"  Backtest Period: {metadata.get('Begin', 'N/A')} - {metadata.get('End', 'N/A')}")
        print(f"  Rebalance: {metadata.get('Rebalance timing', 'N/A')}")
        print(f"  Number of Stocks: {metadata.get('Number of stocks', 'N/A')}")
        
        # Display key statistics
        stats = data.get("statistics", {})
        yearly_return = stats.get("Return_yearly", "N/A")
        yearly_std = stats.get("(Avg of) Period SD_yearly", "N/A")
        sharpe = stats.get("Sharpe ratio_yearly", "N/A")
        
        print(f"  Yearly Return: {yearly_return}")
        print(f"  Yearly Std Dev: {yearly_std}")
        print(f"  Sharpe Ratio: {sharpe}")
        
        # Display quarterly summary
        quarterly_data = data.get("quarterly_performance", [])
        print(f"  Total Quarters: {len(quarterly_data)}")
        
        if quarterly_data:
            # Calculate some summary stats
            returns = []
            for q in quarterly_data:
                try:
                    ret = q.get("return", "").replace("%", "")
                    if ret:
                        returns.append(float(ret))
                except (ValueError, AttributeError):
                    pass
            
            if returns:
                avg_return = sum(returns) / len(returns)
                print(f"  Avg Quarterly Return: {avg_return:.2f}%")

if __name__ == "__main__":
    print("Uncle Stock Historical Performance Parser")
    print("="*50)
    
    # Display performance summary
    display_performance_summary()
    
    # Update universe.json
    print("\n" + "="*50)
    print("UPDATING UNIVERSE.JSON")
    print("="*50)
    
    success = update_universe_with_history()
    
    if success:
        print("\nHistorical performance data successfully added to universe.json metadata!")
    else:
        print("\nFailed to update universe.json with historical data.")