import re

__author__ = 'niklas'
"""
Containing different classes implementing the align-interface
"""

import abc


class AbstractAligner():
    """
    Class defining the align interface. Inherit from this, implement align method in sublcasses
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def align(self, transcriptions, audio_path=""):
        """
        Given a pandas DataFrame with transcriptions (columns: t_start, t_end, text) and possibly a path
        to a matching audio file, return a list of time-tagged words
        :param transcriptions: pd data frame, columns: t_start, t_end, text. text can coin multiple sentences per row
        :param audio_path: possible path to audio data
        :return: list, each element a dict with t_start, t_end, text, in which 'text' is only one word. words are all
        lowercase
        """
        return


def sentences2words(sentence):
    """
    In: String possibly containing multiple sentences and special characters
    Out: List of words
    """
    # splits into words, drops all special characters
    words = re.sub("[^\w]", " ", sentence).split()
    words = list(words)
    return words


class UniformAligner(AbstractAligner):
    """
    Gives equal time to each word in a text block
    """

    def row2words_dicts(self, row):
        words_dicts = []
        t_start = row["t_start"]
        t_end = row["t_end"]
        words = sentences2words(row["text"])
        timediff = t_end - t_start
        word_time = timediff / len(words)
        # idea: each word in a sentence uses the same amount of time, approximately
        for i, word in enumerate(words):
            words_dicts.append({"t_start": t_start + i * word_time,
                                "t_end": t_start + (i + 1) * word_time,
                                "text": word})
        return words_dicts

    def align(self, transcriptions, audio_path=""):
        words_dicts = []
        for i in range(transcriptions.shape[0]):
            row = transcriptions.iloc[i]
            words_dicts.extend(self.row2words_dicts(row))
        for word_dict in words_dicts:
            word_dict["text"] = word_dict["text"].lower()
        return words_dicts


class WeightedAligner(AbstractAligner):
    """
    Time in a block is divided according to word weight
    """

    def row2words_dicts(self, row):

        weights = [len(word) for word in words]
        total = sum(weights)
        weight_fractions = [weight / total for weight in weights]
        time_fractions = [weight_fraction * timediff for weight_fraction in weight_fractions]
        offset = t_start
        for i, word in enumerate(words):
            words_dicts.append({"t_start": offset,
                                "t_end": offset + time_fractions[i],
                                "text": word})
            offset += time_fractions[i]

        words_dicts = []
        t_start = row["t_start"]
        t_end = row["t_end"]
        words = sentences2words(row["text"])
        timediff = t_end - t_start
        word_time = timediff / len(words)
        # idea: each word in a sentence uses the same amount of time, approximately
        for i, word in enumerate(words):
            words_dicts.append({"t_start": t_start + i * word_time,
                                "t_end": t_start + (i + 1) * word_time,
                                "text": word})
        return words_dicts

    def align(self, transcriptions, audio_path=""):
        words_dicts = []
        for i in range(transcriptions.shape[0]):
            row = transcriptions.iloc[i]
            words_dicts.extend(self.row2words_dicts(row))
        for word_dict in words_dicts:
            word_dict["text"] = word_dict["text"].lower()
        return words_dicts