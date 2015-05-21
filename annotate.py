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
    sentence = re.sub(crosstalk_pattern, " ", sentence)
    # splits into words, drops all special characters
    words = re.sub("[^\w]", " ", sentence).split()
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


def time_tag2seconds(time_tag):
    """
    Takes a time tag in the format hr:min:sec.mil and transforms it into seconds
    :param time_tag:
    :return:
    """
    hr, min, sec_mil = time_tag.split(":")
    sec, mil = sec_mil.split(".")
    return 3600*int(hr)+60*int(min)+int(sec)


def load_transcriptions():
    """
    Gather all transcriptions for voice-over and narrations. Return them in one pandas DataFrame, sorted
    by t_start. If necessary, do pre-processing that differs between voice-over and narration.
    :return: list of pandas dataframes, columns: t_start, t_end, text, each row one block of transcriptions. times in
    seconds, referring to time within current section (1-8). one dataframe per section
    """
    sentence_sources = ["narration", "dialogue"]
    sentences_path = {"narration": os.path.join("..", "transcriptions", "german_audio_description.csv"),
                      "dialogue": os.path.join("..", "transcriptions", "german_dialog_20150211.csv")}
    # narration read-in. it's pretty much in the right form already, except for textual pre-processing
    # which happens later in the pipeline
    narration = pandas.read_csv(filepath_or_buffer=sentences_path["narration"],
                                header=None,
                                names=["t_start", "t_end", "text"])
    # dialogue read-in + some pre-processing
    dialogue = pandas.read_csv(filepath_or_buffer=sentences_path["dialogue"],
                               header=None,
                               names=["t_start", "t_end", "person", "text"],
                               skiprows=1,
                               encoding="utf-8")
    # 'person' column not needed for rest of pipeline
    del dialogue["person"]
    # there are some entries in the dialogue transcriptions that have start/end times and a speaker but no
    # actual dialogue string. let's drop them here to prevent problems down the pipeline.
    dialogue = dialogue.dropna()
    # time stamps in dialogue data are milliseconds, convert to seconds to have one unit across data
    for ms_time_field in ["t_start", "t_end"]:
        dialogue[ms_time_field] /= 1000

    # rest of the pipeline assumes all transcriptions to be in one, sorted, data structure
    all_transcriptions = pandas.concat([narration, dialogue])
    all_transcriptions = all_transcriptions.sort(columns="t_start")
    # now we wish to emulate the procedure used to generate the 8 movie sections. this is:
    # 1: split into 7 non-consecutive parts, which cuts the movie down to ~2 hours
    # 2: concat these 7 parts, then split them into the 8 sections
    # Now: splitting into 7 parts
    # This is what the authors have to say about these parts:
    # Part Start time End time Start frame End frame
    # 0 00:00:00.00 00:21:32.12 0 32312
    # 1 00:24:13.24 00:38:31.23 36349 57798
    # 2 00:38:58.20 00:57:19.22 58470 85997
    # 3 00:59:31.17 01:18:14.00 89293 117351
    # 4 01:20:24.16 01:34:18.06 120616 141457
    # 5 01:37:14.19 01:41:30.19 145869 152269
    # 6 01:42:49.19 02:09:51.17 154244 194792
    # Table 1. Parts of the original “Forrest Gump” movie that comprise the actual stimulus. These seven
    # parts are concatenated and then split again into eight segments – one for each fMRI recording run.
    # Timestamps are given in HH:MM:SS.FRAME format, and refer to the 2002 DVD release (PAL-video,
    # 25 frames per second, DE103519SV).
    # (Hanke et al. 2014
    # "A high-resolution 7-Tesla fMRI dataset from complex natural stimulation with an audio movie", Nature)
    # I have recorded the 'start time' and 'end time' columns in 'split_starts.txt' and 'split_ends.txt'
    # respectively.
    # We use seconds as time-measurements throughout
    # Read in starting and ending positions of splits, convert them into seconds
    split_seconds = {}
    for location in ["starts", "ends"]:
        with open(os.path.join("..", "transcriptions", "split_" + location + ".txt"), "r") as f:
            split_seconds[location] = [time_tag2seconds(line.strip()) for line in f.readlines()]

    # Now to the actual splitting
    splits = []
    for i, (split_start, split_end) in enumerate(zip(split_seconds["starts"], split_seconds["ends"])):
        split_transcriptions = all_transcriptions[
            (all_transcriptions["t_start"] >= split_start) & (all_transcriptions["t_end"] <= split_end)]
        splits.append(split_transcriptions)

    #############################################################################################
    # WATCH OUT: Time-shifting might be wrong. Maybe times already refer to edited-movie-time
    # Then only normalizing per section might be necessary
    ##############################################################################################
    # we want new time-tags to be in edited-movie-time (i.e. going from 0 to 2 hrs)
    # so we have to shift later time tags forward to cover the 'holes' in-between the splits
    # the expression below lines up all split-ends with the start of the next split. last end point is omitted
    for i, (first_end, next_start) in enumerate(zip(split_seconds["ends"], split_seconds["starts"][1:])):
        offset = first_end - next_start
        # all splits with index > i have to be time-shifted
        for split in splits[i + 1:]:
            split["t_start"] += offset
            split["t_end"] += offset

    return splits


def create_tagged_word_list(transcriptions):
    """
    Take blockwise (e.g. sentene) transcriptions, each block having t_start and t_end, and turn it into
    a list of words, each word having t_start and t_end
    :param transcriptions:
    :return:
    """
    tagged_words = []
    for i in range(transcriptions.shape[0]):
        row = transcriptions.ix[i]
        words = clean_and_split(row["text"])
        words_dicts = gen_time_tag_dicts(words, row["t_start"], row["t_end"], method="weighted")
        tagged_words.extend(words_dicts)
    return tagged_words


if __name__ == "__main__":
    ################################################################
    # setup
    ################################################################
    transcriptions_per_section = load_transcriptions()

    ################################################################
    # create tagged word list
    ################################################################
    tagged_words_per_section = [create_tagged_word_list(transcriptions) for transcriptions in transcriptions_per_section]

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