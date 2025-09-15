#!/usr/bin/env python3
"""
Interactive Brokers API script to fetch account information
Gets account value, positions, and portfolio data from paper trading account
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time

class IBApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.account_summary = {}
        self.positions = []
        self.portfolio_items = []
        self.account_value = {}
        self.account_id = None

    def connectAck(self):
        super().connectAck()
        print("Connected to IB Gateway")
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        print("Connection closed")
        self.connected = False

    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        accounts = accountsList.split(",")
        self.account_id = accounts[0]
        print(f"Account ID: {self.account_id}")

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        self.account_summary[tag] = {"value": value, "currency": currency}
        print(f"Account Summary - {tag}: {value} {currency}")

    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        print("\n=== Account Summary Complete ===")

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        super().updateAccountValue(key, val, currency, accountName)
        self.account_value[key] = {"value": val, "currency": currency}

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        super().position(account, contract, position, avgCost)
        if position != 0:  # Only show non-zero positions
            pos_info = {
                "symbol": contract.symbol,
                "secType": contract.secType,
                "currency": contract.currency,
                "exchange": contract.exchange,
                "position": position,
                "avgCost": avgCost,
                "marketValue": position * avgCost
            }
            self.positions.append(pos_info)
            print(f"Position - {contract.symbol}: {position} shares @ ${avgCost:.2f} avg cost")

    def positionEnd(self):
        super().positionEnd()
        print("\n=== Positions Complete ===")

    def updatePortfolio(self, contract: Contract, position: float, marketPrice: float, marketValue: float, 
                       averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        super().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)
        if position != 0:  # Only show non-zero positions
            portfolio_item = {
                "symbol": contract.symbol,
                "position": position,
                "marketPrice": marketPrice,
                "marketValue": marketValue,
                "averageCost": averageCost,
                "unrealizedPNL": unrealizedPNL,
                "realizedPNL": realizedPNL
            }
            self.portfolio_items.append(portfolio_item)
            print(f"Portfolio - {contract.symbol}: {position} @ ${marketPrice:.2f} = ${marketValue:.2f} (PNL: ${unrealizedPNL:.2f})")

    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        print("\n=== Account Download Complete ===")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')

def print_summary(app):
    """Print formatted account summary"""
    print("\n" + "="*60)
    print("               ACCOUNT SUMMARY")
    print("="*60)
    
    # Total account value
    if "NetLiquidation" in app.account_summary:
        total_value = app.account_summary["NetLiquidation"]["value"]
        currency = app.account_summary["NetLiquidation"]["currency"]
        print(f"Total Account Value: ${float(total_value):,.2f} {currency}")
    
    # Available funds
    if "AvailableFunds" in app.account_summary:
        available = app.account_summary["AvailableFunds"]["value"]
        print(f"Available Funds: ${float(available):,.2f}")
    
    # Buying power
    if "BuyingPower" in app.account_summary:
        buying_power = app.account_summary["BuyingPower"]["value"]
        print(f"Buying Power: ${float(buying_power):,.2f}")
    
    print("\n" + "-"*60)
    print("               POSITIONS")
    print("-"*60)
    
    if app.portfolio_items:
        total_portfolio_value = 0
        for item in app.portfolio_items:
            print(f"{item['symbol']:>6}: {item['position']:>8.0f} shares @ ${item['marketPrice']:>8.2f} = ${item['marketValue']:>10.2f}")
            print(f"        Avg Cost: ${item['averageCost']:>8.2f} | P&L: ${item['unrealizedPNL']:>10.2f}")
            total_portfolio_value += item['marketValue']
            print()
        
        print(f"{'Total Portfolio Value:':>40} ${total_portfolio_value:>10.2f}")
    else:
        print("No positions found")
    
    print("="*60)

def main():
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=2)
    
    # Start message processing in separate thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for connection
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect to IB Gateway")
        return
    
    # Wait a moment for account ID
    time.sleep(2)
    
    if not app.account_id:
        print("No account ID received")
        return
    
    print(f"\nFetching data for account: {app.account_id}")
    print("-" * 50)
    
    # Request account summary
    app.reqAccountSummary(9001, "All", "NetLiquidation,TotalCashValue,SettledCash,AccruedCash,BuyingPower,EquityWithLoanValue,AvailableFunds")
    
    # Request positions
    app.reqPositions()
    
    # Request account updates
    app.reqAccountUpdates(True, app.account_id)
    
    # Wait for data to be received
    print("\nFetching account data...")
    time.sleep(5)
    
    # Cancel subscriptions
    app.cancelAccountSummary(9001)
    app.cancelPositions()
    app.reqAccountUpdates(False, app.account_id)
    
    # Print summary
    print_summary(app)
    
    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    main()