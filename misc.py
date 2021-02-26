import emoji

def emojize(text):
    return emoji.emojize(text, use_aliases=True)