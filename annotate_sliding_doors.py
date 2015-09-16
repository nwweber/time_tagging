__author__ = 'niklas'
import os
import pandas
import re
import csv
from aligners import UniformAligner
from aligners import WeightedAligner
from os.path import join as ospj
import pprint
import annotate_forrest


def parse_timestamp(line):
    '''
    Takes a line of the form 'hh:mm::ss,mill --> hh:mm:ss,mill', extracts these timestamps and transforms them into
    seconds
    :param line:
    :return: a list with [t_start, t_end] in seconds since movie start
    '''
    t_start, t_end = line.split(' --> ')
    # could have written this with map or something else. but this is more expressive and i'll hopefully
    # still understand it in a few weeks
    return annotate_forrest.time_tag2seconds(t_start, ','), annotate_forrest.time_tag2seconds(t_end, ',')


def srtlines2dict(lines):
    # for clarity: these are the states that the 'state' variable indices. these are the building blocks of a srt file
    states = ["nr",
              "timestamp",
              "text"]
    state = 0
    all_blocks = []
    current_block = {}
    current_speech = ''
    for line in lines:
        # reading the block number. we don't care about it.
        if state == 0:
            state += 1
        # timestamp
        elif state == 1:
            current_block["t_start"], current_block["t_end"] = parse_timestamp(line.strip())
            state += 1
        # we want to read the text and combine contiguous lines into one block of text
        elif state == 2 and line != '\n':
            # part of the current speech block
            current_speech += line.strip() + " "
        elif state == 2:
            # empty line in-between blocks
            current_block["text"] = current_speech
            all_blocks.append(current_block)
            current_speech = ''
            current_block = {}
            state = 0
        else:
            # something went wrong
            raise ValueError('Something went wrong, state is out of bounds')
    return all_blocks


if __name__ == "__main__":
    datadir = ospj("..", "..", "data")
    subdir = ospj(datadir, "in", "sd_subs")
    subpath = ospj(subdir, "sliding_doors_dummy.srt")
    f = open(subpath, "r", encoding="cp1252")
    lines = f.readlines()
    dicts = srtlines2dict(lines)
    # 1st dict (index 0) just says 'Synchronized by ShooCat', not actual movie dialogue
    dicts = dicts[1:]
    pprint.pprint(dicts[:10])