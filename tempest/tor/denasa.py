#!/usr/bin/env python3

from collections import defaultdict
import functools
import sys

from .. import ip_to_asn
from . import relays

# The two ASes the DeNASA authors identified as likely to be on both the ingress
# and egress sides of a circuit.
SUSPECTS = set(["3356", "1299"])

def bidirectional_lookup(asn_1, asn_2, pfi):
    """
    Returns all the ASes on the forward and reverse paths between the two
    specified ASes, or None if no inference could be performed.
    """
    ases_forward_path = pfi.get_path(asn_1, asn_2)
    ases_reverse_path = pfi.get_path(asn_2, asn_1)

    if ases_forward_path is not None:
        ases_forward_path = set(ases_forward_path)

    if ases_reverse_path is not None:
        ases_reverse_path = set(ases_reverse_path)

    return union_of_non_none_sets([ases_forward_path, ases_reverse_path])

def compute_denasa_guard_selection_probs(client_asns,
                                         network_state_filename,
                                         pfx_tree,
                                         pfi):
    """
    Returns a dict mapping each client to its DeNASA guard selection probability
    distribution.
    """

    network_state_vars = relays.fat_network_state(network_state_filename)

    guard_fp_to_ip = relays.get_guards(network_state_vars[0],
                                       network_state_vars[1])

    guard_fp_to_asns =\
            relays.make_relay_fp_to_asns_dict(guard_fp_to_ip, pfx_tree)

    guard_fps = []
    for guard_fp, asns in guard_fp_to_asns.items():
        if asns is not None:
            guard_fps.append(guard_fp)

    guard_weights = relays.pathsim_get_position_weights(guard_fps,
                                                        network_state_vars[0],
                                                        'g',
                                                        network_state_vars[4],
                                                        network_state_vars[5])

    usability_table = make_client_guard_usability_table(client_asns, guard_fps,
                                                        guard_fp_to_asns, pfi)

    client_guard_selection_probs = dict()
    for client_asn in client_asns:
        probs = get_guard_selection_probs_for_client(guard_fps, client_asn,
                                                     guard_weights,
                                                     usability_table)
        client_guard_selection_probs[client_asn] = probs

    return client_guard_selection_probs

def get_guard_selection_probs_for_client(guard_fps, client_asn, guard_weights,
                                         usability_table):

    safe_guard_fps = list(filter(lambda x: usability_table[(client_asn, x)],
                                 guard_fps))

    bw_sum = sum(map(lambda x: guard_weights[x], safe_guard_fps))

    if len(safe_guard_fps) == 0 or bw_sum == 0:
        # If there are no safe guards to use, resort back to vanilla bandwidth
        # weighting
        bw_sum = sum(guard_weights.values())
        scaled_bw_weights = dict()
        for guard_fp, weight in guard_weights.items():
            scaled_bw_weights[guard_fp] = float(weight) / float(bw_sum)
        return scaled_bw_weights

    else:
        safe_guard_weights = dict.fromkeys(guard_fps, 0.0)

        for safe_guard_fp in safe_guard_fps:
            safe_guard_weights[safe_guard_fp] =\
                (float(guard_weights[safe_guard_fp]) / float(bw_sum))

        return safe_guard_weights

def make_client_guard_usability_table(client_asns, guard_fps, guard_fp_to_asns,
                                      pfi):
    """
    Creates a dict mapping (client_asn, guard_fp) to bool values.  Value is True
    if a client can use a guard according to DeNASA's no-suspect-on-ingress
    policy, False otherwise.
    """

    usability_table = dict()

    for client_asn in client_asns:
        for guard_fp in guard_fps:
            guard_asns = guard_fp_to_asns[guard_fp]
            lookup = lambda x: bidirectional_lookup(client_asn, x, pfi)
            suspects = union_of_non_none_sets(map(lookup, guard_asns))

            table_key = (client_asn, guard_fp)

            if len(suspects) == 0:
                # No path inference could be performed
                usability_table[table_key] = False
            elif (len(suspects & SUSPECTS) != 0):
                # Suspect on path
                usability_table[table_key] = False
            else:
                usability_table[table_key] = True

    return usability_table

def union_of_non_none_sets(sets):
    """
    Helper function, takes a list of [set or None] and returns the union of all
    non-None elements.
    """
    return functools.reduce(lambda x, y: x.union(y), filter(lambda z: z is not\
                                                            None, sets), set())
