import logging
import telegram
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
COINS = ['BTC', 'ETH', 'LTC', 'XRP', 'BNB', 'ADA', 'BAT', 'FTM']
NOTIF_LIMIT = 2

# Portfolio
INITIAL = 600
PORTFOLIO = {'USDT': INITIAL, 'FTM': 0, 'BuyPrice': 0, 'SellPrice': 0, 'TransTime': dt.now(), 'TransFee': 0.001,
             'TradeLimit': 0.002}

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

def period_price_check(context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    for coin in COINS:
        text = get_price_change(coin, client)
        if len(text) > 0:
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
    symbol = 'FTM' + BRIDGE
    curr_price = float(client.get_ticker(symbol=symbol)['lastPrice'])
    if PORTFOLIO['USDT'] > 0:
        networth = PORTFOLIO['USDT']
    else:
        networth = PORTFOLIO['FTM'] * curr_price
    net_growth = networth - INITIAL
    percent_growth = net_growth / INITIAL * 100
    text = PORTFOLIO_TEMPLATE.format(PORTFOLIO['USDT'], PORTFOLIO['FTM'], curr_price, networth, net_growth, percent_growth)
    update.message.reply_text(emojize(text))

def buy(update, context):
    try:
        coin = context.args[0].upper()
        if coin == 'FTM':
            if PORTFOLIO['USDT'] > 0:
                symbol = coin + BRIDGE
                client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
                curr_price = float(client.get_ticker(symbol=symbol)['lastPrice'])
                buy_ftm(context, curr_price)
            else:
                update.message.reply_text(text='Not enough USDT.')
        else:
            update.message.reply_text(text='Please provide a valid coin.')
    except:
        update.message.reply_text(text='Error encountered. Please try again later.')

def sell(update, context):
    try:
        coin = context.args[0].upper()
        if coin == 'FTM':
            if PORTFOLIO['FTM'] > 0:
                symbol = coin + BRIDGE
                client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
                curr_price = float(client.get_ticker(symbol=symbol)['lastPrice'])
                sell_ftm(context, curr_price)
            else:
                update.message.reply_text(text='Not enough FTM.')
        else:
            update.message.reply_text(text='Please provide a valid coin.')
    except:
        update.message.reply_text(text='Error encountered. Please try again later.')

def scout_market(context):
    symbol = 'FTM' + BRIDGE
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    curr_price = float(client.get_ticker(symbol=symbol)['lastPrice'])
    if PORTFOLIO['FTM'] > 0:
        if percent_diff(curr_price, PORTFOLIO['BuyPrice']) > PORTFOLIO['TradeLimit']:
            sell_ftm(context, curr_price)
    else:
        if percent_diff(PORTFOLIO['SellPrice'], curr_price) > PORTFOLIO['TradeLimit']:
            buy_ftm(context, curr_price)
        elif (dt.now() - PORTFOLIO['TransTime']).seconds > 60 * 30:
            buy_ftm(context, curr_price)

def buy_ftm(context, price):
    PORTFOLIO['FTM'] = PORTFOLIO['USDT'] / price * (1 - PORTFOLIO['TransFee'])
    PORTFOLIO['USDT'] = 0
    PORTFOLIO['BuyPrice'] = price
    PORTFOLIO['TransTime'] = dt.now()
    text = BUY_TEMPLATE.format(PORTFOLIO['FTM'], price, PORTFOLIO['FTM'] * price)
    context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emojize(text))

def sell_ftm(context, price):
    PORTFOLIO['USDT'] = PORTFOLIO['FTM'] * price * (1 - PORTFOLIO['TransFee'])
    PORTFOLIO['SellPrice'] = price
    PORTFOLIO['TransTime'] = dt.now()
    text = SELL_TEMPLATE.format(PORTFOLIO['FTM'], price, PORTFOLIO['USDT'])
    PORTFOLIO['FTM'] = 0
    context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emojize(text))


def main():
    updater = Updater(token=TELEGRAM_TOKEN)
    # Bot commands
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('check', check))
    dp.add_handler(CommandHandler('winner', winner))
    dp.add_handler(CommandHandler('loser', loser))
    dp.add_handler(CommandHandler('portfolio', portfolio))
    dp.add_handler(CommandHandler('buy', buy))
    dp.add_handler(CommandHandler('sell', sell))
    # Job queue
    job_queue = updater.job_queue
    job_queue.run_repeating(period_price_check, interval=500, first=10)
    job_queue.run_repeating(scout_market, interval=300, first=10)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
