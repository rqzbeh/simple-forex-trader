#!/usr/bin/env python3
"""
Test script to verify cryptocurrency filtering and error message suppression
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import extract_forex_and_tickers, FOREX_SYMBOL_MAP

def test_crypto_filtering():
    """Test that cryptocurrency symbols are filtered out from news"""
    print("\n" + "="*80)
    print("TEST 1: Cryptocurrency Symbol Filtering")
    print("="*80)
    
    # Test cases with crypto symbols
    test_texts = [
        "$TRX is rising 10% today due to market sentiment",
        "$MKR token shows strong performance",
        "$BTC and $ETH lead the crypto market",
        "$EURUSD continues to trade sideways while $DOGE surges",
        "Gold $XAUUSD rises as $SOL falls",
    ]
    
    print("\nTesting news text extraction...\n")
    
    all_passed = True
    for text in test_texts:
        print(f"Text: '{text}'")
        extracted = extract_forex_and_tickers(text)
        
        # Check if any crypto symbols were extracted
        crypto_found = []
        valid_found = []
        
        for item in extracted:
            symbol = item['symbol']
            # Check if it's a known crypto (should have been filtered)
            crypto_symbols = {'BTC', 'ETH', 'USDT', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 
                              'DOT', 'MATIC', 'TRX', 'AVAX', 'LINK', 'UNI', 'LTC', 
                              'ATOM', 'XLM', 'ALGO', 'VET', 'FIL', 'THETA', 'XMR',
                              'ETC', 'AAVE', 'MKR', 'COMP', 'SUSHI', 'YFI', 'SNX'}
            
            if symbol in crypto_symbols:
                crypto_found.append(symbol)
            else:
                valid_found.append(symbol)
        
        if crypto_found:
            print(f"  ✗ FAIL: Crypto symbols extracted: {crypto_found}")
            all_passed = False
        else:
            print(f"  ✓ PASS: No crypto symbols extracted")
        
        if valid_found:
            print(f"  Valid symbols: {valid_found}")
        print()
    
    return all_passed

def test_natural_gas_removal():
    """Test that Natural Gas is removed from the symbol map"""
    print("\n" + "="*80)
    print("TEST 2: Natural Gas Symbol Removal")
    print("="*80)
    
    # Check if NATURALGAS is still in the map
    if 'NATURALGAS' in FOREX_SYMBOL_MAP:
        print(f"\n✗ FAIL: NATURALGAS still in FOREX_SYMBOL_MAP")
        print(f"  Value: {FOREX_SYMBOL_MAP['NATURALGAS']}")
        return False
    else:
        print(f"\n✓ PASS: NATURALGAS successfully removed from FOREX_SYMBOL_MAP")
        return True

def test_known_good_symbols():
    """Test that known good symbols are still extracted"""
    print("\n" + "="*80)
    print("TEST 3: Known Good Symbol Extraction")
    print("="*80)
    
    test_texts = [
        "EURUSD is trading higher today",
        "Gold XAUUSD shows strength",
        "$GBPUSD breaks resistance",
    ]
    
    expected_symbols = ['EURUSD', 'XAUUSD', 'GBPUSD']
    
    print("\nTesting that valid forex symbols are still extracted...\n")
    
    all_passed = True
    for text, expected in zip(test_texts, expected_symbols):
        print(f"Text: '{text}'")
        extracted = extract_forex_and_tickers(text)
        
        symbols = [item['symbol'] for item in extracted]
        
        if expected in symbols:
            print(f"  ✓ PASS: {expected} correctly extracted")
        else:
            print(f"  ✗ FAIL: {expected} not extracted (got: {symbols})")
            all_passed = False
        print()
    
    return all_passed

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SYMBOL FILTERING AND ERROR SUPPRESSION TESTS")
    print("="*80)
    print("\nThese tests verify:")
    print("  1. Cryptocurrency symbols are filtered out from news")
    print("  2. Natural Gas (NG=F) is removed from the symbol map")
    print("  3. Valid forex symbols are still properly extracted")
    print()
    
    results = []
    
    # Run tests
    results.append(('Crypto Filtering', test_crypto_filtering()))
    results.append(('Natural Gas Removal', test_natural_gas_removal()))
    results.append(('Good Symbol Extraction', test_known_good_symbols()))
    
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
        print("  - Filter out cryptocurrency symbols from news")
        print("  - Remove Natural Gas from the symbol map")
        print("  - Preserve valid forex/commodity symbol extraction")
        print()
        return 0
    else:
        print(f"\n✗ {total - passed} test group(s) failed")
        print()
        return 1

if __name__ == '__main__':
    exit(main())
