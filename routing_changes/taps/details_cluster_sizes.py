#!/usr/bin/env python3

import argparse
import datetime
import functools
import os
import ujson as json

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

    def cluster_filename_to_datetime_str(x):
        return os.path.split(x)[1].split(".")[1]

    cluster_dates = list(map(cluster_filename_to_datetime_str,
                         args.cluster_filenames))

    output_lines = []

    eventual_clusters = dict()

    for idx in range(0, len(as_to_clusters)):
        as_to_cluster = as_to_clusters[idx]
        for core_as in core_ases:
            if core_as not in eventual_clusters:
                eventual_clusters[core_as] = as_to_cluster[core_as]
            else:
                eventual_clusters[core_as] =\
                    eventual_clusters[core_as].intersection(as_to_cluster[core_as])

        for asn in core_ases:
            abs_len = len(eventual_clusters[asn])
            output_lines.append((cluster_dates[idx], asn, abs_len))

    for output_line in output_lines:
        print(",".join(map(lambda x: str(x), output_line)))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("cluster_filenames", nargs="+")
    return parser.parse_args()

if __name__ == "__main__":
    main(parse_args())
