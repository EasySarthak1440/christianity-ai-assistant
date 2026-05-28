import re

def clean_text(text):
    text = text.replace('\u25a1', ' ')   
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'\n', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'Page \d+', '', text)
    return text.strip()