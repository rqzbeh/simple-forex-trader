# Forex, Commodities & Indices News Trading Bot

A Python-based automated trading bot that analyzes forex, commodities, and indices news and market data to generate trading signals. It combines sentiment analysis from news articles with technical indicators to recommend long/short positions on major currency pairs, commodities, and global indices with appropriate leverage and risk management.

## Features

- **News Aggregation**: Fetches forex, commodities, and indices-related news from NewsAPI and multiple RSS feeds from authoritative sources
- **Sentiment Analysis**: Uses TextBlob to analyze news sentiment, with boosts for central bank and economic data sources
- **Technical Analysis**: Incorporates Ichimoku Cloud, volume analysis, Fair Value Gaps (FVG), and candlestick patterns optimized for forex, commodities, and indices markets
- **Risk Management**: Calculates optimal stop losses, leverage, and risk-reward ratios for forex, commodities, and indices trading
- **Market Session Awareness**: Adjusts trading parameters based on current market session (Sydney, Tokyo, London, New York)
- **Telegram Notifications**: Sends trade recommendations via Telegram (optional)
- **Adaptive Learning**: Evaluates past trades and adjusts indicator weights for improved performance
- **Low Money Mode**: Optimized settings for smaller trading accounts

## Requirements

- Python 3.8 or higher
- NewsAPI account (free tier available)
- Internet connection for data fetching

## Dependencies

Install the required packages using pip:

```bash
pip install newsapi-python yfinance textblob requests
```

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/crypto-news-trading-bot.git
   cd crypto-news-trading-bot
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables

Set the following environment variables:

- `NEWS_API_KEY`: Your NewsAPI key (required)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (optional, for notifications)
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (optional, for notifications)

### Settings

Edit the constants in `main.py` to customize:

- `LOW_MONEY_MODE`: Set to `True` for smaller accounts (< $500)
- `MAX_LEVERAGE_CRYPTO`: Maximum leverage for crypto trades
- Risk parameters: `MIN_STOP_PCT`, `EXPECTED_RETURN_PER_SENTIMENT`, etc.

## Usage

Run the bot:

```bash
python main.py
```

The bot will:

1. Check the current market session
2. Fetch recent crypto news
3. Analyze sentiment and technical indicators
4. Generate trade recommendations
5. Send notifications via Telegram (if configured)
6. Log trades to `trade_log.json`
7. Evaluate performance and adjust parameters

## Output

The bot outputs recommended trades in the console and via Telegram, including:

- Symbol and direction (LONG/SHORT)
- Entry price
- Stop loss and take profit levels
- Recommended leverage
- Risk-reward ratio

## Files

- `main.py`: Main bot script
- `trade_log.json`: Log of recommended trades (created automatically)
- `README.md`: This file

## Risk Disclaimer

**IMPORTANT**: This software is for educational and research purposes only. It is not intended to provide financial advice, and trading forex, commodities, and indices involves significant risk of loss. Past performance does not guarantee future results. Always do your own research and consider consulting a financial advisor before making trading decisions.

The authors are not responsible for any financial losses incurred through the use of this software.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you find this project helpful, please give it a star on GitHub!
