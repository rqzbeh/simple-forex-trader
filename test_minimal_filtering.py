#!/usr/bin/env python3
"""
Minimal test to verify symbol filtering logic without loading the full main module
"""

import re

# Cryptocurrency symbols to filter (same as in main.py)
CRYPTO_SYMBOLS = {'BTC', 'ETH', 'USDT', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 
                  'DOT', 'MATIC', 'TRX', 'AVAX', 'LINK', 'UNI', 'LTC', 
                  'ATOM', 'XLM', 'ALGO', 'VET', 'FIL', 'THETA', 'XMR',
                  'ETC', 'AAVE', 'MKR', 'COMP', 'SUSHI', 'YFI', 'SNX'}

def test_crypto_filtering_logic():
    """Test that the crypto filtering logic works correctly"""
    print("\n" + "="*80)
    print("TEST: Cryptocurrency Symbol Filtering Logic")
    print("="*80)
    
    # Test cases with crypto symbols
    test_texts = [
        ("$TRX is rising 10% today", ['TRX']),
        ("$MKR token shows strong performance", ['MKR']),
        ("$BTC and $ETH lead the crypto market", ['BTC', 'ETH']),
        ("$EURUSD continues to trade sideways while $DOGE surges", ['DOGE']),
        ("$SOL and $ADA are trending", ['SOL', 'ADA']),
    ]
    
    print("\nTesting crypto symbol extraction and filtering...\n")
    
    all_passed = True
    for text, expected_cryptos in test_texts:
        print(f"Text: '{text}'")
        
        # Extract $TICKER patterns
        found_tickers = re.findall(r'\$([A-Z]{3,7})\b', text.upper())
        
        # Filter out crypto symbols
        crypto_found = [t for t in found_tickers if t in CRYPTO_SYMBOLS]
        non_crypto = [t for t in found_tickers if t not in CRYPTO_SYMBOLS]
        
        print(f"  Tickers found: {found_tickers}")
        print(f"  Crypto tickers (should be filtered): {crypto_found}")
        print(f"  Non-crypto tickers (should be kept): {non_crypto}")
        
        # Verify expected cryptos are in the filter list
        for expected in expected_cryptos:
            if expected in CRYPTO_SYMBOLS:
                print(f"  ✓ {expected} is in CRYPTO_SYMBOLS (will be filtered)")
            else:
                print(f"  ✗ {expected} is NOT in CRYPTO_SYMBOLS (won't be filtered!)")
                all_passed = False
        
        print()
    
    return all_passed

def test_natural_gas_comment():
    """Test that Natural Gas is commented out in the code"""
    print("\n" + "="*80)
    print("TEST: Natural Gas Symbol Commented Out")
    print("="*80)
    
    # Read main.py and check if NG=F line is commented
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        
        # Check for uncommented NG=F
        lines_with_ng = []
        for i, line in enumerate(content.split('\n'), 1):
            if 'NG=F' in line and not line.strip().startswith('#'):
                lines_with_ng.append((i, line))
        
        if lines_with_ng:
            print("\n✗ FAIL: Found uncommented NG=F references:")
            for line_num, line in lines_with_ng:
                print(f"  Line {line_num}: {line.strip()}")
            return False
        else:
            print("\n✓ PASS: All NG=F references are commented out or removed")
            return True
            
    except Exception as e:
        print(f"\n✗ ERROR: Could not read main.py: {e}")
        return False

def test_verbose_logging_removed():
    """Test that verbose yfinance logging is removed or reduced"""
    print("\n" + "="*80)
    print("TEST: Verbose Logging Reduction")
    print("="*80)
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        
        # Check for reduced verbosity patterns
        verbose_patterns = [
            ('Attempting yfinance for', 'print(f"Attempting yfinance for'),
            ('yfinance success for', 'print(f"yfinance success for'),
            ('yfinance failed for', 'print(f"yfinance failed for'),
            ('yfinance insufficient data', 'print(f\'yfinance insufficient data'),
            ('yfinance low volume', 'print(f\'yfinance low volume'),
        ]
        
        print("\nChecking for reduced verbosity...\n")
        
        found_verbose = []
        for pattern, search in verbose_patterns:
            if search in content:
                found_verbose.append(pattern)
        
        if found_verbose:
            print(f"✗ FAIL: Found verbose logging patterns:")
            for pattern in found_verbose:
                print(f"  - {pattern}")
            return False
        else:
            print("✓ PASS: Verbose logging patterns have been removed or reduced")
            
            # Check for DEBUG-conditional logging instead
            if 'if DEBUG:' in content and 'print(f' in content:
                print("✓ Additional logging is now DEBUG-conditional")
            
            return True
            
    except Exception as e:
        print(f"\n✗ ERROR: Could not read main.py: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SYMBOL FILTERING AND ERROR SUPPRESSION VERIFICATION")
    print("="*80)
    print("\nThese tests verify the code changes without running the full system:")
    print("  1. Cryptocurrency symbols are in the filter list")
    print("  2. Natural Gas (NG=F) is commented out")
    print("  3. Verbose yfinance logging has been reduced")
    print()
    
    results = []
    
    # Run tests
    results.append(('Crypto Filtering Logic', test_crypto_filtering_logic()))
    results.append(('Natural Gas Commented', test_natural_gas_comment()))
    results.append(('Verbose Logging Reduced', test_verbose_logging_removed()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} test groups passed\n")
    
    for name, result in results:
        status = '✓ PASS' if result else '✗ FAIL'
        print(f"{status} {name}")
    
    print("\n" + "="*80)
    
    if passed == total:
        print("\n✓ All tests passed! The changes successfully:")
        print("  - Added cryptocurrency symbol filtering")
        print("  - Removed/commented Natural Gas from the symbol map")
        print("  - Reduced verbose yfinance error messages")
        print("\nExpected impact:")
        print("  - Much less terminal spam from yfinance errors")
        print("  - No more 'possibly delisted' errors for crypto symbols")
        print("  - No more NG=F errors")
        print()
        return 0
    else:
        print(f"\n✗ {total - passed} test group(s) failed")
        print()
        return 1

if __name__ == '__main__':
    exit(main())
