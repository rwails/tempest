#!/usr/bin/env python3

import argparse
import atexit
from collections import Counter, ChainMap, defaultdict
import datetime
import functools
import hashlib
import ipaddress
import itertools
import logging
import random
import re
import sys

import ujson

from tempest import sample_generation

from boundary_search import boundary_search
import caida_routeviews
import persistent_lru
import prefix_to_as
import ripe_atlas
import serial

ASN_DELIM_RE = ",|_"
BAD_RESOLVE = "*"

HORNET_HDR = ("MSM_ID", "PROBE_ID", "T0", "T1", "T0_OBS", "T1_OBS",
              "#_ALL_PROBES", "#_ALL_PFX", "#_ALL_ADDR",
              "PCT_ALL_ADDR", "NUM_ALL_ASES",
              "#_VALID_PROBES", "#_VALID_PFX", "#_VALID_ADDR",
              "PCT_VALID_ADDR", "NUM_VALID_ASES",
              "#_PRV_PROBE", "#_PRV_PFX", "#_PRV_ADDR",
              "PCT_PRV_ADDR", "NUM_PRV_ASES",
              "#_ITC_PROBES", "#_ITC_PFX", "#_ITC_ADDR",
              "PCT_ITC_ADDR", "NUM_ITC_ASES")

def all_known_probes(msm_id, datetimes):
    all_probes = list()

    for dt in datetimes:
        paths = probe_paths_cached(msm_id, dt)
        probes = [(k, dt) for k in paths.keys()]
        all_probes.extend(probes)

    return all_probes

def all_probes_with_valid_obs(msm_id, observation_fn, observation_valid_fn,
                              datetimes):
    all_probes = list()

    for dt in datetimes:
        paths = probe_paths_cached(msm_id, dt)
        for probe, path in paths.items():
            if observation_valid_fn(observation_fn(path)):
                all_probes.append((probe, dt))

    return all_probes

def analysis_interval_points(start_datetime, end_datetime, tick_width, msm_id):
    assert(start_datetime <= end_datetime)
    interval = [start_datetime]

    next_dt = start_datetime + tick_width
    time_to_add = round_datetime_to_interval(next_dt, msm_id)

    while(time_to_add <= end_datetime):
        interval.append(time_to_add)
        next_dt = time_to_add + tick_width
        time_to_add = round_datetime_to_interval(next_dt, msm_id)

    return interval

def anonymity_set(msm_id, observation, observation_fn, observation_eq_fn, dt):
    paths = probe_paths_cached(msm_id, dt)

    anon_set = set()

    for probe, path in paths.items():
        if observation_eq_fn(observation_fn(path), observation):
            anon_set.add((probe, dt))

    return anon_set

def anonymity_set_wide(msm_id, observation, observation_fn, observation_eq_fn,
                       datetimes):

    anon_set = set()

    for dt in datetimes:
        anon_set.update(anonymity_set(msm_id, observation, observation_fn,
                                      observation_eq_fn, dt))

    return anon_set

def asns_are_indistinguishable(x, y):
    if x == None or y == None:
        return False

    if x == BAD_RESOLVE and y == BAD_RESOLVE:
        return True

    x_set = split_asn_set(x)
    y_set = split_asn_set(y)

    return len(x_set.intersection(y_set)) > 0

def asn_is_unambig(asn):
    # Basic validity check
    if asn is None or len(asn) == 0:
        return False
    if asn == BAD_RESOLVE:
        return False
    return True

def common_probes(probe_paths_t1, probe_paths_t2):
    return list(sorted(probe_paths_t1.keys() & probe_paths_t2.keys()))

def common_probe_locations(msm_id, analysis_interval):
    start_paths = probe_paths_cached(msm_id, analysis_interval[0])
    end_paths = probe_paths_cached(msm_id, analysis_interval[-1])

    probes = common_probes(start_paths, end_paths)

    probe_locs = defaultdict(list)

    for dt in analysis_interval:
        probe_paths = probe_paths_cached(msm_id, dt)
        for probe in probes:
            if probe in probe_paths:
                path = probe_paths[probe]
                probe_locs[probe].append(path[0])

    return probe_locs

common_probe_locations_cached = None

def datetimes_from_stride(dt, stride_seconds, num_strides, stride_factor=1):
    datetimes = [dt]

    for idx in range(1, num_strides + 1):
        num_seconds = stride_seconds * idx * stride_factor
        datetimes.append(dt + datetime.timedelta(seconds=num_seconds))

    return datetimes

def define_common_probe_locations_cached(cache):
    global common_probe_locations_cached

    def key_fn(msm_id, analysis_interval):
        interval_bytes = ujson.dumps(analysis_interval).encode('utf-8')
        hash_v = hashlib.md5(interval_bytes).hexdigest()
        return ("{} - {}".format(msm_id, hash_v))

    common_probe_locations_cached = persistent_lru.add_persistent_caching(
        common_probe_locations,
        "common_probe_locations",
        key_fn,
        cache,
        False
    )

def define_hornet_obs_seqs_cached(cache):
    global hornet_obs_seqs_cached

    def key_fn(probes, analysis_interval, msm_id):
        probe_bytes = ujson.dumps(sorted(probes)).encode('utf-8')
        interval_bytes = ujson.dumps(analysis_interval).encode('utf-8')
        hash_1 = hashlib.md5(probe_bytes).hexdigest()
        hash_2 = hashlib.md5(interval_bytes).hexdigest()
        return ("{} - {} - {}".format(msm_id, hash_1, hash_2))

    hornet_obs_seqs_cached = persistent_lru.add_persistent_caching(
        hornet_obs_seqs,
        "hornet_obs_seqs",
        key_fn,
        cache,
        False
    )

def define_pfx2as_cached(cache):
    global pfx2as_cached

    def key_fn(dt):
        best_url = caida_routeviews.best_pfx2as_url(dt)
        return best_url

    pfx2as_cached = persistent_lru.add_persistent_caching(
        caida_routeviews.dl_pfx2as_closest_to_datetime,
        "pfx2as",
        key_fn,
        cache,
        False
    )

def define_probe_paths_cached(cache):
    global probe_paths_cached

    def key_fn(msm_id, start_datetime):
        start_datetime = round_datetime_to_interval(start_datetime, msm_id)
        return "{} {}".format(msm_id, str(start_datetime))

    probe_paths_cached =\
        persistent_lru.add_persistent_caching(probe_paths, "paths", key_fn,
                                              cache, True)

def hornet_adv_obs(path):
    if path is None:
        return None
    else:
        return path[1][-2]

def hornet_analyze_boundary_asn(msm_id, probe_id, boundary, num_strides=4):
    t0, t1 = boundary
    p0 = probe_path_at_time(msm_id, probe_id, t0)
    p1 = probe_path_at_time(msm_id, probe_id, t1)

    t0_obs = hornet_adv_obs(p0)
    t1_obs = hornet_adv_obs(p1)

    interval = ripe_atlas.msm_interval(msm_id)

    t0_date_range = datetimes_from_stride(t1, interval, num_strides, -1)
    t1_date_range = datetimes_from_stride(t0, interval, num_strides, 1)

    t0_anon = anonymity_set_wide(msm_id, t0_obs, hornet_adv_obs,
                                 asns_are_indistinguishable, t0_date_range)

    t1_anon = anonymity_set_wide(msm_id, t1_obs, hornet_adv_obs,
                                 asns_are_indistinguishable, t1_date_range)

    t0_ases = probe_times_to_uniq_ases(msm_id, t0_anon)
    t1_ases = probe_times_to_uniq_ases(msm_id, t1_anon)

    itc_ases = t0_ases.intersection(t1_ases)

    return len(t0_ases), len(itc_ases)

def hornet_analyze_boundary_pfx(msm_id, probe_id, boundary, num_strides=4):
    t0, t1 = boundary
    p0 = probe_path_at_time(msm_id, probe_id, t0)
    p1 = probe_path_at_time(msm_id, probe_id, t1)

    t0_obs = hornet_adv_obs(p0)
    t1_obs = hornet_adv_obs(p1)

    interval = ripe_atlas.msm_interval(msm_id)

    t0_date_range = datetimes_from_stride(t1, interval, num_strides, -1)
    t1_date_range = datetimes_from_stride(t0, interval, num_strides, 1)

    t0_anon = anonymity_set_wide(msm_id, t0_obs, hornet_adv_obs,
                                 asns_are_indistinguishable, t0_date_range)

    t1_anon = anonymity_set_wide(msm_id, t1_obs, hornet_adv_obs,
                                 asns_are_indistinguishable, t1_date_range)

    t0_prefixes = probe_times_to_uniq_pfxs(msm_id, t0_anon)
    t1_prefixes = probe_times_to_uniq_pfxs(msm_id, t1_anon)

    itc_pfxs = t0_prefixes.intersection(t1_prefixes)

    t0_num_addrs = num_ipv4_addrs(t0_prefixes)
    itc_num_addrs = num_ipv4_addrs(itc_pfxs)

    return t0_num_addrs, itc_num_addrs

def hornet_analyze_boundaries(msm_id, probe_id, boundaries, num_strides=4):

    found_result = False

    for (t0, t1) in boundaries:
        if t0 == None or t1 == None:
            continue

        p0 = probe_path_at_time(msm_id, probe_id, t0)
        p1 = probe_path_at_time(msm_id, probe_id, t1)
        if p0 is None or p1 is None or (p0[0] != p1[0]):
            s = "Ignoring boundary {} - {} with location {} change to {}"
            logging.info(s.format(str(t0), str(t1), p0, p1))

        t0_obs = hornet_adv_obs(p0)
        t1_obs = hornet_adv_obs(p1)

        if not asn_is_unambig(t0_obs) or not asn_is_unambig(t1_obs):
            s = "Ignoring boundary {} - {} with hop {} change to {}"
            logging.info(s.format(str(t0), str(t1), t0_obs, t1_obs))
            continue

        interval = ripe_atlas.msm_interval(msm_id)

        # Overlapping intervals?
        t0_date_range = datetimes_from_stride(t1, interval, num_strides, -1)
        t1_date_range = datetimes_from_stride(t0, interval, num_strides, 1)

        all_probes = all_known_probes(msm_id, t0_date_range)
        all_valid = all_probes_with_valid_obs(msm_id, hornet_adv_obs,
                                              asn_is_unambig, t0_date_range)

        out_0 = probe_times_stats(msm_id, all_probes)
        out_1 = probe_times_stats(msm_id, all_valid)

        prv = anonymity_set_wide(msm_id, t0_obs, hornet_adv_obs,
                                 asns_are_indistinguishable, t0_date_range)

        out_2 = probe_times_stats(msm_id, prv)

        prv_ases = probe_times_to_uniq_ases(msm_id, prv)
        prv_pfxs = probe_times_to_uniq_pfxs(msm_id, prv)
        prv_probes = probe_times_to_uniq_probes(prv)

        nxt = anonymity_set_wide(msm_id, t1_obs, hornet_adv_obs,
                                 asns_are_indistinguishable, t1_date_range)

        nxt_ases = probe_times_to_uniq_ases(msm_id, nxt)
        nxt_pfxs = probe_times_to_uniq_pfxs(msm_id, nxt)
        nxt_probes = probe_times_to_uniq_probes(nxt)

        itc_ases = prv_ases.intersection(nxt_ases)
        itc_pfxs = prv_pfxs.intersection(nxt_pfxs)
        itc_probes = prv_probes.intersection(nxt_probes)

        itc_addrs = num_ipv4_addrs(itc_pfxs)
        itc_pct = pct_ipv4_addrs(itc_pfxs)

        out_3 = (len(itc_probes), len(itc_pfxs), itc_addrs, itc_pct,
                 len(itc_ases))

        out = (msm_id, probe_id, t0, t1, t0_obs, t1_obs) + out_0 + out_1 +\
                out_2 + out_3

        print(",".join(map(lambda x: str(x), out)))

        found_result = True

        break

    if not found_result:
        out = (msm_id, probe_id, "NIL")
        print(",".join(map(lambda x: str(x), out)))

def hornet_candidate_score(probe_path_t1, probe_path_t2,
                           t1_obs_frq, t2_obs_frq):
    if probe_path_t1[0] != probe_path_t2[0]: # Probe changed network location
        return 0.0

    o1 = hornet_adv_obs(probe_path_t1)
    o2 = hornet_adv_obs(probe_path_t2)

    if (o1 == BAD_RESOLVE or o2 == BAD_RESOLVE):
        # Avoid traceroutes where the previous hop was a *
        return 0.0

    if asns_are_indistinguishable(o1, o2):
        return 0.0

    return t1_obs_frq[o1] / t2_obs_frq[o2]

def hornet_diffs(msm_id, start_datetime, end_datetime):
    changed_probes = []

    start_paths = probe_paths_cached(msm_id, start_datetime)
    end_paths = probe_paths_cached(msm_id, end_datetime)

    probes = common_probes(start_paths, end_paths)

    for probe in probes:
        probe_path_t0 = start_paths[probe]
        probe_path_t1 = end_paths[probe]

        if probe_path_t0[0] != probe_path_t1[0]: # Probe changed location
            continue

        t0_obs = hornet_adv_obs(probe_path_t0)
        t1_obs = hornet_adv_obs(probe_path_t1)

        if t0_obs == BAD_RESOLVE or t1_obs == BAD_RESOLVE:
            continue

        if not asns_are_indistinguishable(t0_obs, t1_obs):
            changed_probes.append(probe)

    return changed_probes

hornet_obs_seqs_cached = None

def hornet_obs_seqs(probes, analysis_interval, msm_id):
    probe_to_hornet_obs = defaultdict(list)

    for dt in analysis_interval:
        probe_paths = probe_paths_cached(msm_id, dt)
        for probe in probes:
            if probe not in probe_paths:
                probe_to_hornet_obs[probe].append((None, dt))
            else:
                path = probe_paths[probe]
                probe_to_hornet_obs[probe].append((hornet_adv_obs(path), dt))

    return probe_to_hornet_obs

def hornet_obs_frq(probe_paths):
    c = Counter()

    for value in probe_paths.values():
        c[hornet_adv_obs(value)] += 1

    num_observations = sum(c.values())

    for key in c.keys():
        c[key] /= num_observations

    return c

def hornet_scores(msm_id, start_datetime, end_datetime):

    start_paths = probe_paths_cached(msm_id, start_datetime)
    end_paths = probe_paths_cached(msm_id, end_datetime)

    start_path_obs_frq = hornet_obs_frq(start_paths)
    end_path_obs_frq = hornet_obs_frq(end_paths)

    probe_scores = []

    for probe_id in common_probes(start_paths, end_paths):
        sp = start_paths[probe_id]
        ep = end_paths[probe_id]
        score = hornet_candidate_score(sp, ep, start_path_obs_frq,
                                       end_path_obs_frq)
        probe_scores.append((probe_id, score))

    probe_scores = sorted(probe_scores, key=lambda x: x[1], reverse=True)

    return probe_scores

def ip_addr_to_asn(ip_addr, prefix_tree):
    if ip_addr is None or len(ip_addr) == 0:
        return None
    if ip_addr not in prefix_tree:
        return None
    else:
        return prefix_tree[ip_addr]

def ip_addr_to_pfx(ip_addr, prefix_tree):
    if ip_addr is None or len(ip_addr) == 0:
        return None
    if ip_addr not in prefix_tree:
        return None
    else:
        return prefix_tree.get_key(ip_addr)

def jaccard_idx(a, b):
    return len(a.intersection(b)) / len(a.union(b))

def list_of_boundaries(hornet_obs_seq):
    ret = list()
    possible_boundaries = itertools.zip_longest(hornet_obs_seq[:-1],
                                                hornet_obs_seq[1:])

    for x, y in possible_boundaries:
        if x[0] is None or y[0] is None:
            continue
        if x[0] == BAD_RESOLVE or y[0] == BAD_RESOLVE:
            continue
        if not asns_are_indistinguishable(x[0], y[0]):
            t0 = datetime.datetime.fromtimestamp(x[1], datetime.timezone.utc)
            t1 = datetime.datetime.fromtimestamp(y[1], datetime.timezone.utc)
            ret.append((t0, t1))

    return ret

def main(args):

    random.seed(313)

    std_format =\
        ("[%(asctime)s %(process)d %(filename)s %(funcName)s %(levelname)s" +
         "] -- %(message)s")

    logging.basicConfig(format=std_format, stream=sys.stderr,
                        level=logging.INFO)

    cache = persistent_lru.PersistentLRU(args.cache_filename, 8096)
    cache.load()
    atexit.register(cache.close)

    define_probe_paths_cached(cache)
    define_pfx2as_cached(cache)

    msm_id = args.msm_id

    start_datetime = datetime.datetime(year=2016, month=1, day=1,
                                       tzinfo=datetime.timezone.utc)

    end_datetime = datetime.datetime(year=2016, month=2, day=1,
                                     tzinfo=datetime.timezone.utc)

    print(",".join(HORNET_HDR))

    diff_probes = hornet_diffs(msm_id, start_datetime, end_datetime)

    logging.info("{} probes with a HORNET diff".format(len(diff_probes)))

    as_thresh = 50

    sampled_probes = sample_probes_by_as_thresh(msm_id, diff_probes,
                                                start_datetime, as_thresh)

    for probe_id in sampled_probes:

        logging.info("PROBE ID: {}".format(probe_id))
        start_path = probe_path_at_time(msm_id, probe_id, start_datetime)
        end_path = probe_path_at_time(msm_id, probe_id, end_datetime)
        logging.info("Start path {} at {}".format(start_path,
                                                  str(start_datetime)))
        logging.info("End path {} at {}".format(end_path, str(end_datetime)))

        boundaries = search_for_boundaries(msm_id, probe_id, start_datetime,
                                           end_datetime)

        hornet_analyze_boundaries(msm_id, probe_id, boundaries)

def make_pfx_to_probes(msm_id, probes, dt):

    pfx_to_probes = defaultdict(list)

    paths = probe_paths_cached(msm_id, dt)
    for probe_id in probes:
        pfx_to_probes[paths[probe_id][0][1]].append(probe_id)

    return pfx_to_probes

def num_ipv4_addrs(pfxs):
    num_addrs = 0

    for pfx in pfxs:
        num_addrs += ipaddress.ip_network(pfx).num_addresses

    return num_addrs

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("msm_id", type=int)
    parser.add_argument("start_date", help="Format: YYYY-mm-dd")
    parser.add_argument("end_date", help="Format: YYYY-mm-dd")

    parser.add_argument("--cache_filename", default="cache.db")
    parser.add_argument("--num_top_probes", type=int, default=50)

    return parser.parse_args()

def pct_ipv4_addrs(pfxs):
    return num_ipv4_addrs(pfxs) / num_allocable_ipv4_addrs()

def num_allocable_ipv4_addrs():
    return 2**32 - num_reserved_ipv4_addrs()

def num_reserved_ipv4_addrs():
    num_reserved_addrs = 0

    reserved_ranges = [
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "255.255.255.255/32"
    ]

    for reserved_range in reserved_ranges:
        num_reserved_addrs +=\
            ipaddress.ip_network(reserved_range).num_addresses

    return num_reserved_addrs

pfx2as_cached = None

def probe_path_at_time(msm_id, probe_id, dt):
    paths = probe_paths_cached(msm_id, dt)

    if probe_id not in paths:
        return None
    else:
        return paths[probe_id]

def probe_paths(msm_id, start_datetime):
    start_datetime = round_datetime_to_interval(start_datetime, msm_id)

    probe_to_interval_results =\
        ripe_atlas.make_probe_to_interval_results(msm_id, start_datetime)

    pfx2as_file_contents = pfx2as_cached(start_datetime)

    prefix_tree = prefix_to_as.prefix_tree_from_pfx2as(pfx2as_file_contents)

    remove_bad_origin_probes(probe_to_interval_results, prefix_tree)

    ret = dict()

    for probe_id, result in probe_to_interval_results.items():
        ip_addr = result["origin_addr"]
        network_loc = (ip_addr, ip_addr_to_pfx(ip_addr, prefix_tree),
                       ip_addr_to_asn(ip_addr, prefix_tree))

        ret[probe_id] = (network_loc,
                         resolve_probe_results_to_as_path(result, prefix_tree))

    return ret

probe_paths_cached = None

def probe_times_stats(msm_id, probe_times):
    uniq_ases = probe_times_to_uniq_ases(msm_id, probe_times)
    uniq_pfxs = probe_times_to_uniq_pfxs(msm_id, probe_times)
    uniq_probes = probe_times_to_uniq_probes(probe_times)

    num_ases = len(uniq_ases)
    num_pfxs = len(uniq_pfxs)
    num_probes = len(uniq_probes)

    num_addrs = num_ipv4_addrs(uniq_pfxs)
    pct_addrs = pct_ipv4_addrs(uniq_pfxs)

    return (num_probes, num_pfxs, num_addrs, pct_addrs, num_ases)

def probe_time_to_as(msm_id, probe_id, dt):
    paths = probe_paths_cached(msm_id, dt)
    return paths[probe_id][0][2]

def probe_time_to_pfx(msm_id, probe_id, dt):
    paths = probe_paths_cached(msm_id, dt)
    return paths[probe_id][0][1]

def probe_times_to_uniq_ases(msm_id, probe_times):
    uniq_ases = set()

    for probe, dt in probe_times:
        uniq_ases.update(split_asn_set(probe_time_to_as(msm_id, probe, dt)))

    return uniq_ases

def probe_times_to_uniq_pfxs(msm_id, probe_times):
    uniq_pfxs = set()

    for probe, dt in probe_times:
        uniq_pfxs.add(probe_time_to_pfx(msm_id, probe, dt))

    return uniq_pfxs

def probe_times_to_uniq_probes(probe_times):
    uniq_probes = set()

    for probe, dt in probe_times:
        uniq_probes.add(probe)

    return uniq_probes

def process_unmapped_intra_as_hops(as_path):
    if len(as_path) < 3:
        return as_path
    else:
        slice = as_path[0:3]
        if slice[0] == slice[2] and slice[1] == BAD_RESOLVE:
            return process_unmapped_intra_as_hops([as_path[0]] + as_path[3:])
        else:
            return [as_path[0]] + process_unmapped_intra_as_hops(as_path[1:])

def replace_private_addrs(ip_addrs, origin_addr):
    return list(map(lambda x: (origin_addr if
                               ipaddress.ip_address(x).is_private else x),
                    ip_addrs))

def remove_bad_origin_probes(probe_to_interval_results, prefix_tree):
    probes_to_remove = list()

    for probe_id, probe_result in probe_to_interval_results.items():
        if probe_result["origin_addr"] not in prefix_tree:
            probes_to_remove.append(probe_id)

    for probe_id in probes_to_remove:
        logging.info("Removing probe {} (bad origin)".format(probe_id))
        del probe_to_interval_results[probe_id]

def resolve_probe_results_to_as_path(probe_result, prefix_tree):
    origin_addr = probe_result["origin_addr"]
    origin_as = prefix_tree[probe_result["origin_addr"]]
    as_path = []
    in_src_as = True

    for hop_results in probe_result["ip_path"]:
        valid_hop_results = filter(lambda x: x is not None, hop_results)
        if in_src_as:
            valid_hop_results = replace_private_addrs(valid_hop_results,
                                                      origin_addr)

        resolved_hop_results = resolve_hop_results(hop_results, prefix_tree)

        if resolved_hop_results_are_unambig(resolved_hop_results):
            asn = resolved_hop_results[0]
        else:
            asn = BAD_RESOLVE

        if len(as_path) == 0 or as_path[-1] != asn:
            as_path.append(asn)

        if in_src_as and asn != origin_as:
            in_src_as = False

    if as_path[0] != origin_as:
        as_path.insert(0, origin_as)

    return process_unmapped_intra_as_hops(as_path)

def resolve_hop_results(hop_results, prefix_tree):
    ret = map(lambda x: ip_addr_to_asn(x, prefix_tree), hop_results)
    return list(filter(lambda x: x is not None, ret))

def resolved_hop_results_are_unambig(resolved_hop_results):
    unique_asns_with_mapping = set(resolved_hop_results)
    return (len(unique_asns_with_mapping) == 1 and
            asn_is_unambig(unique_asns_with_mapping.pop()))

def round_datetime_to_interval(dt, msm_id):
    ts = int(dt.timestamp())
    interval = ripe_atlas.msm_interval(msm_id)
    ts = ts - (ts % interval)
    dt = datetime.datetime.utcfromtimestamp(ts)
    return dt.replace(tzinfo=datetime.timezone.utc)

def sample_probes_by_as_thresh(msm_id, probes, dt, as_thresh,
                               with_replacement=True):
    pfx_to_probes = make_pfx_to_probes(msm_id, probes, dt)
    pfx_list, cumul_probs = pfx_list_and_cumul_probs(pfx_to_probes)

    chosen_ases = set()
    chosen_probes = list()

    select_probe = lambda x: random.choice(pfx_to_probes[x])

    while (len(chosen_ases) < as_thresh):
        pfx = sample_generation.select_key_from_cumulative_probs(pfx_list,
                                                                 cumul_probs)
        probe = select_probe(pfx)
        if probe in chosen_probes and not with_replacement:
            continue
        else:
            chosen_probes.append(probe)
            chosen_ases.add(probe_time_to_as(msm_id, probe, dt))

    logging.info("Num ASes:\t{}".format(len(chosen_ases)))
    logging.info("Num Probes:\t{}".format(len(chosen_probes)))

    return chosen_probes

def pfx_list_and_cumul_probs(pfx_to_probes):
    pfx_to_prob = dict()

    for pfx in pfx_to_probes:
        pfx_to_prob[pfx] = ipaddress.ip_network(pfx).num_addresses

    total_num_addrs = float(sum(pfx_to_prob.values()))

    for pfx in pfx_to_prob:
        pfx_to_prob[pfx] /= total_num_addrs

    pfx_list, cumul_probs =\
        sample_generation.make_key_list_and_cumulative_probs(pfx_to_prob)

    return pfx_list, cumul_probs

def search_for_boundaries(msm_id, probe_id, start_datetime, end_datetime):

    array_fn = lambda x: probe_path_at_time(msm_id, probe_id, x)

    key_fn = lambda x: None if x is None else hornet_adv_obs(x)

    idx_metric_fn = lambda x, y: abs(y.timestamp() - x.timestamp())

    def idx_mid_fn(x, y):
        ts = (x.timestamp() + y.timestamp()) / 2
        dt = datetime.datetime.utcfromtimestamp(ts)
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        return round_datetime_to_interval(dt, msm_id)

    interval = ripe_atlas.msm_interval(msm_id)

    return boundary_search(array_fn, key_fn, idx_metric_fn, idx_mid_fn,
                           start_datetime, end_datetime, interval)

def split_asn_set(asn):
    return set(re.split(ASN_DELIM_RE, asn))

def stable_loc_probes(msm_id, analysis_interval):
    probe_locs =\
        common_probe_locations_cached(msm_id, analysis_interval)

    probes = list(probe_locs.keys())

    stable_probes = list()

    for p in probes:
        locs = map(lambda x: tuple(x[1:]), probe_locs[p])
        if len(set(locs)) == 1:
            stable_probes.append(p)

    return stable_probes

if __name__ == "__main__":
    main(parse_args())
