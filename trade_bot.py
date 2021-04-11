# Portfolio
INITIAL = 200
TRANS_FEE = 0.001
PORTFOLIO = {'BTC': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]}, 'ETH': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]},
             'BNB': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]}, 'BAT': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]},
             'FTM': {'USDT': INITIAL, 'COIN': 0, 'HIST':[]}}

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
    if len(PORTFOLIO[coin]['HIST']) >= 5:
        PORTFOLIO[coin]['HIST'].pop(0)
    tz = pytz.timezone('Asia/Kuala_Lumpur')
    text = BUY_TEMPLATE.\
        format(dt.now(tz).strftime('%Y/%m/%d %H:%M:%S'), PORTFOLIO[coin]['COIN'], coin, price, PORTFOLIO[coin]['COIN'] * price)
    PORTFOLIO[coin]['HIST'].append(text)

def sell_coin(context, coin, price):
    PORTFOLIO[coin]['USDT'] = PORTFOLIO[coin]['COIN'] * price * (1 - TRANS_FEE)
    PORTFOLIO[coin]['COIN'] = 0
    if len(PORTFOLIO[coin]['HIST']) >= 5:
        PORTFOLIO[coin]['HIST'].pop(0)
    tz = pytz.timezone('Asia/Kuala_Lumpur')
    text = SELL_TEMPLATE.\
        format(dt.now(tz).strftime('%Y/%m/%d %H:%M:%S'), PORTFOLIO[coin]['COIN'], coin, price, PORTFOLIO[coin]['USDT'])
    PORTFOLIO[coin]['HIST'].append(text)

# TA functions
def get_kdj1(kline):
    cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QuoteVolume', 'NumberTrades',
        'TakerBuyBaseVolume', 'TakerBuyQuoteVolume', 'Ignore']
    num_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    df = pd.DataFrame(kline, columns=cols)
    df = df.drop(columns=['CloseTime', 'QuoteVolume', 'NumberTrades', 'TakerBuyBaseVolume', 'TakerBuyQuoteVolume', 'Ignore'])
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce')
    low_list = df['Low'].rolling(9, min_periods=9).min()
    low_list.fillna(value=df['Low'].expanding().min(), inplace=True)
    high_list = df['High'].rolling(9, min_periods=9).max()
    high_list.fillna(value=df['High'].expanding().max(), inplace=True)
    rsv = (df['Close'] - low_list) / (high_list - low_list) * 100
    df_kdj = df.copy()
    df_kdj['K'] = pd.DataFrame(rsv).ewm(com=2).mean()
    df_kdj['D'] = df_kdj['K'].ewm(com=2).mean()
    df_kdj['J'] = 3 * df_kdj['K'] - 2 * df_kdj['D']
    return df_kdj.tail(1)['K'].item(), df_kdj.tail(1)['D'].item(), df_kdj.tail(1)['J'].item()


def get_kdj2(kline, k_periods=9, d_periods=3):
    k_periods -= 1
    array_open = np.array([k[1] for k in kline]).astype(np.float)
    array_high = np.array([k[2] for k in kline]).astype(np.float)
    array_low = np.array([k[3] for k in kline]).astype(np.float)
    array_close = np.array([k[4] for k in kline]).astype(np.float)
    array_volume = np.array([k[5] for k in kline]).astype(np.float)
    array_highest = get_highest_values(array_high, k_periods)
    array_lowest = get_lowest_values(array_low, k_periods)
    # K Value
    K_value = []
    for i in range(k_periods, array_close.size):
        k = ((array_close[i] - array_lowest[i - k_periods]) * 100 /
             (array_highest[i - k_periods] - array_lowest[i - k_periods]))
        K_value.append(k)
    # D Value
    y = 0
    D_value = [None, None]
    mean = 0
    for x in range(0, len(K_value) - d_periods + 1):
        this_sum = 0
        for i in range(0, d_periods):
            this_sum += K_value[y]
            y += 1
        mean = this_sum / d_periods
        D_value.append(mean)
        y -= (d_periods - 1)
    # J Value
    J_value = [None, None]
    for i in range(0, len(D_value) - d_periods + 1):
        j = (D_value[i + 2] * 3) - (K_value[i + 2] * 2)
        J_value.append(j)
    return K_value, D_value, J_value

def get_highest_values(array_high, k_periods):
    y = 0
    z = 0
    array_highest = []
    for x in range(0, array_high.size - k_periods):
        z = array_high[y]
        for j in range(0, k_periods):
            if z < array_high[y+1]:
                z = array_high[y+1]
            y += 1
        array_highest.append(z)
        y -= (k_periods - 1)
    return array_highest

def get_lowest_values(array_low, k_periods):
    y = 0
    z = 0
    array_lowest = []
    for x in range(0, array_low.size - k_periods):
        z = array_low[y]
        for j in range(0, k_periods):
            if z > array_low[y+1]:
                z = array_low[y+1]
            y += 1
        array_lowest.append(z)
        y -= (k_periods - 1)
    return array_lowest
