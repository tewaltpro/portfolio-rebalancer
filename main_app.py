"""
Smart Portfolio Rebalancing System - Main Application
Complete workflow for portfolio analysis and rebalancing

Usage:
    python main_app.py --portfolio my_portfolio.csv
    python main_app.py --create-sample
    python main_app.py --interactive
"""

import argparse
import sys
import os
from datetime import datetime
from typing import Optional

# Import our modules (these would be in separate files)
# For now, assume they're available or copy the classes here

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     SMART PORTFOLIO REBALANCING SYSTEM                       ║
║     Tax-Optimized Portfolio Management                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def get_api_key(data_source: str) -> Optional[str]:
    """
    Get API key with fallback chain:
    1. Environment variable (automated runs)
    2. Streamlit secrets (deployed app - future)
    3. User input (manual runs)
    
    Args:
        data_source: The data source being used
    
    Returns:
        API key or None
    """
    if data_source != 'alphavantage':
        return None
    
    # Try environment variable first (for automated runs)
    api_key = os.getenv('ALPHAVANTAGE_API_KEY')
    if api_key:
        print("✓ Using API key from environment variable")
        return api_key
    
    # Try Streamlit secrets (if running in Streamlit - future)
    try:
        import streamlit as st
        api_key = st.secrets.get("ALPHAVANTAGE_API_KEY")
        if api_key:
            print("✓ Using API key from Streamlit secrets")
            return api_key
    except:
        pass
    
    # Last resort: prompt user
    return input("Enter Alpha Vantage API key: ").strip()


def interactive_mode():
    """Run in interactive mode with user prompts"""
    print("\n" + "="*60)
    print("INTERACTIVE SETUP")
    print("="*60 + "\n")
    
    # Get portfolio file
    print("Step 1: Portfolio Data")
    print("-" * 40)
    portfolio_file = input("Enter path to portfolio CSV (or 'sample' for demo): ").strip().strip('"').strip("'")
    
    if portfolio_file.lower() == 'sample':
        from data_loader import DataLoader
        loader = DataLoader()
        portfolio_file = loader.create_sample_csv()
        print()
    
    # Get target allocation
    print("\nStep 2: Target Allocation")
    print("-" * 40)
    print("Enter your target allocation (must sum to 100%)")
    print("Example: VTI=60, BND=40")
    
    target_allocation = {}
    while True:
        allocation_str = input("Enter allocation (ticker=percent, comma-separated): ").strip()
        
        try:
            for pair in allocation_str.split(','):
                ticker, percent = pair.split('=')
                target_allocation[ticker.strip().upper()] = float(percent.strip()) / 100
            
            total = sum(target_allocation.values())
            if abs(total - 1.0) < 0.01:  # Allow small rounding errors
                break
            else:
                print(f"✗ Allocation sums to {total*100:.1f}%, must be 100%. Try again.")
                target_allocation = {}
        except:
            print("✗ Invalid format. Use: TICKER=PERCENT, TICKER=PERCENT")
            target_allocation = {}
    
    print(f"✓ Target allocation set: {target_allocation}\n")
    
    # Get tax rate
    print("Step 3: Tax Information")
    print("-" * 40)
    tax_rate = float(input("Enter your combined tax rate (e.g., 24 for 24%, or 0 for Roth IRA): ").strip()) / 100
    print(f"✓ Tax rate set: {tax_rate*100:.0f}%\n")
    
    # Get API key for price data (optional)
    print("Step 4: Market Data Source")
    print("-" * 40)
    print("Options:")
    print("  1. Yahoo Finance (free, no API key needed)")
    print("  2. Alpha Vantage (more reliable, API key required)")
    print("  3. Manual entry (enter prices yourself)")
    
    data_source = input("Choose option (1-3): ").strip()
    
    # Determine data source name
    if data_source == '1':
        source_name = 'yahoo'
    elif data_source == '2':
        source_name = 'alphavantage'
    else:
        source_name = 'manual'
    
    # Get API key using smart fallback
    api_key = get_api_key(source_name)
    
    # Run analysis
    print("\n" + "="*60)
    print("RUNNING ANALYSIS...")
    print("="*60 + "\n")
    
    run_analysis(
        portfolio_file=portfolio_file,
        target_allocation=target_allocation,
        tax_rate=tax_rate,
        api_key=api_key,
        data_source=source_name
    )


def run_analysis(portfolio_file: str, 
                target_allocation: dict,
                tax_rate: float = 0.24,
                api_key: Optional[str] = None,
                data_source: str = 'yahoo'):
    """
    Run complete portfolio analysis
    
    Args:
        portfolio_file: Path to portfolio CSV
        target_allocation: Dict of ticker: target_weight
        tax_rate: Combined tax rate
        api_key: API key for market data
        data_source: Data source for prices
    """
    from data_loader import DataLoader
    from portfolio_rebalancer import PortfolioRebalancer
    
    # Load data
    print("Loading portfolio data...")
    loader = DataLoader(api_key=api_key)
    holdings = loader.load_from_csv(portfolio_file)
    
    if not holdings:
        print("✗ No holdings loaded. Exiting.")
        return
    
    print()
    
    # Get current prices
    tickers = list(set(h['ticker'] for h in holdings))
    print(f"Fetching prices for: {', '.join(tickers)}\n")
    
    if data_source == 'manual':
        prices = {}
        for ticker in tickers:
            price = float(input(f"Enter current price for {ticker}: $").strip())
            prices[ticker] = price
        print()
    else:
        prices = loader.get_current_prices(tickers, source=data_source)
    
    if not prices:
        print("✗ Could not fetch prices. Exiting.")
        return
    
    print("\n" + "="*60)
    
    # Initialize rebalancer
    rebalancer = PortfolioRebalancer(target_allocation, tax_rate=tax_rate)
    
    # Load and analyze portfolio
    portfolio_df = rebalancer.load_portfolio(holdings)
    portfolio_df = rebalancer.calculate_current_values(portfolio_df, prices)

    # Validation: Check for mismatches between portfolio and targets
    print("\n" + "="*60)
    print("ALLOCATION VALIDATION")
    print("="*60)

    actual_tickers = set(portfolio_df['ticker'].unique())
    target_tickers = set(target_allocation.keys())

    missing_tickers = actual_tickers - target_tickers
    extra_tickers = target_tickers - actual_tickers

    if missing_tickers:
        print(f"\n⚠️  WARNING: You own {len(missing_tickers)} ticker(s) NOT in your target allocation:")
        print(f"   {', '.join(sorted(missing_tickers))}")
        print(f"\n   The system will recommend SELLING all of these positions.")
        print(f"   Is this what you want?")
        
        confirm = input("\n   Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("\n   ✗ Analysis cancelled.")
            print("\n   💡 Tip: Update your target allocation to include all tickers you want to keep.")
            print(f"   Example: --target \"AAPL=7,NVDA=5,VFORX=60,...\"")
            return

    if extra_tickers:
        print(f"\n💡 Note: Target allocation includes {len(extra_tickers)} ticker(s) you don't currently own:")
        print(f"   {', '.join(sorted(extra_tickers))}")
        print(f"   The system will recommend BUYING these.\n")

    if not missing_tickers and not extra_tickers:
        print("\n✓ All portfolio tickers have target allocations set.")

    print("="*60 + "\n")
    
    # Run analysis
    allocation_df = rebalancer.analyze_allocation(portfolio_df)
    tlh_opportunities = rebalancer.identify_tax_loss_harvesting(portfolio_df, min_loss=500)
    
    total_value = portfolio_df['current_value'].sum()
    trades = rebalancer.generate_rebalancing_trades(allocation_df, portfolio_df, total_value)
    
    # Generate report
    report = rebalancer.generate_report(portfolio_df, allocation_df, tlh_opportunities, trades)
    print(report)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"portfolio_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ Report saved to: {report_file}")
    
    # Ask about executing trades
    if trades:
        print("\n" + "="*60)
        execute = input("\nWould you like to save trade recommendations to CSV? (y/n): ").strip().lower()
        
        if execute == 'y':
            trades_file = f"recommended_trades_{timestamp}.csv"
            import pandas as pd
            pd.DataFrame(trades).to_csv(trades_file, index=False)
            print(f"✓ Trade recommendations saved to: {trades_file}")


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description='Smart Portfolio Rebalancing System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_app.py --interactive
  python main_app.py --portfolio my_portfolio.csv --target "VTI=60,BND=40"
  python main_app.py --create-sample
        """
    )
    
    parser.add_argument('--portfolio', '-p', 
                       help='Path to portfolio CSV file')
    parser.add_argument('--target', '-t',
                       help='Target allocation (e.g., "VTI=60,BND=40")')
    parser.add_argument('--tax-rate', '-r', type=float, default=24.0,
                       help='Tax rate percentage (default: 24)')
    parser.add_argument('--api-key', '-k',
                       help='API key for market data')
    parser.add_argument('--source', '-s', default='yahoo',
                       choices=['yahoo', 'alphavantage', 'polygon'],
                       help='Market data source (default: yahoo)')
    parser.add_argument('--create-sample', action='store_true',
                       help='Create sample portfolio CSV and exit')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run in interactive mode')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Create sample CSV if requested
    if args.create_sample:
        from data_loader import DataLoader
        loader = DataLoader()
        filepath = loader.create_sample_csv()
        print(f"\nYou can now run: python main_app.py --portfolio {filepath}")
        return
    
    # Run in interactive mode
    if args.interactive or (not args.portfolio and not args.target):
        interactive_mode()
        return
    
    # Command-line mode
    if not args.portfolio:
        print("✗ Error: --portfolio required (or use --interactive mode)")
        parser.print_help()
        return
    
    if not args.target:
        print("✗ Error: --target required (or use --interactive mode)")
        parser.print_help()
        return
    
    # Parse target allocation
    target_allocation = {}
    try:
        for pair in args.target.split(','):
            ticker, percent = pair.split('=')
            target_allocation[ticker.strip().upper()] = float(percent.strip()) / 100
    except:
        print("✗ Error: Invalid target allocation format")
        print("   Use: --target 'VTI=60,BND=40'")
        return
    
    # Get API key if needed (smart fallback)
    api_key = args.api_key if args.api_key else get_api_key(args.source)
    
    # Run analysis
    run_analysis(
        portfolio_file=args.portfolio,
        target_allocation=target_allocation,
        tax_rate=args.tax_rate / 100,
        api_key=api_key,
        data_source=args.source
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)