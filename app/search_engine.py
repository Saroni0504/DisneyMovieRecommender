from collections import defaultdict
from enum import Enum
from math import log
from string import punctuation

from nltk import pos_tag
from nltk.corpus import (
    stopwords,
    wordnet,
)
from nltk.stem import WordNetLemmatizer
from nltk.stem.snowball import SnowballStemmer


def remove_stopwords(input_string: str) -> str:
    stop_words = set(stopwords.words("english"))
    words = input_string.split()
    filtered_words = [word for word in words if word.lower() not in stop_words]
    filtered_text = " ".join(filtered_words)
    return filtered_text


def stemming(input_string: str) -> str:
    stemmer = SnowballStemmer("english", ignore_stopwords=False)
    words = input_string.split()  # alternative approach - from nltk.tokenize import word_tokenize
    stemmed_words = [stemmer.stem(word) for word in words]
    filtered_text = " ".join(stemmed_words)
    return filtered_text


def lemmatizing(input_string: str) -> str:
    # helper function to convert POS(Part Of Speech) tags
    # generated by pos_tags into a format recognized by WordNetLemmatizer
    def get_wordnet_pos(tag):
        if tag.startswith("J"):
            return wordnet.ADJ
        elif tag.startswith("V"):
            return wordnet.VERB
        elif tag.startswith("N"):
            return wordnet.NOUN
        elif tag.startswith("R"):
            return wordnet.ADV
        else:
            return wordnet.NOUN

    def lemmatize_passage(text):
        words = text.split()  # alternative approach - from nltk.tokenize import word_tokenize
        pos_tags = pos_tag(words)
        lemmatizer = WordNetLemmatizer()
        lemmatized_words = [
            lemmatizer.lemmatize(word, get_wordnet_pos(tag)) for word, tag in pos_tags
        ]
        lemmatized_sentence = " ".join(lemmatized_words)
        return lemmatized_sentence

    return lemmatize_passage(input_string)


# This code is partially taken from
# https://www.alexmolas.com/2024/02/05/a-search-engine-in-80-lines.html

def update_url_scores(old: dict[str, float], new: dict[str, float]):
    for url, score in new.items():
        if url in old:
            old[url] += score
        else:
            old[url] = score
    return old


def normalize_string(input_string: str) -> str:
    translation_table = str.maketrans(punctuation, " " * len(punctuation))
    string_without_punc = input_string.translate(translation_table)
    string_without_double_spaces = " ".join(string_without_punc.split())
    return string_without_double_spaces.lower()


class TextProcessing(str, Enum):
    Lemmatizer = "lemmatizer"
    LemmatizerPOS = "lemmetizer_pos"
    Stemmer = "stemmer"


class SearchEngine:
    def __init__(self,
                 k1: float = 1.5,
                 b: float = 0.75,
                 stopwords: bool = False,
                 text_proccessing: TextProcessing = None):

        self._index: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._documents: dict[str, str] = {}
        self.k1 = k1
        self.b = b
        self.stopwords = stopwords
        self.text_proccessing = text_proccessing

    @property
    def posts(self) -> list[str]:
        return list(self._documents.keys())

    @property
    def number_of_documents(self) -> int:
        return len(self._documents)

    @property
    def avdl(self) -> float:
        # todo: refactor this. it can be slow to compute it every time. compute it once and cache it
        return sum(len(d) for d in self._documents.values()) / len(self._documents)

    def idf(self, kw: str) -> float:
        N = self.number_of_documents
        n_kw = len(self.get_urls(kw))
        return log((N - n_kw + 0.5) / (n_kw + 0.5) + 1)

    def bm25(self, kw: str) -> dict[str, float]:
        result = {}
        idf_score = self.idf(kw)
        avdl = self.avdl
        for url, freq in self.get_urls(kw).items():
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (
                1 - self.b + self.b * len(self._documents[url]) / avdl
            )
            result[url] = idf_score * numerator / denominator
        return result

    def search(self, query: str) -> dict[str, float]:
        normalize_query = normalize_string(query)
        if self.text_proccessing is TextProcessing.Stemmer:
            _query = stemming(input_string=normalize_query)
        elif self.text_proccessing is TextProcessing.Lemmatizer:
            _query = lemmatizing(input_string=normalize_query)
        else:
            _query = normalize_query
        keywords = _query.split(" ")
        url_scores: dict[str, float] = {}
        for kw in keywords:
            kw_urls_score = self.bm25(kw)
            url_scores = update_url_scores(url_scores, kw_urls_score)
        return url_scores

    def index(self, url: str, content: str) -> None:
        self._documents[url] = content
        normalized_content = normalize_string(content)
        if self.stopwords:
            _content = remove_stopwords(input_string=normalized_content)
        if self.text_proccessing is TextProcessing.Stemmer:
            _content = stemming(input_string=normalized_content)
        elif self.text_proccessing is TextProcessing.Lemmatizer:
            _content = lemmatizing(input_string=normalized_content)
        else:
            _content = normalized_content
        words = _content.split(" ")
        for word in words:
            self._index[word][url] += 1

    def bulk_index(self, documents: list[tuple[str, str]]):
        for url, content in documents:
            self.index(url, content)

    def get_urls(self, keyword: str) -> dict[str, int]:
        keyword = normalize_string(keyword)
        return self._index[keyword]
