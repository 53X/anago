# -*- coding: utf-8 -*-
"""
Preprocessors.
"""
import itertools
import re

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.externals import joblib
from keras.utils.np_utils import to_categorical
from keras.preprocessing.sequence import pad_sequences

UNK = '<UNK>'
PAD = '<PAD>'


def normalize_number(text):
    return re.sub(r'[0-9０１２３４５６７８９]', r'0', text)


class StaticPreprocessor(BaseEstimator, TransformerMixin):

    def __init__(self, lowercase=True, num_norm=True,
                 char_feature=True, vocab_init=None):
        self._lowercase = lowercase
        self._num_norm = num_norm
        self._char_feature = char_feature
        self._vocab_init = vocab_init or {}
        self.word_dic = {PAD: 0, UNK: 1}
        self.char_dic = {PAD: 0, UNK: 1}
        self.label_dic = {PAD: 0}

    def fit(self, X, y=None):

        for w in set(itertools.chain(*X)) | set(self._vocab_init):

            # create character dictionary
            if self._char_feature:
                for c in w:
                    if c in self.char_dic:
                        continue
                    self.char_dic[c] = len(self.char_dic)

            # create word dictionary
            if self._lowercase:
                w = w.lower()
            if self._num_norm:
                w = normalize_number(w)
            self.word_dic[w] = len(self.word_dic)

        # create label dictionary
        for t in set(itertools.chain(*y)):
            self.label_dic[t] = len(self.label_dic)

        return self

    def transform(self, X, y=None):
        words = []
        chars = []
        for sent in X:
            word_ids = []
            char_ids = []
            for w in sent:
                if self._char_feature:
                    char_ids.append(self._get_char_ids(w))

                if self._lowercase:
                    w = w.lower()
                if self._num_norm:
                    w = normalize_number(w)
                word_id = self.word_dic.get(w, self.word_dic[UNK])
                word_ids.append(word_id)

            words.append(word_ids)
            chars.append(char_ids)

        if y is not None:
            y = np.array([[self.label_dic[t] for t in sent] for sent in y])

        if self._char_feature:
            inputs = [words, chars]
        else:
            inputs = [words]
        inputs = [np.array(inp) for inp in inputs]

        return (inputs, y) if y is not None else inputs

    def fit_transform(self, X, y=None, **fit_params):
        return self.fit(X, y).transform(X, y)

    def inverse_transform(self, docs):
        id2label = {i: t for t, i in self.label_dic.items()}

        return [[id2label[t] for t in doc] for doc in docs]

    def _get_char_ids(self, word):
        return [self.char_dic.get(c, self.char_dic[UNK]) for c in word]

    def save(self, file_path):
        joblib.dump(self, file_path)

    @classmethod
    def load(cls, file_path):
        p = joblib.load(file_path)

        return p


class DynamicPreprocessor(BaseEstimator, TransformerMixin):

    def __init__(self, n_labels):
        self.n_labels = n_labels

    def transform(self, X, y=None):
        words, chars = X
        words = pad_sequences(words, padding='post')
        chars = pad_nested_sequences(chars)

        if y is not None:
            y = pad_sequences(y, padding='post')
            y = to_categorical(y, self.n_labels)
        sents = [words, chars]

        return (sents, y) if y is not None else sents

    def save(self, file_path):
        joblib.dump(self, file_path)

    @classmethod
    def load(cls, file_path):
        p = joblib.load(file_path)

        return p


def pad_nested_sequences(sequences, dtype='int32'):
    """Pads nested sequences to the same length.

    This function transforms a list of list sequences
    into a 3D Numpy array of shape `(num_samples, max_sent_len, max_word_len)`.

    Args:
        sequences: List of lists of lists.
        dtype: Type of the output sequences.

    # Returns
        x: Numpy array.
    """
    maxlen_sent = 0
    maxlen_word = 0
    for sent in sequences:
        maxlen_sent = max(len(sent), maxlen_sent)
        for word in sent:
            maxlen_word = max(len(word), maxlen_word)

    x = np.zeros((len(sequences), maxlen_sent, maxlen_word)).astype(dtype)
    for i, sent in enumerate(sequences):
        for j, word in enumerate(sent):
            x[i, j, :len(word)] = word

    return x
