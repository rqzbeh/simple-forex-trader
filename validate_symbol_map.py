#!/usr/bin/env python3
"""
Script to validate FOREX_SYMBOL_MAP symbols against yfinance
Run this periodically to ensure all symbols have valid data

Requirements:
- Internet connectivity
- yfinance package installed
- Run from environment with proper network access

Usage:
    python validate_symbol_map.py [--verbose] [--fix]
    
Options:
    --verbose    Show detailed information for each symbol
    --fix        Generate code to comment out invalid symbols (dry-run by default)
"""

import sys
import time
import argparse
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

# Import the symbol map from main
try:
    from main import FOREX_SYMBOL_MAP, DEFAULT_SYMBOLS
except ImportError:
    print("Error: Could not import from main.py")
    print("Make sure you're running this from the same directory as main.py")
    sys.exit(1)


def test_symbol(symbol, description, verbose=False):
    """
    Test a symbol to see if it has sufficient data for the bot
    
    Returns:
        (status, details) where status is 'valid', 'low_data', or 'invalid'
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Test hourly data (bot requires 26+ candles for indicators)
        hist_hourly = ticker.history(period='3d', interval='1h')
        hist_daily = ticker.history(period='30d', interval='1d')
        
        hourly_count = len(hist_hourly)
        daily_count = len(hist_daily)
        
        details = {
            'hourly_count': hourly_count,
            'daily_count': daily_count,
            'error': None
        }
        
        # Calculate average volume if data exists
        if hourly_count > 0:
            details['avg_volume'] = hist_hourly['Volume'].tail(10).mean()
        
        # Check bot requirements
        if hourly_count >= 26 and daily_count >= 2:
            return 'valid', details
        elif hourly_count > 0 or daily_count > 0:
            return 'low_data', details
        else:
            return 'invalid', details
            
    except Exception as e:
        return 'invalid', {'error': str(e)[:100]}


def validate_all_symbols(verbose=False, rate_limit_delay=0.2):
    """
    Validate all symbols in FOREX_SYMBOL_MAP
    
    Args:
        verbose: Show detailed info for each symbol
        rate_limit_delay: Seconds to wait between API calls
    
    Returns:
        dict with 'valid', 'low_data', and 'invalid' lists
    """
    print("\n" + "="*90)
    print("VALIDATING FOREX_SYMBOL_MAP")
    print("="*90)
    print(f"Total symbols to test: {len(FOREX_SYMBOL_MAP)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        'valid': [],
        'low_data': [],
        'invalid': []
    }
    
    for i, (key, yf_symbol) in enumerate(FOREX_SYMBOL_MAP.items(), 1):
        if verbose:
            print(f"[{i}/{len(FOREX_SYMBOL_MAP)}] Testing {key} -> {yf_symbol}...", end=' ')
        
        status, details = test_symbol(yf_symbol, key, verbose)
        
        results[status].append({
            'key': key,
            'yf_symbol': yf_symbol,
            'details': details
        })
        
        if verbose:
            if status == 'valid':
                vol = details.get('avg_volume', 0)
                print(f"✓ VALID (H:{details['hourly_count']}, D:{details['daily_count']}, Vol:{vol:,.0f})")
            elif status == 'low_data':
                print(f"⚠ LOW DATA (H:{details['hourly_count']}, D:{details['daily_count']})")
            else:
                error = details.get('error', 'No data')
                print(f"✗ INVALID ({error})")
        elif i % 10 == 0:
            print(f"Progress: {i}/{len(FOREX_SYMBOL_MAP)} symbols tested...")
        
        time.sleep(rate_limit_delay)
    
    return results


def print_summary(results):
    """Print a summary of validation results"""
    print("\n" + "="*90)
    print("VALIDATION SUMMARY")
    print("="*90)
    
    total = len(results['valid']) + len(results['low_data']) + len(results['invalid'])
    
    print(f"\n✓ Valid symbols: {len(results['valid'])} ({len(results['valid'])/total*100:.1f}%)")
    print(f"⚠ Low data symbols: {len(results['low_data'])} ({len(results['low_data'])/total*100:.1f}%)")
    print(f"✗ Invalid symbols: {len(results['invalid'])} ({len(results['invalid'])/total*100:.1f}%)")
    
    if results['invalid']:
        print("\n" + "-"*90)
        print("INVALID SYMBOLS (should be removed or commented out):")
        print("-"*90)
        for item in results['invalid']:
            error = item['details'].get('error', 'No data')
            print(f"  '{item['key']}': '{item['yf_symbol']}',  # {error[:60]}")
    
    if results['low_data']:
        print("\n" + "-"*90)
        print("LOW DATA SYMBOLS (may work intermittently):")
        print("-"*90)
        for item in results['low_data']:
            h = item['details']['hourly_count']
            d = item['details']['daily_count']
            print(f"  '{item['key']}': '{item['yf_symbol']}',  # H:{h}, D:{d} (needs 26+ hourly)")


def validate_default_symbols(verbose=False):
    """Validate symbols in DEFAULT_SYMBOLS list"""
    print("\n" + "="*90)
    print("VALIDATING DEFAULT_SYMBOLS")
    print("="*90)
    print(f"Total default symbols: {len(DEFAULT_SYMBOLS)}")
    print()
    
    issues = []
    
    for key, yf_symbol, kind in DEFAULT_SYMBOLS:
        if verbose:
            print(f"Testing {key} ({kind}) -> {yf_symbol}...", end=' ')
        
        status, details = test_symbol(yf_symbol, key, verbose)
        
        if status != 'valid':
            issues.append({
                'key': key,
                'yf_symbol': yf_symbol,
                'kind': kind,
                'status': status,
                'details': details
            })
            if verbose:
                print(f"⚠ {status.upper()}")
        elif verbose:
            print("✓ VALID")
        
        time.sleep(0.2)
    
    if issues:
        print("\n" + "-"*90)
        print("ISSUES WITH DEFAULT_SYMBOLS:")
        print("-"*90)
        for issue in issues:
            h = issue['details'].get('hourly_count', 0)
            d = issue['details'].get('daily_count', 0)
            print(f"  {issue['status'].upper():10} {issue['key']:15} -> {issue['yf_symbol']:15} (H:{h}, D:{d})")
        print(f"\nRecommendation: Consider removing or replacing {len(issues)} symbol(s) from DEFAULT_SYMBOLS")
    else:
        print("\n✓ All DEFAULT_SYMBOLS are valid!")
    
    return issues


def main():
    parser = argparse.ArgumentParser(description='Validate FOREX_SYMBOL_MAP against yfinance')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    parser.add_argument('--defaults-only', action='store_true', help='Only validate DEFAULT_SYMBOLS')
    parser.add_argument('--quick', action='store_true', help='Sample 20 symbols instead of all')
    
    args = parser.parse_args()
    
    print("\n" + "="*90)
    print("FOREX SYMBOL MAP VALIDATOR")
    print("="*90)
    print("\nThis script validates that symbols in FOREX_SYMBOL_MAP have sufficient")
    print("yfinance data for the trading bot to function properly.")
    print("\nRequirements:")
    print("  - Hourly data: 26+ candles (for technical indicators)")
    print("  - Daily data: 2+ candles (for pivot calculations)")
    
    try:
        # Validate DEFAULT_SYMBOLS
        if not args.quick:
            default_issues = validate_default_symbols(args.verbose)
        
        # Validate full map unless defaults-only
        if not args.defaults_only:
            if args.quick:
                print("\n⚠ Quick mode: Testing sample of 20 symbols")
                print("Run without --quick to test all symbols")
            
            results = validate_all_symbols(args.verbose, rate_limit_delay=0.2)
            print_summary(results)
            
            # Return exit code based on results
            if len(results['invalid']) > len(FOREX_SYMBOL_MAP) * 0.1:  # More than 10% invalid
                print(f"\n⚠ WARNING: {len(results['invalid'])} invalid symbols found!")
                print("Consider updating FOREX_SYMBOL_MAP to remove invalid symbols.")
                return 1
        
        print("\n" + "="*90)
        print("✓ Validation complete")
        print("="*90 + "\n")
        return 0
        
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\n✗ Error during validation: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
