#!/usr/bin/env python3
"""
Interactive Brokers trading script that combines account fetching and order placement
Can fetch account info, positions, and place buy/sell orders
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time

class IBTradingApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.nextorderId = None
        
        # Account data
        self.account_summary = {}
        self.positions = []
        self.portfolio_items = []
        self.account_value = {}
        self.account_id = None
        
        # Order tracking
        self.orders = {}

    def connectAck(self):
        super().connectAck()
        print("Connected to IB Gateway")
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        print("Connection closed")
        self.connected = False

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId
        print(f'Next valid order ID: {self.nextorderId}')

    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        accounts = accountsList.split(",")
        self.account_id = accounts[0]
        print(f"Account ID: {self.account_id}")

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        self.account_summary[tag] = {"value": value, "currency": currency}

    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        print("Account summary received")

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

    def positionEnd(self):
        super().positionEnd()
        print("Positions received")

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

    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        print("Account data download complete")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f'Order {orderId} Status: {status}, Filled: {filled}, Remaining: {remaining}, Avg Fill Price: {avgFillPrice}')
        self.orders[orderId] = {
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice
        }

    def openOrder(self, orderId, contract, order, orderState):
        print(f'Open Order {orderId}: {contract.symbol}, {order.action} {order.totalQuantity}, Status: {orderState.status}')

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')

def create_stock_contract(symbol, currency="USD", exchange="SMART"):
    """Create a stock contract"""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = exchange
    contract.currency = currency
    return contract

def create_market_order(action, quantity):
    """Create a market order"""
    order = Order()
    order.action = action
    order.orderType = "MKT"
    order.totalQuantity = quantity
    order.eTradeOnly = False
    order.firmQuoteOnly = False
    return order

def print_account_summary(app):
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

def test_trading():
    """Test trading functionality with buy and sell orders"""
    print("Interactive Brokers Trading Test")
    print("="*50)
    
    # Initialize API client
    app = IBTradingApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=5)
    
    # Start message processing in separate thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for connection and next valid order ID
    timeout = 10
    start_time = time.time()
    while (app.nextorderId is None or not app.connected) and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if app.nextorderId is None or not app.connected:
        print("Failed to connect or get valid order ID")
        return
    
    # Wait for account ID
    time.sleep(2)
    if not app.account_id:
        print("No account ID received")
        return
    
    print(f"\nFetching account data for: {app.account_id}")
    
    # Request account data
    app.reqAccountSummary(9001, "All", "NetLiquidation,TotalCashValue,SettledCash,AccruedCash,BuyingPower,EquityWithLoanValue,AvailableFunds")
    app.reqPositions()
    app.reqAccountUpdates(True, app.account_id)
    
    # Wait for account data
    time.sleep(3)
    
    # Print current account status
    print_account_summary(app)
    
    # Test trading - Buy 1 share of AAPL
    print(f"\n{'='*50}")
    print("TESTING BUY ORDER")
    print("="*50)
    
    contract_aapl = create_stock_contract("AAPL")
    buy_order = create_market_order("BUY", 1)
    
    buy_order_id = app.nextorderId
    print(f"Placing BUY order for 1 share of AAPL (Order ID: {buy_order_id})")
    app.placeOrder(buy_order_id, contract_aapl, buy_order)
    app.nextorderId += 1
    
    # Wait for order to process
    time.sleep(5)
    
    # Check if buy order was filled
    if buy_order_id in app.orders and app.orders[buy_order_id]['status'] == 'Filled':
        print("BUY order filled successfully!")
        
        # Test sell order - Sell the share we just bought
        print(f"\n{'='*50}")
        print("TESTING SELL ORDER")
        print("="*50)
        
        sell_order = create_market_order("SELL", 1)
        sell_order_id = app.nextorderId
        print(f"Placing SELL order for 1 share of AAPL (Order ID: {sell_order_id})")
        app.placeOrder(sell_order_id, contract_aapl, sell_order)
        app.nextorderId += 1
        
        # Wait for sell order to process
        time.sleep(5)
        
        if sell_order_id in app.orders and app.orders[sell_order_id]['status'] == 'Filled':
            print("SELL order filled successfully!")
        else:
            print(f"SELL order status: {app.orders.get(sell_order_id, {}).get('status', 'Unknown')}")
    else:
        print(f"BUY order status: {app.orders.get(buy_order_id, {}).get('status', 'Unknown')}")
    
    # Cancel subscriptions
    app.cancelAccountSummary(9001)
    app.cancelPositions()
    app.reqAccountUpdates(False, app.account_id)
    
    # Final account summary
    time.sleep(2)
    app.reqAccountSummary(9002, "All", "NetLiquidation,TotalCashValue,SettledCash,AccruedCash,BuyingPower,EquityWithLoanValue,AvailableFunds")
    app.reqPositions()
    app.reqAccountUpdates(True, app.account_id)
    time.sleep(3)
    
    print(f"\n{'='*50}")
    print("FINAL ACCOUNT STATUS")
    print("="*50)
    print_account_summary(app)
    
    # Disconnect
    app.disconnect()
    print("\nDisconnected from IB Gateway")

if __name__ == "__main__":
    test_trading()