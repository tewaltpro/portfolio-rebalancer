"""
Universal Auto-Import Module
Automatically imports portfolio data from any brokerage CSV format
"""

import os
import glob
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict

# Import existing parsers
from schwab_parser import parse_schwab_csv


class UniversalImporter:
    """Universal portfolio importer supporting multiple brokerages"""
    
    def __init__(self, auto_import_folder: str = None, output_folder: str = None):
        """
        Initialize the importer
        
        Args:
            auto_import_folder: Folder to watch for new CSV files
            output_folder: Where to save converted portfolios
        """
        if auto_import_folder is None:
            auto_import_folder = os.path.join(
                os.path.dirname(__file__), 
                "Inputs", 
                "auto-import"
            )
        
        if output_folder is None:
            output_folder = os.path.join(
                os.path.dirname(__file__), 
                "Inputs"
            )
        
        self.auto_import_folder = auto_import_folder
        self.output_folder = output_folder
        
        # Create folders if they don't exist
        os.makedirs(self.auto_import_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
    
    def detect_brokerage(self, filepath: str) -> Optional[str]:
        """
        Detect which brokerage a CSV is from
        
        Args:
            filepath: Path to CSV file
        
        Returns:
            Brokerage name ('schwab', 'vanguard', 'fidelity', etc.) or None
        """
        try:
            # Read first few lines to detect format
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
            
            # Schwab: First line contains "Positions for account"
            if 'Positions for account' in first_line:
                return 'schwab'
            
            # Vanguard: Headers include "Fund Name" or "Account Number"
            if 'Fund Name' in first_line or 'Account Number' in first_line:
                return 'vanguard'
            
            # Fidelity: Headers include "Account Name" and "Symbol"
            if 'Account Name' in first_line and 'Symbol' in first_line:
                return 'fidelity'
            
            # Generic format: Already in our standard format
            if 'ticker,shares,cost_basis,purchase_date' in first_line.lower():
                return 'standard'
            
            # Try to detect by column patterns in header
            if 'Symbol' in first_line and 'Quantity' in first_line and 'Cost' in first_line:
                return 'generic'
            
            print(f"⚠ Could not auto-detect brokerage from file")
            print(f"  First line: {first_line[:100]}...")
            return None
            
        except Exception as e:
            print(f"✗ Error detecting brokerage: {e}")
            return None
    
    def parse_vanguard_csv(self, filepath: str, output_file: str) -> Optional[str]:
        """Parse Vanguard CSV format"""
        try:
            # Vanguard CSVs typically have headers on first row
            df = pd.read_csv(filepath)
            
            # Map Vanguard columns to our format
            converted = pd.DataFrame()
            
            # Vanguard uses different column names
            if 'Fund Name' in df.columns:
                converted['ticker'] = df['Symbol'] if 'Symbol' in df.columns else df['Fund Name']
            else:
                converted['ticker'] = df['Symbol']
            
            converted['shares'] = df['Shares'] if 'Shares' in df.columns else df['Quantity']
            
            # Vanguard often provides total cost, need to divide by shares
            if 'Total Cost' in df.columns:
                converted['cost_basis'] = df['Total Cost'] / converted['shares']
            else:
                converted['cost_basis'] = df['Price Paid'] if 'Price Paid' in df.columns else df['Cost Basis']
            
            # Vanguard rarely includes purchase dates in position exports
            converted['purchase_date'] = '2023-01-01'  # PLACEHOLDER
            
            # Clean up
            converted = converted[converted['ticker'].notna()]
            converted = converted[converted['shares'] > 0]
            
            # Save
            converted.to_csv(output_file, index=False)
            print(f"✓ Converted Vanguard portfolio: {len(converted)} holdings")
            print(f"⚠ WARNING: Purchase dates set to placeholder. Update manually for tax optimization.")
            
            return output_file
            
        except Exception as e:
            print(f"✗ Error parsing Vanguard CSV: {e}")
            return None
    
    def parse_fidelity_csv(self, filepath: str, output_file: str) -> Optional[str]:
        """Parse Fidelity CSV format"""
        try:
            # Fidelity CSVs have account info in first rows
            df = pd.read_csv(filepath, skiprows=1)
            
            converted = pd.DataFrame()
            
            converted['ticker'] = df['Symbol']
            converted['shares'] = df['Quantity']
            
            # Fidelity shows cost basis per share
            if 'Cost Basis Per Share' in df.columns:
                converted['cost_basis'] = df['Cost Basis Per Share']
            else:
                converted['cost_basis'] = df['Cost Basis Total'] / df['Quantity']
            
            converted['purchase_date'] = '2023-01-01'  # PLACEHOLDER
            
            # Clean up
            converted = converted[converted['ticker'].notna()]
            converted = converted[converted['ticker'] != '']
            converted = converted[converted['shares'] > 0]
            
            # Save
            converted.to_csv(output_file, index=False)
            print(f"✓ Converted Fidelity portfolio: {len(converted)} holdings")
            print(f"⚠ WARNING: Purchase dates set to placeholder. Update manually for tax optimization.")
            
            return output_file
            
        except Exception as e:
            print(f"✗ Error parsing Fidelity CSV: {e}")
            return None
    
    def parse_generic_csv(self, filepath: str, output_file: str) -> Optional[str]:
        """Parse generic brokerage CSV format"""
        try:
            df = pd.read_csv(filepath)
            
            converted = pd.DataFrame()
            
            # Try to map common column names
            ticker_cols = ['Symbol', 'Ticker', 'Security']
            shares_cols = ['Quantity', 'Shares', 'Qty']
            cost_cols = ['Cost Basis', 'Cost Per Share', 'Average Cost']
            
            # Find the right columns
            ticker_col = next((c for c in ticker_cols if c in df.columns), None)
            shares_col = next((c for c in shares_cols if c in df.columns), None)
            cost_col = next((c for c in cost_cols if c in df.columns), None)
            
            if not ticker_col or not shares_col or not cost_col:
                print(f"✗ Could not find required columns in CSV")
                print(f"  Available columns: {', '.join(df.columns)}")
                return None
            
            converted['ticker'] = df[ticker_col]
            converted['shares'] = df[shares_col]
            converted['cost_basis'] = df[cost_col]
            converted['purchase_date'] = '2023-01-01'
            
            # Clean up
            converted = converted[converted['ticker'].notna()]
            converted = converted[converted['shares'] > 0]
            
            # Save
            converted.to_csv(output_file, index=False)
            print(f"✓ Converted generic portfolio: {len(converted)} holdings")
            
            return output_file
            
        except Exception as e:
            print(f"✗ Error parsing generic CSV: {e}")
            return None
    
    def get_latest_csv(self) -> Optional[str]:
        """Find the most recent CSV in the auto-import folder"""
        search_pattern = os.path.join(self.auto_import_folder, "*.csv")
        csv_files = glob.glob(search_pattern)
        
        if not csv_files:
            print(f"✗ No CSV files found in {self.auto_import_folder}")
            return None
        
        # Get the most recently modified file
        latest_file = max(csv_files, key=os.path.getmtime)
        print(f"✓ Found latest CSV: {os.path.basename(latest_file)}")
        
        return latest_file
    
    def import_latest(self) -> Optional[str]:
        """
        Import and convert the latest CSV file
        
        Returns:
            Path to converted portfolio CSV or None
        """
        # Find latest CSV
        latest_csv = self.get_latest_csv()
        if not latest_csv:
            return None
        
        # Detect brokerage
        print(f"\nDetecting brokerage format...")
        brokerage = self.detect_brokerage(latest_csv)
        
        if not brokerage:
            print(f"✗ Could not determine brokerage format")
            print(f"\n💡 Tip: Use a specific parser instead:")
            print(f"  python schwab_parser.py \"{latest_csv}\" output.csv")
            return None
        
        print(f"✓ Detected: {brokerage.upper()}")
        
        # Generate output filename
        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(self.output_folder, f"portfolio_{today}.csv")
        
        # Parse based on brokerage
        print(f"\nConverting to standard format...")
        
        if brokerage == 'schwab':
            return parse_schwab_csv(latest_csv, output_file)
        elif brokerage == 'vanguard':
            return self.parse_vanguard_csv(latest_csv, output_file)
        elif brokerage == 'fidelity':
            return self.parse_fidelity_csv(latest_csv, output_file)
        elif brokerage == 'standard':
            # Already in our format, just copy it
            import shutil
            shutil.copy(latest_csv, output_file)
            print(f"✓ Portfolio already in standard format")
            return output_file
        elif brokerage == 'generic':
            return self.parse_generic_csv(latest_csv, output_file)
        else:
            print(f"✗ No parser available for {brokerage}")
            return None


def import_portfolio_auto() -> Optional[str]:
    """
    Convenience function: Import latest portfolio automatically
    
    Returns:
        Path to converted portfolio CSV
    """
    importer = UniversalImporter()
    return importer.import_latest()


if __name__ == "__main__":
    print("="*60)
    print("UNIVERSAL PORTFOLIO IMPORTER")
    print("="*60 + "\n")
    
    result = import_portfolio_auto()
    
    if result:
        print(f"\n{'='*60}")
        print("✓ SUCCESS!")
        print(f"{'='*60}")
        print(f"\nConverted portfolio saved to:")
        print(f"  {result}")
        print(f"\nNext step:")
        print(f"  python main_app.py --portfolio \"{result}\" --interactive")
    else:
        print(f"\n{'='*60}")
        print("✗ IMPORT FAILED")
        print(f"{'='*60}")
        print(f"\nPlease check:")
        print(f"  1. CSV file exists in: Inputs/auto-import/")
        print(f"  2. CSV is from a supported brokerage")
        print(f"  3. File is not corrupted")