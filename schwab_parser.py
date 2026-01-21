"""
Schwab CSV Parser
Converts Schwab's complex export format to our simple format
"""

import pandas as pd
import re

def clean_currency(value):
    """Remove $, commas, and convert to float"""
    if pd.isna(value) or value == '' or value == '--':
        return 0.0
    # Remove $, commas, parentheses, and convert to float
    cleaned = str(value).replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def parse_schwab_csv(schwab_file: str, output_file: str = 'converted_portfolio.csv'):
    """
    Parse Schwab CSV export into our format
    
    Args:
        schwab_file: Path to Schwab CSV
        output_file: Path for converted CSV
    """
    # Read Schwab CSV - skip first row (account header)
    df = pd.read_csv(schwab_file, skiprows=1)
    
    # Print columns to debug
    print("Found columns in CSV:")
    for i, col in enumerate(df.columns):
        print(f"  {i}: '{col}'")
    print()
    
    # Try to find the right columns (handle various naming conventions)
    symbol_col = None
    qty_col = None
    cost_basis_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'symbol' in col_lower and 'description' not in col_lower:
            symbol_col = col
        elif 'qty' in col_lower or 'quantity' in col_lower:
            qty_col = col
        elif 'cost basis' in col_lower:
            cost_basis_col = col
    
    if not symbol_col or not qty_col or not cost_basis_col:
        print("✗ Could not find required columns!")
        print(f"  Symbol column: {symbol_col}")
        print(f"  Quantity column: {qty_col}")
        print(f"  Cost Basis column: {cost_basis_col}")
        print("\nPlease check the CSV format and update the parser.")
        return None
    
    print(f"✓ Using columns:")
    print(f"  Symbol: '{symbol_col}'")
    print(f"  Quantity: '{qty_col}'")
    print(f"  Cost Basis: '{cost_basis_col}'")
    print()
    
    # Create our format
    converted = pd.DataFrame()
    
    # Map columns
    converted['ticker'] = df[symbol_col]
    
    # Clean and convert numeric columns
    converted['shares'] = df[qty_col].apply(clean_currency)
    cost_basis_total = df[cost_basis_col].apply(clean_currency)
    
    # Calculate cost basis per share
    converted['cost_basis'] = (cost_basis_total / converted['shares']).round(2)
    
    # Purchase date - will need manual entry or from tax lots
    # For now, use a placeholder that user must update
    converted['purchase_date'] = '2023-01-01'  # PLACEHOLDER
    
    # Remove non-equity holdings (cash, etc.)
    converted = converted[converted['ticker'].notna()]
    converted = converted[converted['ticker'] != '--']
    converted = converted[converted['ticker'] != '']
    
    # Remove any rows where shares is 0 or NaN or invalid
    converted = converted[converted['shares'] > 0]
    converted = converted[~converted['cost_basis'].isna()]
    converted = converted[converted['cost_basis'] > 0]
    
    # Reset index
    converted = converted.reset_index(drop=True)
    
    # Save
    converted.to_csv(output_file, index=False)
    
    print(f"✓ Converted {len(converted)} holdings")
    print(f"✓ Saved to: {output_file}")
    print(f"\n⚠ WARNING: Purchase dates set to placeholder '2023-01-01'!")
    print(f"   You MUST update the 'purchase_date' column with real dates for accurate tax optimization")
    print(f"   In Schwab: Positions → Click on holding → Cost Basis → Tax Lots")
    print(f"\n📝 Next step: Edit {output_file} and update purchase dates, then run:")
    print(f'   python main_app.py --portfolio "{output_file}" --interactive')
    
    return output_file


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python schwab_parser.py <schwab_export.csv> [output_file.csv]")
        print("\nExample:")
        print('  python schwab_parser.py "schwab_positions.csv" "my_portfolio.csv"')
        sys.exit(1)
    
    schwab_file = sys.argv[1].strip().strip('"').strip("'")
    
    # Check if output file was provided
    if len(sys.argv) >= 3:
        output_file = sys.argv[2].strip().strip('"').strip("'")
    else:
        output_file = 'converted_portfolio.csv'
    
    try:
        result = parse_schwab_csv(schwab_file, output_file)
        if result:
            print(f"\n✓ SUCCESS! Now edit {result} to add real purchase dates.")
            print(f"\nNext step:")
            print(f'  python main_app.py --portfolio "{result}" --interactive')
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()