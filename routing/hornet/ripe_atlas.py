#!/usr/bin/env python3

from collections import Counter
import datetime
import functools
import logging
import urllib.request
import urllib.parse

from ripe.atlas.cousteau import Measurement
from ripe.atlas.sagan import TracerouteResult
import ujson

from util import ExponentialBackoff

RIPE_ATLAS_MSM_URL =\
    "https://atlas.ripe.net/api/v2/measurements/{}/results/"

@ExponentialBackoff
def _get_request(base_url, params):
    req_url = base_url + "?" + urllib.parse.urlencode(params)
    logging.info("Making request <{}>".format(req_url))
    with urllib.request.urlopen(req_url) as f:
        result = ujson.loads(f.read().decode('utf-8'))
    return result

def make_probe_to_interval_results(msm_id, start_datetime):
    """
    Retreive a single interval of traceroute results.  Only returns results
    where the traceroute successfully made it to the destination.
    """

    probe_to_interval_results = dict()

    msm_meta = query_msm_meta(msm_id)
    msm_interval = msm_meta.interval
    msm_target_ip_addr = msm_meta.target_ip

    stop_datetime = start_datetime + datetime.timedelta(seconds=msm_interval)

    measurements = query_msm(msm_id, int(start_datetime.timestamp()),
                             int(stop_datetime.timestamp()))

    for msm in measurements:
        tracert_msm = TracerouteResult(msm)
        if not tracert_is_clean(tracert_msm, msm_target_ip_addr):
            continue
        probe_result = { "origin_addr" : tracert_msm.origin,
                         "stop_timestamp" : tracert_msm.end_time.timestamp(),
                         "ip_path" : tracert_msm.ip_path }

        if tracert_msm.probe_id not in probe_to_interval_results:
            probe_to_interval_results[tracert_msm.probe_id] = probe_result
        else:
            current_result = probe_to_interval_results[tracert_msm.probe_id]
            if (probe_result["stop_timestamp"] <
                current_result["stop_timestamp"]):
                probe_to_interval_results[tracert_msm.probe_id] = probe_result

    return probe_to_interval_results

def msm_interval(msm_id):
    return query_msm_meta(msm_id).interval

@ExponentialBackoff
def query_msm(msm_id, start_timestamp, stop_timestamp):
    url = RIPE_ATLAS_MSM_URL.format(msm_id)
    params = {'start' : start_timestamp, 'stop' : stop_timestamp}
    return _get_request(url, params)

@ExponentialBackoff
@functools.lru_cache(maxsize=32)
def query_msm_meta(msm_id):
    return Measurement(id=msm_id)

def tracert_is_clean(tracert_msm, target_ip_addr):
    if tracert_msm.origin is None or len(tracert_msm.origin) == 0:
        return False
    if not tracert_msm.destination_ip_responded:
        return False
    if len(tracert_msm.ip_path) < 2:
        return False
    valid_last_hop_results = list(filter(lambda x: x is not None,
                                         tracert_msm.ip_path[-1]))
    if len(valid_last_hop_results) == 0:
        return False
    if any(map(lambda x: x != target_ip_addr, valid_last_hop_results)):
        str = "Excluding tracert with bad last hop {}"
        logging.info(str.format(valid_last_hop_results))
        return False
    return True
