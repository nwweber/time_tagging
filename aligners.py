import re

__author__ = 'niklas'
"""
Containing different classes implementing the align-interface.

Writing your own:
Recommended method:
    Make your own class
    Inherit from AbstractAligner
    Implement align() method
    This would look something like this:
        class MyAlignerWhichDoesCoolStuff(AbstractAligner):
            def align(self, transcriptions, audio_path=""):
                [Logic]
                return words_dicts
    Then, to use your own aligner:
        Go into 'annotate_forrest.py'
        Make your aligner available by adding the following to the top of the file:
            from aligners import MyAlignerWhichDoesCoolStuff
        In the if __name__ == "__main__" block:
            Find the "aligner = ..." line
            Change it to "aligner = MyAlignerWhichDoesCoolStuff()"

However, inheriting from AbstractAligner is not a necessity. As long as your class has an align() class with the
right signature you are good to go
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

    @staticmethod
    def extract_row_data(row):
        """
        Given a row of transcription data, return the fields and the time difference. Purely for convenience.
        """
        t_start = row["t_start"]
        t_end = row["t_end"]
        words = AbstractAligner.sentences2words(row["text"])
        timediff = t_end - t_start
        return t_start, t_end, timediff, words

    @staticmethod
    def sentences2words(sentence):
        """
        In: String possibly containing multiple sentences and special characters
        Out: List of words
        """
        # splits into words, drops all special characters
        words = re.sub("[^\w]", " ", sentence).split()
        words = list(words)
        return words


class AbstractRowBasedAligner(AbstractAligner):
    """Inherit from this if your aligner does things row-by-row"""

    @abc.abstractmethod
    def row2words_dicts(self, row):
        return

    def align(self, transcriptions, audio_path=""):
        words_dicts = []
        for i in range(transcriptions.shape[0]):
            row = transcriptions.iloc[i]
            words_dicts.extend(self.row2words_dicts(row))
        for word_dict in words_dicts:
            word_dict["text"] = word_dict["text"].lower()
        return words_dicts


class UniformAligner(AbstractRowBasedAligner):
    """
    Gives equal time to each word in a text block
    """

    def row2words_dicts(self, row):
        print("doing uniform row alignment")
        words_dicts = []
        t_start, t_end, timediff, words = self.extract_row_data(row)
        word_time = timediff / len(words)
        # idea: each word in a sentence uses the same amount of time, approximately
        for i, word in enumerate(words):
            words_dicts.append({"t_start": t_start + i * word_time,
                                "t_end": t_start + (i + 1) * word_time,
                                "text": word})
        return words_dicts


class WeightedAligner(AbstractRowBasedAligner):
    """
    Time in a block is divided according to word weight
    """

    def row2words_dicts(self, row):
        words_dicts = []
        t_start, t_end, timediff, words = self.extract_row_data(row)
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
            # print("word {}, time fraction: {}".format(word, time_fractions[i]))
        return words_dicts