import os
import time
import math
import re
import json
import requests
import logging
from functools import lru_cache
from datetime import datetime, timedelta, timezone
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
    ('CNBC Forex', 'https://www.cnbc.com/forex/'),
    ('Financial Times Markets', 'https://www.ft.com/markets'),
    ('The Economist Finance', 'https://www.economist.com/finance-and-economics'),
    ('WSJ Markets', 'https://www.wsj.com/news/markets'),
    ('BBC Business', 'https://www.bbc.com/business'),
    ('Forbes Markets', 'https://www.forbes.com/markets/'),
    ('Business Insider Markets', 'https://markets.businessinsider.com/'),
    ('ZeroHedge', 'https://www.zerohedge.com/'),
    ('Seeking Alpha Forex', 'https://seekingalpha.com/currency'),
    ('FX Empire', 'https://www.fxempire.com/news'),
    ('MyFXBook News', 'https://www.myfxbook.com/news'),
    ('FXCM Insights', 'https://www.fxcm.com/insights/'),
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

# Risk settings (optimized for 1h fast forex trading)
MIN_STOP_PCT = 0.001  # 0.1% minimal stop for 1h
EXPECTED_RETURN_PER_SENTIMENT = 0.004  # 0.4% per full +1.0 sentiment for 1h (increased for longer timeframe)
NEWS_COUNT_BONUS = 0.001  # 0.1% per article bonus
MAX_NEWS_BONUS = 0.004  # Max 0.4%

# Leverage caps - Updated to 500x for forex
MAX_LEVERAGE_FOREX = 500
MAX_LEVERAGE_STOCK = 5

# Low money mode flag - Set to True for accounts with small capital (< $500 equivalent)
LOW_MONEY_MODE = True

if LOW_MONEY_MODE:
    EXPECTED_RETURN_PER_SENTIMENT = 0.006  # Higher ROI to offset fees
    NEWS_COUNT_BONUS = 0.002  # Increased bonus
    MAX_NEWS_BONUS = 0.008  # Higher max bonus
    MIN_STOP_PCT = 0.0005  # Tighter stops for better R/R

# Daily risk limit (1% max loss per day)
DAILY_RISK_LIMIT = 0.01  # 1%
DAILY_RISK_FILE = 'daily_risk.json'

# Trade logging file
TRADE_LOG_FILE = 'trade_log.json'

# Indicator weights (adaptive learning)
ICHIMOKU_WEIGHT = 1.2
VOLUME_WEIGHT = 1.15
FVG_WEIGHT = 1.1
CANDLE_WEIGHT = 1.1
NEW_TECHNIQUE_ENABLED = False  # Placeholder for adding new techniques

# Market sessions (UTC, Monday-Friday)
MARKET_SESSIONS = [
    ('Sydney', 0, 8),
    ('Tokyo', 0, 8),
    ('London', 8, 16),
    ('New York', 13.5, 20),  # 13:30 to 20:00
]

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
        items = fetch_rss_items(url)
        for it in items:
            results.append({'title': it.get('title', ''), 'description': it.get('description', ''), 'source': name})

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

def analyze_sentiment(texts):
    '''Aggregate sentiment over a list of texts using TextBlob. Boost influential sources.'''
    scores = []
    for t in texts:
        try:
            b = TextBlob(t)
            polarity = b.sentiment.polarity
            # Boost sentiment from influential forex sources (central banks, economists)
            if any(word in t.get('source', '').lower() for word in ['ecb', 'fed', 'boj', 'boe', 'reuters', 'bloomberg']):
                polarity *= 1.5  # Boost for authoritative sources
            scores.append(polarity)
        except Exception:
            continue
    if not scores:
        return 0.0
    # weighted by recency could be added; simple average for now
    return sum(scores) / len(scores)

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

        # Candle patterns: simple bullish/bearish signal from last 3 candles
        candle_signal = 0  # -1 bearish, 0 neutral, 1 bullish
        if len(close) >= 3:
            last3 = close.tail(3).values
            if last3[2] > last3[1] > last3[0]:  # Rising
                candle_signal = 1
            elif last3[2] < last3[1] < last3[0]:  # Falling
                candle_signal = -1

        # Ichimoku Cloud
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        chikou = close.shift(-26)
        ichimoku_signal = 0  # 1 bullish, -1 bearish
        if (current_price > senkou_a.iloc[-1] and current_price > senkou_b.iloc[-1] and 
            tenkan.iloc[-1] > kijun.iloc[-1] and senkou_a.iloc[-1] > senkou_b.iloc[-1]):
            ichimoku_signal = 1
        elif (current_price < senkou_a.iloc[-1] and current_price < senkou_b.iloc[-1] and 
              tenkan.iloc[-1] < kijun.iloc[-1] and senkou_a.iloc[-1] < senkou_b.iloc[-1]):
            ichimoku_signal = -1

        # Smart Money: Volume confirmation (institutional order flow)
        volume_avg = volume.tail(20).mean()
        recent_volume = volume.iloc[-1]
        volume_signal = 0  # 1 smart money buying, -1 smart money selling
        if recent_volume > volume_avg * 1.2:
            if close.iloc[-1] > close.iloc[-2]:
                volume_signal = 1
            elif close.iloc[-1] < close.iloc[-2]:
                volume_signal = -1

        # ICT: Fair Value Gap (FVG) detection - simple version
        fvg_signal = 0  # 1 bullish FVG, -1 bearish FVG
        if len(close) >= 4:
            # Bullish FVG: low of current > high of 2 candles ago
            if low.iloc[-1] > high.iloc[-3]:
                fvg_signal = 1
            # Bearish FVG: high of current < low of 2 candles ago
            elif high.iloc[-1] < low.iloc[-3]:
                fvg_signal = -1

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
            'candle_signal': candle_signal,
            'ichimoku_signal': ichimoku_signal,
            'volume_signal': volume_signal,
            'fvg_signal': fvg_signal
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
            'candle_signal': 0,
            'ichimoku_signal': 0,
            'volume_signal': 0,
            'fvg_signal': 0
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
            'candle_signal': 0,
            'ichimoku_signal': 0,
            'volume_signal': 0,
            'fvg_signal': 0
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
            'candle_signal': candle_signal,
            'ichimoku_signal': ichimoku_signal,
            'volume_signal': volume_signal,
            'fvg_signal': fvg_signal
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
            'candle_signal': candle_signal,
            'ichimoku_signal': ichimoku_signal,
            'volume_signal': volume_signal,
            'fvg_signal': fvg_signal
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
            'candle_signal': 0,
            'ichimoku_signal': 0,
            'volume_signal': 0,
            'fvg_signal': 0
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
            'candle_signal': 0,
            'ichimoku_signal': 0,
            'volume_signal': 0,
            'fvg_signal': 0
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

def recommend_leverage(rr, volatility, kind='crypto'):
    '''Recommend leverage given RR and volatility. Returns integer leverage.'''
    # Base leverage from RR: more RR allows more leverage
    base = max(1, int(math.floor(rr * 10)))  # Increased multiplier for higher leverage in crypto
    # Cap by asset class
    max_lev = MAX_LEVERAGE_FOREX if kind == 'forex' else MAX_LEVERAGE_STOCK
    # If volatility is very high, reduce recommended leverage
    if volatility is None:
        volatility = 1.0
    if volatility > 1.0:  # >100% annualized -> risky
        max_lev = min(max_lev, 50)  # Adjusted for higher cap
    if volatility > 2.0:
        max_lev = min(max_lev, 20)
    lev = min(base, max_lev)
    return max(1, lev)

def calculate_trade_plan(avg_sentiment, news_count, market_data, kind='forex'):
    '''Return dict with direction, expected_profit_pct, stop_pct, rr, recommended_leverage.'''
    global ICHIMOKU_WEIGHT, VOLUME_WEIGHT, FVG_WEIGHT, CANDLE_WEIGHT
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
    candle_signal = market_data['candle_signal']
    ichimoku_signal = market_data['ichimoku_signal']
    volume_signal = market_data['volume_signal']
    fvg_signal = market_data['fvg_signal']

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

    # Candle confirmation: boost if matches sentiment (using adaptive weight)
    if (avg_sentiment > 0 and candle_signal > 0) or (avg_sentiment < 0 and candle_signal < 0):
        expected_return *= CANDLE_WEIGHT
    elif (avg_sentiment > 0 and candle_signal < 0) or (avg_sentiment < 0 and candle_signal > 0):
        expected_return *= (2 - CANDLE_WEIGHT)  # Dampen inversely

    # Ichimoku confirmation: boost if matches sentiment
    if (avg_sentiment > 0 and ichimoku_signal > 0) or (avg_sentiment < 0 and ichimoku_signal < 0):
        expected_return *= ICHIMOKU_WEIGHT
    elif (avg_sentiment > 0 and ichimoku_signal < 0) or (avg_sentiment < 0 and ichimoku_signal > 0):
        expected_return *= (2 - ICHIMOKU_WEIGHT)
    elif ichimoku_signal == 0:
        expected_return *= 0.95  # slight dampen if Ichimoku neutral

    # Smart Money: Volume confirmation boost
    if (avg_sentiment > 0 and volume_signal > 0) or (avg_sentiment < 0 and volume_signal < 0):
        expected_return *= VOLUME_WEIGHT
    elif (avg_sentiment > 0 and volume_signal < 0) or (avg_sentiment < 0 and volume_signal > 0):
        expected_return *= (2 - VOLUME_WEIGHT)

    # ICT: FVG confirmation
    if (avg_sentiment > 0 and fvg_signal > 0) or (avg_sentiment < 0 and fvg_signal < 0):
        expected_return *= FVG_WEIGHT
    elif (avg_sentiment > 0 and fvg_signal < 0) or (avg_sentiment < 0 and fvg_signal > 0):
        expected_return *= (2 - FVG_WEIGHT)

    expected_profit_pct = abs(expected_return)

    vol = market_data.get('volatility_hourly', 0.0)
    atr_pct = market_data.get('atr_pct', 0.005)
    # Determine stop loss percent (use ATR for optimized 15m/30m stops, adjusted for forex)
    if kind == 'forex':
        stop_pct = max(MIN_STOP_PCT, atr_pct * 1.5)  # 1.5x ATR for forex (more volatile)
    else:
        stop_pct = max(MIN_STOP_PCT, atr_pct * 1.0)  # 1.0x ATR for commodities

    if stop_pct <= 0:
        return None

    rr = expected_profit_pct / stop_pct if stop_pct > 0 else 0.0

    # Force minimum 2:1 RR for actionable trades (more realistic than 3:1)
    if rr < 2 and expected_profit_pct > 0:
        expected_profit_pct = 2 * stop_pct
        rr = 2.0

    # decide direction (relaxed thresholds for more trades on 1h timeframe)
    direction = 'flat'
    if expected_return > 0.0005:  # 0.05% for long
        direction = 'long'
    elif expected_return < -0.0002:  # -0.02% for short
        direction = 'short'

    # For bearish Ichimoku or candle, allow short even if sentiment neutral
    if direction == 'flat' and ichimoku_signal == -1:
        direction = 'short'
        expected_return = -0.001  # Set small negative
        expected_profit_pct = 0.001
    elif direction == 'flat' and candle_signal == -1 and avg_sentiment < 0.1:
        direction = 'short'
        expected_return = -0.001
        expected_profit_pct = 0.001

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
        'candle_signal': candle_signal,
        'ichimoku_signal': ichimoku_signal,
        'volume_signal': volume_signal,
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
            'candle_signal': r['candle_signal'],
            'ichimoku_signal': r['ichimoku_signal'],
            'volume_signal': r['volume_signal'],
            'fvg_signal': r['fvg_signal']
        }
        logs.append(trade)
        # Update daily risk
        trade_risk = stop_pct * r['recommended_leverage']
        update_daily_risk(trade_risk)
    
    with open(TRADE_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def evaluate_trades():
    """Evaluate past trades and adjust indicator weights based on performance."""
    global ICHIMOKU_WEIGHT, VOLUME_WEIGHT, FVG_WEIGHT, CANDLE_WEIGHT, NEW_TECHNIQUE_ENABLED
    if not os.path.exists(TRADE_LOG_FILE):
        return
    
    with open(TRADE_LOG_FILE, 'r') as f:
        logs = json.load(f)
    
    indicator_wins = {'candle': 0, 'ichimoku': 0, 'volume': 0, 'fvg': 0}
    indicator_losses = {'candle': 0, 'ichimoku': 0, 'volume': 0, 'fvg': 0}
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
        for ind in ['candle', 'ichimoku', 'volume', 'fvg']:
            signal = trade[f'{ind}_signal']
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
        for ind in ['candle', 'ichimoku', 'volume', 'fvg']:
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
                print(f"{ind.capitalize()} win rate: {ind_win_rate:.2%}, new weight: {globals()[f'{ind.upper()}_WEIGHT']:.2f}")
        
        # Adjust overall parameters if win rate < 30%
        if win_rate < 0.3:
            global EXPECTED_RETURN_PER_SENTIMENT, MIN_STOP_PCT
            MIN_STOP_PCT *= 0.9
            print("Adjusted: tighter stops due to low win rate (<30%).")
            # Enable new technique if overall poor
            NEW_TECHNIQUE_ENABLED = True
            print("Enabled new technique placeholder due to low performance.")
        
        # Save back
        with open(TRADE_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

def main():
    # Check market session
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
    
    global EXPECTED_RETURN_PER_SENTIMENT
    EXPECTED_RETURN_PER_SENTIMENT *= session_multiplier
    print(f"Session multiplier applied: {session_multiplier:.1f}")
    
    print('Forex, Commodities & Indices News Trading Bot v2.0 - Fetching latest signals (1h timeframe)...')
    articles = get_news()

    # Initialize with default symbols (news optional)
    symbol_articles = {}
    for sym, yf, kind in DEFAULT_SYMBOLS:
        symbol_articles[sym] = {'yf': yf, 'kind': kind, 'texts': [], 'count': 0}

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
                symbol_articles[key] = {'yf': h['yf'], 'kind': h['kind'], 'texts': [], 'count': 0}
            symbol_articles[key]['texts'].append(text)
            symbol_articles[key]['count'] += 1

    print(f'Retrieved {len(articles)} articles for analysis. Analyzing {len(symbol_articles)} symbols (defaults + news mentions).')

    results = []
    print('Analyzing candidates...')
    for sym, info in symbol_articles.items():
        texts = info['texts']
        avg_sent = analyze_sentiment(texts)
        news_count = info['count']
        yf_symbol = info['yf']
        kind = info['kind']

        market = get_market_data(yf_symbol, kind=kind)
        if not market:
            continue

        plan = calculate_trade_plan(avg_sent, news_count, market, kind=kind)
        if not plan:
            continue

        # Only keep actionable plans
        if plan['direction'] == 'flat' or plan['rr'] < 0.5:
            continue
# --- OPTIONAL safety in main() loop, just before get_market_data(...) ---
        # Skip unknown/price-less stock-like tickers defensively
        if kind == 'stock' and not _symbol_has_prices(yf_symbol):
            continue

        # Check daily risk limit
        trade_risk = plan['stop_pct'] * plan['recommended_leverage']
        current_daily_risk = get_daily_risk()
        if current_daily_risk + trade_risk > DAILY_RISK_LIMIT:
            continue  # Skip this trade to stay within daily risk limit

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
                continue  # Still skip if exceeds

        results.append({
            'symbol': sym,
            'yf_symbol': yf_symbol,
            'kind': kind,
            'avg_sentiment': avg_sent,
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
            'candle_signal': market['candle_signal'],
            'ichimoku_signal': market['ichimoku_signal'],
            'volume_signal': market['volume_signal'],
            'fvg_signal': market['fvg_signal'],
            **plan
        })

    # sort by quality: rr then news_count
    results.sort(key=lambda r: (r['rr'], r['news_count']), reverse=True)

    if not results:
        message = 'No actionable forex, commodities, or indices trades found at this time.'
        print(message)
        send_telegram_message(message)
        return []

    message = f"Recommended trades:\nGenerated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Current session: {current_session}\nTotal articles: {len(articles)} | Symbols analyzed: {len(symbol_articles)} | Daily risk used: {get_daily_risk():.1%}\n"
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
        trade_line = f"Symbol: {r['symbol']} | Direction: {r['direction'].upper()} | Entry Price: {r['price']:.4f} | Stop Loss: {stop_price:.4f} | Take Profit: {target_price:.4f} | Leverage: {r['recommended_leverage']}"
        message += trade_line + "\n"
        print(trade_line)

    send_telegram_message(message)
    
    # Log trades
    log_trades(results)
    
    # Evaluate and learn every run
    evaluate_trades()
    
    return results

@lru_cache(maxsize=100)
def get_market_data(yf_symbol, kind='forex'):
    """Get recent price, volatility/ATR, pivots, S/R, psych levels, candle patterns, smart money volume, ICT FVG."""
    # Try yfinance first (primary)
    print(f"Attempting yfinance for {yf_symbol}...")
    data = _get_yfinance_data(yf_symbol, kind)
    if data:
        print(f"yfinance success for {yf_symbol}")
        return data
    else:
        print(f"yfinance failed or no data for {yf_symbol}")
    
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
    main()
