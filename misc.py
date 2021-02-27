import emoji

def emojize(text):
    return emoji.emojize(text, use_aliases=True)

def percent_diff(curr, prev):
    return (curr - prev) / prev