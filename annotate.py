import os
import pandas
import re
import csv

def clean_and_split(sentence):
    """
    Take a sentence of voiceover. Clean up artefacts, special characters, comments etc. Split into lowercase words. Return.
    :param sentence:
    :return: a list of words
    """
    # filter out (CAPITALIZED WORD) and "CAPITALIZED WORD". These are not enunciated in the voiceover, but rather
    # indicate noise/words from the original audio track that get interspersed into the voice
    # Might contain special characters
    # Update: Capitalization etc are inconsistent. But all follow the pattern "text" and (text). Remove these instead
    crosstalk_pattern = '\(.*?\)|\".*?\"'
    # crosstalk_findings = re.findall(crosstalk_pattern, sentence)
    # print("Crosstalk: "+str(crosstalk_findings))
    sentence = re.sub(crosstalk_pattern, " ",  sentence)
    # splits into words, drops all special characters
    words = re.sub("[^\w]", " ",  sentence).split()
    # filter out all "s" and "ss" tokens. these are special voiceover items and not enunciated
    words = filter(lambda word: word is not "s" and word is not "ss", words)
    # Lowercase all words, because we want "Hello" to be the same as "hello"
    words = map(lambda word: word.lower(), words)
    # words might be an iterator at this point, we want a list
    words = list(words)
    return words


def gen_time_tag_dicts(words, t_start, t_end, method="constant"):
    """
    Given the words in sentence, the start/end times of that sentence, generate time-tagged words
    :param words: a list of words
    :param t_start: start time, absolute
    :param t_end: end time, absolute
    :return: a list of dicts, each dict contains: the word, its t_start, its t_end
    """
    words_dicts = []
    timediff = t_end - t_start
    word_time = timediff / len(words)
    if method == "constant":
        # idea: each word in a sentence uses the same amount of time, approximately
        for i, word in enumerate(words):
            words_dicts.append({"t_start": t_start+i*word_time,
                                "t_end": t_start+(i+1)*word_time,
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
                                "t_end": offset+time_fractions[i],
                                "text": word})
            offset += time_fractions[i]
    else:
        raise ValueError("unsupported value for the 'method' argument")
    return words_dicts

def time_tag_to_srt_time(seconds):
    """
    Take a timestamp in seconds, convert it to the SRT time format
    :param seconds:
    :return: string in SRT format
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    s, mill = divmod(s, 1)
    mill *= 1000
    template = "{:0>2d}:{:0>2d}:{:0>2d},{:0>3d}"
    return template.format(int(h), int(m), int(s), int(mill))


def word_to_srt(word, i):
    """
    Create one SRT entry from one time-tagged word and its index
    :param word:
    :param i:
    :return: SRT-formatted text string
    """
    t_start_str = time_tag_to_srt_time(word["t_start"])
    t_end_str = time_tag_to_srt_time(word["t_end"])
    template = "{}\n{} --> {}\n{}"
    return template.format(i, t_start_str, t_end_str, word["text"])


def word_list_to_srt(tagged_words):
    """
    Takes a list of time-tagged words and transforms them into srt-format
    :param tagged_words: list, each element a dict with keys "text", "t_start", "t_end"
    :return: srt-formatted text string for whole list
    """
    out = ""
    for i, word in enumerate(tagged_words):
        out += word_to_srt(word, i)
        out += "\n\n"
    return out

if __name__ == "__main__":
    ################################################################
    # setup
    ################################################################
    sentence_sources = ["narration", "dialogue"]
    sentences_path = {"narration": os.path.join(".", "..", "german_audio_description.csv"),
                  "dialogue": ""}
    narration = pandas.read_csv(filepath_or_buffer=sentences_path["narration"],
                            header=None,
                            names=["t_start", "t_end", "text"])

    ################################################################
    # create tagged word list
    ################################################################
    tagged_words = []
    for i in range(narration.shape[0]):
        row = narration.ix[i]
        words = clean_and_split(row["text"])
        words_dicts = gen_time_tag_dicts(words, row["t_start"], row["t_end"], method="weighted")
        tagged_words.extend(words_dicts)

    # for word in tagged_words:
    #     print("{}, {}, {}".format(word["t_start"], word["t_end"], word["text"]))

    ################################################################
    # write tagged word list to CSV
    ################################################################
    fout = "words_tagged.csv"
    with open(fout, "w") as fhandle:
        writer = csv.writer(fhandle, dialect="excel")
        for word in tagged_words:
            writer.writerow([word["t_start"], word["t_end"], word["text"]])

    ################################################################
    # write tagged word list to .srt for inspection
    ################################################################
    with open(os.path.join("..", "fgad", "fg_ad_seg0.mkv.srt"), "w") as fout:
        fout.write(word_list_to_srt(tagged_words))
        print(word_list_to_srt(tagged_words))