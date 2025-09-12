#!/usr/bin/env python3
"""
Interactive Brokers API script to search for a GBP stock from universe.json
and place a market buy order for 1 share
"""

import json
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time

class IBApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.contract_details = []
        self.market_data = {}
        self.next_req_id = 1
        self.nextorderId = None
        self.contract_found = False

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

    def contractDetails(self, reqId, contractDetails):
        super().contractDetails(reqId, contractDetails)
        contract = contractDetails.contract
        details = {
            "reqId": reqId,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "exchange": contract.exchange,
            "currency": contract.currency,
            "localSymbol": contract.localSymbol,
            "tradingClass": contract.tradingClass,
            "marketName": contractDetails.marketName,
            "minTick": contractDetails.minTick,
            "longName": contractDetails.longName,
            "industry": contractDetails.industry,
            "category": contractDetails.category,
            "contract": contract  # Store the actual contract object
        }
        self.contract_details.append(details)
        self.contract_found = True
        print(f"Contract found: {contract.symbol} ({contract.localSymbol}) on {contract.exchange}")
        print(f"   Long Name: {contractDetails.longName}")
        print(f"   Currency: {contract.currency}")
        print(f"   Exchange: {contract.exchange}")

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        print(f"Contract details search completed for reqId: {reqId}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f'Order Status - ID: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, Avg Fill Price: {avgFillPrice}')

    def openOrder(self, orderId, contract, order, orderState):
        print(f'Open Order - ID: {orderId}, Symbol: {contract.symbol}, Action: {order.action}, Qty: {order.totalQuantity}, Status: {orderState.status}')

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')

def load_gbp_stocks():
    """Load GBP stocks from universe.json"""
    try:
        with open('data/universe.json', 'r') as f:
            data = json.load(f)
        
        gbp_stocks = []
        # Get GBP stocks from all screens
        for screen_name, screen_data in data['screens'].items():
            for stock in screen_data['stocks']:
                if stock['currency'] == 'GBP':
                    gbp_stocks.append(stock)
        
        return gbp_stocks
    except Exception as e:
        print(f"Error loading universe data: {e}")
        return []

def create_contract_from_isin(isin, currency="GBP"):
    """Create a contract using ISIN"""
    contract = Contract()
    contract.secIdType = "ISIN"
    contract.secId = isin
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = "SMART"
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

def main():
    # Load GBP stocks from universe
    gbp_stocks = load_gbp_stocks()
    if not gbp_stocks:
        print("No GBP stocks found in universe data")
        return
    
    # Select the first GBP stock for testing
    target_stock = gbp_stocks[0]
    print("="*70)
    print("TARGETING GBP STOCK FOR PURCHASE")
    print("="*70)
    print(f"Stock: {target_stock['name']}")
    print(f"Ticker: {target_stock['ticker']}")
    print(f"ISIN: {target_stock['isin']}")
    print(f"Currency: {target_stock['currency']}")
    print(f"Sector: {target_stock['sector']}")
    print(f"Universe Price: £{target_stock['price']}")
    print("-" * 70)
    
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=4)
    
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
    
    # Wait for nextValidId
    while app.nextorderId is None and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if app.nextorderId is None:
        print("Failed to get valid order ID")
        return
    
    # Step 1: Search for contract using ISIN
    print(f"Searching for contract using ISIN: {target_stock['isin']}")
    contract = create_contract_from_isin(target_stock['isin'], target_stock['currency'])
    app.reqContractDetails(app.next_req_id, contract)
    
    # Wait for contract details
    wait_time = 5
    start_time = time.time()
    while not app.contract_found and (time.time() - start_time) < wait_time:
        time.sleep(0.1)
    
    if not app.contract_details:
        print("No contract details found for this ISIN")
        app.disconnect()
        return
    
    # Step 2: Use the found contract details to create buy order
    contract_detail = app.contract_details[0]
    trading_contract = contract_detail['contract']  # Use the actual contract from IBKR
    
    print("\n" + "="*70)
    print("CONTRACT DETAILS CONFIRMED")
    print("="*70)
    print(f"Symbol: {contract_detail['symbol']}")
    print(f"Exchange: {contract_detail['exchange']}")
    print(f"Currency: {contract_detail['currency']}")
    print(f"Long Name: {contract_detail['longName']}")
    print(f"Industry: {contract_detail['industry']}")
    
    # Step 3: Create and place market buy order
    print(f"\nPlacing market buy order for 1 share of {contract_detail['symbol']}...")
    order = create_market_order("BUY", 1)
    
    app.placeOrder(app.nextorderId, trading_contract, order)
    
    # Wait for order updates
    print("Waiting for order updates...")
    time.sleep(8)
    
    print("\n" + "="*70)
    print("ORDER PLACEMENT COMPLETED")
    print("="*70)
    print(f"Target Stock: {target_stock['name']}")
    print(f"IBKR Symbol: {contract_detail['symbol']}")
    print(f"Order ID: {app.nextorderId}")
    print(f"Action: BUY 1 share")
    print(f"Currency: {contract_detail['currency']}")
    
    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    main()