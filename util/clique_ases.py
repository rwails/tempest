#!/usr/bin/env python3

import argparse
import logging
import random
import sys

import tempest.pfi
from tempest.file_parsing import read_map_ases

def are_neighbors(pfi, x, y):
    if (pfi.get_path(x, y) == ['None'] or pfi.get_path(y, x) == ['None']):
        return False
    else:
        return True

def main(args):
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    pfi = tempest.pfi.PFI(args.libspookyhash_path,
                          args.path_filename,
                          args.index_filename)
    pfi.load()
    pfi.verify()

    map_ases = read_map_ases(args.asrel_filename)

    p = set(map_ases)
    r = list()

    while len(p) > 0:
        if len(p) % 10 == 0:
            print("{} ASes left in p".format(len(p)), file=sys.stderr)
        v = p.pop()
        v_nbhd = { n for n in p if are_neighbors(pfi, v, n) }
        if len(v_nbhd) >= (len(p) / 2):
            r.append(v)
            p.intersection_update(v_nbhd)

    print("Output clique contains {} ASes".format(len(r)), file=sys.stderr)

    for asn in sorted(r):
        print(asn)

    pfi.close()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("libspookyhash_path")
    parser.add_argument("path_filename")
    parser.add_argument("index_filename")
    parser.add_argument("asrel_filename")
    return parser.parse_args()

if __name__ == "__main__":
    main(parse_args())
