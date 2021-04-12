import pandas as pd
from datetime import datetime as dt
from binance.client import Client
from sqlalchemy import create_engine
from secrets import secrets

BINANCE_API_KEY = secrets['BINANCE_API_KEY']
BINANCE_SECRET_KEY = secrets['BINANCE_SECRET_KEY']
BRIDGE = 'USDT'
DATABASE_URL = secrets['DATABASE_URL']
TRANS_FEE = 0.0075

def get_holdings(user_id, engine):
    df = pd.read_sql_query('select * from "Transaction" where "Id" = {}'.format(user_id), engine)
    usd = df['USD'].sum()
    df = df.groupby('Coin')['Amount'].sum().reset_index()
    df.loc[len(df)] = ['USD', usd]
    return df

def invest_func(user_id, amount):
    df = pd.DataFrame(columns=['Id', 'Date', 'Action', 'USD', 'Coin', 'Amount', 'Price'])
    df.loc[len(df)] = [user_id, dt.now(), 'IN', amount, None, None, None]
    engine = create_engine(DATABASE_URL)
    add_transaction(user_id, 'IN', amount, None, None, None, engine)
    engine.dispose()

def buy_func(user_id, coin, amount, price):
    engine = create_engine(DATABASE_URL)
    df = get_holdings(user_id, engine)
    try:
        curr_amount = df.loc[df['Coin'] == 'USD', 'Amount'].item()
    except:
        return -1 * amount
    if amount is None:
        amount = curr_amount
    if curr_amount < amount:
        return curr_amount - amount
    new_amount = (amount / price) * (1 - TRANS_FEE)
    add_transaction(user_id, 'BUY', -1 * amount, coin, new_amount, price, engine)
    engine.dispose()
    return amount, new_amount

def sell_func(user_id, coin, amount, price):
    engine = create_engine(DATABASE_URL)
    df = get_holdings(user_id, engine)
    try:
        curr_amount = df.loc[df['Coin'] == coin, 'Amount'].item()
    except:
        return -1 * amount
    if amount is None:
        amount = curr_amount
    if curr_amount < amount:
        return curr_amount - amount
    new_amount = amount * price * (1 - TRANS_FEE)
    add_transaction(user_id, 'SELL', new_amount, coin, -1 * amount, price, engine)
    engine.dispose()
    return amount, new_amount

def portfolio_func(user_id):
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql_query('select * from "Transaction" where "Id" = {}'.format(user_id), engine)
    if len(df) < 1:
        return -1, -1
    engine.dispose()
    initial = df.loc[df['Action'] == 'IN', 'USD'].sum()
    curr_usd = df['USD'].sum()
    df = df.groupby('Coin')['Amount'].sum().reset_index()
    df['Price'] = df['Coin'].apply(lambda x: check_price(x))
    df['Value'] = df['Amount'] * df['Price']
    df.loc[len(df)] = ['USD', curr_usd, 1, curr_usd]
    return initial, df

def add_transaction(user_id, action, usd, coin, amount, price, engine):
    df = pd.DataFrame(columns=['Id', 'Date', 'Action', 'USD', 'Coin', 'Amount', 'Price'])
    df.loc[len(df)] = [user_id, dt.now(), action, usd, coin, amount, price]
    df.to_sql('Transaction', engine, index=False, if_exists='append')

def check_price(coin):
    symbol = coin + BRIDGE
    client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    t = client.get_ticker(symbol=symbol)
    return float(t['lastPrice'])
