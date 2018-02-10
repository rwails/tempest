#!/usr/bin/env python3

import argparse
import ipaddress
import logging
import sys

import tempest.pfi
from tempest import ip_to_asn
from tempest.tor import denasa
from tempest.tor import entropy_analysis

def main(args):
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    client_ases = read_clique_file(args.clique_filename)

    pfi = tempest.pfi.PFI(args.libspookyhash_path,
                          args.path_filename,
                          args.index_filename)

    pfi.load()
    pfi.verify()

    pfx_tree = ip_to_asn.prefix_tree_from_pfx2as_file(args.pfx2as_filename)

    client_guard_selection_probs =\
        denasa.compute_denasa_guard_selection_probs(
            client_ases,
            args.nsf_filename,
            pfx_tree,
            pfi)

    guard_fps = sorted(client_guard_selection_probs[client_ases[0]].keys())

    prob_matrix = entropy_analysis.make_prob_matrix(client_ases, guard_fps,
                                                    client_guard_selection_probs)

    dissim_scores = entropy_analysis.score_clients_by_dissim(prob_matrix)
    dissim_scores = sorted(dissim_scores, key=lambda x: x[1], reverse=True)

    print("* DISSIMILARITY *")
    for idx, score in dissim_scores:
        print(client_ases[idx], score)

    entropy_scores = entropy_analysis.score_clients_by_entropy(prob_matrix)
    entropy_scores = sorted(entropy_scores, key=lambda x: x[1], reverse=False)

    print("* ENTROPY *")
    for idx, score in entropy_scores:
        print(client_ases[idx], score)

    pfi.close()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("nsf_filename")
    parser.add_argument("pfx2as_filename")
    parser.add_argument("libspookyhash_path")
    parser.add_argument("path_filename")
    parser.add_argument("index_filename")
    parser.add_argument("clique_filename")
    return parser.parse_args()

def read_clique_file(clique_filename):
    return [line.strip() for line in open(clique_filename, 'r')]

if __name__ == "__main__":
    main(parse_args())
