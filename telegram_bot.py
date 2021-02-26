import logging
import telegram
import emoji
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from binance.client import Client
from binance.exceptions import BinanceAPIException
from secrets import secrets
from templates import *

TELEGRAM_CHAT_ID = secrets['TELEGRAM_CHAT_ID']
TELEGRAM_TOKEN = secrets['TELEGRAM_TOKEN']
BINANCE_API_KEY = secrets['BINANCE_API_KEY']
BINANCE_SECRET_KEY = secrets['BINANCE_SECRET_KEY']
BRIDGE = 'USDT'
COINS = ['BTC', 'ETH', 'LTC', 'XRP', 'BNB', 'ADA', 'BAT', 'FTM']
NOTIF_LIMIT = 2

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def help(update, context):
    coins = ', '.join(COINS)
    update.message.reply_text('Coins available: {}\nUse /check to check status of coin.'.format(coins))

def check(update, context):
    try:
        coin = context.args[0].upper()
        if coin in COINS:
            get_coin_price(update, context, coin)
        else:
            update.message.reply_text(text='Please provide a valid coin.')
    except:
        update.message.reply_text(text='Error encountered. Please provide a valid coin.')

def period_price_check(context):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    for coin in COINS:
        text = get_price_change(coin, client)
        if len(text) > 0:
            context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=emoji.emojize(text, use_aliases=True))

def get_coin_price(update, context, coin):
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    symbol = coin + BRIDGE
    avg_price = client.get_avg_price(symbol=symbol)['price']
    t = client.get_ticker(symbol=symbol)
    text = CHECK_TEMPLATE.format(coin, BRIDGE, t['lastPrice'], avg_price, t['weightedAvgPrice'], t['priceChange'], 
                                t['priceChangePercent'], t['openPrice'], t['highPrice'], t['lowPrice'],
                                t['prevClosePrice'])
    update.message.reply_text(text=emoji.emojize(text, use_aliases=True))

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

def main():
    updater = Updater(token=TELEGRAM_TOKEN)
    # Bot commands
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('check', check))
    # Job queue
    job_queue = updater.job_queue
    job_queue.run_repeating(period_price_check, interval=480, first=20) # Run every 8 minutes
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
