import os
import pandas
import re
import csv
from aligners import UniformAligner

# def clean_and_split(sentence):
#     """
#     Take a sentence of voiceover. Clean up artifacts, special characters, comments etc. Split into lowercase words. Return.
#     :param sentence:
#     :return: a list of words
#     """
#     # filter out (CAPITALIZED WORD) and "CAPITALIZED WORD". These are not enunciated in the voiceover, but rather
#     # indicate noise/words from the original audio track that get interspersed into the voice
#     # Might contain special characters
#     # Update: Capitalization etc are inconsistent. But all follow the pattern "text" and (text). Remove these instead
#     crosstalk_pattern = '\(.*?\)|\".*?\"'
#     # crosstalk_findings = re.findall(crosstalk_pattern, sentence)
#     # print("Crosstalk: "+str(crosstalk_findings))
#     sentence = re.sub(crosstalk_pattern, " ", sentence)
#     # splits into words, drops all special characters
#     words = re.sub("[^\w]", " ", sentence).split()
#     # filter out all "s" and "ss" tokens. these are special voiceover items and not enunciated
#     words = filter(lambda word: word is not "s" and word is not "ss", words)
#     # Lowercase all words, because we want "Hello" to be the same as "hello"
#     words = map(lambda word: word.lower(), words)
#     # words might be an iterator at this point, we want a list
#     words = list(words)
#     return words


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
    return 3600 * int(hr) + 60 * int(min) + int(sec)


def remove_crosstalk(transcription_row):
    """
    Remove crosstalk from narration transcriptions. Crosstalk is annotations of noise or dialogue, which happens at the
    same time as voice-over narration, in the voice-over transcripts.
    :param transcription_row: pandas data frame, cols: t_start, t_end, text
    :return: data frame, same cols, same text except no crosstalk
    """
    sentence = transcription_row["text"]
    # filter out (CAPITALIZED WORD) and "CAPITALIZED WORD". These are not enunciated in the voiceover, but rather
    # indicate noise/words from the original audio track that get interspersed into the voice
    # Might contain special characters
    # Update: Capitalization etc are inconsistent. But all follow the pattern "text" and (text). Remove these instead
    crosstalk_pattern = '\(.*?\)|\".*?\"'
    # crosstalk_findings = re.findall(crosstalk_pattern, sentence)
    # print("Crosstalk: "+str(crosstalk_findings))
    sentence = re.sub(crosstalk_pattern, " ", sentence)
    transcription_row["text"] = sentence
    return transcription_row


def load_and_normalize_transcriptions():
    sentences_path = {"narration": os.path.join("..", "transcriptions", "german_audio_description.csv"),
                      "dialogue": os.path.join("..", "transcriptions", "german_dialog_20150211.csv")}

    # narration read-in. it contains some crosstalk (i.e. annotations of noise or of dialogue which happen at the same
    # time as the narration). we remove this.
    narration = pandas.read_csv(filepath_or_buffer=sentences_path["narration"],
                                header=None,
                                names=["t_start", "t_end", "text"])
    narration = narration.apply(remove_crosstalk, axis=1)

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

    all_transcriptions = pandas.concat([narration, dialogue])
    all_transcriptions = all_transcriptions.sort(columns="t_start")
    return all_transcriptions


def cut_into_sections_and_normalize_times(all_transcriptions):
    """
    :param all_transcriptions: One big pandas Dataframe with all transcriptions, having fields t_start, t_end, text
    :return: a list of 8 smaller data frames, having the same fields, with t_start and t_end normalized within this section
    """
    # These are the lenghts of the audio segments 0 - 7, as measured by:
    # for i in `seq 0 7`; do
    #    avprobe ../fgad/fg_ad_seg${i}.mkv 2>&1 | grep "Duration" | cut -d "," -f 1 | cut -d " " -f 4
    # done
    lengths_hms = ["00:15:03.04",
                   "00:14:43.08",
                   "00:14:37.08",
                   "00:16:17.08",
                   "00:15:25.08",
                   "00:14:39.09",
                   "00:18:07.08",
                   "00:11:14.44"]
    lengths_secs = map(time_tag2seconds, lengths_hms)
    boundary = 0
    boundaries = []
    for length in lengths_secs:
        boundary += length
        boundaries.append(boundary)
    sections = []
    for i, boundary in enumerate(boundaries):
        if i == 0:
            prev = 0
        else:
            prev = boundaries[i - 1]
        sections.append(
            all_transcriptions[(all_transcriptions["t_start"] >= prev) & (all_transcriptions["t_start"] <= boundary)])
    return sections


def load_transcriptions_and_paths():
    """
    Gather all transcriptions for voice-over and narrations. Return them in one pandas DataFrame, sorted
    by t_start. If necessary, do pre-processing that differs between voice-over and narration.
    :return: list of tuples. each tuple has: pandas dataframes, columns: t_start, t_end, text, each row one block of transcriptions. times in
    seconds, referring to time within current section (1-8). one dataframe per section. every tuple also contains the path to an audio file correpsonding
    to these transcriptions
    """
    all_transcriptions = load_and_normalize_transcriptions()

    sections = cut_into_sections_and_normalize_times(all_transcriptions)

    audio_paths = [os.path.join("..", "fgad", "fg_ad_seg" + str(i)) for i in range(8)]

    return zip(sections, audio_paths)


def write_to_csv(section, csv_path):
    fout = csv_path
    with open(fout, "w") as fhandle:
        writer = csv.writer(fhandle, dialect="excel")
        for word in section:
            writer.writerow([word["t_start"], word["t_end"], word["text"]])


def write_to_srt(section, srt_path):
    with open(srt_path, "w") as fout:
        fout.write(word_list_to_srt(section))


def write_to_files(section, csv_path, srt_path):
    """
    Take a a list of time-tagged words. Write it to CSV and to SRT.
    :param section:
    :param audio_path:
    :return:
    """
    write_to_csv(section, csv_path)
    write_to_srt(section, srt_path)


if __name__ == "__main__":
    section_audio_path_pairs = load_transcriptions_and_paths()
    aligner = UniformAligner()
    for i, (section, audio_path) in enumerate(section_audio_path_pairs):
        annotated_words = aligner.align(section, audio_path)
        fname = "fg_ad_seg" + str(i)
        csv_path = os.path.join("..", "aligned_words", fname + ".csv")
        srt_path = os.path.join("..", "fgad", fname + ".srt")
        write_to_files(section, csv_path, srt_path)