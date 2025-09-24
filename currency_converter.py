import requests
import json
from datetime import datetime, timedelta
from functools import lru_cache

class CurrencyConverter:
    """Handle currency conversions for multi-market trading data"""

    def __init__(self, base_currency='USD'):
        self.base_currency = base_currency
        self.market_currencies = {
            'US.': 'USD',
            'HK.': 'HKD',
            'SG.': 'SGD',
            'SH.': 'CNY',  # Shanghai
            'SZ.': 'CNY',  # Shenzhen
            'AU.': 'AUD',
            'CA.': 'CAD',
            'JP.': 'JPY',
            'MY.': 'MYR',
        }

        # Fallback static rates (foreign currency per 1 USD)
        self.static_rates = {
            'USD': 1.0,
            'HKD': 7.8,    # 1 USD = 7.8 HKD
            'SGD': 1.35,   # 1 USD = 1.35 SGD
            'CNY': 7.2,    # 1 USD = 7.2 CNY
            'AUD': 1.5,    # 1 USD = 1.5 AUD
            'CAD': 1.35,   # 1 USD = 1.35 CAD
            'JPY': 150.0,  # 1 USD = 150 JPY
            'MYR': 4.7,    # 1 USD = 4.7 MYR
        }

    def get_currency_from_code(self, stock_code):
        """Extract currency from stock code"""
        for market, currency in self.market_currencies.items():
            if stock_code.startswith(market):
                return currency
        return 'USD'  # Default to USD if unknown

    @lru_cache(maxsize=100)
    def get_fx_rate(self, from_currency, to_currency='USD', date=None):
        """Get FX rate with caching"""
        if from_currency == to_currency:
            return 1.0

        # Try to get live rates first, fallback to static rates
        try:
            rate = self._get_live_rate(from_currency, to_currency)
            if rate:
                return rate
        except:
            pass

        # Use static rates as fallback
        if from_currency in self.static_rates:
            # Static rates are foreign_currency/USD, so return as-is
            return self.static_rates[from_currency]

        return 1.0  # Default

    def _get_live_rate(self, from_currency, to_currency='USD'):
        """Attempt to get live FX rates (with error handling)"""
        if from_currency == to_currency:
            return 1.0

        # Using a free FX API (exchangerate-api.com)
        try:
            # Note: This is a free tier API call
            url = f"https://api.exchangerate-api.com/v4/latest/{to_currency}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                rates = data.get('rates', {})
                if from_currency in rates:
                    # API returns rates where base is to_currency (USD)
                    # rates[from_currency] gives us how many from_currency per 1 USD
                    # This is what we want: foreign_currency/USD
                    return rates[from_currency]
        except Exception as e:
            print(f"Live FX rate fetch failed for {from_currency}/{to_currency}: {e}")

        return None

    def convert_amount(self, amount, stock_code, target_currency='USD', trade_date=None):
        """Convert trading amount to target currency"""
        source_currency = self.get_currency_from_code(stock_code)

        if source_currency == target_currency:
            return amount

        rate = self.get_fx_rate(source_currency, target_currency, trade_date)
        # Rate is foreign_currency/USD (e.g., 7.8 HKD per 1 USD)
        # To convert FROM foreign TO USD: divide by rate
        return amount / rate

    def get_rate_info(self, stock_code):
        """Get rate info for debugging/display"""
        currency = self.get_currency_from_code(stock_code)
        rate = self.get_fx_rate(currency)
        return {
            'currency': currency,
            'rate_to_usd': rate,
            'is_static': currency in self.static_rates
        }

# Global converter instance
converter = CurrencyConverter()

def convert_to_usd(amount, stock_code, trade_date=None):
    """Quick conversion function"""
    return converter.convert_amount(amount, stock_code, 'USD', trade_date)