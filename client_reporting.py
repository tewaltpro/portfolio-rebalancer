"""
Client Reporting Module
Generate professional reports and performance tracking for clients
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List
import json

class ClientReporter:
    """Generate client-facing reports and visualizations"""
    
    def __init__(self, client_name: str, portfolio_value: float):
        """
        Initialize reporter
        
        Args:
            client_name: Client name
            portfolio_value: Current portfolio value
        """
        self.client_name = client_name
        self.portfolio_value = portfolio_value
        self.report_date = datetime.now()
    
    def generate_executive_summary(self, 
                                   total_gain: float,
                                   tax_savings_ytd: float,
                                   rebalances_ytd: int) -> str:
        """
        Generate executive summary section
        
        Args:
            total_gain: Total unrealized gains
            tax_savings_ytd: Tax savings this year
            rebalances_ytd: Number of rebalances this year
        
        Returns:
            Formatted summary text
        """
        gain_pct = (total_gain / self.portfolio_value) * 100
        
        summary = f"""
{'='*70}
EXECUTIVE SUMMARY
Client: {self.client_name}
Report Date: {self.report_date.strftime('%B %d, %Y')}
{'='*70}

Portfolio Overview:
  Total Value:              ${self.portfolio_value:,.2f}
  Year-to-Date Return:      {gain_pct:+.2f}%
  
Tax Optimization Results:
  Tax Savings (YTD):        ${tax_savings_ytd:,.2f}
  Rebalancing Events:       {rebalances_ytd}
  Effective Tax Rate:       {(1 - tax_savings_ytd/total_gain)*100:.1f}% (vs. standard rate)

Service Value:
  Annual Tax Savings:       ${tax_savings_ytd:,.2f}
  Management Fee:           $150.00/month ($1,800/year)
  Net Benefit:              ${tax_savings_ytd - 1800:,.2f}
  ROI on Service:           {((tax_savings_ytd - 1800) / 1800) * 100:+.1f}%

{'='*70}
"""
        return summary
    
    def generate_performance_chart(self, 
                                  historical_values: List[Dict],
                                  benchmark_values: List[Dict],
                                  output_file: str = 'performance_chart.png'):
        """
        Generate performance comparison chart
        
        Args:
            historical_values: List of {'date': date, 'value': float}
            benchmark_values: List of {'date': date, 'value': float} for comparison
            output_file: Output filename
        """
        # Convert to DataFrames
        portfolio_df = pd.DataFrame(historical_values)
        benchmark_df = pd.DataFrame(benchmark_values)
        
        portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])
        benchmark_df['date'] = pd.to_datetime(benchmark_df['date'])
        
        # Calculate normalized returns (start at 100)
        portfolio_df['normalized'] = (portfolio_df['value'] / portfolio_df['value'].iloc[0]) * 100
        benchmark_df['normalized'] = (benchmark_df['value'] / benchmark_df['value'].iloc[0]) * 100
        
        # Create chart
        plt.figure(figsize=(12, 6))
        plt.plot(portfolio_df['date'], portfolio_df['normalized'], 
                label='Your Portfolio', linewidth=2, color='#2E86DE')
        plt.plot(benchmark_df['date'], benchmark_df['normalized'], 
                label='Benchmark (60/40)', linewidth=2, color='#EA8685', linestyle='--')
        
        plt.title(f'Portfolio Performance - {self.client_name}', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Value (Normalized to 100)', fontsize=12)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Performance chart saved: {output_file}")
    
    def generate_allocation_chart(self, 
                                 allocation_df: pd.DataFrame,
                                 output_file: str = 'allocation_chart.png'):
        """
        Generate current vs. target allocation chart
        
        Args:
            allocation_df: DataFrame with allocation data
            output_file: Output filename
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Current allocation pie chart
        ax1.pie(allocation_df['current_value'], 
               labels=allocation_df['ticker'],
               autopct='%1.1f%%',
               startangle=90,
               colors=['#2E86DE', '#EA8685', '#A29BFE', '#FDCB6E'])
        ax1.set_title('Current Allocation', fontsize=14, fontweight='bold')
        
        # Target allocation pie chart
        ax2.pie(allocation_df['target_weight'], 
               labels=allocation_df['ticker'],
               autopct='%1.1f%%',
               startangle=90,
               colors=['#2E86DE', '#EA8685', '#A29BFE', '#FDCB6E'])
        ax2.set_title('Target Allocation', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Allocation chart saved: {output_file}")
    
    def generate_tax_summary(self, 
                           tlh_opportunities: List[Dict],
                           realized_losses_ytd: float,
                           tax_rate: float) -> str:
        """
        Generate tax optimization summary
        
        Args:
            tlh_opportunities: Current TLH opportunities
            realized_losses_ytd: Realized losses year-to-date
            tax_rate: Tax rate
        
        Returns:
            Formatted tax summary
        """
        current_tlh_potential = sum(opp['tax_benefit'] for opp in tlh_opportunities)
        
        summary = f"""
{'='*70}
TAX OPTIMIZATION SUMMARY
{'='*70}

Year-to-Date Activity:
  Realized Losses:          ${abs(realized_losses_ytd):,.2f}
  Tax Savings:              ${abs(realized_losses_ytd) * tax_rate:,.2f}
  Harvesting Events:        {len(tlh_opportunities)} opportunities identified

Current Opportunities:
  Potential Additional Savings: ${current_tlh_potential:,.2f}

"""
        
        if tlh_opportunities:
            summary += "Available Tax-Loss Harvesting:\n"
            summary += "-" * 70 + "\n"
            
            for i, opp in enumerate(tlh_opportunities[:5], 1):  # Top 5
                summary += f"  {i}. {opp['ticker']:6s}  "
                summary += f"Loss: ${abs(opp['unrealized_loss']):>10,.2f}  "
                summary += f"Benefit: ${opp['tax_benefit']:>8,.2f}\n"
        
        summary += "\n" + "="*70 + "\n"
        
        return summary
    
    def generate_monthly_report(self,
                              portfolio_df: pd.DataFrame,
                              allocation_df: pd.DataFrame,
                              tlh_opportunities: List[Dict],
                              trades: List[Dict],
                              previous_value: float) -> str:
        """
        Generate complete monthly client report
        
        Args:
            portfolio_df: Portfolio holdings DataFrame
            allocation_df: Allocation analysis DataFrame
            tlh_opportunities: Tax-loss harvesting opportunities
            trades: Recommended trades
            previous_value: Portfolio value from last month
        
        Returns:
            Complete report text
        """
        current_value = portfolio_df['current_value'].sum()
        monthly_change = current_value - previous_value
        monthly_pct = (monthly_change / previous_value) * 100
        
        total_gain = portfolio_df['unrealized_gain'].sum()
        tax_savings = sum(opp['tax_benefit'] for opp in tlh_opportunities)
        
        # Executive summary
        report = self.generate_executive_summary(
            total_gain=total_gain,
            tax_savings_ytd=tax_savings,
            rebalances_ytd=2  # Would track this in production
        )
        
        # Monthly performance
        report += f"""
MONTHLY PERFORMANCE
{'='*70}

Portfolio Value:
  Beginning of Month:       ${previous_value:,.2f}
  End of Month:             ${current_value:,.2f}
  Change:                   ${monthly_change:+,.2f} ({monthly_pct:+.2f}%)

Holdings Summary:
  Number of Positions:      {len(portfolio_df)}
  Largest Position:         {portfolio_df.loc[portfolio_df['current_value'].idxmax(), 'ticker']}
  Most Profitable:          {portfolio_df.loc[portfolio_df['gain_pct'].idxmax(), 'ticker']} ({portfolio_df['gain_pct'].max():+.1f}%)

{'='*70}

"""
        
        # Allocation status
        report += "ALLOCATION STATUS\n"
        report += "="*70 + "\n\n"
        
        for _, row in allocation_df.iterrows():
            status = "✓ ON TARGET" if abs(row['drift_pct']) < 5 else "⚠ NEEDS REBALANCING"
            report += f"{row['ticker']:8s}  Current: {row['current_weight']*100:5.2f}%  "
            report += f"Target: {row['target_weight']*100:5.2f}%  "
            report += f"Drift: {row['drift_pct']:+6.2f}%  {status}\n"
        
        report += "\n" + "="*70 + "\n"
        
        # Tax optimization
        report += self.generate_tax_summary(
            tlh_opportunities=tlh_opportunities,
            realized_losses_ytd=0,  # Would track this
            tax_rate=0.24
        )
        
        # Recommended actions
        if trades:
            report += "RECOMMENDED ACTIONS\n"
            report += "="*70 + "\n\n"
            
            for i, trade in enumerate(trades, 1):
                report += f"{i}. {trade['action']} ${trade['dollar_amount']:,.2f} of {trade['ticker']}\n"
                report += f"   Reason: Rebalance from {trade['current_weight']*100:.1f}% to "
                report += f"{trade['target_weight']*100:.1f}%\n"
                if trade['tax_impact'] > 0:
                    report += f"   Tax Impact: ${trade['tax_impact']:,.2f}\n"
                report += "\n"
            
            report += "="*70 + "\n"
        
        # Next steps
        report += """
NEXT STEPS
{'='*70}

1. Review the recommended trades above
2. Approve trades via email or phone call
3. I will execute approved trades within 1 business day
4. You will receive trade confirmations from your broker
5. Next monthly report: {next_month}

Questions? Contact me anytime:
  Email: olivertewalt.pro@gmail.com
  Phone: (725) 377-3465

{'='*70}

DISCLAIMER: This report is for informational purposes only and does not 
constitute investment advice. Past performance does not guarantee future 
results. All investments involve risk.

""".format(next_month=(datetime.now() + timedelta(days=30)).strftime('%B %d, %Y'))
        
        return report
    
    def save_report(self, report_text: str, output_file: str = None):
        """
        Save report to file
        
        Args:
            report_text: Report content
            output_file: Output filename (auto-generated if None)
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d')
            output_file = f"monthly_report_{self.client_name.replace(' ', '_')}_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"Report saved: {output_file}")
        return output_file


class PerformanceTracker:
    """Track portfolio performance over time"""
    
    def __init__(self, tracking_file: str = 'performance_history.json'):
        """
        Initialize tracker
        
        Args:
            tracking_file: JSON file to store historical data
        """
        self.tracking_file = tracking_file
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load historical data from file"""
        try:
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'snapshots': [], 'trades': [], 'tlh_events': []}
    
    def _save_history(self):
        """Save historical data to file"""
        with open(self.tracking_file, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)
    
    def add_snapshot(self, 
                    portfolio_value: float,
                    total_gain: float,
                    allocation: Dict[str, float]):
        """
        Add portfolio snapshot
        
        Args:
            portfolio_value: Current portfolio value
            total_gain: Total unrealized gains
            allocation: Current allocation dict
        """
        snapshot = {
            'date': datetime.now().isoformat(),
            'value': portfolio_value,
            'total_gain': total_gain,
            'allocation': allocation
        }
        
        self.history['snapshots'].append(snapshot)
        self._save_history()
        
        print(f"✓ Snapshot saved: ${portfolio_value:,.2f}")
    
    def add_trade(self, ticker: str, action: str, shares: float, price: float):
        """Record a trade"""
        trade = {
            'date': datetime.now().isoformat(),
            'ticker': ticker,
            'action': action,
            'shares': shares,
            'price': price,
            'total': shares * price
        }
        
        self.history['trades'].append(trade)
        self._save_history()
    
    def add_tlh_event(self, ticker: str, loss: float, tax_benefit: float):
        """Record a tax-loss harvesting event"""
        event = {
            'date': datetime.now().isoformat(),
            'ticker': ticker,
            'loss': loss,
            'tax_benefit': tax_benefit
        }
        
        self.history['tlh_events'].append(event)
        self._save_history()
    
    def get_ytd_stats(self) -> Dict:
        """Calculate year-to-date statistics"""
        current_year = datetime.now().year
        
        ytd_snapshots = [s for s in self.history['snapshots'] 
                        if datetime.fromisoformat(s['date']).year == current_year]
        ytd_tlh = [e for e in self.history['tlh_events']
                  if datetime.fromisoformat(e['date']).year == current_year]
        
        if ytd_snapshots:
            first_value = ytd_snapshots[0]['value']
            last_value = ytd_snapshots[-1]['value']
            ytd_return = ((last_value - first_value) / first_value) * 100
        else:
            ytd_return = 0
        
        ytd_tax_savings = sum(e['tax_benefit'] for e in ytd_tlh)
        
        return {
            'ytd_return_pct': ytd_return,
            'ytd_tax_savings': ytd_tax_savings,
            'ytd_tlh_events': len(ytd_tlh),
            'snapshots_count': len(ytd_snapshots)
        }


# Example usage
if __name__ == "__main__":
    print("Client Reporting Module - Demo\n")
    
    # Initialize reporter
    reporter = ClientReporter(
        client_name="John Smith",
        portfolio_value=275000
    )
    
    # Sample data
    tlh_opportunities = [
        {'ticker': 'BND', 'unrealized_loss': -2500, 'tax_benefit': 600},
        {'ticker': 'VEA', 'unrealized_loss': -1200, 'tax_benefit': 288}
    ]
    
    # Generate executive summary
    summary = reporter.generate_executive_summary(
        total_gain=15000,
        tax_savings_ytd=2400,
        rebalances_ytd=3
    )
    
    print(summary)
    
    # Generate tax summary
    tax_summary = reporter.generate_tax_summary(
        tlh_opportunities=tlh_opportunities,
        realized_losses_ytd=-3500,
        tax_rate=0.24
    )
    
    print(tax_summary)