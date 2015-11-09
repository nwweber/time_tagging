#! /usr/bin/python3

import os
import pandas
import re
import csv
from aligners import UniformAligner
from aligners import WeightedAligner
from os.path import join as ospj


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


def time_tag2seconds(time_tag, millisecond_separator="."):
    """
    Takes a time tag in the format hr:min:sec.mil and transforms it into seconds
    :param time_tag:
    :return:
    """
    hr, min, sec_mil = time_tag.split(":")
    sec, mil = sec_mil.split(millisecond_separator)
    return 3600 * int(hr) + 60 * int(min) + int(sec)


def remove_non_narration_strings(transcription_row):
    """
    Remove crosstalk from narration transcriptions. Crosstalk is annotations of noise or dialogue, which happens at the
    same time as voice-over narration, in the voice-over transcripts.
    Also remove 's' and 'ss' special strings, which are not enunciated.
    :param transcription_row: pandas data frame, cols: t_start, t_end, text
    :return: data frame, same cols, same text except no crosstalk and and no ' s '
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
    # filter out ' s ' ' Ss ' etc
    s_pattern = r'\b[sS]+\b'
    s_pattern_findings = re.findall(s_pattern, sentence)
    # if len(s_pattern_findings) > 0:
    # print("S-pattern: "+str(s_pattern_findings))
    sentence = re.sub(s_pattern, " ", sentence)
    transcription_row["text"] = sentence
    return transcription_row


def load_and_normalize_transcriptions(dirs):
    transcriptions_dir = ospj(dirs["data_in_dir"], "transcriptions")
    sentences_path = {"narration": ospj(transcriptions_dir, "german_audio_description.csv"),
                      "dialogue": ospj(transcriptions_dir, "german_dialog_20150211.csv")}

    # narration read-in. it contains some crosstalk (i.e. annotations of noise or of dialogue which happen at the same
    # time as the narration). we remove this.
    narration = pandas.read_csv(filepath_or_buffer=sentences_path["narration"],
                                header=None,
                                names=["t_start", "t_end", "text"])
    narration = narration.apply(remove_non_narration_strings, axis=1)

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
    # avprobe ../fgad/fg_ad_seg${i}.mkv 2>&1 | grep "Duration" | cut -d "," -f 1 | cut -d " " -f 4
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

    # These are the starting times for each section in stimulus time in seconds, as measured by aligning all sections
    # in Audacity in such a way that overlapping parts are only played once
    section_starts_stimulus = [
        0,
        885,
        1752,
        2612,
        3572,
        4480,
        5342,
        6412
    ]

    # we know when a section starts and how long it is, so we also know when it ends
    section_ends_stimulus = []
    for s_start, s_length in zip(section_starts_stimulus, lengths_secs):
        section_ends_stimulus.append(s_start + s_length)

    sections = []
    for s_start, s_end in zip(section_starts_stimulus, section_ends_stimulus):
        sections.append(all_transcriptions[(all_transcriptions["t_start"] >= s_start) &
                                           (all_transcriptions["t_end"] <= s_end)].copy())

    # transforming stimulus-time to section-time
    for s_start, section in zip(section_starts_stimulus, sections):
        section["t_start"] -= s_start
        section["t_end"] -= s_start
    return sections


def load_transcriptions_and_paths(dirs):
    """
    Gather all transcriptions for voice-over and narrations. Return them in one pandas DataFrame, sorted
    by t_start. If necessary, do pre-processing that differs between voice-over and narration.
    :return: list of tuples. each tuple has: pandas dataframes, columns: t_start, t_end, text, each row one block of transcriptions. times in
    seconds, referring to time within current section (1-8). one dataframe per section. every tuple also contains the path to an audio file correpsonding
    to these transcriptions
    """
    all_transcriptions = load_and_normalize_transcriptions(dirs)

    sections = cut_into_sections_and_normalize_times(all_transcriptions)

    audio_paths = [ospj(dirs["data_in_dir"], "fgad", "fg_ad_seg" + str(i)) for i in range(8)]

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
    """
    When calling this file as a stand-alone script we execute the code below.
    It takes the transcriptions (voiceover + dialogue) and the paths to the audio files and produces, per section,
    1) a .csv containing each word in the transcription and it's start and end time within this section (so the
    starting point of a section is always 0 seconds)
    2) a .srt file containing the same data in a different format. You can use these as subtitles to the .mkv media
    files in the fgad directory with your favourite video play. Use this to visually and quickyl inspect how good the
    alignment works
    """
    dirs = {}
    dirs["home_dir"] = ospj("..", "..")
    dirs["data_dir"] = ospj(dirs["home_dir"], "data")
    dirs["data_in_dir"], dirs["data_out_dir"] = ospj(dirs["data_dir"], "in"), ospj(dirs["data_dir"], "out")
    section_audio_path_pairs = load_transcriptions_and_paths(dirs)
    aligner = WeightedAligner()
    save_dir = ospj(dirs["data_out_dir"], "aligned_words")
    problematic_pairs = []
    for section_index, (section, audio_path) in enumerate(section_audio_path_pairs):
        fname = "fg_ad_seg" + str(section_index)
        csv_path, srt_path = ospj(save_dir, fname + ".csv"), ospj(save_dir, fname + ".srt")

        annotated_words = aligner.align(section, audio_path)
        for word_index in range(len(annotated_words) - 1):
            next_word_dict = annotated_words[word_index + 1]
            current_word_dict = annotated_words[word_index]
            if next_word_dict["t_start"] < current_word_dict["t_start"]:
                problematic_pairs.append((section_index, next_word_dict, current_word_dict))
        write_to_files(annotated_words, csv_path, srt_path)
    # below: report sanity violations in something of a table layout
    print("Sanity violations. Pairs of words for which the successor has an earlier starting time than the predecessor:")
    print("Total: {}".format(len(problematic_pairs)))
    print("{:>6} {:>10} {:>4} {:>4}".format("sec-id", "word", "t_start", "t_end"))
    print("-"*60)
    for (section_index, next_word_dict, current_word_dict) in problematic_pairs:
        if section_index != 0:
            continue
        print("-"*60)
        print("{:>6} {:>10} {:>4} {:>4}".format(section_index,
                                                current_word_dict["text"],
                                                current_word_dict["t_start"],
                                                current_word_dict["t_end"]))
        print("{:>6} {:>10} {:>4} {:>4}".format(section_index,
                                                next_word_dict["text"],
                                                next_word_dict["t_start"],
                                                next_word_dict["t_end"]))
    print("-"*60)