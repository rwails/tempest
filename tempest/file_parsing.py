#!/usr/bin/env python3

import datetime
import multiprocessing
import os
import re

from .tor import relays
from . import util

def parallel_load_nsf(args):
    file_date, filename = args
    network_state = relays.fat_network_state(filename)
    return (file_date, network_state)

def read_clique_file(clique_ases_filename):
    """
    Format of clique file:
        !XXXXX <- These lines correspond to blacklisted guard ASes
        XXXXX  <- These lines correspond to client ASes in the clique
        One AS per line.
    """
    blacklisted_guard_asns = []
    clique_asns = []

    with open(clique_ases_filename, 'r') as clique_file:
        for line in clique_file:
            line = line.strip('\n')
            if line[0] == '!':
                blacklisted_guard_asns.append(line[1:])
            else:
                clique_asns.append(line)

    return clique_asns, blacklisted_guard_asns

def read_map_ases(asrel_filename):
    ases = set()

    with open(asrel_filename, "r") as f:
        for line in f:
            if line[0] != '#':
                splits = line.split("|")
                ases |= {splits[0]}
                ases |= {splits[1]}

    return ases

def nsf_datetime_to_filename(nsf_dir):
    nsf_datetime_regex =\
        re.compile(".*/([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2})")

    datetime_to_nsf_filename = dict()

    for nsf_filename in util.get_all_filenames_in_directory(nsf_dir):
        nsf_datetime_str = nsf_datetime_regex.match(nsf_filename).group(1)
        nsf_datetime = datetime.datetime.strptime(nsf_datetime_str,
                                                  "%Y-%m-%d-%H-%M-%S")
        datetime_to_nsf_filename[nsf_datetime] = nsf_filename

    return datetime_to_nsf_filename

def read_nsf_files_by_time(nsf_dir, num_procs):
    datetime_regex =\
        re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}")

    nsf_filenames = [fn for fn in os.listdir(nsf_dir) if
                     os.path.isfile(os.path.join(nsf_dir, fn))]

    arg_list = []

    for filename in nsf_filenames:
        date_string = datetime_regex.match(filename).group()
        file_date = datetime.datetime.strptime(date_string, "%Y-%m-%d-%H-%M-%S")
        arg_list.append((file_date, os.path.join(nsf_dir, filename)))

    pool = multiprocessing.Pool(num_procs)
    results = pool.map(parallel_load_nsf, arg_list)
    pool.close()
    pool.join()

    datetime_to_nsf = dict()

    for dt, nsf in results:
        datetime_to_nsf[dt] = nsf

    return datetime_to_nsf
