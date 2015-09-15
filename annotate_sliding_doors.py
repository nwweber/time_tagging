__author__ = 'niklas'
import os
import pandas
import re
import csv
from aligners import UniformAligner
from aligners import WeightedAligner
from os.path import join as ospj


def parse_timestamp(line):
    # !TODO implement
    raise NotImplementedError
    return 42, 42


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


if __name__ == 'main':
    datadir = ospj("..", "..", "data")
    subdir = ospj(datadir, "in", "sd_subs")
    subpath = ospj(subdir, "sliding_doors_dummy.srt")