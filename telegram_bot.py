import logging
import telegram
import pytz
from datetime import datetime as dt
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from binance.client import Client
from binance.exceptions import BinanceAPIException
from secrets import secrets
from misc import *
from templates import *

TELEGRAM_CHAT_ID = secrets['TELEGRAM_CHAT_ID']
TELEGRAM_TOKEN = secrets['TELEGRAM_TOKEN']
BINANCE_API_KEY = secrets['BINANCE_API_KEY']
BINANCE_SECRET_KEY = secrets['BINANCE_SECRET_KEY']
BRIDGE = 'USDT'
COINS = ['BTC', 'ETH', 'LTC', 'XRP', 'BNB', 'ADA', 'BAT', 'OGN', 'FTM']
NOTIF_LIMIT = 2

# Portfolio
INITIAL = 200
TRANS_FEE = 0.001
PORTFOLIO = {'BTC': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]}, 'ETH': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]},
             'BNB': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]}, 'BAT': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]},
             'FTM': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]}}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

# Telegram functions
def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def help(update, context):
    coins = ', '.join(COINS)
    update.message.reply_text(emojize(HELP_TEMPLATE.format(COINS)))

def check(update, context):
    try:
        coin = context.args[0].upper()
        if coin in COINS:
            get_coin_price(update, context, coin)
        else:
            update.message.reply_text(text='Please provide a valid coin.')
    except:
        update.message.reply_text(text='Error encountered. Please provide a valid coin.')

def winner(update, context):
    arg_list = get_top_change(reverse=True)
    update.message.reply_text(text=emojize(WIN_TEMPLATE.format(*arg_list)))

def loser(update, context):
    arg_list = get_top_change()
    update.message.reply_text(text=emojize(LOSE_TEMPLATE.format(*arg_list)))

def reddit(update, context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    info = client.get_exchange_info()
    coins = [s['baseAsset'] for s in info['symbols']]
    coins = list(set(coins))
    if len(context.args) > 0:
        try:
            top_coins = get_reddit_trending(coins, context.args[0])
        except:
            update.message.reply_text('Please provide a valid sub.')
            return
    else:
        top_coins = get_reddit_trending(coins)
    text = ":alien: Reddit Top Mentions :alien:"
    for i, coin in enumerate(top_coins):
        text += "\n{}. {} @ {}".format(i+1, coin['coin'], coin['mentions'])
    update.message.reply_text(text=emojize(text))

def period_price_check(context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    for coin in COINS:
        text = get_price_change(coin, client)
        if len(text) > 0:
            context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emojize(text))

def period_reddit_check(context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    info = client.get_exchange_info()
    coins = [s['baseAsset'] for s in info['symbols']]
    coins = list(set(coins))
    top_coins = get_reddit_trending(coins)
    text = ":alien: Reddit Top Mentions :alien:"
    for i, coin in enumerate(top_coins):
        text += "\n{}. {} @ {}".format(i+1, coin['coin'], coin['mentions'])
    context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emojize(text))

def get_coin_price(update, context, coin):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    symbol = coin + BRIDGE
    avg_price = client.get_avg_price(symbol=symbol)['price']
    t = client.get_ticker(symbol=symbol)
    text = CHECK_TEMPLATE.format(coin, BRIDGE, t['lastPrice'], avg_price, t['weightedAvgPrice'], t['priceChange'], 
                                t['priceChangePercent'], t['openPrice'], t['highPrice'], t['lowPrice'],
                                t['prevClosePrice'])
    update.message.reply_text(text=emojize(text))

def get_price_change(coin, client):
    symbol = coin + BRIDGE
    kline = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=1)[0]
    open_price = float(kline[1])
    close_price = float(kline[4])
    price_diff = close_price - open_price
    price_diff_percent = price_diff / open_price * 100
    if abs(price_diff_percent) >= NOTIF_LIMIT:
        if price_diff_percent > 0:
            return UP_TEMPLATE.format(coin, price_diff_percent, open_price, close_price, price_diff)
        else:
            return DOWN_TEMPLATE.format(coin, abs(price_diff_percent), open_price, close_price, price_diff)
    else:
        return ''

def get_top_change(reverse=False):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    dict_list = []
    for coin in COINS:
        symbol = coin + BRIDGE
        t = client.get_ticker(symbol=symbol)
        dict_list.append({'coin': coin, 'price': t['lastPrice'], 'price_change': t['priceChangePercent']})
    dict_list = sorted(dict_list, key=lambda i: float(i['price_change']), reverse=reverse)[:5]
    arg_list = [item for sublist in [list(d.values()) for d in dict_list] for item in sublist]
    return arg_list

# Tradebot functions
def portfolio(update, context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    try:
        coin = context.args[0].upper()
        if coin in PORTFOLIO.keys():
            portfolio = PORTFOLIO[coin]
            symbol = coin + BRIDGE
            price = float(client.get_ticker(symbol=symbol)['lastPrice'])
            text = PORTFOLIO_HEADER.format(portfolio['USDT'])
            text += PORTFOLIO_BODY.format(coin, portfolio['COIN'], price)
            text += 'Past Transactions'
            for h in portfolio['HIST']:
                text += '\n' + h
            update.message.reply_text(emojize(text))
        else:
            update.message.reply_text(text='Please provide a valid coin.')
    except:
        total_fiat = 0
        total_networth = 0
        text = ""
        for p in PORTFOLIO:
            symbol = p + BRIDGE
            price = float(client.get_ticker(symbol=symbol)['lastPrice'])
            if PORTFOLIO[p]['USDT'] > 0:
                total_fiat += PORTFOLIO[p]['USDT']
                total_networth += PORTFOLIO[p]['USDT']
                text += PORTFOLIO_BODY.format(p, 0, price)
            else:
                total_networth += PORTFOLIO[p]['COIN'] * price
                text += PORTFOLIO_BODY.format(p, PORTFOLIO[p]['COIN'], price)
        net_growth = total_networth - (len(PORTFOLIO) * INITIAL)
        percent_growth = net_growth / (len(PORTFOLIO) * INITIAL) * 100
        text = PORTFOLIO_HEADER.format(total_fiat) + text + PORTFOLIO_FOOTER.format(total_networth, net_growth, percent_growth)
        update.message.reply_text(emojize(text))

def buy(update, context):
    try:
        coin = context.args[0].upper()
        if coin in PORTFOLIO.keys():
            if PORTFOLIO[coin]['USDT'] > 0:
                symbol = coin + BRIDGE
                client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
                price = float(client.get_ticker(symbol=symbol)['lastPrice'])
                buy_coin(context, coin, price)
            else:
                update.message.reply_text(text='Not enough USDT.')
        else:
            update.message.reply_text(text='Please provide a valid coin.')
    except:
        update.message.reply_text(text='Error encountered. Please try again later.')

def sell(update, context):
    try:
        coin = context.args[0].upper()
        if coin in PORTFOLIO.keys():
            if PORTFOLIO[coin]['COIN'] > 0:
                symbol = coin + BRIDGE
                client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
                price = float(client.get_ticker(symbol=symbol)['lastPrice'])
                sell_coin(context, coin, price)
            else:
                update.message.reply_text(text='Not enough {}.'.format(coin))
        else:
            update.message.reply_text(text='Please provide a valid coin.')
    except:
        update.message.reply_text(text='Error encountered. Please try again later.')

def scout_btc(context):
    scout_market(context, 'BTC')

def scout_eth(context):
    scout_market(context, 'ETH')

def scout_bnb(context):
    scout_market(context, 'BNB')

def scout_bat(context):
    scout_market(context, 'BAT')

def scout_ftm(context):
    scout_market(context, 'FTM')

def scout_market(context, coin):
    symbol = coin + BRIDGE
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    kline = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR)
    k, d, j = get_kdj1(kline)
    if PORTFOLIO[coin]['USDT'] > 0:
        if d < k:
            price = float(client.get_ticker(symbol=symbol)['lastPrice'])
            buy_coin(context, coin, price)
    else:
        if d > k:
            price = float(client.get_ticker(symbol=symbol)['lastPrice'])
            sell_coin(context, coin, price)

def buy_coin(context, coin, price):
    PORTFOLIO[coin]['COIN'] = PORTFOLIO[coin]['USDT'] / price * (1 - TRANS_FEE)
    PORTFOLIO[coin]['USDT'] = 0
    # text = BUY_TEMPLATE.format(PORTFOLIO[coin]['COIN'], coin, price, PORTFOLIO[coin]['COIN'] * price)
    # context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emojize(text))
    if len(PORTFOLIO[coin]['HIST']) >= 5:
        PORTFOLIO[coin]['HIST'].pop(0)
    tz = pytz.timezone('Asia/Kuala_Lumpur')
    text = BUY_TEMPLATE.\
        format(dt.now(tz).strftime('%Y/%m/%d %H:%M:%S'), PORTFOLIO[coin]['COIN'], coin, price, PORTFOLIO[coin]['COIN'] * price)
    PORTFOLIO[coin]['HIST'].append(text)

def sell_coin(context, coin, price):
    PORTFOLIO[coin]['USDT'] = PORTFOLIO[coin]['COIN'] * price * (1 - TRANS_FEE)
    # text = SELL_TEMPLATE.format(PORTFOLIO[coin]['COIN'], coin, price, PORTFOLIO[coin]['USDT'])
    PORTFOLIO[coin]['COIN'] = 0
    # context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emojize(text))
    if len(PORTFOLIO[coin]['HIST']) >= 5:
        PORTFOLIO[coin]['HIST'].pop(0)
    tz = pytz.timezone('Asia/Kuala_Lumpur')
    text = SELL_TEMPLATE.\
        format(dt.now(tz).strftime('%Y/%m/%d %H:%M:%S'), PORTFOLIO[coin]['COIN'], coin, price, PORTFOLIO[coin]['USDT'])
    PORTFOLIO[coin]['HIST'].append(text)


def main():
    updater = Updater(token=TELEGRAM_TOKEN)
    # Bot commands
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('check', check))
    dp.add_handler(CommandHandler('winner', winner))
    dp.add_handler(CommandHandler('loser', loser))
    dp.add_handler(CommandHandler('reddit', reddit))
    dp.add_handler(CommandHandler('portfolio', portfolio))
    dp.add_handler(CommandHandler('buy', buy))
    dp.add_handler(CommandHandler('sell', sell))
    # Job queue
    job_queue = updater.job_queue
    job_queue.run_repeating(period_price_check, interval=600, first=10)
    job_queue.run_repeating(period_reddit_check, interval=3600, first=20)
    job_queue.run_repeating(scout_btc, interval=600, first=15)
    job_queue.run_repeating(scout_eth, interval=600, first=30)
    job_queue.run_repeating(scout_bnb, interval=600, first=45)
    job_queue.run_repeating(scout_bat, interval=600, first=60)
    job_queue.run_repeating(scout_ftm, interval=600, first=75)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
