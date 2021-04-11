import emoji
import numpy as np
import pandas as pd
import requests
import re
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
from matplotlib import pyplot as plt
from secrets import secrets

def get_coins():
    coins = []
    with open('coins.txt') as f:
        for line in f:
            coins.append(line.strip('\n'))
    return coins

def add_coin(coin):
    coins = get_coins()
    coins.append(coin)
    with open('coins.txt', 'w') as f:
        f.truncate(0)
        f.write('\n'.join(coins))
    return coins

def remove_coin(coin):
    coins = get_coins()
    coins.remove(coin)
    with open('coins.txt', 'w') as f:
        f.truncate(0)
        f.write('\n'.join(coins))
    return coins

def emojize(text):
    return emoji.emojize(text, use_aliases=True)

def percent_diff(curr, prev):
    return (curr - prev) / prev

# Chart functions
cols = ['OpenTime', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QuoteVolume', 'NumberTrades',
        'TakerBuyBaseVolume', 'TakerBuyQuoteVolume', 'Ignore']
timezone = 8
figsize = (16, 8)

def line_plot(coin, kline):
    # Format to df
    to_keep = ['CloseTime', 'Close']
    df = pd.DataFrame(kline, columns=cols)
    df = df[to_keep]
    df['CloseTime'] = pd.to_datetime(df['CloseTime'], unit='ms')
    df['CloseTime'] = df['CloseTime'] + pd.DateOffset(hours=timezone)
    df['Close'] = df['Close'].apply(pd.to_numeric, errors='coerce')
    # Plot
    plt.ioff()
    fig = plt.figure(figsize=figsize)
    plt.style.use('dark_background')
    ax = sns.lineplot(data=df, x='CloseTime', y='Close')
    date_fmt = mdates.DateFormatter('%m-%d %H:%M')
    ax.xaxis.set_major_formatter(date_fmt)
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_title(coin + '-USD Price Chart')
    # Save image
    file_name = coin + '_USD_LINE_CHART.png'
    plt.savefig(file_name)
    plt.close(fig)
    return file_name

def candle_plot(coin, kline):
    # Format to df
    num_cols = ['Open', 'High', 'Low', 'Close']
    to_keep = ['CloseTime', 'Open', 'High', 'Low', 'Close']
    df = pd.DataFrame(kline, columns=cols)
    df = df[to_keep]
    df['CloseTime'] = pd.to_datetime(df['CloseTime'], unit='ms')
    df['CloseTime'] = df['CloseTime'] + pd.DateOffset(hours=8)
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce')
    # Plot
    plt.ioff()
    fig = plt.figure(figsize=figsize)
    plt.style.use('dark_background')
    ax = fig.add_subplot()
    for _, row in df.iterrows():
        ax.vlines(x=row['CloseTime'], ymin=row['Low'], ymax=row['High'], color='black', linewidth=1)
        if row['Close'] > row['Open']:
            ax.vlines(x=row['CloseTime'], ymin=row['Open'], ymax=row['Close'], color='green', linewidth=4)
        elif row['Close'] < row['Open']:
            ax.vlines(x=row['CloseTime'], ymin=row['Close'], ymax=row['Open'], color='red', linewidth=4)
        else:
            ax.vlines(x=row['CloseTime'], ymin=row['Open'], ymax=row['Close'], color='black', linewidth=4)
    date_fmt = mdates.DateFormatter('%m-%d %H:%M')
    ax.xaxis.set_major_formatter(date_fmt)
    ax.set_title(coin + '-USD Price Chart')
    # Save image
    file_name = coin + '_USD_CANDLE_CHART.png'
    plt.savefig(file_name)
    plt.close(fig)
    return file_name

# Reddit Scraper
def get_reddit_trending(coins, sub='cryptocurrency', mode='hot'):
    auth = requests.auth.HTTPBasicAuth(secrets['REDDIT_API_KEY'], secrets['REDDIT_SECRET_KEY'])
    headers = {'User-Agent': 'MyBot/0.0.1'}
    data = {'grant_type': 'password', 'username': secrets['REDDIT_USERNAME'], 'password': secrets['REDDIT_PASSWORD']}
    res = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
    TOKEN = res.json()['access_token']
    headers = {**headers, **{'Authorization': f"bearer {TOKEN}"}}
    df = pd.DataFrame(columns=['coin', 'mentions'])
    df['coin'] = coins
    df['mentions'] = 0
    res = requests.get('https://oauth.reddit.com/r/{}/{}'.format(sub, mode), headers=headers, params={'limit': 100})
    for post in res.json()['data']['children']:
        text = post['data']['title'] + ' ' + post['data']['selftext']
        for coin in coins:
            pattern = r'\b{}\b'.format(coin)
            if re.search(pattern, text) is not None:
                df.loc[df['coin'] == coin, 'mentions'] += 1
    df = df.sort_values(by='mentions', ascending=False)
    return df.head(10).to_dict('records')

def get_reddit_daily(coins, comments=1000):
    auth = requests.auth.HTTPBasicAuth(secrets['REDDIT_API_KEY'], secrets['REDDIT_SECRET_KEY'])
    headers = {'User-Agent': 'MyBot/0.0.1'}
    data = {'grant_type': 'password', 'username': secrets['REDDIT_USERNAME'], 'password': secrets['REDDIT_PASSWORD']}
    res = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
    TOKEN = res.json()['access_token']
    headers = {**headers, **{'Authorization': f"bearer {TOKEN}"}}
    df = pd.DataFrame(columns=['coin', 'mentions'])
    df['coin'] = coins
    df['mentions'] = 0
    res = requests.get("https://oauth.reddit.com/r/cryptocurrency/hot", headers=headers, params={'limit': 10})
    for post in res.json()['data']['children']:
        if 'Daily Discussion' in post['data']['title']:
            daily_id = post['data']['id']
            break
    res2 = requests.get("https://oauth.reddit.com/r/cryptocurrency/comments/" + daily_id, headers=headers, params={'limit': comments})
    for post in res2.json()[1]['data']['children']:
        text = get_comments(post['data'])
        for coin in coins:
            pattern = r'\b{}\b'.format(coin)
            if re.search(pattern, text) is not None:
                df.loc[df['coin'] == coin, 'mentions'] += 1
    df = df.sort_values(by='mentions', ascending=False)
    return df.head(10).to_dict('records')

def get_comments(p_comment):
    if 'body' not in p_comment:
        return ''
    text = p_comment['body']
    replies = p_comment['replies']
    if len(replies) > 0:
        for c_comment in replies['data']['children']:
            text += ' ' + get_comments(c_comment['data'])
    return text
