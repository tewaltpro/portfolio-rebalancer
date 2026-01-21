"""
Data Loader Module
Handles importing portfolio data from CSV files and broker APIs
"""

import pandas as pd
import requests
from datetime import datetime
from typing import Dict, List, Optional
import json
import time  # ADD THIS IMPORT

class DataLoader:
    """Load portfolio data from various sources"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize data loader
        
        Args:
            api_key: API key for market data (e.g., Alpha Vantage, Polygon.io)
        """
        self.api_key = api_key
    
    def load_from_csv(self, filepath: str) -> List[Dict]:
        """
        Load portfolio holdings from CSV file
        
        Expected CSV format:
        ticker,shares,cost_basis,purchase_date
        VTI,100,220.00,2023-01-15
        BND,300,82.00,2023-03-10
        
        Args:
            filepath: Path to CSV file
        
        Returns:
            List of holding dictionaries
        """
        try:
            df = pd.read_csv(filepath)
            
            # Validate required columns
            required_cols = ['ticker', 'shares', 'cost_basis', 'purchase_date']
            missing_cols = set(required_cols) - set(df.columns)
            
            if missing_cols:
                raise ValueError(f"CSV missing required columns: {missing_cols}")
            
            # Convert to list of dicts
            holdings = df.to_dict('records')
            
            print(f"✓ Loaded {len(holdings)} holdings from {filepath}")
            return holdings
            
        except FileNotFoundError:
            print(f"✗ Error: File not found - {filepath}")
            return []
        except Exception as e:
            print(f"✗ Error loading CSV: {str(e)}")
            return []
    
    def export_to_csv(self, holdings: List[Dict], filepath: str) -> bool:
        """
        Export holdings to CSV file
        
        Args:
            holdings: List of holding dictionaries
            filepath: Path to save CSV file
        
        Returns:
            True if successful
        """
        try:
            df = pd.DataFrame(holdings)
            df.to_csv(filepath, index=False)
            print(f"✓ Exported {len(holdings)} holdings to {filepath}")
            return True
        except Exception as e:
            print(f"✗ Error exporting CSV: {str(e)}")
            return False
    
    def get_current_prices(self, tickers: List[str], 
                          source: str = 'alphavantage') -> Dict[str, float]:
        """
        Fetch current market prices for tickers
        
        Args:
            tickers: List of ticker symbols
            source: Data source ('alphavantage', 'polygon', 'yahoo')
        
        Returns:
            Dict of ticker: price
        """
        if source == 'alphavantage':
            return self._fetch_alphavantage(tickers)
        elif source == 'polygon':
            return self._fetch_polygon(tickers)
        elif source == 'yahoo':
            return self._fetch_yahoo(tickers)
        else:
            print(f"✗ Unknown data source: {source}")
            return {}
    
    def _fetch_alphavantage(self, tickers: List[str]) -> Dict[str, float]:
        """
        Fetch prices from Alpha Vantage API
        Free tier: 25 requests/day, 5 requests/minute
        """
        if not self.api_key:
            print("✗ Alpha Vantage API key required")
            return {}
        
        prices = {}
        base_url = "https://www.alphavantage.co/query"
        
        print(f"Fetching prices for {len(tickers)} tickers from Alpha Vantage...")
        print(f"(Rate limited to 5 per minute - this may take a few minutes)\n")
        
        for i, ticker in enumerate(tickers):
            # Rate limiting: wait 12 seconds between requests (5 per minute max)
            if i > 0:
                print(f"  Waiting 12 seconds... ({i}/{len(tickers)} complete)")
                time.sleep(12)
            
            try:
                params = {
                    'function': 'GLOBAL_QUOTE',
                    'symbol': ticker,
                    'apikey': self.api_key
                }
                
                response = requests.get(base_url, params=params)
                data = response.json()
                
                # Check for API rate limit error
                if 'Note' in data:
                    print(f"⚠ API rate limit reached. Waiting 60 seconds...")
                    time.sleep(60)
                    # Retry this ticker
                    response = requests.get(base_url, params=params)
                    data = response.json()
                
                if 'Global Quote' in data and '05. price' in data['Global Quote']:
                    price = float(data['Global Quote']['05. price'])
                    prices[ticker] = price
                    print(f"✓ {ticker}: ${price:.2f}")
                elif 'Error Message' in data:
                    print(f"✗ Invalid ticker: {ticker}")
                else:
                    print(f"✗ Could not fetch price for {ticker}")
                    print(f"  Response: {data}")
                    
            except Exception as e:
                print(f"✗ Error fetching {ticker}: {str(e)}")
        
        print(f"\n✓ Fetched {len(prices)}/{len(tickers)} prices successfully")
        return prices
    
    def _fetch_polygon(self, tickers: List[str]) -> Dict[str, float]:
        """
        Fetch prices from Polygon.io API
        Free tier: 5 API calls/minute
        """
        if not self.api_key:
            print("✗ Polygon.io API key required")
            return {}
        
        prices = {}
        base_url = "https://api.polygon.io/v2/aggs/ticker"
        
        # Get yesterday's date for "previous close"
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        for ticker in tickers:
            try:
                url = f"{base_url}/{ticker}/prev"
                params = {'apiKey': self.api_key}
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'results' in data and len(data['results']) > 0:
                    price = data['results'][0]['c']  # Close price
                    prices[ticker] = price
                    print(f"✓ {ticker}: ${price:.2f}")
                else:
                    print(f"✗ Could not fetch price for {ticker}")
                    
            except Exception as e:
                print(f"✗ Error fetching {ticker}: {str(e)}")
        
        return prices
    
    def _fetch_yahoo(self, tickers: List[str]) -> Dict[str, float]:
        """
        Fetch prices using yfinance (no API key needed)
        Requires: pip install yfinance
        """
        try:
            import yfinance as yf
        except ImportError:
            print("✗ yfinance not installed. Install with: pip install yfinance")
            return {}
        
        prices = {}
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
                
                if price:
                    prices[ticker] = float(price)
                    print(f"✓ {ticker}: ${price:.2f}")
                else:
                    print(f"✗ Could not fetch price for {ticker}")
                    
            except Exception as e:
                print(f"✗ Error fetching {ticker}: {str(e)}")
        
        return prices
    
    def create_sample_csv(self, filepath: str = 'sample_portfolio.csv'):
        """
        Create a sample portfolio CSV for testing
        """
        sample_data = [
            {'ticker': 'VTI', 'shares': 100, 'cost_basis': 220.00, 'purchase_date': '2023-01-15'},
            {'ticker': 'VTI', 'shares': 50, 'cost_basis': 195.00, 'purchase_date': '2022-06-20'},
            {'ticker': 'VXUS', 'shares': 75, 'cost_basis': 58.00, 'purchase_date': '2023-05-10'},
            {'ticker': 'BND', 'shares': 300, 'cost_basis': 82.00, 'purchase_date': '2023-03-10'},
            {'ticker': 'BND', 'shares': 100, 'cost_basis': 78.50, 'purchase_date': '2024-08-05'},
        ]
        
        df = pd.DataFrame(sample_data)
        df.to_csv(filepath, index=False)
        print(f"✓ Created sample portfolio CSV: {filepath}")
        print(f"  Contains {len(sample_data)} holdings")
        
        return filepath


class BrokerageConnector:
    """
    Connect to brokerage APIs (Alpaca, Interactive Brokers, etc.)
    Note: Requires separate authentication and setup
    """
    
    def __init__(self, broker: str, api_key: str, api_secret: str):
        """
        Initialize brokerage connection
        
        Args:
            broker: Broker name ('alpaca', 'ibkr', 'tdameritrade')
            api_key: API key
            api_secret: API secret
        """
        self.broker = broker
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self._get_base_url()
    
    def _get_base_url(self) -> str:
        """Get API base URL for broker"""
        urls = {
            'alpaca': 'https://paper-api.alpaca.markets',  # Paper trading
            'alpaca_live': 'https://api.alpaca.markets',
            'ibkr': 'https://localhost:5000/v1/api',  # Interactive Brokers Gateway
        }
        return urls.get(self.broker, '')
    
    def get_positions(self) -> List[Dict]:
        """
        Fetch current positions from brokerage
        
        Returns:
            List of position dictionaries
        """
        if self.broker == 'alpaca':
            return self._get_alpaca_positions()
        else:
            print(f"✗ Broker {self.broker} not yet implemented")
            return []
    
    def _get_alpaca_positions(self) -> List[Dict]:
        """Fetch positions from Alpaca API"""
        headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/v2/positions",
                headers=headers
            )
            
            if response.status_code == 200:
                positions = response.json()
                
                # Convert to our format
                holdings = []
                for pos in positions:
                    holdings.append({
                        'ticker': pos['symbol'],
                        'shares': float(pos['qty']),
                        'cost_basis': float(pos['avg_entry_price']),
                        'purchase_date': pos.get('created_at', datetime.now().isoformat())[:10]
                    })
                
                print(f"✓ Fetched {len(holdings)} positions from Alpaca")
                return holdings
            else:
                print(f"✗ Error fetching positions: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"✗ Error connecting to Alpaca: {str(e)}")
            return []


# Example usage
if __name__ == "__main__":
    print("Data Loader Module - Test\n")
    
    # Create sample CSV
    loader = DataLoader()
    csv_file = loader.create_sample_csv()
    
    print("\n" + "="*50 + "\n")
    
    # Load from CSV
    holdings = loader.load_from_csv(csv_file)
    
    print("\n" + "="*50 + "\n")
    
    # Get unique tickers
    tickers = list(set(h['ticker'] for h in holdings))
    print(f"Tickers in portfolio: {tickers}\n")
    
    # Fetch current prices (using yfinance - no API key needed)
    print("Fetching current prices...\n")
    prices = loader.get_current_prices(tickers, source='yahoo')
    
    if prices:
        print(f"\n✓ Successfully fetched {len(prices)} prices")
    else:
        print("\n✗ Could not fetch prices (install yfinance or provide API key)")