#!/usr/bin/env python3

import argparse
import json

import pandas as pd

def get_as_to_cluster(cluster_filename):

    as_to_cluster = dict()

    with open(cluster_filename, 'r') as f:
        clusters = json.loads(f.read())

    for cluster in clusters.values():
        cluster_set = set(cluster)
        for asn in cluster:
            as_to_cluster[asn] = cluster_set

    return as_to_cluster

def main(args):

    as_to_clusters = list(map(get_as_to_cluster, args.cluster_filenames))

    core_ases = [x for x in as_to_clusters[0].keys()
                 if all(map(lambda y: x in y.keys(), as_to_clusters))]

    eventual_clusters = dict()

    for idx in range(0, len(as_to_clusters)):
        as_to_cluster = as_to_clusters[idx]
        for core_as in core_ases:
            if core_as not in eventual_clusters:
                eventual_clusters[core_as] = as_to_cluster[core_as]
            else:
                eventual_clusters[core_as] =\
                    eventual_clusters[core_as].intersection(as_to_cluster[core_as])

        if (args.verbose):
            print("Added data for clusters <%s>." % (args.cluster_filenames[idx],))
            print("Cluster size dist summary after %d clusterings:\n" % (idx + 1,))
            s = pd.Series(map(lambda x: len(x), eventual_clusters.values()))
            print(s.describe())

    if not args.verbose:
        s = pd.Series(map(lambda x: len(x), eventual_clusters.values()))
        print(s.median(), "\t", s.mean())

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("cluster_filenames", nargs="+")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    main(parse_args())
