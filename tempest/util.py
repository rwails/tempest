#!/usr/bin/env python3

import datetime
import os
import re

def dict_keys_str_to_datetime(the_dict, compiled_regex, time_format):
    new_dict = dict()
    for old_key, val in the_dict.items():
        new_key = str_to_datetime_by_regex(old_key, compiled_regex, time_format)
        new_dict[new_key] = val
    return new_dict

def get_all_filenames_by_regex(directory, compiled_regex):
    all_filenames = get_all_filenames_in_directory(directory)
    return list(sorted(filter(lambda x: compiled_regex.match(x) is not None,
                       all_filenames)))

def get_all_filenames_in_date_range(directory, compiled_regex, time_format,
                                    start_date, end_date):
    def fname_in_range(fname):
        fname_datetime = str_to_datetime_by_regex(fname, compiled_regex,
                                                  time_format)
        return (fname_datetime >= start_date and fname_datetime < end_date)

    return [f for f in get_all_filenames_by_regex(directory, compiled_regex) if
            fname_in_range(f)]

# Ripped from pycomnrl.file_system
def get_all_filenames_in_directory(directory):
    dir_path = os.path.abspath(directory)
    return [f for f in [dir_path + "/" + x for x in os.listdir(dir_path)] if
            os.path.isfile(f)]

def read_file_contents_by_filename(filenames, read_fn):
    filename_to_obj = dict()
    for filename in filenames:
        obj = read_fn(filename)
        filename_to_obj[filename] = obj
    return filename_to_obj

def str_to_datetime_by_regex(raw_str, compiled_regex, time_format):
    datetime_str = compiled_regex.match(raw_str).group(1)
    return datetime.datetime.strptime(datetime_str, time_format)
