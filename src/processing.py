import re

import nltk

pattern_alpha = re.compile('[^a-zA-Z ]+')
pattern_alphanumeric = re.compile('[\W]+')
stop_words = set(nltk.corpus.stopwords.words('english'))
stemmer = nltk.stem.SnowballStemmer('english')


def clean_field(s: str) -> str:
    return s.replace('"', '').replace('\t', ' ').replace('\\', '\\\\').strip()


def clean_id(s: str) -> str:
    s = clean_field(s)
    s = pattern_alphanumeric.sub('_', s)
    return s


def clean_authors(s: str) -> str:
    s = ' '.join([w.strip().split('.')[-1]
                  for w in s.split(',')])
    s = clean_query(s)
    return s


def clean_title(s: str, min_title_word_length: int = 3) -> str:
    s = clean_query(s)
    s = ' '.join([w
                  for w in s.split()
                  if w not in stop_words and len(w) > min_title_word_length])
    return s


def clean_query(s: str) -> str:
    s = clean_field(s)
    s = s.lower()
    s = pattern_alpha.sub(' ', s)

    s = [stemmer.stem(w)
         for w in s.split()]
    s = ' '.join(s)
    return s
