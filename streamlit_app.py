"""
Portfolio Rebalancer - Streamlit Web App
Client-facing interface for portfolio analysis
"""

import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
from data_loader import DataLoader
from portfolio_rebalancer import PortfolioRebalancer

# Manually include schwab parser logic for now
def detect_brokerage(filepath):
    """Detect brokerage from CSV"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        
        if 'Positions for account' in first_line:
            return 'schwab'
        elif 'ticker,shares,cost_basis,purchase_date' in first_line.lower():
            return 'standard'
        else:
            return 'generic'
    except:
        return 'unknown'

def convert_csv(uploaded_file):
    """Convert uploaded CSV to standard format"""
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
        tmp.write(uploaded_file.getvalue())
        temp_path = tmp.name
    
    # Detect brokerage
    brokerage = detect_brokerage(temp_path)
    
    if brokerage == 'schwab':
        from schwab_parser import parse_schwab_csv
        output_path = temp_path.replace('.csv', '_converted.csv')
        parse_schwab_csv(temp_path, output_path)
        return output_path
    elif brokerage == 'standard':
        return temp_path  # Already in correct format
    else:
        # Try to parse as generic
        try:
            df = pd.read_csv(temp_path)
            if all(col in df.columns for col in ['ticker', 'shares', 'cost_basis', 'purchase_date']):
                return temp_path
        except:
            pass
        return None

# Page config with dark theme
st.set_page_config(
    page_title="Smart Portfolio Rebalancer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark mode styling
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Text colors */
    .stMarkdown, p, li, label {
        color: #fafafa !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #fafafa !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #262730;
    }
    
    /* Info boxes - make them darker with better contrast */
    .stAlert {
        background-color: #1e2130;
        color: #fafafa;
    }
    
    /* Make success/info messages more visible */
    .stSuccess {
        background-color: #0e4429;
        color: #3fb950;
    }
    
    /* Dataframes */
    .dataframe {
        color: #fafafa !important;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #238636;
        color: white;
        border: none;
    }
    
    .stButton button:hover {
        background-color: #2ea043;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #fafafa !important;
    }
    
    /* Text inputs */
    .stTextInput input, .stTextArea textarea {
        background-color: #1e2130;
        color: #fafafa;
        border-color: #30363d;
    }
    
    /* Number inputs */
    .stNumberInput input {
        background-color: #1e2130;
        color: #fafafa;
        border-color: #30363d;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1e2130;
        color: #fafafa !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0e1117;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #8b949e;
    }
    
    .stTabs [aria-selected="true"] {
        color: #58a6ff !important;
        border-bottom-color: #58a6ff !important;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📊 Smart Portfolio Rebalancer")
st.markdown("Tax-optimized portfolio management made simple")

# Sidebar - User inputs
with st.sidebar:
    st.header("⚙️ Settings")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Portfolio CSV",
        type=['csv'],
        help="Download from Schwab, Vanguard, Fidelity, etc."
    )
    
    st.markdown("---")
    
    # Target allocation
    st.subheader("Target Allocation")
    
    with st.expander("ℹ️ What is target allocation?"):
        st.markdown("""
        **Target allocation** is your ideal portfolio mix - what percentage you want in each investment.
        
        **Common strategies:**
        
        📊 **Conservative (Low Risk)**
        - 70-80% Bonds/Stable Funds (VFORX, BND)
        - 20-30% Stocks (VTI, AAPL)
        - Good for: Near retirement, low risk tolerance
        
        ⚖️ **Moderate (Balanced)**
        - 50-60% Stocks
        - 40-50% Bonds
        - Good for: 10+ years to retirement
        
        🚀 **Aggressive (Higher Risk)**
        - 80-90% Stocks
        - 10-20% Bonds
        - Good for: Young investors, 20+ years to retirement
        
        **Example:** If you're 25 years old:
        - VFORX (Target Date Fund): 70%
        - AAPL (Tech stock): 15%
        - NVDA (Growth stock): 15%
        """)
    
    allocation_text = st.text_area(
        "Enter allocation",
        placeholder="VFORX=70, AAPL=10, NVDA=8, JNJ=7, VFH=5",
        help="Format: TICKER=PERCENT, separated by commas"
    )

    with st.expander("🎯 Help me choose my allocation"):
        age = st.number_input("Your age", 18, 100, 30)
        risk_tolerance = st.select_slider(
            "Risk tolerance",
            options=["Very Conservative", "Conservative", "Moderate", "Aggressive", "Very Aggressive"]
        )
        time_horizon = st.selectbox(
            "When do you need this money?",
            ["Less than 5 years", "5-10 years", "10-20 years", "20+ years"]
        )
        
        if st.button("Generate Recommended Allocation"):
            # Simple algorithm
            if time_horizon == "Less than 5 years":
                stock_pct = 30
            elif time_horizon == "5-10 years":
                stock_pct = 50
            elif time_horizon == "10-20 years":
                stock_pct = 70
            else:
                stock_pct = 85
            
            # Adjust for risk tolerance
            if risk_tolerance == "Very Conservative":
                stock_pct -= 20
            elif risk_tolerance == "Conservative":
                stock_pct -= 10
            elif risk_tolerance == "Aggressive":
                stock_pct += 10
            elif risk_tolerance == "Very Aggressive":
                stock_pct += 15
            
            stock_pct = max(20, min(95, stock_pct))
            bond_pct = 100 - stock_pct
            
            st.success(f"""
            **Recommended Allocation:**
            - Stocks/Growth: {stock_pct}%
            - Bonds/Stable: {bond_pct}%
            
            **Example allocation to enter above:**
            VFORX={bond_pct}, VTI={stock_pct}
            
            Or diversify stocks:
            VFORX={bond_pct}, AAPL={stock_pct//3}, NVDA={stock_pct//3}, VTI={stock_pct - 2*(stock_pct//3)}
            """)
    
    # Parse allocation
    target_allocation = {}
    total_pct = 0
    
    if allocation_text:
        try:
            for pair in allocation_text.split(','):
                ticker, pct = pair.split('=')
                target_allocation[ticker.strip().upper()] = float(pct.strip()) / 100
                total_pct += float(pct.strip())
        except:
            st.error("Invalid format. Use: TICKER=PERCENT, TICKER=PERCENT")
    
    if total_pct > 0:
        if abs(total_pct - 100) < 1:
            st.success(f"✓ Total: {total_pct:.1f}%")
        else:
            st.error(f"✗ Total must equal 100% (currently {total_pct:.1f}%)")
    
    st.markdown("---")
    
    # Tax rate
    tax_rate = st.number_input(
        "Tax Rate (%)",
        0.0, 50.0, 0.0,
        help="Enter 0 for Roth IRA, 24 for typical taxable account"
    ) / 100

    st.markdown("---")

    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        min_trade_size = st.number_input(
            "Minimum trade size ($)",
            100, 10000, 1000,
            step=100,
            help="Ignore recommendations smaller than this to avoid excessive transaction fees"
        )
        st.session_state['min_trade_size'] = min_trade_size

# Main area
if uploaded_file and target_allocation and abs(total_pct - 100) < 1:
    
    if st.button("🔍 Analyze Portfolio", type="primary", use_container_width=True):
        
        try:
            with st.spinner("Converting CSV format..."):
                converted_file = convert_csv(uploaded_file)
                
                if not converted_file:
                    st.error("❌ Could not process CSV. Please check format.")
                    st.stop()
            
            with st.spinner("Loading portfolio data..."):
                loader = DataLoader()
                holdings = loader.load_from_csv(converted_file)
                
                if not holdings:
                    st.error("❌ Could not load portfolio holdings")
                    st.stop()
            
            with st.spinner("Fetching current market prices..."):
                tickers = list(set(h['ticker'] for h in holdings))
                
                try:
                    api_key = st.secrets["ALPHAVANTAGE_API_KEY"]
                except:
                    api_key = os.getenv('ALPHAVANTAGE_API_KEY')
                
                if api_key:
                    loader_with_key = DataLoader(api_key=api_key)
                    prices = loader_with_key.get_current_prices(tickers, source='alphavantage')
                else:
                    prices = loader.get_current_prices(tickers, source='yahoo')
                
                if not prices:
                    st.error("❌ Could not fetch prices")
                    st.stop()
            
            with st.spinner("Running analysis..."):
                rebalancer = PortfolioRebalancer(target_allocation, tax_rate=tax_rate)
                
                portfolio_df = rebalancer.load_portfolio(holdings)
                portfolio_df = rebalancer.calculate_current_values(portfolio_df, prices)
                
                allocation_df = rebalancer.analyze_allocation(portfolio_df)
                tlh_opportunities = rebalancer.identify_tax_loss_harvesting(portfolio_df, min_loss=500)
                
                total_value = portfolio_df['current_value'].sum()
                trades = rebalancer.generate_rebalancing_trades(allocation_df, portfolio_df, total_value)
            
            st.success("✅ Analysis Complete!")
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Portfolio Value", f"${total_value:,.0f}")
            
            with col2:
                total_cost = portfolio_df['total_cost'].sum()
                total_gain = total_value - total_cost
                gain_pct = (total_gain / total_cost) * 100
                st.metric("Total Gain", f"${total_gain:,.0f}", f"{gain_pct:+.1f}%")
            
            with col3:
                tlh_benefit = sum(opp['tax_benefit'] for opp in tlh_opportunities) if tlh_opportunities else 0
                st.metric("Tax Savings Available", f"${tlh_benefit:,.0f}")
            
            # Tabs
            tab1, tab2, tab3 = st.tabs(["📊 Allocation", "💡 Recommendations", "📄 Full Report"])
            
            with tab1:
                st.subheader("Current vs Target Allocation")
                
                display_df = allocation_df[['ticker', 'current_weight', 'target_weight', 'drift_pct']].copy()
                display_df['current_weight'] = display_df['current_weight'] * 100
                display_df['target_weight'] = display_df['target_weight'] * 100
                display_df['drift_pct'] = display_df['drift_pct'].replace([float('inf'), float('-inf')], 'N/A')
                display_df.columns = ['Ticker', 'Current %', 'Target %', 'Drift %']
                
                st.dataframe(display_df, use_container_width=True)
            
            with tab2:
                st.subheader("Recommended Rebalancing Trades")
                
                st.warning("""
                ⚠️ **Before executing these trades, consider:**
                - **Transaction fees** from your broker ($0-$50 per trade)
                - **Mutual fund minimums** (e.g., VFORX requires $3,000 minimum purchase)
                - **Tax consequences** (especially important for taxable accounts)
                - **Small trades** under $1,000 may not be worth the fees
                
                💡 Adjust "Minimum trade size" in Advanced Settings to filter small trades.
                """)
                
                if trades:
                    min_trade_size = st.session_state.get('min_trade_size', 1000)
                    filtered_trades = [t for t in trades if t['dollar_amount'] >= min_trade_size]
                    
                    if not filtered_trades:
                        st.info(f"✅ No trades needed above ${min_trade_size:,.0f} threshold. Portfolio is well-balanced!")
                    else:
                        st.markdown(f"*Showing {len(filtered_trades)} trade(s) above ${min_trade_size:,.0f} threshold*")
                        st.markdown("---")
                        
                        MUTUAL_FUND_MINIMUMS = {
                            'VFORX': 3000, 'VDIGX': 3000, 'VFIAX': 3000,
                            'VTSAX': 3000, 'VTIAX': 3000, 'VBTLX': 3000,
                        }
                        
                        FUND_ALTERNATIVES = {
                            'VFORX': 'VT (Vanguard Total World Stock ETF)',
                            'VFIAX': 'VOO (Vanguard S&P 500 ETF)',
                            'VDIGX': 'VIG (Vanguard Dividend Appreciation ETF)',
                            'VTSAX': 'VTI (Vanguard Total Stock Market ETF)',
                            'VBTLX': 'BND (Vanguard Total Bond Market ETF)',
                        }
                        
                        for i, trade in enumerate(filtered_trades, 1):
                            with st.container():
                                if trade['action'] == 'SELL':
                                    st.markdown(f"**{i}. 🔴 SELL** ${trade['dollar_amount']:,.0f} of **{trade['ticker']}**")
                                else:
                                    st.markdown(f"**{i}. 🟢 BUY** ${trade['dollar_amount']:,.0f} of **{trade['ticker']}**")
                                
                                if trade.get('trade_type') == 'LIQUIDATE':
                                    st.caption(f"Liquidate entire position (target = 0%)")
                                else:
                                    st.caption(f"Adjust from {trade['current_weight']*100:.1f}% to {trade['target_weight']*100:.1f}%")
                                
                                if trade['action'] == 'BUY' and trade['ticker'] in MUTUAL_FUND_MINIMUMS:
                                    minimum = MUTUAL_FUND_MINIMUMS[trade['ticker']]
                                    if trade['dollar_amount'] < minimum:
                                        st.error(f"⚠️ **{trade['ticker']} requires ${minimum:,} minimum purchase.** Consider buying ${minimum:,} instead or use {FUND_ALTERNATIVES.get(trade['ticker'], 'an ETF alternative')}")
                                    else:
                                        st.info(f"ℹ️ {trade['ticker']} minimum: ${minimum:,} (buying ${trade['dollar_amount']:,.0f} ✓)")
                                
                                if trade['dollar_amount'] < 500:
                                    st.caption("⚠️ Very small trade - fees may outweigh benefit")
                                
                                st.markdown("---")
                else:
                    st.info("✅ No rebalancing needed. Portfolio is within acceptable thresholds.")
            
            with tab3:
                report = rebalancer.generate_report(portfolio_df, allocation_df, tlh_opportunities, trades)
                
                st.text_area("Full Analysis Report", report, height=400)
                
                st.download_button(
                    "📥 Download Report",
                    report,
                    file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

else:
    # Welcome screen
    st.markdown("""
    <div style='background-color: #1e2130; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #58a6ff;'>
        <p style='margin: 0; color: #58a6ff;'>
            👈 Upload your portfolio CSV and set your target allocation to get started
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
    ### How it works:
    1. **Download** your portfolio CSV from your brokerage
    2. **Upload** it using the sidebar
    3. **Set** your target allocation (e.g., "VFORX=70, AAPL=30")
    4. **Click** Analyze to get instant recommendations
    
    ### Supported brokerages:
    - ✅ Charles Schwab
    - ✅ Vanguard  
    - ✅ Fidelity
    - ✅ Most others (standard CSV format)
    
    ### What you'll get:
    - Current portfolio analysis
    - Recommended trades for rebalancing
    - Tax-loss harvesting opportunities
    - Downloadable detailed report
    """)

# Beta section
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")

col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h2 style='margin-bottom: 1rem; color: #fafafa;'>
            Beta-Testers Use This Tool 
            <span style='color: #3fb950; font-weight: bold;'>FREE</span>
        </h2>
        <h3 style='color: #30363d; font-weight: normal; margin-bottom: 2rem;'>
            In Exchange for Testimonials & Feedback
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; font-size: 1.1rem; line-height: 1.8; color: #c9d1d9;'>
        <p style='margin-bottom: 1.5rem;'>
            This is a <strong>student project</strong> designed to help people like you 
            <strong>save money on taxes</strong> and make the most of your investments.
        </p>
        <p style='margin-bottom: 1.5rem;'>
            The rebalancing engine uses the <strong>same algorithms as robo-advisors</strong> 
            like Wealthfront—and it only gets better each day.
        </p>
        <p style='margin-bottom: 2rem;'>
            Want to see what it recommends for your portfolio? 
            <strong>Try it above—completely free!</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background-color: #21262d; padding: 1.25rem; border-radius: 8px; 
                border-left: 4px solid #f85149; margin-top: 2rem; color: #c9d1d9; text-align: left;'>
        <strong style='color: #f85149;'>⚠️ IMPORTANT DISCLAIMER</strong><br>
        This is an educational portfolio analysis tool and is <strong>NOT investment advice</strong>. 
        I am not a licensed financial advisor. All investment decisions are your own responsibility.<br><br>
        Always consult with a licensed financial professional before making investment decisions. 
        Transaction costs, taxes, and other factors may affect actual results.
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")

st.markdown("""
<div style='background-color: #161b22; padding: 2rem; border-radius: 8px; margin-top: 2rem; border: 1px solid #30363d;'>
    <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;'>
        <div style='color: #c9d1d9;'>
            <p style='margin: 0; font-size: 0.95rem;'>
                📧 <a href='mailto:olivertewalt.pro@gmail.com' style='color: #58a6ff; text-decoration: none;'>
                olivertewalt.pro@gmail.com
                </a>
            </p>
        </div>
        <div style='color: #8b949e; font-size: 0.85rem;'>
            <p style='margin: 0;'>Version 1.0 Beta</p>
        </div>
    </div>
    <div style='text-align: center; color: #8b949e; font-size: 0.8rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #21262d;'>
        <p style='margin: 0;'>© 2026 Portfolio Rebalancer • Educational Tool • Not Investment Advice</p>
    </div>
</div>
""", unsafe_allow_html=True)