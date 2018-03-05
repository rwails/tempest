#!/usr/bin/env python3

import argparse
import atexit
from collections import defaultdict
import datetime
import ipaddress
import logging
import sys

import numpy as np

import hornet
import persistent_lru
import ripe_atlas

def info(type, value, tb):
   if hasattr(sys, 'ps1') or not sys.stderr.isatty(  ):
      # You are in interactive mode or don't have a tty-like
      # device, so call the default hook
      sys.__excepthook__(type, value, tb)
   else:
      import traceback, pdb
      # You are NOT in interactive mode; print the exception...
      traceback.print_exception(type, value, tb)
      print()
      # ...then start the debugger in post-mortem mode
      pdb.pm(  )

# sys.excepthook = info

def main(args):
    std_format =\
        ("[%(asctime)s %(process)d %(filename)s %(funcName)s %(levelname)s" +
         "] -- %(message)s")

    logging.basicConfig(format=std_format, stream=sys.stderr,
                        level=logging.INFO)

    cache = persistent_lru.PersistentLRU(args.cache_filename, 8096)
    cache.load()
    atexit.register(cache.close)

    hornet.define_common_probe_locations_cached(cache)
    hornet.define_hornet_obs_seqs_cached(cache)
    hornet.define_pfx2as_cached(cache)
    hornet.define_probe_paths_cached(cache)

    start_datetime = datetime.datetime.strptime(args.start_date, "%Y-%m-%d")
    start_datetime = start_datetime.replace(tzinfo=datetime.timezone.utc)

    end_datetime = datetime.datetime.strptime(args.end_date, "%Y-%m-%d")
    end_datetime = end_datetime.replace(tzinfo=datetime.timezone.utc)

    tick_width =\
        datetime.timedelta(seconds=ripe_atlas.msm_interval(args.msm_id))

    analysis_interval = hornet.analysis_interval_points(start_datetime,
                                                        end_datetime,
                                                        tick_width,
                                                        args.msm_id)

    stable_probes = hornet.stable_loc_probes(args.msm_id, analysis_interval)

    single_origin_stable_probes = list(filter(
        lambda x: len(
            hornet.split_asn_set(hornet.probe_time_to_as(args.msm_id,
                                                         x,
                                                         analysis_interval[0])))
            == 1,
        stable_probes
    ))

    # print(len(stable_probes))

    probe_to_asn =\
        lambda x: hornet.split_asn_set(hornet.probe_time_to_as(args.msm_id, x,
                                                          analysis_interval[0])).pop()

    unique_stable_ases = set(map(probe_to_asn, stable_probes))
    # print(len(unique_stable_ases))

    # return

    single_origin_stable_probes = single_origin_stable_probes[:100]

    hornet_obs_seqs = hornet.hornet_obs_seqs_cached(stable_probes,
                                                    analysis_interval,
                                                    args.msm_id)

    asn_before_means = defaultdict(list)
    asn_after_means = defaultdict(list)
    changes_per_asn = defaultdict(list)

    for idx, probe in enumerate(single_origin_stable_probes):
        if idx % 10 == 0:
            logging.info("Analyzing probe {} of {}".format(idx,
                                                           len(stable_probes)))
        try:
            boundaries = hornet.list_of_boundaries(hornet_obs_seqs[probe])

            probe_asn = hornet.probe_time_to_as(args.msm_id, probe,
                                                start_datetime)

            changes_per_asn[probe_asn].append(len(boundaries))

            if len(boundaries) == 0:
                continue

            before_sz = list()
            after_sz = list()

            for boundary in boundaries:
                before_size, after_size =\
                    hornet.hornet_analyze_boundary_asn(args.msm_id, probe,
                                                       boundary)

                before_sz.append(before_size)
                after_sz.append(after_size)

                # before_sz_rel.append(before_size / pfx_size)
                #after_sz_rel.append(after_size / pfx_size)

            asn_before_means[probe_asn].append(np.mean(before_sz))
            asn_after_means[probe_asn].append(np.mean(after_sz))
        except Exception as e:
            logging.warn(
                "Encountered exception {} during probe {}".format(e, probe)
            )
            continue

    # Changes per pfx contains all probe pfxs, whereas before and after means
    # only contain pfx's with at least one change
    for asn in changes_per_asn.keys():
        mean_changes = np.mean(changes_per_asn[asn])

        before_means = asn_before_means[asn]
        after_means = asn_after_means[asn]
        before_grand_mean = np.mean(before_means)
        after_grand_mean = np.mean(after_means)

        output = (asn, mean_changes, before_grand_mean, after_grand_mean)

        print(",".join(map(lambda x: str(x), output)))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("msm_id", type=int)
    parser.add_argument("start_date", help="Format: YYYY-mm-dd")
    parser.add_argument("end_date", help="Format: YYYY-mm-dd")
    parser.add_argument("--cache_filename", default="cache.db")
    return parser.parse_args()

def prefix_weight(str_pfx):
    network = ipaddress.ip_network(str_pfx)
    return 33 - network.prefixlen

if __name__ == "__main__":
    main(parse_args())
