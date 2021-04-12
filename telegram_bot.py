import os
import logging
import telegram
import pytz
from datetime import datetime as dt
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from binance.client import Client
from binance.exceptions import BinanceAPIException
from secrets import secrets
from misc import *
from trade_func import *
from templates import *

TELEGRAM_CHAT_ID = secrets['TELEGRAM_CHAT_ID']
TELEGRAM_TOKEN = secrets['TELEGRAM_TOKEN']
BINANCE_API_KEY = secrets['BINANCE_API_KEY']
BINANCE_SECRET_KEY = secrets['BINANCE_SECRET_KEY']
BRIDGE = 'USDT'
TRANS_FEE = 0.0075
NOTIF_LIMIT = 2

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

# Telegram functions
def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def help(update, context):
    coins = ', '.join(get_coins())
    update.message.reply_text(emojize(HELP_TEMPLATE.format(coins)))

def check(update, context):
    try:
        coin = context.args[0].upper()
        get_coin_price(update, context, coin)
    except:
        update.message.reply_text(text='Please provide a valid coin.')

def add(update, context):
    coin = context.args[0].upper()
    if coin in get_coins():
        update.message.reply_text(text='{} already in coin list.'.format(coin))
        return
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    info = client.get_exchange_info()
    coins = [s['baseAsset'] for s in info['symbols']]
    coins = list(set(coins))
    if coin in coins:
        try:
            add_coin(coin)
            update.message.reply_text(text='{} added to coin list.'.format(coin))
        except:
            update.message.reply_text(text='Error encountered. Unable to add {} to coin list.'.format(coin))
    else:
        update.message.reply_text(text='{} not found in Binance. Please provide a valid coin'.format(coin))

def remove(update, context):
    coin = context.args[0].upper()
    if coin in get_coins():
        try:
            remove_coin(coin)
            update.message.reply_text(text='{} removed from coin list.'.format(coin))
        except:
            update.message.reply_text(text='Error encountered. Unable to remove {} to coin list.'.format(coin))
    else:
        update.message.reply_text(text='{} not found in coin list. Please provide a valid coin'.format(coin))

def winner(update, context):
    arg_list = get_top_change(reverse=True)
    update.message.reply_text(text=emojize(WIN_TEMPLATE.format(*arg_list)))

def loser(update, context):
    arg_list = get_top_change()
    update.message.reply_text(text=emojize(LOSE_TEMPLATE.format(*arg_list)))

def line(update, context):
    try:
        coin = context.args[0].upper()
        symbol = coin + BRIDGE
        client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
        kline = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=96)
    except:
        update.message.reply_text(text='Please provide a valid coin.')
        return
    file_name = line_plot(coin, kline)
    context.bot.send_photo(chat_id=update.message.chat_id, photo=open(file_name, 'rb'),
                           reply_to_message_id=update.message.message_id, allow_sending_without_reply=False)
    os.remove(file_name)

def candle(update, context):
    try:
        coin = context.args[0].upper()
        symbol = coin + BRIDGE
        client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
        kline = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=96)
    except:
        update.message.reply_text(text='Please provide a valid coin.')
        return
    file_name = candle_plot(coin, kline)
    context.bot.send_photo(chat_id=update.message.chat_id, photo=open(file_name, 'rb'),
                           reply_to_message_id=update.message.message_id, allow_sending_without_reply=False)
    os.remove(file_name)

def reddit(update, context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    info = client.get_exchange_info()
    coins = [s['baseAsset'] for s in info['symbols']]
    coins = list(set(coins))
    if len(context.args) > 0:
        try:
            subreddit = context.args[0]
            top_coins = get_reddit_trending(coins, context.args[0])
        except:
            update.message.reply_text('Please provide a valid subreddit.')
            return
    else:
        subreddit = 'CryptoCurrency'
        top_coins = get_reddit_trending(coins)
    text = ":alien: {} Top Mentions :alien:".format(subreddit)
    for i, coin in enumerate(top_coins):
        text += "\n{}. {} @ {}".format(i+1, coin['coin'], coin['mentions'])
    update.message.reply_text(text=emojize(text))

# Portfolio
def invest(update, context):
    try:
        amount = float(context.args[0])
        print(amount)
    except:
        update.message.reply_text(text='Please provide a valid amount to invest.')
        return
    user_id = update.message.chat.id
    res = invest_func(user_id, amount)
    update.message.reply_text(text='Successfully invested ${}.'.format(amount))

def valid_check(context):
    try:
        coin = context.args[0].upper()
        price = check_price(coin)
    except:
        return -1
    amount = None
    if len(context.args) > 1:
        try:
            amount = float(context.args[1])
            if amount < 0:
                return -2
        except:
            return -2
    return coin, price, amount

def buy(update, context):
    valid = valid_check(context)
    if isinstance(valid, tuple):
        coin, price, amount = valid
        user_id = update.message.chat.id
        amount, res = buy_func(user_id, coin, amount, price)
        if res >= 0:
            update.message.reply_text(text='Successfully bought {:.4f} {} (Priced @ {:.2f}) for ${:.2f}.'\
                                    .format(res, coin, price, amount))
        else:
            update.message.reply_text(text='Not enough USD for transaction. Missing ${:.2f}.'.format(-1 * res))
    elif valid == -1:
        update.message.reply_text(text='Please provide a valid coin')
    elif valid == -2:
        update.message.reply_text(text='Please provide a valid amount to buy.')

def sell(update, context):
    valid = valid_check(context)
    if isinstance(valid, tuple):
        coin, price, amount = valid
        user_id = update.message.chat.id
        amount, res = sell_func(user_id, coin, amount, price)
        if res >= 0:
            update.message.reply_text(text='Successfully sold {:.4f} {} (Priced @ {:.2f}) for ${:.2f}.'\
                                    .format(amount, coin, price, res))
        else:
            update.message.reply_text(text='Not enough {} for transaction. Missing {:.4f}.'.format(coin, -1 * res))
    elif valid == -1:
        update.message.reply_text(text='Please provide a valid coin')
    elif valid == -2:
        update.message.reply_text(text='Please provide a valid amount to buy.')

def portfolio(update, context):
    user_id = update.message.chat.id
    initial, df = portfolio_func(user_id)
    if initial == -1:
        update.message.reply_text(text='Portfolio not found.')
    else:
        curr_val = df['Value'].sum()
        profit = curr_val - initial
        percent = profit / initial * 100
        coins = df.loc[df['Amount'] > 0].to_dict('records')
        # Message
        portfolio_temp = """Portfolio:\t ${:.2f}\nInitial:\t ${:.2f}\nProfit:\t\t ${:.2f} ({:.2f}%)\nWallet:"""\
            .format(curr_val, initial, profit, percent)
        for coin in coins:
            portfolio_temp += "\n- {:.4f} {}\t ~ ${:.2f}".format(coin['Amount'], coin['Coin'], coin['Value'])
        update.message.reply_text(text=portfolio_temp)

# Schedule
def period_price_check(context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    for coin in get_coins():
        text = get_price_change(coin, client)
        if len(text) > 0:
            context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emojize(text))

def period_daily_check(context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    info = client.get_exchange_info()
    coins = [s['baseAsset'] for s in info['symbols']]
    coins = list(set(coins))
    top_coins = get_reddit_daily(coins)
    text = ":alien: r/cc Daily Top Mentions :alien:"
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
                                t['volume'])
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
    for coin in get_coins():
        symbol = coin + BRIDGE
        t = client.get_ticker(symbol=symbol)
        dict_list.append({'coin': coin, 'price': t['lastPrice'], 'price_change': t['priceChangePercent']})
    dict_list = sorted(dict_list, key=lambda i: float(i['price_change']), reverse=reverse)[:5]
    arg_list = [item for sublist in [list(d.values()) for d in dict_list] for item in sublist]
    return arg_list

def main():
    updater = Updater(token=TELEGRAM_TOKEN)
    # Bot commands
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('check', check))
    dp.add_handler(CommandHandler('add', add))
    dp.add_handler(CommandHandler('remove', remove))
    dp.add_handler(CommandHandler('winner', winner))
    dp.add_handler(CommandHandler('loser', loser))
    dp.add_handler(CommandHandler('line', line))
    dp.add_handler(CommandHandler('candle', candle))
    dp.add_handler(CommandHandler('reddit', reddit))
    dp.add_handler(CommandHandler('invest', invest))
    dp.add_handler(CommandHandler('buy', buy))
    dp.add_handler(CommandHandler('sell', sell))
    dp.add_handler(CommandHandler('portfolio', portfolio))
    # Job queue
    job_queue = updater.job_queue
    job_queue.run_repeating(period_price_check, interval=500, first=10)
    job_queue.run_repeating(period_daily_check, interval=3500, first=20)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
