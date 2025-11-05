import os
import time
import math
import re
import json
import requests
import logging
import sys
import asyncio
import aiohttp
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from newsapi import NewsApiClient
import yfinance as yf
from textblob import TextBlob
from alpha_vantage.foreignexchange import ForeignExchange
from iexfinance.stocks import Stock
try:
    from polygon import RESTClient as PolygonRESTClient
except ImportError:
    PolygonRESTClient = None

try:
    from twelvedata import TDClient
except ImportError:
    TDClient = None

try:
    from fmp_python.fmp import FMP
except ImportError:
    FMP = None

try:
    import quandl
except ImportError:
    quandl = None

try:
    from fredapi import Fred
except ImportError:
    Fred = None

try:
    from ml_predictor import get_ml_predictor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: ML predictor not available. Install scikit-learn for ML features.")

# LLM is now mandatory - import or fail
try:
    from llm_news_analyzer import enhance_sentiment_with_llm, get_llm_analyzer
    LLM_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: LLM news analyzer is required but not available: {e}")
    print("Install with: pip install groq")
    exit(1)

# Suppress yfinance warnings and errors for cleaner output
logging.getLogger('yfinance').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)

# Silence yfinance verbosity
logging.getLogger("yfinance").setLevel(logging.ERROR)

# -------------------- Configuration --------------------
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
if not NEWS_API_KEY:
    raise ValueError('Please set the NEWS_API_KEY environment variable')

ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')  # Optional, for backup data
IEX_API_TOKEN = os.getenv('IEX_API_TOKEN')  # Optional, for IEX Cloud data

# New API keys (optional) - set these if you want additional free-data fallbacks
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')
FMP_API_KEY = os.getenv('FMP_API_KEY')
QUANDL_API_KEY = os.getenv('QUANDL_API_KEY')
FRED_API_KEY = os.getenv('FRED_API_KEY')

print("API Keys status:")
print(f"NEWS_API_KEY: {'Set' if NEWS_API_KEY else 'Not set'}")
print(f"ALPHA_VANTAGE_API_KEY: {'Set' if ALPHA_VANTAGE_API_KEY else 'Not set'}")
print(f"POLYGON_API_KEY: {'Set' if POLYGON_API_KEY else 'Not set'}")
print(f"TWELVE_DATA_API_KEY: {'Set' if TWELVE_DATA_API_KEY else 'Not set'}")
print(f"FMP_API_KEY: {'Set' if FMP_API_KEY else 'Not set'}")
print(f"QUANDL_API_KEY: {'Set' if QUANDL_API_KEY else 'Not set'}")
print(f"FRED_API_KEY: {'Set' if FRED_API_KEY else 'Not set'}")
print(f"IEX_API_TOKEN: {'Set' if IEX_API_TOKEN else 'Not set'}")
print(f"GROQ_API_KEY: {'Set' if os.getenv('GROQ_API_KEY') else 'Not set (REQUIRED)'}")
print(f"Groq Rate Limits: {'Disabled' if not GROQ_ENFORCE_LIMITS else f'{GROQ_MAX_REQUESTS_PER_DAY} req/day, {GROQ_MAX_TOKENS_PER_DAY} tokens/day'}")


# Initialize clients lazily when keys are present
_polygon_client = PolygonRESTClient(POLYGON_API_KEY) if POLYGON_API_KEY else None
_td_client = TDClient(apikey=TWELVE_DATA_API_KEY) if TWELVE_DATA_API_KEY else None
_fmp_client = FMP(FMP_API_KEY) if FMP_API_KEY and FMP else None
if QUANDL_API_KEY:
    quandl.ApiConfig.api_key = QUANDL_API_KEY
_fred_client = Fred(api_key=FRED_API_KEY) if FRED_API_KEY else None

newsapi = NewsApiClient(api_key=NEWS_API_KEY)

def send_telegram_message(message):
    """Send a message via Telegram bot."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id:
        print("Telegram credentials not set. Skipping Telegram send.")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

FOREX_NEWS_SOURCES = [
    ('Reuters Forex', 'https://www.reuters.com/markets/currencies/'),
    ('Bloomberg Markets', 'https://www.bloomberg.com/markets'),
    ('Forex Factory', 'https://www.forexfactory.com/news'),
    ('DailyFX', 'https://www.dailyfx.com/'),
    ('Investing.com', 'https://www.investing.com/news/forex-news'),
    ('FXStreet', 'https://www.fxstreet.com/news'),
    ('ForexLive', 'https://www.forexlive.com/'),
    ('MarketWatch Forex', 'https://www.marketwatch.com/investing/currencies'),
    ('CNBC Forex Web', 'https://www.cnbc.com/forex/'),
    ('Financial Times Markets Web', 'https://www.ft.com/markets'),
    ('The Economist Finance', 'https://www.economist.com/finance-and-economics'),
    ('WSJ Markets Web', 'https://www.wsj.com/news/markets'),
    ('BBC Business', 'https://www.bbc.com/business'),
    ('Forbes Markets Web', 'https://www.forbes.com/markets/'),
    ('Business Insider Markets', 'https://markets.businessinsider.com/'),
    ('ZeroHedge', 'https://www.zerohedge.com/'),
    ('Seeking Alpha Forex', 'https://seekingalpha.com/currency'),
    ('FX Empire', 'https://www.fxempire.com/news'),
    ('MyFXBook News', 'https://www.myfxbook.com/news'),
    ('FXCM Insights', 'https://www.fxcm.com/insights/'),
    # Additional RSS feeds for enhanced news coverage
    ('CNBC Business RSS', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
    ('Financial Times Global Economy RSS', 'https://www.ft.com/rss/home/us'),
    ('WSJ Markets RSS', 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml'),
    ('MarketWatch Commodities RSS', 'https://feeds.marketwatch.com/marketwatch/marketpulse/'),
    ('Bloomberg Business RSS', 'https://feeds.bloomberg.com/bloomberg/markets/rss.xml'),
    ('Reuters Business News RSS', 'https://feeds.reuters.com/reuters/businessNews'),
    ('Forbes Finance RSS', 'https://www.forbes.com/finance/feed/'),
]

# Map simple tickers/names to yfinance symbols for forex and commodities
FOREX_SYMBOL_MAP = {
    # Major Currency Pairs
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'USDJPY=X',
    'USDCHF': 'USDCHF=X',
    'AUDUSD': 'AUDUSD=X',
    'USDCAD': 'USDCAD=X',
    'NZDUSD': 'NZDUSD=X',
    # European Crosses
    'EURGBP': 'EURGBP=X',
    'EURJPY': 'EURJPY=X',
    'EURCHF': 'EURCHF=X',
    'EURAUD': 'EURAUD=X',
    'EURNZD': 'EURNZD=X',
    'EURCAD': 'EURCAD=X',
    'EURNOK': 'EURNOK=X',
    'EURSEK': 'EURSEK=X',
    'EURTRY': 'EURTRY=X',
    'EURZAR': 'EURZAR=X',
    'EURMXN': 'EURMXN=X',
    'EURSGD': 'EURSGD=X',
    'EURHKD': 'EURHKD=X',
    'EURKRW': 'EURKRW=X',
    # British Pound Crosses
    'GBPJPY': 'GBPJPY=X',
    'GBPCHF': 'GBPCHF=X',
    'GBPAUD': 'GBPAUD=X',
    'GBPNZD': 'GBPNZD=X',
    'GBPCAD': 'GBPCAD=X',
    'GBPNOK': 'GBPNOK=X',
    'GBPSEK': 'GBPSEK=X',
    'GBPTRY': 'GBPTRY=X',
    'GBPZAR': 'GBPZAR=X',
    'GBPMXN': 'GBPMXN=X',
    'GBPSGD': 'GBPSGD=X',
    'GBPHKD': 'GBPHKD=X',
    'GBPKRW': 'GBPKRW=X',
    # Japanese Yen Crosses
    'AUDJPY': 'AUDJPY=X',
    'CADJPY': 'CADJPY=X',
    'CHFJPY': 'CHFJPY=X',
    'NZDJPY': 'NZDJPY=X',
    'NOKJPY': 'NOKJPY=X',
    'SEKJPY': 'SEKJPY=X',
    'TRYJPY': 'TRYJPY=X',
    'ZARJPY': 'ZARJPY=X',
    'MXNJPY': 'MXNJPY=X',
    'SGDJPY': 'SGDJPY=X',
    'HKDJPY': 'HKDJPY=X',
    'KRWJPY': 'KRWJPY=X',
    # US Dollar Crosses
    'USDNOK': 'USDNOK=X',
    'USDSEK': 'USDSEK=X',
    'USDTRY': 'USDTRY=X',
    'USDZAR': 'USDZAR=X',
    'USDMXN': 'USDMXN=X',
    'USDSGD': 'USDSGD=X',
    'USDHKD': 'USDHKD=X',
    'USDKRW': 'USDKRW=X',
    'USDBRL': 'USDBRL=X',
    'USDPLN': 'USDPLN=X',
    'USDCZK': 'USDCZK=X',
    'USDHUF': 'USDHUF=X',
    'USDDKK': 'USDDKK=X',
    # Australian Dollar Crosses
    'AUDCHF': 'AUDCHF=X',
    'AUDCAD': 'AUDCAD=X',
    'AUDNZD': 'AUDNZD=X',
    'AUDNOK': 'AUDNOK=X',
    'AUDSEK': 'AUDSEK=X',
    'AUDTRY': 'AUDTRY=X',
    'AUDZAR': 'AUDZAR=X',
    'AUDMXN': 'AUDMXN=X',
    'AUDSGD': 'AUDSGD=X',
    'AUDHKD': 'AUDHKD=X',
    'AUDKRW': 'AUDKRW=X',
    # New Zealand Dollar Crosses
    'NZDJPY': 'NZDJPY=X',
    'NZDCHF': 'NZDCHF=X',
    'NZDCAD': 'NZDCAD=X',
    'NZDNOK': 'NZDNOK=X',
    'NZDSEK': 'NZDSEK=X',
    'NZDTRY': 'NZDTRY=X',
    'NZDZAR': 'NZDZAR=X',
    'NZDMXN': 'NZDMXN=X',
    'NZDSGD': 'NZDSGD=X',
    'NZDHKD': 'NZDHKD=X',
    'NZDKRW': 'NZDKRW=X',
    # Canadian Dollar Crosses
    'CADCHF': 'CADCHF=X',
    'CADNOK': 'CADNOK=X',
    'CADSEK': 'CADSEK=X',
    'CADTRY': 'CADTRY=X',
    'CADZAR': 'CADZAR=X',
    'CADMXN': 'CADMXN=X',
    'CADSGD': 'CADSGD=X',
    'CADHKD': 'CADHKD=X',
    'CADKRW': 'CADKRW=X',
    # Swiss Franc Crosses
    'CHFNOK': 'CHFNOK=X',
    'CHFSEK': 'CHFSEK=X',
    'CHFTRY': 'CHFTRY=X',
    'CHFZAR': 'CHFZAR=X',
    'CHFMXN': 'CHFMXN=X',
    'CHFSGD': 'CHFSGD=X',
    'CHFHKD': 'CHFHKD=X',
    'CHFKRW': 'CHFKRW=X',
    # Commodities
    'XAUUSD': 'GC=F',  # Gold
    'XAGUSD': 'SI=F',  # Silver
    'WTI': 'CL=F',     # WTI Crude Oil
    'BRENT': 'BZ=F',   # Brent Crude Oil
    'COFFEE': 'KC=F',  # Coffee
    'COCOA': 'CC=F',   # Cocoa
    'SUGAR': 'SB=F',   # Sugar
    'COTTON': 'CT=F',  # Cotton
    'COPPER': 'HG=F',  # Copper
    'PLATINUM': 'PL=F', # Platinum
    'PALLADIUM': 'PA=F', # Palladium
    'NATURALGAS': 'NG=F', # Natural Gas
    'CORN': 'ZC=F',    # Corn
    'WHEAT': 'ZW=F',   # Wheat
    'SOYBEANS': 'ZS=F', # Soybeans
    'LIVECATTLE': 'LE=F', # Live Cattle
    'LEANHOGS': 'HE=F', # Lean Hogs
    'LUMBER': 'LBS=F', # Lumber
    'ORANGEJUICE': 'OJ=F', # Orange Juice
    'MILK': 'DC=F',    # Milk
    'FEEDCATTLE': 'GF=F', # Feeder Cattle
    # Indices
    'SPX': 'SPY',      # S&P 500 (using ETF)
    'NDX': 'QQQ',      # Nasdaq 100
    'DJI': 'DIA',      # Dow Jones
    'FTSE': 'EWU',     # FTSE 100
    'DAX': 'EWG',      # DAX
    'NIKKEI': 'EWJ',   # Nikkei 225
    'HSI': 'EWH',      # Hang Seng
    'CAC': 'EWQ',      # CAC 40
    # Bonds/ETFs
    'TLT': 'TLT',      # US Treasuries 20+ Year
    'IEF': 'IEF',      # US Treasuries 7-10 Year
    'SHY': 'SHY',      # US Treasuries 1-3 Year
}

# Aliases for additional search terms
FOREX_ALIASES = {
    'EURO': 'EURUSD',
    'POUND': 'GBPUSD',
    'STERLING': 'GBPUSD',
    'YEN': 'USDJPY',
    'SWISS': 'USDCHF',
    'FRANC': 'USDCHF',
    'AUSTRALIAN': 'AUDUSD',
    'KIWI': 'NZDUSD',
    'LOONIE': 'USDCAD',
    'CABLE': 'GBPUSD',
    'EUR/USD': 'EURUSD',
    'GBP/USD': 'GBPUSD',
    'USD/JPY': 'USDJPY',
    'USD/CHF': 'USDCHF',
    'AUD/USD': 'AUDUSD',
    'USD/CAD': 'USDCAD',
    'NZD/USD': 'NZDUSD',
    'GOLD': 'XAUUSD',
    'SILVER': 'XAGUSD',
    'OIL': 'WTI',
    'CRUDE': 'WTI',
    'BRENT OIL': 'BRENT',
    'COFFEE': 'COFFEE',
    'COCOA': 'COCOA',
    'SUGAR': 'SUGAR',
    'COTTON': 'COTTON',
    'COPPER': 'COPPER',
    'PLATINUM': 'PLATINUM',
    'PALLADIUM': 'PALLADIUM',
    'NATURAL GAS': 'NATURALGAS',
    'GAS': 'NATURALGAS',
    'CORN': 'CORN',
    'WHEAT': 'WHEAT',
    'SOYBEANS': 'SOYBEANS',
    'SOY': 'SOYBEANS',
    'LIVE CATTLE': 'LIVECATTLE',
    'CATTLE': 'LIVECATTLE',
    'LEAN HOGS': 'LEANHOGS',
    'HOGS': 'LEANHOGS',
    'LUMBER': 'LUMBER',
    'ORANGE JUICE': 'ORANGEJUICE',
    'MILK': 'MILK',
    'FEEDER CATTLE': 'FEEDCATTLE',
    'EUR/GBP': 'EURGBP',
    'EUR/JPY': 'EURJPY',
    'GBP/JPY': 'GBPJPY',
    'AUD/JPY': 'AUDJPY',
    'CAD/JPY': 'CADJPY',
    'CHF/JPY': 'CHFJPY',
    'NZD/JPY': 'NZDJPY',
    'USD/NOK': 'USDNOK',
    'USD/SEK': 'USDSEK',
    'USD/TRY': 'USDTRY',
    'USD/ZAR': 'USDZAR',
    'USD/MXN': 'USDMXN',
    'USD/BRL': 'USDBRL',
    'USD/PLN': 'USDPLN',
    'EUR/NOK': 'EURNOK',
    'EUR/SEK': 'EURSEK',
    'GBP/NOK': 'GBPNOK',
    'GBP/SEK': 'GBPSEK',
    'SP500': 'SPX',
    'NASDAQ': 'NDX',
    'DOW': 'DJI',
    'FTSE100': 'FTSE',
    'DAX30': 'DAX',
    'NIKKEI225': 'NIKKEI',
    'HANGSENG': 'HSI',
    'CAC40': 'CAC',
    'TREASURIES': 'TLT',
    'BONDS': 'TLT',
}

# Default symbols to always analyze (news optional)
DEFAULT_SYMBOLS = [
    ('EURUSD', 'EURUSD=X', 'forex'),
    ('GBPUSD', 'GBPUSD=X', 'forex'),
    ('USDJPY', 'USDJPY=X', 'forex'),
    ('USDCHF', 'USDCHF=X', 'forex'),
    ('AUDUSD', 'AUDUSD=X', 'forex'),
    ('USDCAD', 'USDCAD=X', 'forex'),
    ('NZDUSD', 'NZDUSD=X', 'forex'),
    ('XAUUSD', 'GC=F', 'forex'),  # Gold
    ('XAGUSD', 'SI=F', 'forex'),  # Silver
    ('WTI', 'CL=F', 'forex'),     # Oil
    ('SPX', 'SPY', 'stock'),      # S&P 500
    ('NDX', 'QQQ', 'stock'),      # Nasdaq
]

# Risk settings (optimized based on industry best practices)
MIN_STOP_PCT = 0.0008  # 0.08% (0.0008 as decimal) - More realistic stops to avoid premature exits
EXPECTED_RETURN_PER_SENTIMENT = 0.012  # 1.2% per sentiment point (0.012 as decimal)
NEWS_COUNT_BONUS = 0.003  # 0.3% per article (appropriate news impact)
MAX_NEWS_BONUS = 0.015  # Max 1.5% bonus from news

# Leverage caps - Optimized for safety and regulatory compliance
MAX_LEVERAGE_FOREX = 50  # Reduced to 50:1 for better risk management (EU standard)
MAX_LEVERAGE_STOCK = 5    # Increased to 5:1 for stocks (more reasonable)

# Low money mode flag - Set to True for accounts with small capital (< $500 equivalent)
LOW_MONEY_MODE = True

if LOW_MONEY_MODE:
    EXPECTED_RETURN_PER_SENTIMENT = 0.015  # 1.5% (0.015 as decimal) - Better ROI for small accounts
    NEWS_COUNT_BONUS = 0.004  # 0.4% - Enhanced news impact
    MAX_NEWS_BONUS = 0.02  # 2% - Higher max bonus
    MIN_STOP_PCT = 0.0006  # 0.06% (0.0006 as decimal) - Tighter but realistic stops

# Daily risk limit (optimized for consistent profitability)
DAILY_RISK_LIMIT = 0.02  # 2% max loss per day (industry standard)
DAILY_RISK_FILE = 'daily_risk.json'

# Trade logging file
TRADE_LOG_FILE = 'trade_log.json'

# ML Configuration
ML_ENABLED = True  # Enable machine learning predictions
NEWS_IMPACT_ENABLED = True  # Enable news impact analysis for trade direction
ML_MIN_CONFIDENCE = 0.60  # Minimum confidence for ML predictions
ML_MIN_PROBABILITY = 0.55  # Minimum win probability from ML
ML_RETRAIN_INTERVAL = 24  # Retrain model every 24 hours

# LLM Configuration for News Analysis (Groq - MANDATORY)
# LLM analysis is now mandatory and always enabled
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # Only 'groq' is supported
LLM_MODEL = os.getenv('LLM_MODEL', None)  # Auto-selects llama-3.3-70b-versatile if None

# Groq Rate Limiting (Free Tier: 1k requests/day, 500k tokens/day)
# Set GROQ_ENFORCE_LIMITS=false to disable limits (may exceed free tier)
GROQ_MAX_REQUESTS_PER_DAY = int(os.getenv('GROQ_MAX_REQUESTS_PER_DAY', 1000))
GROQ_MAX_TOKENS_PER_DAY = int(os.getenv('GROQ_MAX_TOKENS_PER_DAY', 500000))
GROQ_ENFORCE_LIMITS = os.getenv('GROQ_ENFORCE_LIMITS', 'true').lower() == 'true'


# Backtesting configuration
BACKTEST_ENABLED = True  # Enable automatic backtesting for parameter validation
BACKTEST_PERIOD_DAYS = 90  # Increased to 90 days for more accurate historical validation
BACKTEST_ADJUST_THRESHOLD = 0.55  # More realistic win rate threshold (55%) for adjustments
BACKTEST_TEST_MODE = False  # Use fake data for testing (set to False for real backtesting)

# Indicator weights (optimized based on backtesting and industry research)
RSI_WEIGHT = 1.3  # RSI is highly reliable
MACD_WEIGHT = 1.25  # MACD excellent for trend confirmation
BB_WEIGHT = 1.15  # BB good for volatility
TREND_WEIGHT = 1.4  # Trend following is critical
ADVANCED_CANDLE_WEIGHT = 1.2  # Candlestick patterns are valuable
OBV_WEIGHT = 1.2  # Volume confirmation important
FVG_WEIGHT = 1.15  # Fair value gaps useful
VWAP_WEIGHT = 1.5  # VWAP excellent for institutional levels
STOCH_WEIGHT = 1.35  # Stochastic reliable for oversold/overbought
CCI_WEIGHT = 1.3  # CCI good for momentum
HURST_WEIGHT = 1.25  # Hurst useful for trend persistence
ADX_WEIGHT = 1.45  # ADX excellent for trend strength
WILLIAMS_R_WEIGHT = 1.3  # Williams %R good momentum indicator
SAR_WEIGHT = 1.35  # Parabolic SAR excellent for stops

# Market sessions (UTC, Monday-Friday)
MARKET_SESSIONS = [
    ('Sydney', 0, 8),
    ('Tokyo', 0, 8),
    ('London', 8, 16),
    ('New York', 13.5, 20),  # 13:30 to 20:00
]

# Debug symbols for logging
DEBUG_SYMBOLS = ['EURUSD', 'GBPUSD', 'GC=F']

def get_current_market_session():
    """Return the current market session name or 'Off-hours' if none."""
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Saturday or Sunday
        return 'Weekend (no trading)'
    hour = now.hour + now.minute / 60.0
    for name, start, end in MARKET_SESSIONS:
        if start <= hour < end:
            return name
    return 'Off-hours'

def fetch_rss_items(url):
    '''Fetch RSS/Atom feed and return list of {'title','description'} items (best-effort).'''
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'news-trader/1.0'})
        text = resp.text
        items = []
        # crude parsing: find <item> blocks
        for block in re.findall(r'<item>(.*?)</item>', text, flags=re.S | re.I):
            title_m = re.search(r'<title>(.*?)</title>', block, flags=re.S | re.I)
            desc_m = re.search(r'<description>(.*?)</description>', block, flags=re.S | re.I)
            title = re.sub('<.*?>', '', title_m.group(1)).strip() if title_m else ''
            desc = re.sub('<.*?>', '', desc_m.group(1)).strip() if desc_m else ''
            if title or desc:
                items.append({'title': title, 'description': desc})
        return items
    except Exception as e:
        print(f'Failed to fetch RSS {url}: {e}')
        return []

# def fetch_tweets():
#     '''Fetch recent tweets from influential forex market people.'''
#     users = ['federalreserve', 'ecb', 'bankofengland', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve', 'federalreserve']  # Placeholder for actual handles
#     tweets = []
#     cutoff = datetime.now() - timedelta(hours=24) # Last 24 hours for fast trading
#     for user in users:
#         try:
#             query = f'from:{user} since:{cutoff.date()}'
#             for tweet in sntwitter.TwitterSearchScraper(query).get_items():
#                 if tweet.date.replace(tzinfo=None) < cutoff:
#                 break
#                 tweets.append({'title': tweet.rawContent, 'description': '', 'source': f'Twitter-{user}'})
#         except Exception as e:
#             print(f'Failed to fetch tweets from {user}: {e}')
#     return tweets

def get_news():
    '''Fetch news from NewsAPI, RSS, and influential tweets.'''
    results = []
    cutoff = datetime.now() - timedelta(hours=48)  # Last 48 hours for more data
    try:
        # Fetch forex/commodities/indices related from NewsAPI (use q to bias forex and commodities)
        resp_forex = newsapi.get_everything(q='forex OR currency OR EURUSD OR GBPUSD OR USDJPY OR central bank OR fed OR ecb OR boj OR employment OR inflation OR gdp OR interest rate OR fomc OR monetary policy OR commodities OR gold OR silver OR oil OR coffee OR cocoa OR sugar OR copper OR wheat OR corn OR soybeans OR stock market OR sp500 OR nasdaq OR dow jones OR bonds OR treasuries', language='en', sort_by='publishedAt', page_size=100)
        resp_general = newsapi.get_top_headlines(category='business', language='en', country='us', page_size=100)
        for a in resp_forex.get('articles', []) + resp_general.get('articles', []):
            pub_date = a.get('publishedAt')
            if pub_date:
                try:
                    pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    if pub_dt < cutoff:
                        continue
                except:
                    pass  # Include if can't parse
            results.append({'title': a.get('title', ''), 'description': a.get('description', ''), 'source': a.get('source', {}).get('name')})
    except Exception as e:
        print(f'NewsAPI fetch error: {e}')

    # Fetch RSS-based forex sources (assume recent)
    for name, url in FOREX_NEWS_SOURCES:
        try:
            items = fetch_rss_items(url)
            for it in items:
                results.append({'title': it.get('title', ''), 'description': it.get('description', ''), 'source': name})
        except Exception as e:
            print(f'RSS fetch error for {name}: {e}')
            continue

    # Fetch influential tweets (commented out due to snscrape issues in Python 3.12)
    # tweets = fetch_tweets()
    # results.extend(tweets)

    return results

def normalize_text(s: str) -> str:
    return (s or '').upper()

# --- REPLACE your extract_crypto_and_tickers() with this version ---
def extract_forex_and_tickers(text: str):
    """
    Return list of dicts: {'symbol','yf','kind'} where kind in {'forex','stock'}.
    Rules:
      - Accept $TICKER only if it’s a known forex symbol or passes a quick market-data check.
      - Accept plain forex names/symbols from FOREX_SYMBOL_MAP and FOREX_ALIASES.
      - Do NOT infer generic ALL-CAPS words as tickers.
    """
    text_u = normalize_text(text)
    found = {}
 
    # 1) $TICKER patterns (common in forex/news posts)
    for m in re.findall(r'\$([A-Z]{3,7})\b', text_u):
        key = m.upper()
        if key in FOREX_SYMBOL_MAP:
            found[key] = (FOREX_SYMBOL_MAP[key], 'forex')
        elif key in FOREX_ALIASES:
            canonical = FOREX_ALIASES[key]
            found[canonical] = (FOREX_SYMBOL_MAP[canonical], 'forex')
        else:
            # tentatively a stock-like ticker; validate before keeping
            yf_sym = key
            if _symbol_has_prices(yf_sym):
                found[key] = (yf_sym, 'stock')

    # 2) Plain forex tickers and names (EURUSD, GBPUSD, etc.)
    for name in FOREX_SYMBOL_MAP:
        if re.search(r'\b' + re.escape(name) + r'\b', text_u):
            found[name] = (FOREX_SYMBOL_MAP[name], 'forex')
    for alias in FOREX_ALIASES:
        if re.search(r'\b' + re.escape(alias) + r'\b', text_u):
            canonical = FOREX_ALIASES[alias]
            found[canonical] = (FOREX_SYMBOL_MAP[canonical], 'forex')

    return [{'symbol': k, 'yf': v[0], 'kind': v[1]} for k, v in found.items()]

def analyze_sentiment_with_llm(articles, symbol=''):
    '''
    Sentiment analysis using LLM only (no TextBlob fallback)
    
    Args:
        articles: List of article dicts with 'title', 'description', 'source'
        symbol: Trading symbol for context-aware analysis
    
    Returns:
        Tuple of (sentiment_score, llm_confidence, llm_analysis)
    '''
    # LLM is now mandatory - use it directly
    try:
        sentiment, llm_confidence, llm_analysis = enhance_sentiment_with_llm(
            articles, symbol, basic_sentiment=0.0  # No TextBlob, pass 0
        )
        return sentiment, llm_confidence, llm_analysis
    except Exception as e:
        print(f"LLM sentiment analysis error: {e}")
        # No fallback - return neutral
        return 0.0, 0.0, {}

@lru_cache(maxsize=100)
def _get_yfinance_data(yf_symbol, kind='forex'):
    """Get data from yfinance."""
    try:
        ticker = yf.Ticker(yf_symbol)
        # Use 1h timeframe for trading every 1h
        interval = '1h'
        hist_hourly = ticker.history(period='3d', interval=interval)
        # Daily data for pivots
        hist_daily = ticker.history(period='30d', interval='1d')
        if hist_hourly.empty or len(hist_hourly) < 26 or hist_daily.empty or len(hist_daily) < 2:
            print(f'yfinance insufficient data for {yf_symbol}')
            return None

        # Skip delisted or low-volume symbols (stricter for stocks)
        avg_volume = hist_hourly['Volume'].tail(10).mean()
        if kind == 'stock' and avg_volume < 10000:  # Higher threshold for stocks
            print(f'yfinance low volume for {yf_symbol}')
            return None
        # For forex, skip volume check as it may be low but data is valid

        close = hist_hourly['Close'].dropna()
        high = hist_hourly['High'].dropna()
        low = hist_hourly['Low'].dropna()
        volume = hist_hourly['Volume'].dropna()
        current_price = float(close.iloc[-1])

        # Volatility and ATR
        hourly_returns = close.pct_change().dropna()
        vol_hourly = hourly_returns.std()
        tr = []
        for i in range(1, len(high)):
            tr.append(max(high.iloc[i] - low.iloc[i], abs(high.iloc[i] - close.iloc[i-1]), abs(low.iloc[i] - close.iloc[i-1])))
        atr = sum(tr[-14:]) / min(14, len(tr)) if tr else 0
        atr_pct = atr / current_price

        # Pivots from previous day
        prev_day = hist_daily.iloc[-2]  # Yesterday
        pivot = (prev_day['High'] + prev_day['Low'] + prev_day['Close']) / 3
        r1 = 2 * pivot - prev_day['Low']
        s1 = 2 * pivot - prev_day['High']
        r2 = pivot + (prev_day['High'] - prev_day['Low'])
        s2 = pivot - (prev_day['High'] - prev_day['Low'])

        # Support/Resistance: recent swing highs/lows (simple: max/min of last 20 hours)
        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()

        # Psychological levels: round to nearest 0.01 for forex/commodities (e.g., 1.05 for EURUSD)
        psych_level = round(current_price * 100) / 100

        # RSI
        if len(close) >= 14:
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_signal = 1 if rsi.iloc[-1] < 30 else -1 if rsi.iloc[-1] > 70 else 0
        else:
            rsi_signal = 0

        # MACD
        if len(close) >= 26:
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9).mean()
            macd_signal = 1 if macd_line.iloc[-1] > signal_line.iloc[-1] else -1
        else:
            macd_signal = 0

        # Bollinger Bands
        if len(close) >= 20:
            sma20 = close.rolling(window=20).mean()
            std20 = close.rolling(window=20).std()
            upper_bb = sma20 + 2 * std20
            lower_bb = sma20 - 2 * std20
            bb_signal = 1 if close.iloc[-1] < lower_bb.iloc[-1] else -1 if close.iloc[-1] > upper_bb.iloc[-1] else 0
        else:
            bb_signal = 0

        # Trend (EMA50 vs EMA200)
        if len(close) >= 200:
            ema50 = close.ewm(span=50).mean()
            ema200 = close.ewm(span=200).mean()
            trend_signal = 1 if ema50.iloc[-1] > ema200.iloc[-1] else -1
        else:
            trend_signal = 0

        # Advanced candle patterns
        advanced_candle_signal = 0
        if len(close) >= 2:
            prev_high = high.iloc[-2]
            prev_low = low.iloc[-2]
            prev_open = hist_hourly['Open'].iloc[-2]
            prev_close = close.iloc[-2]
            curr_high = high.iloc[-1]
            curr_low = low.iloc[-1]
            curr_open = hist_hourly['Open'].iloc[-1]
            curr_close = close.iloc[-1]
            # Bullish engulfing
            if prev_close < prev_open and curr_close > curr_open and curr_close >= prev_open and curr_open <= prev_close:
                advanced_candle_signal = 1
            # Bearish engulfing
            elif prev_close > prev_open and curr_close < curr_open and curr_close <= prev_open and curr_open >= prev_close:
                advanced_candle_signal = -1
            # Hammer (simplified)
            elif (min(curr_open, curr_close) - curr_low) > 2 * abs(curr_close - curr_open) and (curr_high - max(curr_open, curr_close)) < abs(curr_close - curr_open):
                advanced_candle_signal = 1  # Bullish hammer

        # Better FVG detection: look for imbalances in last 10 candles
        fvg_signal = 0
        if len(close) >= 10:
            for i in range(-10, -1):
                if low.iloc[i] > high.iloc[i+2]:
                    fvg_signal = 1  # Bullish FVG
                    break
                elif high.iloc[i] < low.iloc[i+2]:
                    fvg_signal = -1  # Bearish FVG
                    break

        # Volume: OBV-like
        if len(volume) >= 2:
            obv = [0]
            for i in range(1, len(close)):
                if close.iloc[i] > close.iloc[i-1]:
                    obv.append(obv[-1] + volume.iloc[i])
                elif close.iloc[i] < close.iloc[i-1]:
                    obv.append(obv[-1] - volume.iloc[i])
                else:
                    obv.append(obv[-1])
            obv_signal = 1 if obv[-1] > obv[-2] else -1
        else:
            obv_signal = 0

        # VWAP
        if len(close) >= 2 and volume.sum() > 0:
            vwap = (close * volume).cumsum() / volume.cumsum()
            vwap_signal = 1 if close.iloc[-1] > vwap.iloc[-1] else -1
        else:
            vwap_signal = 0

        # Stochastic Oscillator
        if len(close) >= 14:
            lowest_low = low.rolling(window=14).min()
            highest_high = high.rolling(window=14).max()
            stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
            stoch_d = stoch_k.rolling(window=3).mean()
            stoch_signal = 1 if stoch_k.iloc[-1] < 20 else -1 if stoch_k.iloc[-1] > 80 else 0
        else:
            stoch_signal = 0

        # CCI (Commodity Channel Index)
        if len(close) >= 20:
            typical_price = (high + low + close) / 3
            sma_tp = typical_price.rolling(window=20).mean()
            mean_dev = typical_price.rolling(window=20).apply(lambda x: (x - x.mean()).abs().mean())
            cci = (typical_price - sma_tp) / (0.015 * mean_dev)
            cci_signal = 1 if cci.iloc[-1] < -100 else -1 if cci.iloc[-1] > 100 else 0
        else:
            cci_signal = 0
        
        # Hurst Exponent
        if len(close) >= 40:
            hurst = calculate_hurst_exponent(close, max_lag=20)
            hurst_signal = 1 if hurst > 0.6 else -1 if hurst < 0.4 else 0
        else:
            hurst_signal = 0
        
        # ADX (Average Directional Index)
        if len(close) >= 30:
            adx_value = calculate_adx(high, low, close, period=14)
            adx_signal = 1 if adx_value > 25 else -1 if adx_value < 20 else 0  # Strong trend vs weak/range
        else:
            adx_signal = 0
        
        # Williams %R
        if len(close) >= 14:
            williams_r = calculate_williams_r(high, low, close, period=14)
            williams_r_signal = 1 if williams_r < -80 else -1 if williams_r > -20 else 0
        else:
            williams_r_signal = 0
        
        # Parabolic SAR
        if len(close) >= 2:
            sar = calculate_parabolic_sar(high, low, close)
            sar_signal = 1 if close.iloc[-1] > sar else -1  # Above SAR = bullish, below = bearish
        else:
            sar_signal = 0

        return {
            'price': current_price,
            'volatility_hourly': float(vol_hourly),
            'atr_pct': float(atr_pct),
            'pivot': float(pivot),
            'r1': float(r1), 'r2': float(r2),
            's1': float(s1), 's2': float(s2),
            'support': float(recent_low),
            'resistance': float(recent_high),
            'psych_level': float(psych_level),
            'rsi_signal': rsi_signal,
            'macd_signal': macd_signal,
            'bb_signal': bb_signal,
            'trend_signal': trend_signal,
            'advanced_candle_signal': advanced_candle_signal,
            'obv_signal': obv_signal,
            'fvg_signal': fvg_signal,
            'vwap_signal': vwap_signal,
            'stoch_signal': stoch_signal,
            'cci_signal': cci_signal,
            'hurst_signal': hurst_signal,
            'adx_signal': adx_signal,
            'williams_r_signal': williams_r_signal,
            'sar_signal': sar_signal
        }
    except Exception as e:
        # Suppress yfinance errors for cleaner output
        print(f'yfinance fetch error for {yf_symbol}: {e}')
        return None

@lru_cache(maxsize=100)
def _get_alpha_vantage_data(yf_symbol):
    """Get forex data from Alpha Vantage."""
    if not ALPHA_VANTAGE_API_KEY:
        return None
    try:
        fx = ForeignExchange(key=ALPHA_VANTAGE_API_KEY)
        # Assume yf_symbol like 'EURUSD=X', extract 'EUR' and 'USD'
        from_currency = yf_symbol[:3]
        to_currency = yf_symbol[3:6]
        data, _ = fx.get_currency_exchange_rate(from_currency=from_currency, to_currency=to_currency)
        current_price = float(data['5. Exchange Rate'])
        # Alpha Vantage doesn't provide historical data easily, so basic price only
        # For indicators, we'd need intraday, but free tier limits
        # Return minimal data
        return {
            'price': current_price,
            'volatility_hourly': 0.01,  # Placeholder
            'atr_pct': 0.005,  # Placeholder
            'pivot': current_price,  # Placeholder
            'r1': current_price * 1.01, 'r2': current_price * 1.02,
            's1': current_price * 0.99, 's2': current_price * 0.98,
            'support': current_price * 0.98,
            'resistance': current_price * 1.02,
            'psych_level': round(current_price),
            'rsi_signal': 0,
            'macd_signal': 0,
            'bb_signal': 0,
            'trend_signal': 0,
            'advanced_candle_signal': 0,
            'obv_signal': 0,
            'fvg_signal': 0,
            'vwap_signal': 0,
            'stoch_signal': 0,
            'cci_signal': 0,
            'hurst_signal': 0,
            'adx_signal': 0,
            'williams_r_signal': 0,
            'sar_signal': 0
        }
    except Exception as e:
        print(f'Alpha Vantage fetch error for {yf_symbol}: {e}')
        return None
@lru_cache(maxsize=100)
def _get_iex_data(yf_symbol):
    """Get stock data from IEX Cloud."""
    if not IEX_API_TOKEN:
        return None
    try:
        stock = Stock(yf_symbol.replace('=X', ''), token=IEX_API_TOKEN)
        quote = stock.get_quote()
        current_price = quote['latestPrice']
        # IEX provides quote, but for historical, need chart
        # Placeholder for now
        return {
            'price': current_price,
            'volatility_hourly': 0.01,
            'atr_pct': 0.005,
            'pivot': current_price,
            'r1': current_price * 1.01, 'r2': current_price * 1.02,
            's1': current_price * 0.99, 's2': current_price * 0.98,
            'support': current_price * 0.98,
            'resistance': current_price * 1.02,
            'psych_level': round(current_price),
            'rsi_signal': 0,
            'macd_signal': 0,
            'bb_signal': 0,
            'trend_signal': 0,
            'advanced_candle_signal': 0,
            'obv_signal': 0,
            'fvg_signal': 0,
            'vwap_signal': 0,
            'stoch_signal': 0,
            'cci_signal': 0,
            'hurst_signal': 0,
            'adx_signal': 0,
            'williams_r_signal': 0,
            'sar_signal': 0
        }
    except Exception as e:
        print(f'IEX Cloud fetch error for {yf_symbol}: {e}')
        return None


@lru_cache(maxsize=100)
def _get_polygon_data(yf_symbol):
    """Get data from Polygon with full indicators."""
    if not POLYGON_API_KEY or not _polygon_client:
        return None
    try:
        symbol = yf_symbol.replace('=X', '')
        # For forex, Polygon uses 'C:EURUSD' format
        if len(symbol) == 6 and symbol.isalpha():
            symbol = f'C:{symbol[:3]}{symbol[3:]}'
        # Fetch 1h aggregates for last 3 days
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        aggs = _polygon_client.get_aggs(symbol, 1, 'hour', start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        if not aggs or len(aggs) < 26:
            return None
        # Convert to DataFrame-like
        import pandas as pd
        df = pd.DataFrame([{'Close': a.close, 'High': a.high, 'Low': a.low, 'Open': a.open, 'Volume': a.volume} for a in aggs])
        if df.empty or len(df) < 26:
            print(f'Polygon insufficient data for {yf_symbol}')
            return None
        close = df['Close'].dropna()
        high = df['High'].dropna()
        low = df['Low'].dropna()
        volume = df['Volume'].dropna()
        current_price = float(close.iloc[-1])

        # Compute indicators like yfinance
        hourly_returns = close.pct_change().dropna()
        vol_hourly = hourly_returns.std()
        tr = []
        for i in range(1, len(high)):
            tr.append(max(high.iloc[i] - low.iloc[i], abs(high.iloc[i] - close.iloc[i-1]), abs(low.iloc[i] - close.iloc[i-1])))
        atr = sum(tr[-14:]) / min(14, len(tr)) if tr else 0
        atr_pct = atr / current_price

        # Pivots
        prev_day = df.iloc[-24:]  # Approximate last day
        if len(prev_day) > 0:
            pivot = (prev_day['High'].max() + prev_day['Low'].min() + prev_day['Close'].iloc[-1]) / 3
            r1 = 2 * pivot - prev_day['Low'].min()
            s1 = 2 * pivot - prev_day['High'].max()
            r2 = pivot + (prev_day['High'].max() - prev_day['Low'].min())
            s2 = pivot - (prev_day['High'].max() - prev_day['Low'].min())
        else:
            pivot = r1 = r2 = s1 = s2 = current_price

        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()

        psych_level = round(current_price * 100) / 100

        candle_signal = 0
        if len(close) >= 3:
            last3 = close.tail(3).values
            if last3[2] > last3[1] > last3[0]:
                candle_signal = 1
            elif last3[2] < last3[1] < last3[0]:
                candle_signal = -1

        # Ichimoku (simplified)
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        ichimoku_signal = 0
        if len(tenkan) > 0 and len(kijun) > 0 and len(senkou_a) > 0 and len(senkou_b) > 0:
            if (current_price > senkou_a.iloc[-1] and current_price > senkou_b.iloc[-1] and 
                tenkan.iloc[-1] > kijun.iloc[-1] and senkou_a.iloc[-1] > senkou_b.iloc[-1]):
                ichimoku_signal = 1
            elif (current_price < senkou_a.iloc[-1] and current_price < senkou_b.iloc[-1] and 
                  tenkan.iloc[-1] < kijun.iloc[-1] and senkou_a.iloc[-1] < senkou_b.iloc[-1]):
                ichimoku_signal = -1

        volume_avg = volume.tail(20).mean()
        recent_volume = volume.iloc[-1]
        volume_signal = 0
        if recent_volume > volume_avg * 1.2:
            if close.iloc[-1] > close.iloc[-2]:
                volume_signal = 1
            elif close.iloc[-1] < close.iloc[-2]:
                volume_signal = -1

        fvg_signal = 0
        if len(close) >= 4:
            if low.iloc[-1] > high.iloc[-3]:
                fvg_signal = 1
            elif high.iloc[-1] < low.iloc[-3]:
                fvg_signal = -1

        # VWAP
        if len(close) >= 2 and volume.sum() > 0:
            vwap = (close * volume).cumsum() / volume.cumsum()
            vwap_signal = 1 if close.iloc[-1] > vwap.iloc[-1] else -1
        else:
            vwap_signal = 0

        # Stochastic Oscillator
        if len(close) >= 14:
            lowest_low = low.rolling(window=14).min()
            highest_high = high.rolling(window=14).max()
            stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
            stoch_d = stoch_k.rolling(window=3).mean()
            stoch_signal = 1 if stoch_k.iloc[-1] < 20 else -1 if stoch_k.iloc[-1] > 80 else 0
        else:
            stoch_signal = 0

        # CCI
        if len(close) >= 20:
            typical_price = (high + low + close) / 3
            sma_tp = typical_price.rolling(window=20).mean()
            mean_dev = typical_price.rolling(window=20).apply(lambda x: (x - x.mean()).abs().mean())
            cci = (typical_price - sma_tp) / (0.015 * mean_dev)
            cci_signal = 1 if cci.iloc[-1] < -100 else -1 if cci.iloc[-1] > 100 else 0
        else:
            cci_signal = 0

        return {
            'price': current_price,
            'volatility_hourly': float(vol_hourly),
            'atr_pct': float(atr_pct),
            'pivot': float(pivot),
            'r1': float(r1), 'r2': float(r2),
            's1': float(s1), 's2': float(s2),
            'support': float(recent_low),
            'resistance': float(recent_high),
            'psych_level': float(psych_level),
            'rsi_signal': 0,  # Placeholder for polygon
            'macd_signal': 0,
            'bb_signal': 0,
            'trend_signal': 0,
            'advanced_candle_signal': 0,
            'obv_signal': 0,
            'fvg_signal': fvg_signal,
            'vwap_signal': vwap_signal,
            'stoch_signal': stoch_signal,
            'cci_signal': cci_signal
        }
    except Exception as e:
        print(f'Polygon fetch error for {yf_symbol}: {e}')
        return None


@lru_cache(maxsize=100)
def _get_twelvedata_data(yf_symbol):
    """Get data from Twelve Data with full indicators."""
    if not TWELVE_DATA_API_KEY or not _td_client:
        return None
    try:
        sym = yf_symbol.replace('=X', '')
        if len(sym) == 6 and sym.isalpha():
            print(f'Twelve Data does not support forex for {yf_symbol}')
            return None
        series = _td_client.time_series(symbol=sym, interval='1h', outputsize=100)
        data = series.as_json()
        if isinstance(data, tuple):
            data = data[0]  # Assume first element is the data
        values = data.get('values', [])
        if not values or len(values) < 26:
            print(f'Twelve Data insufficient data for {yf_symbol}')
            return None
        # Convert to DataFrame
        import pandas as pd
        df = pd.DataFrame(values)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        current_price = float(close.iloc[0])  # Most recent first

        # Compute indicators
        hourly_returns = close.pct_change().dropna()
        vol_hourly = hourly_returns.std()
        tr = []
        for i in range(1, len(high)):
            tr.append(max(high.iloc[i] - low.iloc[i], abs(high.iloc[i] - close.iloc[i-1]), abs(low.iloc[i] - close.iloc[i-1])))
        atr = sum(tr[-14:]) / min(14, len(tr)) if tr else 0
        atr_pct = atr / current_price

        # Pivots (approximate last day ~24 hours)
        prev_day = df.iloc[24:48] if len(df) > 48 else df.tail(24)
        if len(prev_day) > 0:
            pivot = (prev_day['high'].max() + prev_day['low'].min() + prev_day['close'].iloc[-1]) / 3
            r1 = 2 * pivot - prev_day['low'].min()
            s1 = 2 * pivot - prev_day['high'].max()
            r2 = pivot + (prev_day['high'].max() - prev_day['low'].min())
            s2 = pivot - (prev_day['high'].max() - prev_day['low'].min())
        else:
            pivot = r1 = r2 = s1 = s2 = current_price

        recent_high = high.head(20).max()  # Since most recent first
        recent_low = low.head(20).min()

        psych_level = round(current_price * 100) / 100

        candle_signal = 0
        if len(close) >= 3:
            last3 = close.head(3).values  # Most recent first
            if last3[0] > last3[1] > last3[2]:  # Rising (reverse order)
                candle_signal = 1
            elif last3[0] < last3[1] < last3[2]:
                candle_signal = -1

        # Ichimoku
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(-26)  # Shift forward since most recent first
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(-26)
        ichimoku_signal = 0
        if len(tenkan) > 0 and len(kijun) > 0 and len(senkou_a) > 0 and len(senkou_b) > 0:
            if (current_price > senkou_a.iloc[0] and current_price > senkou_b.iloc[0] and 
                tenkan.iloc[0] > kijun.iloc[0] and senkou_a.iloc[0] > senkou_b.iloc[0]):
                ichimoku_signal = 1
            elif (current_price < senkou_a.iloc[0] and current_price < senkou_b.iloc[0] and 
                  tenkan.iloc[0] < kijun.iloc[0] and senkou_a.iloc[0] < senkou_b.iloc[0]):
                ichimoku_signal = -1

        volume_avg = volume.head(20).mean()
        recent_volume = volume.iloc[0]
        volume_signal = 0
        if recent_volume > volume_avg * 1.2:
            if close.iloc[0] > close.iloc[1]:
                volume_signal = 1
            elif close.iloc[0] < close.iloc[1]:
                volume_signal = -1

        fvg_signal = 0
        if len(close) >= 4:
            if low.iloc[0] > high.iloc[2]:
                fvg_signal = 1
            elif high.iloc[0] < low.iloc[2]:
                fvg_signal = -1

        # VWAP
        if len(close) >= 2 and volume.sum() > 0:
            vwap = (close * volume).cumsum() / volume.cumsum()
            vwap_signal = 1 if close.iloc[0] > vwap.iloc[0] else -1
        else:
            vwap_signal = 0

        # Stochastic Oscillator
        if len(close) >= 14:
            lowest_low = low.rolling(window=14).min()
            highest_high = high.rolling(window=14).max()
            stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
            stoch_d = stoch_k.rolling(window=3).mean()
            stoch_signal = 1 if stoch_k.iloc[0] < 20 else -1 if stoch_k.iloc[0] > 80 else 0
        else:
            stoch_signal = 0

        # CCI
        if len(close) >= 20:
            typical_price = (high + low + close) / 3
            sma_tp = typical_price.rolling(window=20).mean()
            mean_dev = typical_price.rolling(window=20).apply(lambda x: (x - x.mean()).abs().mean())
            cci = (typical_price - sma_tp) / (0.015 * mean_dev)
            cci_signal = 1 if cci.iloc[0] < -100 else -1 if cci.iloc[0] > 100 else 0
        else:
            cci_signal = 0

        return {
            'price': current_price,
            'volatility_hourly': float(vol_hourly),
            'atr_pct': float(atr_pct),
            'pivot': float(pivot),
            'r1': float(r1), 'r2': float(r2),
            's1': float(s1), 's2': float(s2),
            'support': float(recent_low),
            'resistance': float(recent_high),
            'psych_level': float(psych_level),
            'rsi_signal': 0,  # Placeholder
            'macd_signal': 0,
            'bb_signal': 0,
            'trend_signal': 0,
            'advanced_candle_signal': 0,
            'obv_signal': 0,
            'fvg_signal': fvg_signal,
            'vwap_signal': vwap_signal,
            'stoch_signal': stoch_signal,
            'cci_signal': cci_signal
        }
    except Exception as e:
        print(f'Twelve Data fetch error for {yf_symbol}: {e}')
        return None


@lru_cache(maxsize=100)
def _get_fmp_data(yf_symbol):
    """Get data from FinancialModelingPrep (minimal)."""
    if not FMP_API_KEY:
        return None
    try:
        sym = yf_symbol.replace('=X', '')
        quote = _fmp_client.get_quote(sym)
        if not quote or (isinstance(quote, list) and len(quote) == 0) or quote == 0:
            print(f'FMP no quote for {yf_symbol}')
            return None
        price = float(quote[0].get('price', 0))
        return {
            'price': price,
            'volatility_hourly': 0.01,
            'atr_pct': 0.005,
            'pivot': price,
            'r1': price * 1.01, 'r2': price * 1.02,
            's1': price * 0.99, 's2': price * 0.98,
            'support': price * 0.98,
            'resistance': price * 1.02,
            'psych_level': round(price * 100) / 100,
            'rsi_signal': 0,
            'macd_signal': 0,
            'bb_signal': 0,
            'trend_signal': 0,
            'advanced_candle_signal': 0,
            'obv_signal': 0,
            'fvg_signal': 0,
            'vwap_signal': 0,
            'stoch_signal': 0,
            'cci_signal': 0
        }
    except Exception as e:
        print(f'FMP fetch error for {yf_symbol}: {e}')
        return None


@lru_cache(maxsize=100)
def _get_quandl_data(yf_symbol):
    """Get data from Quandl (minimal)."""
    if not QUANDL_API_KEY:
        return None
    try:
        # Placeholder implementation - Quandl requires specific dataset codes
        # For demo, return basic data
        print(f'Quandl placeholder for {yf_symbol}')
        return {
            'price': 100.0,  # Placeholder
            'volatility_hourly': 0.01,
            'atr_pct': 0.005,
            'pivot': 100.0,
            'r1': 101.0, 'r2': 102.0,
            's1': 99.0, 's2': 98.0,
            'support': 98.0,
            'resistance': 102.0,
            'psych_level': 100.0,
            'rsi_signal': 0,
            'macd_signal': 0,
            'bb_signal': 0,
            'trend_signal': 0,
            'advanced_candle_signal': 0,
            'obv_signal': 0,
            'fvg_signal': 0,
            'vwap_signal': 0,
            'stoch_signal': 0,
            'cci_signal': 0
        }
    except Exception as e:
        print(f'Quandl fetch error for {yf_symbol}: {e}')
        return None


@lru_cache(maxsize=100)
def _get_fred_data(yf_symbol):
    """Get macroeconomic data from FRED as fallback (not for FX tickers, used for macro indicators)."""
    if not FRED_API_KEY or not _fred_client:
        return None
    try:
        # FRED is for macro series, not tickers; skip unless symbol maps to a FRED series
        print(f'FRED not applicable for {yf_symbol}')
        return None
    except Exception as e:
        print(f'FRED fetch error for {yf_symbol}: {e}')
        return None

def calculate_hurst_exponent(price_series, max_lag=20):
    """Calculate Hurst exponent for trend persistence."""
    if len(price_series) < max_lag * 2:
        return 0.5  # Neutral
    
    lags = range(2, min(max_lag, len(price_series)//2))
    tau = []
    
    for lag in lags:
        # Calculate rescaled range
        diff = price_series.diff().dropna()
        mean = diff.mean()
        std = diff.std()
        if std == 0:
            continue
        z_score = (diff - mean) / std
        r = z_score.rolling(window=lag).apply(lambda x: x.max() - x.min())
        s = z_score.rolling(window=lag).std()
        rs = (r / s).mean()
        tau.append(rs)
    
    if len(tau) < 2:
        return 0.5
    
    # Fit line to log-log plot
    import numpy as np
    log_lags = np.log(lags[:len(tau)])
    log_tau = np.log(tau)
    
    try:
        slope = np.polyfit(log_lags, log_tau, 1)[0]
        hurst = slope / 2
        return max(0, min(1, hurst))  # Clamp to [0,1]
    except:
        return 0.5

def calculate_adx(high, low, close, period=14):
    """Calculate Average Directional Index (ADX) for trend strength."""
    import pandas as pd
    import numpy as np
    
    if len(high) < period + 1:
        return 0
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Directional Movement
    dm_plus = high - high.shift(1)
    dm_minus = low.shift(1) - low
    
    # Only count positive movements
    dm_plus = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
    dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)
    
    # Smoothed averages
    atr = tr.rolling(window=period).mean()
    di_plus = 100 * (dm_plus.rolling(window=period).mean() / atr)
    di_minus = 100 * (dm_minus.rolling(window=period).mean() / atr)
    
    # Directional Index
    dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
    dx = dx.replace([np.inf, -np.inf], 0).fillna(0)
    
    # ADX
    adx = dx.rolling(window=period).mean()
    
    return adx.iloc[-1] if len(adx) > 0 else 0

def calculate_williams_r(high, low, close, period=14):
    """Calculate Williams %R oscillator."""
    if len(high) < period:
        return 0
    
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    
    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
    return williams_r.iloc[-1] if len(williams_r) > 0 else 0

def calculate_parabolic_sar(high, low, close, acceleration=0.02, max_acceleration=0.2):
    """Calculate Parabolic SAR."""
    if len(close) < 2:
        return close.iloc[-1] if len(close) > 0 else 0
    
    sar = [close.iloc[0]]  # Start with first close
    trend = 1  # 1 = uptrend, -1 = downtrend
    ep = high.iloc[0] if trend == 1 else low.iloc[0]  # Extreme point
    af = acceleration  # Acceleration factor
    
    for i in range(1, len(close)):
        sar_val = sar[-1] + af * (ep - sar[-1])
        
        # Check for trend change
        if trend == 1:  # Uptrend
            if low.iloc[i] <= sar_val:
                trend = -1
                sar_val = ep  # Set to previous EP
                ep = low.iloc[i]
                af = acceleration
            else:
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + acceleration, max_acceleration)
        else:  # Downtrend
            if high.iloc[i] >= sar_val:
                trend = 1
                sar_val = ep  # Set to previous EP
                ep = high.iloc[i]
                af = acceleration
            else:
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + acceleration, max_acceleration)
        
        # Ensure SAR doesn't go beyond previous bars
        if trend == 1:
            sar_val = min(sar_val, low.iloc[i-1], low.iloc[i])
        else:
            sar_val = max(sar_val, high.iloc[i-1], high.iloc[i])
            
        sar.append(sar_val)
    
    return sar[-1] if len(sar) > 0 else close.iloc[-1]

def recommend_leverage(rr, volatility, kind='forex'):
    '''Recommend leverage given RR and volatility. Returns integer leverage.'''
    # Base leverage from RR: higher RR allows higher leverage, but conservative
    base = max(1, int(math.floor(rr * 2)))  # Reduced multiplier for risk control
    # Cap by asset class
    max_lev = MAX_LEVERAGE_FOREX if kind == 'forex' else MAX_LEVERAGE_STOCK

    # Adjust for volatility (more conservative)
    if volatility is None:
        volatility = 0.5  # Assume moderate volatility
    if volatility > 0.5:  # High volatility -> reduce leverage
        max_lev = min(max_lev, max_lev * 0.7)
    if volatility > 1.0:  # Very high volatility -> significantly reduce
        max_lev = min(max_lev, max_lev * 0.4)

    # Boost leverage for high RR trades (reduced boost for risk control)
    if rr >= 3:
        base = int(base * 1.2)
    elif rr >= 2:
        base = int(base * 1.1)

    lev = min(base, max_lev)
    return max(1, lev)

def calculate_trade_plan(avg_sentiment, news_count, market_data, kind='forex', news_impact=None):
    '''Return dict with direction, expected_profit_pct, stop_pct, rr, recommended_leverage.'''
    global RSI_WEIGHT, MACD_WEIGHT, BB_WEIGHT, TREND_WEIGHT, ADVANCED_CANDLE_WEIGHT, OBV_WEIGHT, FVG_WEIGHT, VWAP_WEIGHT, STOCH_WEIGHT, CCI_WEIGHT, HURST_WEIGHT, ADX_WEIGHT, WILLIAMS_R_WEIGHT, SAR_WEIGHT
    if not market_data:
        return None
    price = market_data['price']
    pivot = market_data['pivot']
    r1 = market_data['r1']
    r2 = market_data['r2']
    s1 = market_data['s1']
    s2 = market_data['s2']
    support = market_data['support']
    resistance = market_data['resistance']
    psych_level = market_data['psych_level']
    rsi_signal = market_data['rsi_signal']
    macd_signal = market_data['macd_signal']
    bb_signal = market_data['bb_signal']
    trend_signal = market_data['trend_signal']
    advanced_candle_signal = market_data['advanced_candle_signal']
    obv_signal = market_data['obv_signal']
    fvg_signal = market_data['fvg_signal']
    vwap_signal = market_data['vwap_signal']
    stoch_signal = market_data['stoch_signal']
    cci_signal = market_data['cci_signal']
    hurst_signal = market_data.get('hurst_signal', 0)
    adx_signal = market_data.get('adx_signal', 0)
    williams_r_signal = market_data.get('williams_r_signal', 0)
    sar_signal = market_data.get('sar_signal', 0)

    # sentiment-driven expected move
    news_bonus = min(MAX_NEWS_BONUS, NEWS_COUNT_BONUS * news_count)
    expected_return = avg_sentiment * EXPECTED_RETURN_PER_SENTIMENT + news_bonus * (1 if avg_sentiment >= 0 else -1)

    # Adjust for technical levels
    # Near resistance: reduce bullish
    if price > resistance * 0.98:
        expected_return *= 0.8
    # Near support: boost bullish
    if price < support * 1.02:
        expected_return *= 1.2
    # Near pivot: neutral
    # Psychological magnet: if close to psych level, slight boost
    if abs(price - psych_level) / price < 0.01:
        expected_return *= 1.1

    # RSI confirmation: oversold for long, overbought for short
    if (avg_sentiment > 0 and rsi_signal > 0) or (avg_sentiment < 0 and rsi_signal < 0):
        expected_return *= RSI_WEIGHT
    elif (avg_sentiment > 0 and rsi_signal < 0) or (avg_sentiment < 0 and rsi_signal > 0):
        expected_return *= (2 - RSI_WEIGHT)

    # MACD confirmation
    if (avg_sentiment > 0 and macd_signal > 0) or (avg_sentiment < 0 and macd_signal < 0):
        expected_return *= MACD_WEIGHT
    elif (avg_sentiment > 0 and macd_signal < 0) or (avg_sentiment < 0 and macd_signal > 0):
        expected_return *= (2 - MACD_WEIGHT)

    # Bollinger Bands confirmation
    if (avg_sentiment > 0 and bb_signal > 0) or (avg_sentiment < 0 and bb_signal < 0):
        expected_return *= BB_WEIGHT
    elif (avg_sentiment > 0 and bb_signal < 0) or (avg_sentiment < 0 and bb_signal > 0):
        expected_return *= (2 - BB_WEIGHT)

    # Trend confirmation (strong weight)
    if (avg_sentiment > 0 and trend_signal > 0) or (avg_sentiment < 0 and trend_signal < 0):
        expected_return *= TREND_WEIGHT
    elif (avg_sentiment > 0 and trend_signal < 0) or (avg_sentiment < 0 and trend_signal > 0):
        expected_return *= (2 - TREND_WEIGHT)

    # Advanced candle confirmation
    if (avg_sentiment > 0 and advanced_candle_signal > 0) or (avg_sentiment < 0 and advanced_candle_signal < 0):
        expected_return *= ADVANCED_CANDLE_WEIGHT
    elif (avg_sentiment > 0 and advanced_candle_signal < 0) or (avg_sentiment < 0 and advanced_candle_signal > 0):
        expected_return *= (2 - ADVANCED_CANDLE_WEIGHT)

    # OBV confirmation
    if (avg_sentiment > 0 and obv_signal > 0) or (avg_sentiment < 0 and obv_signal < 0):
        expected_return *= OBV_WEIGHT
    elif (avg_sentiment > 0 and obv_signal < 0) or (avg_sentiment < 0 and obv_signal > 0):
        expected_return *= (2 - OBV_WEIGHT)

    # FVG confirmation
    if (avg_sentiment > 0 and fvg_signal > 0) or (avg_sentiment < 0 and fvg_signal < 0):
        expected_return *= FVG_WEIGHT
    elif (avg_sentiment > 0 and fvg_signal < 0) or (avg_sentiment < 0 and fvg_signal > 0):
        expected_return *= (2 - FVG_WEIGHT)

    # VWAP confirmation
    if (avg_sentiment > 0 and vwap_signal > 0) or (avg_sentiment < 0 and vwap_signal < 0):
        expected_return *= VWAP_WEIGHT
    elif (avg_sentiment > 0 and vwap_signal < 0) or (avg_sentiment < 0 and vwap_signal > 0):
        expected_return *= (2 - VWAP_WEIGHT)

    # Stochastic confirmation
    if (avg_sentiment > 0 and stoch_signal > 0) or (avg_sentiment < 0 and stoch_signal < 0):
        expected_return *= STOCH_WEIGHT
    elif (avg_sentiment > 0 and stoch_signal < 0) or (avg_sentiment < 0 and stoch_signal > 0):
        expected_return *= (2 - STOCH_WEIGHT)

    # CCI confirmation
    if (avg_sentiment > 0 and cci_signal > 0) or (avg_sentiment < 0 and cci_signal < 0):
        expected_return *= CCI_WEIGHT
    elif (avg_sentiment > 0 and cci_signal < 0) or (avg_sentiment < 0 and cci_signal > 0):
        expected_return *= (2 - CCI_WEIGHT)

    # Hurst confirmation
    if (avg_sentiment > 0 and hurst_signal > 0) or (avg_sentiment < 0 and hurst_signal < 0):
        expected_return *= HURST_WEIGHT
    elif (avg_sentiment > 0 and hurst_signal < 0) or (avg_sentiment < 0 and hurst_signal > 0):
        expected_return *= (2 - HURST_WEIGHT)

    # ADX confirmation (trend strength)
    if (avg_sentiment > 0 and adx_signal > 0) or (avg_sentiment < 0 and adx_signal < 0):
        expected_return *= ADX_WEIGHT
    elif (avg_sentiment > 0 and adx_signal < 0) or (avg_sentiment < 0 and adx_signal > 0):
        expected_return *= (2 - ADX_WEIGHT)

    # Williams %R confirmation
    if (avg_sentiment > 0 and williams_r_signal > 0) or (avg_sentiment < 0 and williams_r_signal < 0):
        expected_return *= WILLIAMS_R_WEIGHT
    elif (avg_sentiment > 0 and williams_r_signal < 0) or (avg_sentiment < 0 and williams_r_signal > 0):
        expected_return *= (2 - WILLIAMS_R_WEIGHT)

    # Parabolic SAR confirmation
    if (avg_sentiment > 0 and sar_signal > 0) or (avg_sentiment < 0 and sar_signal < 0):
        expected_return *= SAR_WEIGHT
    elif (avg_sentiment > 0 and sar_signal < 0) or (avg_sentiment < 0 and sar_signal > 0):
        expected_return *= (2 - SAR_WEIGHT)

    expected_profit_pct = abs(expected_return)

    vol = market_data.get('volatility_hourly', 0.0)
    atr_pct = market_data.get('atr_pct', 0.005)
    # Determine stop loss percent (use ATR for optimized stops, adjusted for forex)
    if kind == 'forex':
        stop_pct = max(MIN_STOP_PCT, min(atr_pct * 1.5, 0.002))  # Cap at 0.2% for better risk control
    else:
        stop_pct = max(MIN_STOP_PCT, min(atr_pct * 1.2, 0.002))  # Cap at 0.2% for commodities

    if stop_pct <= 0:
        return None

    rr = expected_profit_pct / stop_pct if stop_pct > 0 else 0.0

    # Force minimum 2:1 RR for actionable trades (balanced profit/risk)
    if rr < 2 and expected_profit_pct > 0:
        expected_profit_pct = 2 * stop_pct
        rr = 2.0

    # Multi-confirmation: count agreeing indicators
    bullish_signals = sum(1 for s in [rsi_signal, macd_signal, bb_signal, trend_signal, advanced_candle_signal, obv_signal, fvg_signal, vwap_signal, stoch_signal, cci_signal, hurst_signal, adx_signal, williams_r_signal, sar_signal] if s > 0)
    bearish_signals = sum(1 for s in [rsi_signal, macd_signal, bb_signal, trend_signal, advanced_candle_signal, obv_signal, fvg_signal, vwap_signal, stoch_signal, cci_signal, hurst_signal, adx_signal, williams_r_signal, sar_signal] if s < 0)
    total_signals = bullish_signals + bearish_signals

    # Require at least 3 agreeing signals for trade
    min_confirmations = 3

    # decide direction based on sentiment and confirmations
    direction = 'flat'

    # Check if news impact suggests a specific direction
    if news_impact and news_impact.get('suggested_direction'):
        direction = news_impact['suggested_direction']
        if direction in ['long', 'short']:
            # News-driven direction - still require minimum technical confirmation
            if (direction == 'long' and bullish_signals >= 2) or (direction == 'short' and bearish_signals >= 2):
                pass  # Keep news-driven direction
            else:
                direction = 'flat'  # Not enough technical confirmation for news direction
    else:
        # Normal technical + sentiment analysis
        if avg_sentiment > 0.05 and bullish_signals >= min_confirmations:
            direction = 'long'
        elif avg_sentiment < -0.05 and bearish_signals >= min_confirmations:
            direction = 'short'
        # Allow technical-only trades if strong signals
        elif bullish_signals >= 4:
            direction = 'long'
        elif bearish_signals >= 4:
            direction = 'short'

    lev = recommend_leverage(rr, vol, kind=kind)

    return {
        'direction': direction,
        'expected_return_pct': expected_return,
        'expected_profit_pct': expected_profit_pct,
        'stop_pct': stop_pct,
        'rr': rr,
        'recommended_leverage': lev,
        'volatility_hourly': vol,
        'atr_pct': atr_pct,
        'pivot': pivot,
        'r1': r1, 'r2': r2,
        's1': s1, 's2': s2,
        'support': support,
        'resistance': resistance,
        'psych_level': psych_level,
        'rsi_signal': rsi_signal,
        'macd_signal': macd_signal,
        'bb_signal': bb_signal,
        'trend_signal': trend_signal,
        'advanced_candle_signal': advanced_candle_signal,
        'obv_signal': obv_signal,
        'fvg_signal': fvg_signal,
    }

def get_daily_risk():
    """Get current day's cumulative risk taken."""
    today = datetime.now().date().isoformat()
    if not os.path.exists(DAILY_RISK_FILE):
        return 0.0
    with open(DAILY_RISK_FILE, 'r') as f:
        data = json.load(f)
    return data.get(today, 0.0)

def update_daily_risk(risk_amount):
    """Add risk_amount to today's cumulative risk."""
    today = datetime.now().date().isoformat()
    if not os.path.exists(DAILY_RISK_FILE):
        data = {}
    else:
        with open(DAILY_RISK_FILE, 'r') as f:
            data = json.load(f)
    data[today] = data.get(today, 0.0) + risk_amount
    with open(DAILY_RISK_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# --- ADD this helper anywhere above main() ---
@lru_cache(maxsize=2048)
def _symbol_has_prices(yf_symbol: str) -> bool:
    """Fast sanity check: does yfinance return any recent daily history?"""
    try:
        hist = yf.Ticker(yf_symbol).history(period='30d', interval='1d')
        return (not hist.empty) and (len(hist['Close'].dropna()) >= 5)
    except Exception:
        return False

def log_trades(results):
    """Log suggested trades to JSON file with indicator signals."""
    if not os.path.exists(TRADE_LOG_FILE):
        with open(TRADE_LOG_FILE, 'w') as f:
            json.dump([], f)
    
    with open(TRADE_LOG_FILE, 'r') as f:
        logs = json.load(f)
    
    for r in results:
        price = r['price']
        direction = r['direction']
        stop_pct = r['stop_pct']
        exp_return_pct = r['expected_return_pct']
        if direction == 'long':
            stop_price = price * (1 - stop_pct)
            target_price = price * (1 + exp_return_pct)
        elif direction == 'short':
            stop_price = price * (1 + stop_pct)
            target_price = price * (1 - exp_return_pct)
        else:
            continue  # Skip flat
        trade = {
            'timestamp': datetime.now().isoformat(),
            'symbol': r['symbol'],
            'direction': direction,
            'entry_price': price,
            'stop_price': stop_price,
            'target_price': target_price,
            'leverage': r['recommended_leverage'],
            'status': 'open',
            'rsi_signal': r['rsi_signal'],
            'macd_signal': r['macd_signal'],
            'bb_signal': r['bb_signal'],
            'trend_signal': r['trend_signal'],
            'advanced_candle_signal': r['advanced_candle_signal'],
            'obv_signal': r['obv_signal'],
            'fvg_signal': r['fvg_signal'],
            'vwap_signal': r['vwap_signal'],
            'stoch_signal': r['stoch_signal'],
            'cci_signal': r['cci_signal'],
            'hurst_signal': r.get('hurst_signal', 0),
            'adx_signal': r.get('adx_signal', 0),
            'williams_r_signal': r.get('williams_r_signal', 0),
            'sar_signal': r.get('sar_signal', 0)
        }
        logs.append(trade)
        # Update daily risk
        trade_risk = stop_pct * r['recommended_leverage']
        update_daily_risk(trade_risk)
    
    with open(TRADE_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def evaluate_trades():
    """Evaluate past trades and adjust indicator weights based on performance."""
    global RSI_WEIGHT, MACD_WEIGHT, BB_WEIGHT, TREND_WEIGHT, ADVANCED_CANDLE_WEIGHT, OBV_WEIGHT, FVG_WEIGHT, VWAP_WEIGHT, STOCH_WEIGHT, CCI_WEIGHT, HURST_WEIGHT, ADX_WEIGHT, WILLIAMS_R_WEIGHT, SAR_WEIGHT
    if not os.path.exists(TRADE_LOG_FILE):
        return
    
    with open(TRADE_LOG_FILE, 'r') as f:
        logs = json.load(f)
    
    indicator_wins = {'rsi': 0, 'macd': 0, 'bb': 0, 'trend': 0, 'advanced_candle': 0, 'obv': 0, 'fvg': 0, 'vwap': 0, 'stoch': 0, 'cci': 0, 'hurst': 0, 'adx': 0, 'williams_r': 0, 'sar': 0}
    indicator_losses = {'rsi': 0, 'macd': 0, 'bb': 0, 'trend': 0, 'advanced_candle': 0, 'obv': 0, 'fvg': 0, 'vwap': 0, 'stoch': 0, 'cci': 0, 'hurst': 0, 'adx': 0, 'williams_r': 0, 'sar': 0}
    total_wins = 0
    total = 0
    
    for trade in logs:
        if trade['status'] != 'open':
            continue
        # Skip trades logged in the last 1 hour to allow time for execution
        trade_time = datetime.fromisoformat(trade['timestamp'])
        if datetime.now() - trade_time < timedelta(hours=1):
            continue
        symbol = trade['symbol']
        yf_symbol = FOREX_SYMBOL_MAP.get(symbol, symbol + '=X')
        try:
            ticker = yf.Ticker(yf_symbol)
            current_price = float(ticker.history(period='1d')['Close'].iloc[-1])
        except:
            continue
        direction = trade['direction']
        stop = trade['stop_price']
        target = trade['target_price']
        win = False
        if direction == 'long':
            if current_price >= target:
                trade['status'] = 'win'
                win = True
                total_wins += 1
            elif current_price <= stop:
                trade['status'] = 'loss'
        elif direction == 'short':
            if current_price <= target:
                trade['status'] = 'win'
                win = True
                total_wins += 1
            elif current_price >= stop:
                trade['status'] = 'loss'
        total += 1
        
        # Track indicator performance
        for ind in ['rsi', 'macd', 'bb', 'trend', 'advanced_candle', 'obv', 'fvg', 'vwap', 'stoch', 'cci', 'hurst', 'adx', 'williams_r', 'sar']:
            signal = trade.get(f'{ind}_signal', 0)
            if win:
                if (direction == 'long' and signal > 0) or (direction == 'short' and signal < 0):
                    indicator_wins[ind] += 1
            else:
                if (direction == 'long' and signal > 0) or (direction == 'short' and signal < 0):
                    indicator_losses[ind] += 1
    
    if total > 0:
        win_rate = total_wins / total
        print(f"Evaluated {total} trades, win rate: {win_rate:.2%}")
        
        # Adjust weights per indicator
        for ind in ['rsi', 'macd', 'bb', 'trend', 'advanced_candle', 'obv', 'fvg', 'vwap', 'stoch', 'cci', 'hurst', 'adx', 'williams_r', 'sar']:
            wins = indicator_wins[ind]
            losses = indicator_losses[ind]
            if wins + losses > 0:
                ind_win_rate = wins / (wins + losses)
                if ind_win_rate > 0.6:
                    globals()[f'{ind.upper()}_WEIGHT'] *= 1.1  # Boost good performers
                elif ind_win_rate < 0.4:
                    globals()[f'{ind.upper()}_WEIGHT'] *= 0.9  # Reduce bad performers
                if globals()[f'{ind.upper()}_WEIGHT'] < 1.0:
                    globals()[f'{ind.upper()}_WEIGHT'] = 1.0  # Neutralize underperformers
                print(f"{ind.replace('_', ' ').capitalize()} win rate: {ind_win_rate:.2%}, new weight: {globals()[f'{ind.upper()}_WEIGHT']:.2f}")
        
        # Adjust overall parameters if win rate < 45% AND sufficient sample size
        if win_rate < 0.45 and total >= 10:  # Require at least 10 trades for adjustments
            global EXPECTED_RETURN_PER_SENTIMENT, MIN_STOP_PCT
            MIN_STOP_PCT *= 0.95  # Less aggressive adjustment
            print("Adjusted: slightly tighter stops due to low win rate.")
        elif win_rate < 0.3 and total >= 5:  # Very low win rate even with smaller sample
            MIN_STOP_PCT *= 0.9
            print("Adjusted: tighter stops due to very low win rate.")
        elif win_rate > 0.6 and total >= 10:  # Good performance - loosen stops slightly
            MIN_STOP_PCT *= 1.05
            print("Adjusted: slightly looser stops due to good performance.")
        
        # Save back
        with open(TRADE_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

def backtest_parameters():
    """Backtest current parameters on historical data and auto-adjust if needed."""
    if not BACKTEST_ENABLED:
        return
    
    print(f"Running backtest on last {BACKTEST_PERIOD_DAYS} days of data...")
    
    if BACKTEST_TEST_MODE:
        # Fake test data to demonstrate adjustments
        backtest_results = {'total_trades': 100, 'wins': 30, 'losses': 70, 'total_return': -0.05}  # 30% win rate, poor performance
        print("TEST MODE: Using fake backtest data for demonstration.")
    else:
        backtest_results = {'total_trades': 0, 'wins': 0, 'losses': 0, 'total_return': 0.0}
        
        # Test on expanded symbols for more accurate validation
        test_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD', 'GC=F', 'CL=F', 'ZW=F', 'ZC=F']
        
        for sym in test_symbols:
            yf_symbol = FOREX_SYMBOL_MAP.get(sym, sym)
            if sym in ['GC=F', 'CL=F', 'ZW=F', 'ZC=F']:
                yf_symbol = sym  # Commodities already have correct format
            try:
                # Get historical hourly data
                hist = yf.Ticker(yf_symbol).history(period=f'{BACKTEST_PERIOD_DAYS}d', interval='1h')
                if hist.empty or len(hist) < 24:  # Need at least 1 day
                    continue
                
                # Simulate trades on each hour
                for i in range(24, len(hist)):  # Start from 24th hour to have enough data
                    # Mock market data for the hour
                    recent_data = hist.iloc[i-24:i]  # Last 24 hours
                    current_price = hist.iloc[i]['Close']
                    
                    # Calculate ATR and other metrics (simplified)
                    high = recent_data['High']
                    low = recent_data['Low']
                    close = recent_data['Close']
                    atr = (high - low).rolling(14).mean().iloc[-1] if len(high) >= 14 else 0.001
                    atr_pct = atr / current_price
                    
                    # Calculate signals from recent data
                    close = recent_data['Close']
                    high = recent_data['High']
                    low = recent_data['Low']
                    volume = recent_data['Volume']
                    
                    # RSI
                    if len(close) >= 14:
                        delta = close.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        rsi_val = rsi.iloc[-1]
                        rsi_signal = 1 if rsi_val < 30 else -1 if rsi_val > 70 else 0
                    else:
                        rsi_signal = 0
                    
                    # MACD
                    if len(close) >= 26:
                        ema12 = close.ewm(span=12).mean()
                        ema26 = close.ewm(span=26).mean()
                        macd_line = ema12 - ema26
                        signal_line = macd_line.ewm(span=9).mean()
                        macd_signal = 1 if macd_line.iloc[-1] > signal_line.iloc[-1] else -1
                    else:
                        macd_signal = 0
                    
                    # BB
                    if len(close) >= 20:
                        sma20 = close.rolling(window=20).mean()
                        std20 = close.rolling(window=20).std()
                        upper_bb = sma20 + 2 * std20
                        lower_bb = sma20 - 2 * std20
                        bb_signal = 1 if close.iloc[-1] < lower_bb.iloc[-1] else -1 if close.iloc[-1] > upper_bb.iloc[-1] else 0
                    else:
                        bb_signal = 0
                    
                    # Trend
                    if len(close) >= 200:
                        ema50 = close.ewm(span=50).mean()
                        ema200 = close.ewm(span=200).mean()
                        trend_signal = 1 if ema50.iloc[-1] > ema200.iloc[-1] else -1
                    else:
                        trend_signal = 0
                    
                    # Advanced candle
                    advanced_candle_signal = 0
                    if len(close) >= 2:
                        prev_high = high.iloc[-2]
                        prev_low = low.iloc[-2]
                        prev_open = recent_data['Open'].iloc[-2]
                        prev_close = close.iloc[-2]
                        curr_high = high.iloc[-1]
                        curr_low = low.iloc[-1]
                        curr_open = recent_data['Open'].iloc[-1]
                        curr_close = close.iloc[-1]
                        # Bullish engulfing
                        if prev_close < prev_open and curr_close > curr_open and curr_close >= prev_open and curr_open <= prev_close:
                            advanced_candle_signal = 1
                        # Bearish engulfing
                        elif prev_close > prev_open and curr_close < curr_open and curr_close <= prev_open and curr_open >= prev_close:
                            advanced_candle_signal = -1
                    
                    # OBV
                    if len(volume) >= 2:
                        obv = [0]
                        for i in range(1, len(close)):
                            if close.iloc[i] > close.iloc[i-1]:
                                obv.append(obv[-1] + volume.iloc[i])
                            elif close.iloc[i] < close.iloc[i-1]:
                                obv.append(obv[-1] - volume.iloc[i])
                            else:
                                obv.append(obv[-1])
                        obv_signal = 1 if obv[-1] > obv[-2] else -1
                    else:
                        obv_signal = 0
                    
                    # FVG
                    fvg_signal = 0
                    if len(close) >= 10:
                        for i in range(-10, -1):
                            if low.iloc[i] > high.iloc[i+2]:
                                fvg_signal = 1
                                break
                            elif high.iloc[i] < low.iloc[i+2]:
                                fvg_signal = -1
                                break
                    
                    # VWAP
                    if len(close) >= 2 and volume.sum() > 0:
                        vwap = (close * volume).cumsum() / volume.cumsum()
                        vwap_signal = 1 if close.iloc[-1] > vwap.iloc[-1] else -1
                    else:
                        vwap_signal = 0
                    
                    # Stochastic Oscillator
                    if len(close) >= 14:
                        lowest_low = low.rolling(window=14).min()
                        highest_high = high.rolling(window=14).max()
                        stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
                        stoch_d = stoch_k.rolling(window=3).mean()
                        stoch_signal = 1 if stoch_k.iloc[-1] < 20 else -1 if stoch_k.iloc[-1] > 80 else 0
                    else:
                        stoch_signal = 0
                    
                    # CCI
                    if len(close) >= 20:
                        typical_price = (high + low + close) / 3
                        sma_tp = typical_price.rolling(window=20).mean()
                        mean_dev = typical_price.rolling(window=20).apply(lambda x: abs(x - x.mean()).mean())
                        cci = (typical_price - sma_tp) / (0.015 * mean_dev)
                        cci_signal = 1 if cci.iloc[-1] < -100 else -1 if cci.iloc[-1] > 100 else 0
                    else:
                        cci_signal = 0
                    
                    # Hurst Exponent
                    if len(close) >= 40:
                        hurst = calculate_hurst_exponent(close, max_lag=20)
                        hurst_signal = 1 if hurst > 0.6 else -1 if hurst < 0.4 else 0
                    else:
                        hurst_signal = 0
                    
                    # ADX
                    if len(close) >= 30:
                        adx_value = calculate_adx(high, low, close, period=14)
                        adx_signal = 1 if adx_value > 25 else -1 if adx_value < 20 else 0
                    else:
                        adx_signal = 0
                    
                    # Williams %R
                    if len(close) >= 14:
                        williams_r = calculate_williams_r(high, low, close, period=14)
                        williams_r_signal = 1 if williams_r < -80 else -1 if williams_r > -20 else 0
                    else:
                        williams_r_signal = 0
                    
                    # Parabolic SAR
                    if len(close) >= 2:
                        sar = calculate_parabolic_sar(high, low, close)
                        sar_signal = 1 if close.iloc[-1] > sar else -1
                    else:
                        sar_signal = 0
                    
                    # Get trade plan
                    market_data = {
                        'price': current_price,
                        'volatility_hourly': atr_pct,
                        'atr_pct': atr_pct,
                        'pivot': (high.max() + low.min() + close.iloc[-1]) / 3,
                        'r1': ((high.max() + low.min() + close.iloc[-1]) / 3) + atr,
                        'r2': ((high.max() + low.min() + close.iloc[-1]) / 3) + 2*atr,
                        's1': ((high.max() + low.min() + close.iloc[-1]) / 3) - atr,
                        's2': ((high.max() + low.min() + close.iloc[-1]) / 3) - 2*atr,
                        'support': low.min(),
                        'resistance': high.max(),
                        'psych_level': round(current_price * 100) / 100,
                        'rsi_signal': rsi_signal,
                        'macd_signal': macd_signal,
                        'bb_signal': bb_signal,
                        'trend_signal': trend_signal,
                        'advanced_candle_signal': advanced_candle_signal,
                        'obv_signal': obv_signal,
                        'fvg_signal': fvg_signal,
                        'vwap_signal': vwap_signal,
                        'stoch_signal': stoch_signal,
                        'cci_signal': cci_signal,
                        'hurst_signal': hurst_signal,
                        'adx_signal': adx_signal,
                        'williams_r_signal': williams_r_signal,
                        'sar_signal': sar_signal
                    }
                    
                    # For backtest, use neutral sentiment to test technicals
                    avg_sent = 0.0
                    news_count = 0
                    
                    # But to allow trades, set small sentiment based on signals
                    bullish_count = sum(1 for s in [rsi_signal, macd_signal, bb_signal, trend_signal, advanced_candle_signal, obv_signal, fvg_signal, vwap_signal, stoch_signal, cci_signal, hurst_signal, adx_signal, williams_r_signal, sar_signal] if s > 0)
                    bearish_count = sum(1 for s in [rsi_signal, macd_signal, bb_signal, trend_signal, advanced_candle_signal, obv_signal, fvg_signal, vwap_signal, stoch_signal, cci_signal, hurst_signal, adx_signal, williams_r_signal, sar_signal] if s < 0)
                    if bullish_count >= 3:
                        avg_sent = 0.1
                    elif bearish_count >= 3:
                        avg_sent = -0.1
                    
                    plan = calculate_trade_plan(avg_sent, news_count, market_data, kind='forex')
                    if not plan or plan['direction'] == 'flat':
                        continue
                    
                    # Simulate trade outcome (next hour) with spread and slippage
                    next_price = hist.iloc[i+1]['Close'] if i+1 < len(hist) else current_price
                    direction = plan['direction']
                    stop = plan['stop_pct']
                    target = plan['expected_profit_pct']
                    
                    # Add spread and slippage (forex: 1 pip spread, 0.5 pip slippage)
                    spread = 0.0001
                    slippage = 0.00005
                    
                    if direction == 'long':
                        entry_price = current_price + spread/2 + slippage
                        stop_price = current_price * (1 - stop) - spread/2
                        target_price = current_price * (1 + target) + spread/2
                        if next_price >= target_price:
                            backtest_results['wins'] += 1
                            backtest_results['total_return'] += target
                        elif next_price <= stop_price:
                            backtest_results['losses'] += 1
                            backtest_results['total_return'] -= stop
                    elif direction == 'short':
                        entry_price = current_price - spread/2 - slippage
                        stop_price = current_price * (1 + stop) + spread/2
                        target_price = current_price * (1 - target) - spread/2
                        if next_price <= target_price:
                            backtest_results['wins'] += 1
                            backtest_results['total_return'] += target
                        elif next_price >= stop_price:
                            backtest_results['losses'] += 1
                            backtest_results['total_return'] -= stop
                    
                    backtest_results['total_trades'] += 1
                    
            except Exception as e:
                print(f"Backtest error for {sym}: {e}")
                continue
    
    # Evaluate backtest
    if backtest_results['total_trades'] > 0:
        win_rate = backtest_results['wins'] / backtest_results['total_trades']
        total_return = backtest_results['total_return']
        print(f"Backtest results: {backtest_results['total_trades']} trades, win rate: {win_rate:.2%}, total return: {total_return:.4f}")
        
        # Auto-adjust if win rate below threshold (more aggressive adjustments for accuracy)
        if win_rate < BACKTEST_ADJUST_THRESHOLD:
            global EXPECTED_RETURN_PER_SENTIMENT, MIN_STOP_PCT, MAX_LEVERAGE_FOREX
            EXPECTED_RETURN_PER_SENTIMENT *= 0.90  # Reduced to 10% for more aggressive tuning
            MIN_STOP_PCT *= 0.90  # 10% tighter stops
            MAX_LEVERAGE_FOREX = max(50, MAX_LEVERAGE_FOREX * 0.90)  # 10% reduction for stability
            print("Backtest poor - auto-adjusted parameters: reduced returns, tighter stops, lower leverage.")
        else:
            print("Backtest satisfactory - parameters validated.")

def print_current_parameters():
    """Print current optimized parameters for monitoring improvements."""
    print("=== Current Optimized Parameters ===")
    print(f"EXPECTED_RETURN_PER_SENTIMENT: {EXPECTED_RETURN_PER_SENTIMENT:.6f}")
    print(f"MIN_STOP_PCT: {MIN_STOP_PCT:.6f}")
    print(f"MAX_LEVERAGE_FOREX: {MAX_LEVERAGE_FOREX}")
    print(f"DAILY_RISK_LIMIT: {DAILY_RISK_LIMIT:.4f}")
    print(f"RSI_WEIGHT: {RSI_WEIGHT:.2f}")
    print(f"MACD_WEIGHT: {MACD_WEIGHT:.2f}")
    print(f"BB_WEIGHT: {BB_WEIGHT:.2f}")
    print(f"TREND_WEIGHT: {TREND_WEIGHT:.2f}")
    print(f"ADVANCED_CANDLE_WEIGHT: {ADVANCED_CANDLE_WEIGHT:.2f}")
    print(f"OBV_WEIGHT: {OBV_WEIGHT:.2f}")
    print(f"FVG_WEIGHT: {FVG_WEIGHT:.2f}")
    print(f"VWAP_WEIGHT: {VWAP_WEIGHT:.2f}")
    print(f"STOCH_WEIGHT: {STOCH_WEIGHT:.2f}")
    print(f"CCI_WEIGHT: {CCI_WEIGHT:.2f}")
    print(f"HURST_WEIGHT: {HURST_WEIGHT:.2f}")
    print(f"ADX_WEIGHT: {ADX_WEIGHT:.2f}")
    print(f"WILLIAMS_R_WEIGHT: {WILLIAMS_R_WEIGHT:.2f}")
    print(f"SAR_WEIGHT: {SAR_WEIGHT:.2f}")
    print("====================================")

async def main(backtest_only=False):
    if not backtest_only:
        current_session = get_current_market_session()
        print(f"Current market session: {current_session}")
        
        # Adjust parameters based on session
        session_multiplier = 1.0
        if current_session in ['London', 'New York']:
            session_multiplier = 1.2  # Boost expected returns during active sessions
        elif current_session == 'Off-hours':
            session_multiplier = 0.9  # Reduce during low activity
        elif current_session == 'Weekend (no trading)':
            print("It's a weekend—skipping trades to avoid low liquidity.")
            return []  # Skip trading on weekends
        
        # Only trade in active sessions
        if current_session not in ['London', 'New York']:
            print(f"Current session '{current_session}' is not active for trading—skipping to focus on high liquidity periods.")
            return []  # Only trade in London or NY sessions
        
        global EXPECTED_RETURN_PER_SENTIMENT
        EXPECTED_RETURN_PER_SENTIMENT *= session_multiplier
        print(f"Session multiplier applied: {session_multiplier:.1f}")
    else:
        print("Running in backtest-only mode - bypassing session checks")
    
    print('Forex, Commodities & Indices News Trading Bot v2.0 - Fetching latest signals (1h timeframe)...')
    articles = get_news()

    # Initialize with default symbols (news optional)
    symbol_articles = {}
    for sym, yf, kind in DEFAULT_SYMBOLS:
        symbol_articles[sym] = {'yf': yf, 'kind': kind, 'texts': [], 'articles': [], 'count': 0}

    # Group articles mentioning each symbol
    for a in articles:
        title = a.get('title') or ''
        desc = a.get('description') or ''
        text = f'{title} {desc}'.strip()
        if not text:
            continue
        hits = extract_forex_and_tickers(text)
        for h in hits:
            key = h['symbol']
            if key not in symbol_articles:
                symbol_articles[key] = {'yf': h['yf'], 'kind': h['kind'], 'texts': [], 'articles': [], 'count': 0}
            symbol_articles[key]['texts'].append(text)
            symbol_articles[key]['articles'].append(a)  # Store full article for LLM
            symbol_articles[key]['count'] += 1

    print(f'Retrieved {len(articles)} articles for analysis. Analyzing {len(symbol_articles)} symbols (defaults + news mentions).')

    results = []
    print('Analyzing candidates...')
    
    # Prepare concurrent data fetching
    import asyncio
    async def analyze_symbol(sym, info):
        texts = info['texts']
        articles_for_symbol = info.get('articles', [])
        
        # Use LLM-enhanced sentiment if available
        avg_sent, llm_confidence, llm_analysis = analyze_sentiment_with_llm(articles_for_symbol, sym)
        
        # Check news impact and get trading guidance
        news_impact = None
        if NEWS_IMPACT_ENABLED and articles_for_symbol:
            try:
                from news_impact_predictor import get_news_impact_predictor
                impact_predictor = get_news_impact_predictor()
                news_impact = impact_predictor.predict_news_impact(articles_for_symbol, sym)
                
                if sym in DEBUG_SYMBOLS:
                    print(f"NEWS IMPACT {sym}: {news_impact['impact_level']} (score: {news_impact['impact_score']:.2f}) - {news_impact['reason']}")
                
                # Skip if news impact predictor says not to trade
                if not news_impact['should_trade']:
                    if sym in DEBUG_SYMBOLS:
                        print(f"NEWS FILTER {sym}: Skipping due to news impact")
                    return None
                    
            except Exception as e:
                print(f"News impact prediction error for {sym}: {e}")
        
        news_count = info['count']
        yf_symbol = info['yf']
        kind = info['kind']

        market = await get_market_data_async(yf_symbol, kind=kind)
        if not market:
            return None

        # Skip high volatility periods (>2%)
        if market['volatility_hourly'] > 0.02:
            return None

        plan = calculate_trade_plan(avg_sent, news_count, market, kind=kind, news_impact=news_impact)
        if not plan:
            return None

        # Debug for first few
        if sym in DEBUG_SYMBOLS:
            print(f"DEBUG {sym}: sentiment={avg_sent:.3f}, expected_return={plan['expected_return_pct']:.6f}, direction={plan['direction']}, rsi={plan['rsi_signal']}, macd={plan['macd_signal']}, bb={plan['bb_signal']}, rr={plan['rr']:.2f}")

        # Only keep actionable plans
        if plan['direction'] == 'flat' or plan['rr'] < 2.0:  # Minimum 2:1 RR for quality trades
            return None
# --- OPTIONAL safety in main() loop, just before get_market_data(...) ---
        # Skip unknown/price-less stock-like tickers defensively
        if kind == 'stock' and not _symbol_has_prices(yf_symbol):
            return None

        # Check daily risk limit
        trade_risk = plan['stop_pct'] * plan['recommended_leverage']
        current_daily_risk = get_daily_risk()
        if current_daily_risk + trade_risk > DAILY_RISK_LIMIT:
            return None  # Skip this trade to stay within daily risk limit

        # Low money adjustments: if entry * leverage < $100, boost ROI and leverage for better R/R
        entry_cost = market['price'] * plan['recommended_leverage']
        if entry_cost < 100:
            plan['expected_return_pct'] *= 1.5  # Higher ROI
            plan['expected_profit_pct'] *= 1.5
            plan['recommended_leverage'] = min(plan['recommended_leverage'] * 2, MAX_LEVERAGE_FOREX if kind == 'forex' else MAX_LEVERAGE_STOCK)  # Higher leverage
            plan['stop_pct'] *= 0.7  # Tighter stops for better R/R
            plan['rr'] = plan['expected_profit_pct'] / plan['stop_pct'] if plan['stop_pct'] > 0 else 0
            trade_risk = plan['stop_pct'] * plan['recommended_leverage']  # Recalculate risk
            if current_daily_risk + trade_risk > DAILY_RISK_LIMIT:
                return None  # Still skip if exceeds

        # ML prediction filtering (if enabled and available)
        ml_probability = 0.5
        ml_confidence = 0.0
        if ML_ENABLED and ML_AVAILABLE:
            try:
                ml_predictor = get_ml_predictor()
                trade_data = {
                    'avg_sentiment': avg_sent,
                    'news_count': news_count,
                    'price': market['price'],
                    'volatility_hourly': market['volatility_hourly'],
                    'atr_pct': market['atr_pct'],
                    'support': market['support'],
                    'resistance': market['resistance'],
                    'pivot': market['pivot'],
                    'rsi_signal': market['rsi_signal'],
                    'macd_signal': market['macd_signal'],
                    'bb_signal': market['bb_signal'],
                    'trend_signal': market['trend_signal'],
                    'advanced_candle_signal': market['advanced_candle_signal'],
                    'obv_signal': market['obv_signal'],
                    'fvg_signal': market['fvg_signal'],
                    'vwap_signal': market['vwap_signal'],
                    'stoch_signal': market['stoch_signal'],
                    'cci_signal': market['cci_signal'],
                    'hurst_signal': market.get('hurst_signal', 0),
                    'adx_signal': market.get('adx_signal', 0),
                    'williams_r_signal': market.get('williams_r_signal', 0),
                    'sar_signal': market.get('sar_signal', 0),
                }
                should_trade, ml_probability, ml_confidence = ml_predictor.should_trade(
                    trade_data, min_confidence=ML_MIN_CONFIDENCE, min_probability=ML_MIN_PROBABILITY
                )
                if not should_trade:
                    if sym in DEBUG_SYMBOLS:
                        print(f"ML FILTER {sym}: prob={ml_probability:.3f}, conf={ml_confidence:.3f} - Trade rejected")
                    return None  # Skip trades that ML predicts will fail
                else:
                    if sym in DEBUG_SYMBOLS:
                        print(f"ML APPROVED {sym}: prob={ml_probability:.3f}, conf={ml_confidence:.3f}")
            except Exception as e:
                print(f"ML prediction error for {sym}: {e}")
                # Continue without ML filter on error

        return {
            'symbol': sym,
            'yf_symbol': yf_symbol,
            'kind': kind,
            'avg_sentiment': avg_sent,
            'llm_confidence': llm_confidence,
            'llm_analysis': llm_analysis,
            'news_count': news_count,
            'price': market['price'],
            'volatility_hourly': market['volatility_hourly'],
            'atr_pct': market['atr_pct'],
            'pivot': market['pivot'],
            'r1': market['r1'], 'r2': market['r2'],
            's1': market['s1'], 's2': market['s2'],
            'support': market['support'],
            'resistance': market['resistance'],
            'psych_level': market['psych_level'],
            'rsi_signal': market['rsi_signal'],
            'macd_signal': market['macd_signal'],
            'bb_signal': market['bb_signal'],
            'trend_signal': market['trend_signal'],
            'advanced_candle_signal': market['advanced_candle_signal'],
            'obv_signal': market['obv_signal'],
            'fvg_signal': market['fvg_signal'],
            'vwap_signal': market['vwap_signal'],
            'stoch_signal': market['stoch_signal'],
            'cci_signal': market['cci_signal'],
            'hurst_signal': market.get('hurst_signal', 0),
            'adx_signal': market.get('adx_signal', 0),
            'williams_r_signal': market.get('williams_r_signal', 0),
            'sar_signal': market.get('sar_signal', 0),
            'ml_probability': ml_probability,
            'ml_confidence': ml_confidence,
            **plan
        }
    
    # Run concurrent analysis
    tasks = [analyze_symbol(sym, info) for sym, info in symbol_articles.items()]
    analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    for result in analysis_results:
        if result is not None and not isinstance(result, Exception):
            results.append(result)

    # sort by quality: rr then news_count
    results.sort(key=lambda r: (r['rr'], r['news_count']), reverse=True)

    # Evaluate and learn every run
    evaluate_trades()
    
    # Backtest and auto-validate parameters
    backtest_parameters()
    
    # Train/retrain ML model periodically
    if ML_ENABLED and ML_AVAILABLE:
        try:
            ml_predictor = get_ml_predictor()
            # Check if we should retrain (every 24 hours or if model doesn't exist)
            retrain_file = 'ml_last_train.json'
            should_retrain = True
            if os.path.exists(retrain_file):
                try:
                    with open(retrain_file, 'r') as f:
                        last_train_data = json.load(f)
                        last_train_time = datetime.fromisoformat(last_train_data.get('timestamp', '2000-01-01'))
                        hours_since_train = (datetime.now() - last_train_time).total_seconds() / 3600
                        should_retrain = hours_since_train >= ML_RETRAIN_INTERVAL
                except (ValueError, json.JSONDecodeError, KeyError) as e:
                    logging.warning(f"Error reading last train time: {e}, will retrain")
                    should_retrain = True
            
            if should_retrain:
                print("Training/retraining ML model...")
                if ml_predictor.train(TRADE_LOG_FILE):
                    print("ML model trained successfully")
                    with open(retrain_file, 'w') as f:
                        json.dump({'timestamp': datetime.now().isoformat()}, f)
                else:
                    print("ML model training skipped (insufficient data)")
        except Exception as e:
            print(f"ML training error: {e}")
    
    print_current_parameters()  # Show updated parameters after adjustments

    if not results:
        message = 'No actionable forex, commodities, or indices trades found at this time.'
        print(message)
        send_telegram_message(message)
        return []

    message = f"Recommended trades (ML {'Enabled' if ML_ENABLED and ML_AVAILABLE else 'Disabled'}):\nGenerated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Current session: {current_session}\nTotal articles: {len(articles)} | Symbols analyzed: {len(symbol_articles)} | Daily risk used: {get_daily_risk():.1%}\n"
    print('\nRecommended trades:')
    print(f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Current session: {current_session} | Daily risk used: {get_daily_risk():.1%}")
    for r in results:
        price = r['price']
        direction = r['direction']
        stop_pct = r['stop_pct']
        exp_return_pct = r['expected_return_pct']
        if direction == 'long':
            stop_price = price * (1 - stop_pct)
            target_price = price * (1 + exp_return_pct)
        elif direction == 'short':
            stop_price = price * (1 + stop_pct)
            target_price = price * (1 - exp_return_pct)
        else:
            stop_price = price
            target_price = price
        ml_info = f" | ML: {r.get('ml_probability', 0.5):.2%} prob, {r.get('ml_confidence', 0):.2%} conf" if ML_ENABLED and ML_AVAILABLE else ""
        trade_line = f"Symbol: {r['symbol']} | Direction: {r['direction'].upper()} | Entry Price: {r['price']:.4f} | Stop Loss: {stop_price:.4f} | Take Profit: {target_price:.4f} | Leverage: {r['recommended_leverage']}{ml_info}"
        message += trade_line + "\n"
        print(trade_line)

    send_telegram_message(message)
    
    # Log trades
    log_trades(results)
    
    return results

@lru_cache(maxsize=100)
async def get_market_data_async(yf_symbol, kind='forex', session=None):
    """Async version of get_market_data for concurrent fetching."""
    # Try yfinance first (primary)
    print(f"Attempting yfinance for {yf_symbol}...")
    data = _get_yfinance_data(yf_symbol, kind)
    if data:
        print(f"yfinance success for {yf_symbol}")
        return data
    else:
        print(f"yfinance failed for {yf_symbol}")
    
    # For now, keep other providers synchronous as they may not support async easily
    # Fallback to Alpha Vantage for forex
    if kind == 'forex':
        if not ALPHA_VANTAGE_API_KEY:
            print(f"Skipping Alpha Vantage for {yf_symbol} (no key)")
        else:
            print(f"Attempting Alpha Vantage for {yf_symbol}...")
            data = _get_alpha_vantage_data(yf_symbol)
            if data:
                print(f"Alpha Vantage success for {yf_symbol}")
                return data
            else:
                print(f"Alpha Vantage failed for {yf_symbol}")

    # Fallback to Polygon
    if not POLYGON_API_KEY:
        print(f"Skipping Polygon for {yf_symbol} (no key)")
    else:
        print(f"Attempting Polygon for {yf_symbol}...")
        data = _get_polygon_data(yf_symbol)
        if data:
            print(f"Polygon success for {yf_symbol}")
            return data
        else:
            print(f"Polygon failed for {yf_symbol}")

    # Fallback to TwelveData
    if not TWELVE_DATA_API_KEY:
        print(f"Skipping Twelve Data for {yf_symbol} (no key)")
    else:
        print(f"Attempting Twelve Data for {yf_symbol}...")
        data = _get_twelvedata_data(yf_symbol)
        if data:
            print(f"Twelve Data success for {yf_symbol}")
            return data
        else:
            print(f"Twelve Data failed for {yf_symbol}")

    # Fallback to FinancialModelingPrep
    if not FMP_API_KEY:
        print(f"Skipping FMP for {yf_symbol} (no key)")
    else:
        print(f"Attempting FMP for {yf_symbol}...")
        data = _get_fmp_data(yf_symbol)
        if data:
            print(f"FMP success for {yf_symbol}")
            return data
        else:
            print(f"FMP failed for {yf_symbol}")

    # Fallback to Quandl (very limited, dataset dependent)
    if not QUANDL_API_KEY:
        print(f"Skipping Quandl for {yf_symbol} (no key)")
    else:
        print(f"Attempting Quandl for {yf_symbol}...")
        data = _get_quandl_data(yf_symbol)
        if data:
            print(f"Quandl success for {yf_symbol}")
            return data
        else:
            print(f"Quandl failed for {yf_symbol}")

    # Fallback to FRED for macro series (not ticker-level)
    if not FRED_API_KEY:
        print(f"Skipping FRED for {yf_symbol} (no key)")
    else:
        print(f"Attempting FRED for {yf_symbol}...")
        data = _get_fred_data(yf_symbol)
        if data:
            print(f"FRED success for {yf_symbol}")
            return data
        else:
            print(f"FRED failed for {yf_symbol}")
    
    # Fallback to IEX for stocks
    if kind == 'stock':
        if not IEX_API_TOKEN:
            print(f"Skipping IEX for {yf_symbol} (no key)")
        else:
            print(f"Attempting IEX for {yf_symbol}...")
            data = _get_iex_data(yf_symbol)
            if data:
                print(f"IEX success for {yf_symbol}")
                return data
            else:
                print(f"IEX failed for {yf_symbol}")
    
    print(f"All sources failed for {yf_symbol}")
    return None

if __name__ == '__main__':
    import asyncio
    if len(sys.argv) > 1 and sys.argv[1] == '--backtest':
        asyncio.run(main(backtest_only=True))
    else:
        asyncio.run(main())
