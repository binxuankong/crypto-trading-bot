HELP_TEMPLATE = """
:full_moon: Coins available:
{}
:information_source: Commands:
 - /help
 - /check [coin]
 - /add [coin]
 - /remove [coin]
 - /winner
 - /loser
 - /line [coin]
 - /candle [coin]
 - /reddit [subreddit]
"""

CHECK_TEMPLATE = """{} :full_moon: - {} :dollar:
:clock1: Current Price:\t{}
:clock5: 5min Average Price:\t{}
:clock11: 24hr Average Price:\t{}
:repeat: 24hr Price Change:\t{}
:heavy_division_sign: 24hr Price Change %:\t{}
:unlock: Open Price:\t\t{}
:chart_with_upwards_trend: High Price:\t\t{}
:chart_with_downwards_trend: Low Price:\t\t{}
:bar_chart: Volume:\t\t{}
"""

UP_TEMPLATE = """:heavy_exclamation_mark: :heavy_exclamation_mark: Heavy Swing Alert :heavy_exclamation_mark: :heavy_exclamation_mark:
{} UP :arrow_upper_right: :arrow_upper_right: :arrow_upper_right: :arrow_upper_right: :arrow_upper_right:
BY {}% :ox:
:unlock: Open Price:\t\t{}
:lock: Close Price:\t\t{}
:chart_with_upwards_trend: Price Difference:\t{}
"""

DOWN_TEMPLATE = """:heavy_exclamation_mark: :heavy_exclamation_mark: Heavy Swing Alert :heavy_exclamation_mark: :heavy_exclamation_mark:
{} DOWN :arrow_lower_right: :arrow_lower_right: :arrow_lower_right: :arrow_lower_right: :arrow_lower_right:
BY {}% :bear:
:unlock: Open Price:\t\t{}
:lock: Close Price:\t\t{}
:chart_with_downwards_trend: Price Difference:\t{}
"""

WIN_TEMPLATE = """:trophy: 24HR Top Gainers :trophy:
:one: {}
 - Last Price: {}
 - 24h % Change: {}%
:two: {}
 - Last Price: {}
 - 24h % Change: {}%
:three: {}
 - Last Price: {}
 - 24h % Change: {}%
:four: {}
 - Last Price: {}
 - 24h % Change: {}%
:five: {}
 - Last Price: {}
 - 24h % Change: {}%
"""

LOSE_TEMPLATE = """:money_with_wings: 24HR Top Losers :money_with_wings:
:one: {}
 - Last Price: {}
 - 24h % Change: {}%
:two: {}
 - Last Price: {}
 - 24h % Change: {}%
:three: {}
 - Last Price: {}
 - 24h % Change: {}%
:four: {}
 - Last Price: {}
 - 24h % Change: {}%
:five: {}
 - Last Price: {}
 - 24h % Change: {}%
"""

PORTFOLIO_HEADER = """:file_folder: Portfolio :open_file_folder:
:dollar: USDT:\t\t{}
"""

PORTFOLIO_BODY = """:full_moon: {}:\t\t{}
    \t\t\t@ ${}
"""

PORTFOLIO_FOOTER = """:moneybag: Networth:\t{}
:chart_with_upwards_trend: Net Growth:\t{}
:chart_with_upwards_trend: Percent Growth:\t{}%
"""

BUY_TEMPLATE = """{}
- BOUGHT {:.8f} {}
- \t@ {}
- NET: {}
"""

SELL_TEMPLATE = """{}
- SOLD {:.8f} {}
- \t@ {}
- NET: {}
"""
