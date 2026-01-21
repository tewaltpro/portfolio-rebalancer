"""
Smart Portfolio Rebalancing System - Core Engine
A prototype system for tax-efficient portfolio rebalancing and optimization

Features:
- Portfolio analysis and drift detection
- Tax-loss harvesting identification
- Rebalancing recommendations with tax optimization
- Performance tracking and reporting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class PortfolioRebalancer:
    """Main class for portfolio analysis and rebalancing"""
    
    def __init__(self, target_allocation: Dict[str, float], tax_rate: float = 0.24):
        """
        Initialize the rebalancer
        
        Args:
            target_allocation: Dict of ticker: target_weight (e.g., {'VTI': 0.60, 'BND': 0.40})
            tax_rate: Combined federal + state short-term cap gains tax rate
        """
        self.target_allocation = target_allocation
        self.tax_rate = tax_rate
        self.rebalance_threshold = 0.05  # 5% drift triggers rebalance
        
    def load_portfolio(self, holdings_data: List[Dict]) -> pd.DataFrame:
        """
        Load portfolio holdings from data
        
        Args:
            holdings_data: List of dicts with keys: ticker, shares, cost_basis, purchase_date
        
        Returns:
            DataFrame with portfolio holdings
        """
        df = pd.DataFrame(holdings_data)
        df['purchase_date'] = pd.to_datetime(df['purchase_date'])
        return df
    
    def calculate_current_values(self, portfolio_df: pd.DataFrame, 
                                 current_prices: Dict[str, float]) -> pd.DataFrame:
        """
        Calculate current market values and gains/losses
        
        Args:
            portfolio_df: DataFrame with holdings
            current_prices: Dict of ticker: current_price
        
        Returns:
            Updated DataFrame with current values and gains
        """
        df = portfolio_df.copy()
        df['current_price'] = df['ticker'].map(current_prices)
        df['current_value'] = df['shares'] * df['current_price']
        df['total_cost'] = df['shares'] * df['cost_basis']
        df['unrealized_gain'] = df['current_value'] - df['total_cost']
        df['gain_pct'] = (df['unrealized_gain'] / df['total_cost']) * 100
        
        # Calculate holding period for tax treatment
        df['days_held'] = (datetime.now() - df['purchase_date']).dt.days
        df['is_long_term'] = df['days_held'] >= 365
        
        return df
    
    def analyze_allocation(self, portfolio_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze current allocation vs. target
        
        Returns:
            DataFrame with allocation analysis
        """
        total_value = portfolio_df['current_value'].sum()
        
        allocation = portfolio_df.groupby('ticker').agg({
            'current_value': 'sum',
            'unrealized_gain': 'sum'
        }).reset_index()
        
        allocation['current_weight'] = allocation['current_value'] / total_value
        allocation['target_weight'] = allocation['ticker'].map(self.target_allocation).fillna(0)
        allocation['weight_diff'] = allocation['current_weight'] - allocation['target_weight']
        allocation['drift_pct'] = (allocation['weight_diff'] / allocation['target_weight']) * 100
        allocation['dollar_diff'] = allocation['weight_diff'] * total_value
        
        return allocation.sort_values('drift_pct', ascending=False)
    
    def identify_tax_loss_harvesting(self, portfolio_df: pd.DataFrame, 
                                     min_loss: float = 1000) -> List[Dict]:
        """
        Identify tax-loss harvesting opportunities
        
        Args:
            portfolio_df: DataFrame with holdings
            min_loss: Minimum loss to consider (default $1000)
        
        Returns:
            List of harvesting opportunities
        """
        opportunities = []
        
        for _, row in portfolio_df.iterrows():
            if row['unrealized_gain'] < -min_loss:
                # Calculate tax benefit
                tax_benefit = abs(row['unrealized_gain']) * self.tax_rate
                
                opportunities.append({
                    'ticker': row['ticker'],
                    'shares': row['shares'],
                    'unrealized_loss': row['unrealized_gain'],
                    'tax_benefit': tax_benefit,
                    'current_value': row['current_value'],
                    'days_held': row['days_held'],
                    'purchase_date': row['purchase_date'].strftime('%Y-%m-%d')
                })
        
        return sorted(opportunities, key=lambda x: x['tax_benefit'], reverse=True)
    
    def generate_rebalancing_trades(self, allocation_df: pd.DataFrame, 
                                portfolio_df: pd.DataFrame,
                                total_portfolio_value: float) -> List[Dict]:
        """
        Generate optimal rebalancing trades considering taxes
        
        Returns:
            List of recommended trades with BOTH buys and sells clearly separated
        """
        trades = []
        
        for _, row in allocation_df.iterrows():
            if abs(row['weight_diff']) > 0.001 or row['target_weight'] == 0:  # Show any trade > 0.1%
                target_value = row['target_weight'] * total_portfolio_value
                current_value = row['current_value']
                dollar_change = target_value - current_value
                
                # Determine if this is a buy or sell
                action = 'BUY' if dollar_change > 0 else 'SELL'
                
                # For sells, calculate tax impact
                tax_impact = 0
                if action == 'SELL' and row['unrealized_gain'] > 0:
                    ticker_lots = portfolio_df[portfolio_df['ticker'] == row['ticker']]
                    sorted_lots = ticker_lots.sort_values('cost_basis', ascending=False)
                    
                    if len(sorted_lots) > 0:
                        shares_to_sell = abs(dollar_change) / sorted_lots['current_price'].iloc[0]
                        
                        if shares_to_sell > 0:
                            total_shares = sorted_lots['shares'].sum()
                            if shares_to_sell <= total_shares:
                                gain_per_share = row['unrealized_gain'] / total_shares
                                total_gain = gain_per_share * shares_to_sell
                                
                                is_long_term = sorted_lots['is_long_term'].iloc[0]
                                tax_rate = self.tax_rate * (0.6 if is_long_term else 1.0)
                                tax_impact = total_gain * tax_rate
                
                # Determine trade type
                if row['target_weight'] == 0:
                    trade_type = 'LIQUIDATE'
                elif row['current_weight'] == 0 or row['current_weight'] < 0.01:
                    trade_type = 'NEW_POSITION'
                else:
                    trade_type = 'ADJUST'
                
                trades.append({
                    'ticker': row['ticker'],
                    'action': action,
                    'dollar_amount': abs(dollar_change),
                    'current_weight': row['current_weight'],
                    'target_weight': row['target_weight'],
                    'drift_pct': row['drift_pct'],
                    'tax_impact': tax_impact,
                    'net_benefit': abs(dollar_change) - tax_impact,
                    'trade_type': trade_type
                })
        
        # Sort: Liquidations first, then sells, then buys
        sort_order = {'LIQUIDATE': 0, 'ADJUST': 1, 'NEW_POSITION': 2}
        trades.sort(key=lambda x: (sort_order.get(x['trade_type'], 3), x['action'] == 'BUY', -x['dollar_amount']))
        
        return trades
        
    def generate_report(self, portfolio_df: pd.DataFrame, allocation_df: pd.DataFrame,
                       tlh_opportunities: List[Dict], trades: List[Dict]) -> str:
        """
        Generate a comprehensive portfolio report
        """
        total_value = portfolio_df['current_value'].sum()
        total_cost = portfolio_df['total_cost'].sum()
        total_gain = total_value - total_cost
        total_gain_pct = (total_gain / total_cost) * 100
        
        report = f"""
{'='*80}
PORTFOLIO REBALANCING REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

PORTFOLIO SUMMARY
{'-'*80}
Total Market Value:        ${total_value:,.2f}
Total Cost Basis:          ${total_cost:,.2f}
Unrealized Gain/Loss:      ${total_gain:,.2f} ({total_gain_pct:+.2f}%)
Number of Holdings:        {len(portfolio_df)}

CURRENT ALLOCATION
{'-'*80}
"""
        
        for _, row in allocation_df.iterrows():
            report += f"{row['ticker']:8s}  Current: {row['current_weight']*100:5.2f}%  " \
                     f"Target: {row['target_weight']*100:5.2f}%  " \
                     f"Drift: {row['drift_pct']:+6.2f}%\n"
        
        report += f"\n{'='*80}\n"
        
        if tlh_opportunities:
            total_tlh_benefit = sum(opp['tax_benefit'] for opp in tlh_opportunities)
            report += f"\nTAX-LOSS HARVESTING OPPORTUNITIES\n{'-'*80}\n"
            report += f"Total Potential Tax Savings: ${total_tlh_benefit:,.2f}\n\n"
            
            for opp in tlh_opportunities:
                report += f"{opp['ticker']:8s}  Loss: ${opp['unrealized_loss']:,.2f}  " \
                         f"Tax Benefit: ${opp['tax_benefit']:,.2f}  " \
                         f"Held: {opp['days_held']} days\n"
            
            report += f"\n{'='*80}\n"
        
        if trades:
            # Separate trades by type
            liquidations = [t for t in trades if t['trade_type'] == 'LIQUIDATE']
            sells = [t for t in trades if t['action'] == 'SELL' and t['trade_type'] != 'LIQUIDATE']
            buys = [t for t in trades if t['action'] == 'BUY']
            
            report += f"\nRECOMMENDED REBALANCING TRADES\n{'-'*80}\n\n"
            
            if liquidations:
                report += "STEP 1: LIQUIDATE POSITIONS (Target = 0%)\n"
                liquidate_total = 0
                for i, trade in enumerate(liquidations, 1):
                    report += f"{i}. SELL ${trade['dollar_amount']:,.2f} of {trade['ticker']} (liquidate entire position)\n"
                    liquidate_total += trade['dollar_amount']
                report += f"   Subtotal proceeds: ${liquidate_total:,.2f}\n\n"
            
            if sells:
                report += "STEP 2: REDUCE OVERWEIGHT POSITIONS\n"
                for trade in sells:
                    report += f"• SELL ${trade['dollar_amount']:,.2f} of {trade['ticker']}\n"
                    report += f"  (Reduce from {trade['current_weight']*100:.1f}% to {trade['target_weight']*100:.1f}%)\n"
                report += "\n"
            
            if buys:
                buy_total = 0
                report += "STEP 3: BUY/INCREASE POSITIONS\n"
                for trade in buys:
                    if trade['trade_type'] == 'NEW_POSITION':
                        report += f"• BUY ${trade['dollar_amount']:,.2f} of {trade['ticker']} (new position)\n"
                    else:
                        report += f"• BUY ${trade['dollar_amount']:,.2f} of {trade['ticker']}\n"
                        report += f"  (Increase from {trade['current_weight']*100:.1f}% to {trade['target_weight']*100:.1f}%)\n"
                    buy_total += trade['dollar_amount']
                
                if liquidations or sells:
                    liquidate_total = sum(t['dollar_amount'] for t in liquidations)
                    sell_total = sum(t['dollar_amount'] for t in sells)
                    total_proceeds = liquidate_total + sell_total
                    net_cash = buy_total - total_proceeds
                    
                    report += f"\n{'-'*80}\n"
                    report += "TRANSACTION SUMMARY:\n"
                    report += f"  Total proceeds from sales: ${total_proceeds:,.2f}\n"
                    report += f"  Total cost of purchases:   ${buy_total:,.2f}\n"
                    report += f"  Net cash needed:           ${net_cash:,.2f}\n"
                    
                    if abs(net_cash) < 100:
                        report += f"  ✓ Rebalancing is cash-neutral (within $100)\n"
        else:
            report += f"\nNO REBALANCING NEEDED\n{'-'*80}\n"
            report += "Portfolio is within acceptable drift thresholds.\n"
        
        report += f"\n{'='*80}\n"
        
        return report


def run_example():
    """
    Example usage with sample data
    """
    print("Smart Portfolio Rebalancing System - Demo\n")
    
    # Define target allocation (60/40 stocks/bonds)
    target_allocation = {
        'VTI': 0.60,  # Vanguard Total Stock Market ETF
        'BND': 0.40   # Vanguard Total Bond Market ETF
    }
    
    # Sample portfolio holdings
    holdings = [
        {'ticker': 'VTI', 'shares': 100, 'cost_basis': 220.00, 'purchase_date': '2023-01-15'},
        {'ticker': 'VTI', 'shares': 50, 'cost_basis': 195.00, 'purchase_date': '2022-06-20'},
        {'ticker': 'BND', 'shares': 300, 'cost_basis': 82.00, 'purchase_date': '2023-03-10'},
        {'ticker': 'BND', 'shares': 100, 'cost_basis': 78.50, 'purchase_date': '2024-08-05'},
    ]
    
    # Current market prices (example)
    current_prices = {
        'VTI': 245.00,  # Stock market up
        'BND': 75.00    # Bond market down
    }
    
    # Initialize rebalancer
    rebalancer = PortfolioRebalancer(target_allocation, tax_rate=0.24)
    
    # Load and analyze portfolio
    portfolio_df = rebalancer.load_portfolio(holdings)
    portfolio_df = rebalancer.calculate_current_values(portfolio_df, current_prices)
    
    # Analyze allocation
    allocation_df = rebalancer.analyze_allocation(portfolio_df)
    
    # Identify tax-loss harvesting opportunities
    tlh_opportunities = rebalancer.identify_tax_loss_harvesting(portfolio_df, min_loss=500)
    
    # Generate rebalancing trades
    total_value = portfolio_df['current_value'].sum()
    trades = rebalancer.generate_rebalancing_trades(allocation_df, portfolio_df, total_value)
    
    # Generate and print report
    report = rebalancer.generate_report(portfolio_df, allocation_df, tlh_opportunities, trades)
    print(report)
    
    return rebalancer, portfolio_df, allocation_df, tlh_opportunities, trades


if __name__ == "__main__":
    run_example()