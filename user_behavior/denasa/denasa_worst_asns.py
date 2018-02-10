#!/usr/bin/env python3

import argparse

import nrl_princeton.tor.entropy_analysis as entropy_analysis
import nrl_princeton.tor.denasa as denasa

def main(args):

    clients = read_client_file(args.client_filename)

    client_guard_selection_probs =\
        denasa.compute_denasa_guard_selection_probs(
            clients,
            args.network_state_filename,
            args.prefix2as_filename,
            args.libpfi_path)

    guard_fps = sorted(client_guard_selection_probs[clients[0]].keys())

    prob_matrix = entropy_analysis.make_prob_matrix(clients, guard_fps,
                                                    client_guard_selection_probs)

    dissim_scores = entropy_analysis.score_clients_by_dissim(prob_matrix)
    dissim_scores = sorted(dissim_scores, key=lambda x: x[1], reverse=True)

    print("* DISSIMILARITY *")
    for idx, score in dissim_scores:
        print(clients[idx], score)

    entropy_scores = entropy_analysis.score_clients_by_entropy(prob_matrix)
    entropy_scores = sorted(entropy_scores, key=lambda x: x[1], reverse=False)

    print("* ENTROPY *")
    for idx, score in entropy_scores:
        print(clients[idx], score)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network_state_filename",
                        default="../data/2015-10-fat")
    parser.add_argument("--prefix2as_filename",
                        default="../data/routeviews-rv2-20151001-0800.pfx2as")
    parser.add_argument("--libpfi_path",
                        default="/home/rwails/prg/nrl-topology/py_allpairs/libpfi/libpfi.so")
    parser.add_argument("--client_filename",
                        default="../data/client_pool.txt")
    return parser.parse_args()

def read_client_file(client_filename):
    return [line.strip() for line in open(client_filename, 'r')]

if __name__ == "__main__":
    main(parse_args())
