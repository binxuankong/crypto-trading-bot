import emoji
import numpy as np
import pandas as pd

def emojize(text):
    return emoji.emojize(text, use_aliases=True)

def percent_diff(curr, prev):
    return (curr - prev) / prev

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