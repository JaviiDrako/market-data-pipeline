from pprint import pprint

from src.clients.binance.client import BinanceClient
from src.config.settings import Settings
from src.extraction.binance_extractor import BinanceExtractor


def separator(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


settings = Settings()
client = BinanceClient()

extractor = BinanceExtractor(settings, client)


#
# CURRENT PRICE
#
separator("CURRENT PRICE")

prices = extractor.extract_current_price()

print(f"Records: {len(prices)}")
pprint(prices)


#
# 24H TICKER
#
separator("24H TICKER")

tickers = extractor.extract_ticker_24h()

print(f"Records: {len(tickers)}")
pprint(tickers)


#
# HISTORICAL KLINES
#
separator("HISTORICAL KLINES")

klines = extractor.extract_historical_klines()

print(f"Records: {len(klines)}")

print()
print("First record:")
pprint(klines[0])

print()
print("Keys:")
print(klines[0].keys())
