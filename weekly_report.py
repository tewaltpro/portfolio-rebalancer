"""
Automated Weekly Portfolio Analysis and Email Report
Works for any client with any brokerage
"""

import os
import sys
from datetime import datetime
from auto_import import import_portfolio_auto
from data_loader import DataLoader
from portfolio_rebalancer import PortfolioRebalancer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class WeeklyReportConfig:
    """Configuration for weekly reports - customize per client"""
    
    def __init__(self, client_name: str = "Personal"):
        """
        Initialize config for a specific client
        
        Args:
            client_name: Name of the client (used for filenames and emails)
        """
        self.client_name = client_name
        
        # Default target allocation (override per client)
        self.target_allocation = {
            'VFORX': 0.70,
            'AAPL': 0.10,
            'NVDA': 0.08,
            'JNJ': 0.07,
            'VFH': 0.05
        }
        
        # Default tax rate (0 for Roth IRA)
        self.tax_rate = 0.0
        
        # Email settings
        self.recipient_email = os.getenv('CLIENT_EMAIL') or "your.email@gmail.com"
        
        # Data source
        self.data_source = 'alphavantage'  # or 'yahoo'
    
    @classmethod
    def load_from_file(cls, config_file: str):
        """
        Load client configuration from file
        
        Args:
            config_file: Path to JSON config file
        
        Returns:
            WeeklyReportConfig instance
        """
        import json
        
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        config = cls(client_name=data.get('client_name', 'Personal'))
        config.target_allocation = data.get('target_allocation', config.target_allocation)
        config.tax_rate = data.get('tax_rate', 0.0)
        config.recipient_email = data.get('email', config.recipient_email)
        config.data_source = data.get('data_source', 'alphavantage')
        
        return config


def send_email_report(report_text: str, recipient: str, client_name: str) -> bool:
    """
    Send report via email
    
    Args:
        report_text: The report content
        recipient: Email address to send to
        client_name: Name of client for subject line
    
    Returns:
        True if successful
    """
    sender = os.getenv('EMAIL_SENDER')
    password = os.getenv('EMAIL_PASSWORD')
    
    if not sender or not password:
        print("⚠ Email credentials not configured")
        print("  Set EMAIL_SENDER and EMAIL_PASSWORD environment variables")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = f"Portfolio Report - {client_name} - {datetime.now().strftime('%Y-%m-%d')}"
    
    msg.attach(MIMEText(report_text, 'plain'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print(f"✓ Email sent to {recipient}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {e}")
        return False


def run_weekly_analysis(config: WeeklyReportConfig = None):
    """
    Complete weekly analysis workflow
    
    Args:
        config: Client-specific configuration
    """
    if config is None:
        config = WeeklyReportConfig()
    
    print("="*60)
    print(f"WEEKLY PORTFOLIO ANALYSIS - {config.client_name}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Step 1: Import latest portfolio data
    print("Step 1: Importing latest portfolio data...")
    portfolio_file = import_portfolio_auto()
    
    if not portfolio_file:
        print("✗ Failed to import portfolio data")
        print("\n💡 Manual import required:")
        print("  1. Download CSV from your brokerage")
        print("  2. Save to: Inputs/auto-import/")
        print("  3. Run this script again")
        return
    
    # Step 2: Load portfolio
    print("\nStep 2: Loading portfolio...")
    api_key = os.getenv('ALPHAVANTAGE_API_KEY')
    loader = DataLoader(api_key=api_key)
    holdings = loader.load_from_csv(portfolio_file)
    
    if not holdings:
        print("✗ Failed to load portfolio")
        return
    
    # Step 3: Fetch current prices
    print("\nStep 3: Fetching current prices...")
    tickers = list(set(h['ticker'] for h in holdings))
    print(f"  Fetching prices for {len(tickers)} tickers...")
    
    prices = loader.get_current_prices(tickers, source=config.data_source)
    
    if not prices:
        print("✗ Failed to fetch prices")
        return
    
    # Step 4: Run analysis
    print("\nStep 4: Running analysis...")
    rebalancer = PortfolioRebalancer(config.target_allocation, tax_rate=config.tax_rate)
    
    portfolio_df = rebalancer.load_portfolio(holdings)
    portfolio_df = rebalancer.calculate_current_values(portfolio_df, prices)
    
    allocation_df = rebalancer.analyze_allocation(portfolio_df)
    tlh_opportunities = rebalancer.identify_tax_loss_harvesting(portfolio_df, min_loss=500)
    
    total_value = portfolio_df['current_value'].sum()
    trades = rebalancer.generate_rebalancing_trades(allocation_df, portfolio_df, total_value)
    
    # Step 5: Generate report
    print("\nStep 5: Generating report...")
    report = rebalancer.generate_report(portfolio_df, allocation_df, tlh_opportunities, trades)
    
    # Save report
    safe_client_name = config.client_name.replace(' ', '_')
    report_file = f"weekly_report_{safe_client_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✓ Report saved: {report_file}")
    
    # Print report to console
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    # Step 6: Email report (optional)
    if config.recipient_email and config.recipient_email != "your.email@gmail.com":
        print("\nStep 6: Emailing report...")
        send_email_report(report, config.recipient_email, config.client_name)
    else:
        print("\nStep 6: Email not configured (skipping)")
    
    print("\n" + "="*60)
    print(f"✓ WEEKLY ANALYSIS COMPLETE - {config.client_name}")
    print("="*60)


if __name__ == "__main__":
    # Check if config file provided
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        print(f"Loading configuration from: {config_file}\n")
        config = WeeklyReportConfig.load_from_file(config_file)
    else:
        # Use default personal config
        config = WeeklyReportConfig(client_name="Personal")
        print("Using default configuration (personal portfolio)\n")
    
    run_weekly_analysis(config)