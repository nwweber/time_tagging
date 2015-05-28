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


# def create_tagged_word_list(transcriptions, audio_path, method="weighted"):
#     """
#     Take blockwise (e.g. sentence) transcriptions, each block having t_start and t_end, and turn it into
#     a list of words, each word having t_start and t_end
#     :param transcriptions:
#     :return:
#     """
#     tagged_words = []
#     for i in range(transcriptions.shape[0]):
#         row = transcriptions.ix[i]
#         words = clean_and_split(row["text"])
#         words_dicts = gen_time_tag_dicts(words, row["t_start"], row["t_end"], method=method, audio_path=audio_path)
#         tagged_words.extend(words_dicts)
#     return tagged_words

class UniformAligner(AbstractAligner):
    """
    Gives equal time to each word in a text block
    """

    def align(self, transcriptions, audio_path=""):



