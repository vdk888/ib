"""
Portfolio Optimizer Service Implementation
Wraps src/portfolio_optimizer.py functions with Interface-First Design
Maintains 100% behavioral compatibility with CLI implementation
"""

import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Any
import os
from ..interfaces import IPortfolioOptimizer
from ...core.exceptions import ValidationError


class PortfolioOptimizerService(IPortfolioOptimizer):
    """
    Portfolio optimization service implementing modern portfolio theory
    Wraps legacy portfolio_optimizer.py functions while maintaining exact behavior
    """

    def __init__(self, universe_path: str = "data/universe.json"):
        """
        Initialize portfolio optimizer service

        Args:
            universe_path: Path to universe.json file
        """
        self.universe_path = universe_path

    def load_universe_data(self) -> Dict[str, Any]:
        """
        Load universe.json data from data directory
        Exact replication of src/portfolio_optimizer.py:load_universe_data()
        """
        if not os.path.exists(self.universe_path):
            raise FileNotFoundError("universe.json not found - run steps 2 and 3 first")

        with open(self.universe_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_quarterly_returns(self, universe_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract quarterly returns for each screener from universe data
        Exact replication of src/portfolio_optimizer.py:extract_quarterly_returns()
        """
        historical_data = universe_data['metadata']['historical_performance']
        returns_data = {}

        for screener_key, screener_data in historical_data.items():
            if 'quarterly_data' in screener_data:
                quarterly_data = screener_data['quarterly_data']

                # Extract returns and convert to float
                returns = []
                quarters = []

                for quarter in quarterly_data:
                    try:
                        # Remove % sign and convert to decimal
                        return_str = quarter['return'].replace('%', '')
                        return_float = float(return_str) / 100.0  # Convert percentage to decimal
                        returns.append(return_float)
                        quarters.append(quarter['quarter'])
                    except (ValueError, KeyError):
                        continue

                if returns:
                    returns_data[screener_key] = returns

        # Create DataFrame - all screeners should have same number of quarters
        df = pd.DataFrame(returns_data)
        df.index = quarters[:len(df)]  # Use quarters as index

        return df

    def calculate_portfolio_stats(
        self,
        weights: np.ndarray,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.02/4
    ) -> Tuple[float, float, float]:
        """
        Calculate portfolio statistics
        Exact replication of src/portfolio_optimizer.py:calculate_portfolio_stats()
        """
        # Calculate portfolio returns for each quarter
        portfolio_returns = (returns * weights).sum(axis=1)

        # Annualized statistics (multiply quarterly by 4)
        expected_return = portfolio_returns.mean() * 4
        volatility = portfolio_returns.std() * np.sqrt(4)

        # Sharpe ratio
        sharpe_ratio = (expected_return - risk_free_rate * 4) / volatility if volatility > 0 else 0

        return expected_return, volatility, sharpe_ratio

    def _negative_sharpe_ratio(
        self,
        weights: np.ndarray,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.02/4
    ) -> float:
        """
        Objective function: negative Sharpe ratio (for minimization)
        Exact replication of src/portfolio_optimizer.py:negative_sharpe_ratio()
        """
        _, _, sharpe = self.calculate_portfolio_stats(weights, returns, risk_free_rate)
        return -sharpe  # Negative because we want to maximize Sharpe ratio

    def optimize_portfolio(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.02/4
    ) -> Dict[str, Any]:
        """
        Optimize portfolio to maximize Sharpe ratio
        Exact replication of src/portfolio_optimizer.py:optimize_portfolio()
        """
        n_assets = len(returns.columns)

        # Constraints and bounds
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        bounds = tuple((0, 1) for _ in range(n_assets))  # Weights between 0 and 1 (long only)

        # Initial guess: equal weights
        initial_weights = np.array([1/n_assets] * n_assets)

        # Optimization
        result = minimize(
            self._negative_sharpe_ratio,
            initial_weights,
            args=(returns, risk_free_rate),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            print(f"Optimization warning: {result.message}")

        optimal_weights = result.x
        expected_return, volatility, sharpe_ratio = self.calculate_portfolio_stats(
            optimal_weights, returns, risk_free_rate
        )

        # Calculate correlation matrix
        correlation_matrix = returns.corr()

        # Individual screener statistics
        individual_stats = {}
        for col in returns.columns:
            col_returns = returns[col]
            ann_return = col_returns.mean() * 4
            ann_vol = col_returns.std() * np.sqrt(4)
            individual_sharpe = (ann_return - risk_free_rate * 4) / ann_vol if ann_vol > 0 else 0

            individual_stats[col] = {
                'annual_return': ann_return,
                'annual_volatility': ann_vol,
                'sharpe_ratio': individual_sharpe
            }

        return {
            'optimal_weights': dict(zip(returns.columns, optimal_weights)),
            'portfolio_stats': {
                'expected_annual_return': expected_return,
                'annual_volatility': volatility,
                'sharpe_ratio': sharpe_ratio
            },
            'individual_stats': individual_stats,
            'correlation_matrix': correlation_matrix.to_dict(),
            'optimization_success': result.success,
            'optimization_message': result.message if hasattr(result, 'message') else 'Success'
        }

    def update_universe_with_portfolio(
        self,
        universe_data: Dict[str, Any],
        portfolio_results: Dict[str, Any]
    ) -> None:
        """
        Update universe.json with portfolio optimization results
        Exact replication of src/portfolio_optimizer.py:update_universe_with_portfolio()
        """
        if 'portfolio_optimization' not in universe_data['metadata']:
            universe_data['metadata']['portfolio_optimization'] = {}

        universe_data['metadata']['portfolio_optimization'] = {
            'optimal_allocations': {k: float(v) for k, v in portfolio_results['optimal_weights'].items()},
            'portfolio_performance': {k: float(v) for k, v in portfolio_results['portfolio_stats'].items()},
            'individual_screener_stats': {
                screener: {stat: float(value) for stat, value in stats.items()}
                for screener, stats in portfolio_results['individual_stats'].items()
            },
            'correlation_matrix': {
                k: {k2: float(v2) for k2, v2 in v.items()}
                for k, v in portfolio_results['correlation_matrix'].items()
            },
            'optimization_details': {
                'success': bool(portfolio_results['optimization_success']),
                'message': str(portfolio_results['optimization_message']),
                'method': 'SLSQP (Sequential Least Squares Programming)',
                'objective': 'Maximize Sharpe Ratio',
                'constraints': 'Long-only (weights >= 0), weights sum to 1'
            }
        }

    def save_universe(self, universe_data: Dict[str, Any]) -> None:
        """
        Save updated universe data
        Exact replication of src/portfolio_optimizer.py:save_universe()
        """
        with open(self.universe_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2, ensure_ascii=False)

    def display_portfolio_results(self, portfolio_results: Dict[str, Any]) -> None:
        """
        Display portfolio optimization results
        Exact replication of src/portfolio_optimizer.py:display_portfolio_results()
        """
        print("=" * 60)
        print("PORTFOLIO OPTIMIZATION RESULTS")
        print("=" * 60)

        # Optimal allocations
        print("\nOptimal Portfolio Allocations:")
        print("-" * 30)
        for screener, weight in portfolio_results['optimal_weights'].items():
            print(f"{screener:<20}: {weight*100:>6.2f}%")

        # Portfolio performance
        stats = portfolio_results['portfolio_stats']
        print(f"\nOptimal Portfolio Performance:")
        print("-" * 30)
        print(f"Expected Annual Return: {stats['expected_annual_return']*100:>6.2f}%")
        print(f"Annual Volatility:      {stats['annual_volatility']*100:>6.2f}%")
        print(f"Sharpe Ratio:           {stats['sharpe_ratio']:>6.2f}")

        # Individual screener stats
        print(f"\nIndividual Screener Performance:")
        print("-" * 50)
        print(f"{'Screener':<20} {'Return':<8} {'Vol':<8} {'Sharpe':<8}")
        print("-" * 50)

        for screener, stats in portfolio_results['individual_stats'].items():
            print(f"{screener:<20} {stats['annual_return']*100:>6.2f}% {stats['annual_volatility']*100:>6.2f}% {stats['sharpe_ratio']:>6.2f}")

        # Correlation matrix
        print(f"\nCorrelation Matrix:")
        print("-" * 30)
        correlation_df = pd.DataFrame(portfolio_results['correlation_matrix'])
        print(correlation_df.round(3))

        # Optimization details
        print(f"\nOptimization Details:")
        print("-" * 30)
        print(f"Success: {portfolio_results['optimization_success']}")
        print(f"Message: {portfolio_results['optimization_message']}")

    def main(self) -> bool:
        """
        Main portfolio optimization function
        Exact replication of src/portfolio_optimizer.py:main()
        """
        print("Uncle Stock Portfolio Optimizer")
        print("=" * 60)

        try:
            # Load universe data
            print("Loading universe data...")
            universe_data = self.load_universe_data()

            # Extract quarterly returns
            print("Extracting quarterly returns...")
            returns_df = self.extract_quarterly_returns(universe_data)

            print(f"Found {len(returns_df)} quarters of data for {len(returns_df.columns)} screeners")
            print(f"Screeners: {list(returns_df.columns)}")
            print(f"Date range: {returns_df.index[0]} to {returns_df.index[-1]}")

            # Optimize portfolio
            print("\nOptimizing portfolio allocation...")
            portfolio_results = self.optimize_portfolio(returns_df)

            # Display results
            self.display_portfolio_results(portfolio_results)

            # Update universe.json
            print(f"\nUpdating universe.json with portfolio optimization results...")
            self.update_universe_with_portfolio(universe_data, portfolio_results)
            self.save_universe(universe_data)

            print("+ Portfolio optimization complete!")
            print("+ Results saved to universe.json metadata")

        except Exception as e:
            print(f"X Error in portfolio optimization: {e}")
            return False

        return True