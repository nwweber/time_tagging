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

def gen_time_tag_dicts(words, t_start, t_end, method="constant", audio_path=""):
    """
    Given the words in sentence, the start/end times of that sentence, generate time-tagged words
    :param words: a list of words
    :param t_start: start time, absolute
    :param t_end: end time, absolute
    :param audio_path: audio track for this transcription
    :return: a list of dicts, each dict contains: the word, its t_start, its t_end
    """
    words_dicts = []
    timediff = t_end - t_start
    word_time = timediff / len(words)
    if method == "constant":
        # idea: each word in a sentence uses the same amount of time, approximately
        for i, word in enumerate(words):
            words_dicts.append({"t_start": t_start + i * word_time,
                                "t_end": t_start + (i + 1) * word_time,
                                "text": word})
    elif method == "weighted":
        # idea: each word word gets assigned a weight, determining the share of time it gets
        # here the weight is simply the number of characters
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
    else:
        raise ValueError("unsupported value for the 'method' argument")
    return words_dicts


def sentences2words(sentences):
    """
    In: pd series with sentences
    Out: pd series. same index. each entry: list of words in the corresponding sentence
    """
    raise NotImplementedError
    return words

class UniformAligner(AbstractAligner):
    """
    Gives equal time to each word in a text block
    """

    def align(self, transcriptions, audio_path=""):
        transcriptions["text"] = transcriptions["text"].apply(sentences2words)

        words_dicts = []
        timediff = t_end - t_start
        word_time = timediff / len(words)
        if method == "constant":
            # idea: each word in a sentence uses the same amount of time, approximately
            for i, word in enumerate(words):
                words_dicts.append({"t_start": t_start + i * word_time,
                                    "t_end": t_start + (i + 1) * word_time,
                                    "text": word})

