#!/usr/bin/env python3
"""
Functions to grab relays and weights from files.  Altered for python3
compatibility.
"""

################################################################################
# The Tor Path Simulator License
# <https://github.com/torps/torps>
#
# To the extent that a federal employee is an author of a portion of
# this software or a derivative work thereof, no copyright is claimed by
# the United States Government, as represented by the Secretary of the
# Navy ("GOVERNMENT") under Title 17, U.S. Code. All Other Rights 
# Reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the names of the copyright owners nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# GOVERNMENT ALLOWS FREE USE OF THIS SOFTWARE IN ITS "AS IS" CONDITION
# AND DISCLAIMS ANY LIABILITY OF ANY KIND FOR ANY DAMAGES WHATSOEVER
# RESULTING FROM THE USE OF THIS SOFTWARE.
################################################################################

import datetime
from io import BytesIO
import ipaddress
import pickle
import re

from stem import Flag
import stem.descriptor

from .. import ip_to_asn, util

DEFAULT_BWWEIGHTSCALE = 10000

NSF_REGEX =\
    re.compile(".*/([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2})-network_state$")

NSF_TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"

def fat_network_state(ns_filename):
    """Reading fat network state file into commonly-used variables.
    Cannot use pathsim.get_network_state() because nsf is fat."""
    cons_rel_stats = {}
    with open(ns_filename, 'rb') as nsf:
        consensus_str = pickle.load(nsf, encoding='bytes')
        # convert consensus from string to stem object
        i = 0
        for doc in stem.descriptor.parse_file(BytesIO(consensus_str),
                                              validate=True,
                                              document_handler='DOCUMENT'):
            if (i > 0):
                raise ValueError('Unexpectedly found more than one consensus in network state file')
            consensus = doc
            i += 1
        # convert descriptors from strings to stem objets
        descriptors = pickle.load(nsf, encoding='bytes')
        for fprint, desc_str in descriptors.items():
            i = 0
            for desc in stem.descriptor.parse_file(BytesIO(desc_str), validate = True):
                if (i > 0):
                    raise ValueError('Unexpectedly found more than one descriptor in dict entry')
                descriptors[fprint] = desc
                i += 1
        hibernating_statuses = pickle.load(nsf, encoding='bytes')

    # descriptor conversion
    converted_descriptors = dict()
    for fprint, descriptor in descriptors.items():
        converted_descriptors[fprint.decode('utf-8')] = descriptor

    descriptors = converted_descriptors

    # set variables from consensus
    cons_valid_after = pathsim_timestamp(consensus.valid_after)
    cons_fresh_until = pathsim_timestamp(consensus.fresh_until)
    cons_bw_weights = consensus.bandwidth_weights
    if ('bwweightscale' not in consensus.params):
        cons_bwweightscale = DEFAULT_BWWEIGHTSCALE
    else:
        cons_bwweightscale = consensus.params['bwweightscale']
    for relay in consensus.routers:
        if (relay in descriptors):
            cons_rel_stats[relay] = consensus.routers[relay]


    return (cons_rel_stats, descriptors, cons_valid_after, cons_fresh_until,
        cons_bw_weights, cons_bwweightscale, hibernating_statuses)

def fat_network_state_for_datetime(nsf_dir, ns_datetime):
    nsf_fnames = util.get_all_filenames_by_regex(nsf_dir, NSF_REGEX)
    for nsf_fname in nsf_fnames:
        if (util.str_to_datetime_by_regex(nsf_fname, NSF_REGEX, NSF_TIME_FORMAT)
            == ns_datetime):
            return fat_network_state(nsf_fname)
    return None

def get_guards(cons_rel_stats, descriptors):
    """Returns guards in cons_rel_stats. FAST flag required.
    Output is dict mapping fingerprints to IP addresses."""

    # get list of guard fingerprints
    guard_list = pathsim_filter_guards(cons_rel_stats, descriptors) # basic guard filter
    guard_list = filter(lambda x: stem.Flag.FAST in cons_rel_stats[x].flags,
        guard_list)
    guards = dict()
    for guard in guard_list:
        guards[guard] = cons_rel_stats[guard].address

    return guards

def make_relay_fp_to_asns_dict(relay_fp_to_ip, first_octet_to_network_asns):
    """
    Keyword Arguments:
        relay_fp_to_ip -- Dict mapping relay fingerprint to IP address, produced
        by get_guards()

        first_octet_to_network_asns -- Created by ip_to_asn.parse_pfx2as_file
    """
    relay_fp_to_asns = dict()

    for relay_fp, relay_ip in relay_fp_to_ip.items():
        relay_fp_to_asns[relay_fp] =\
            ip_to_asn.ip_to_asns(ipaddress.IPv4Address(relay_ip),
                                 first_octet_to_network_asns)

    return relay_fp_to_asns

# Grabbed from torps pathsim
def pathsim_get_bw_weight(flags, position, bw_weights):
    """Returns weight to apply to relay's bandwidth for given position.  flags:
        list of Flag values for relay from a consensus position: position for
        which to find selection weight, one of 'g' for guard, 'm' for middle,
        and 'e' for exit bw_weights: bandwidth_weights from
        NetworkStatusDocumentV3 consensus """

    if (position == 'g'):
        if (Flag.GUARD in flags) and (Flag.EXIT in flags):
            return bw_weights['Wgd']
        elif (Flag.GUARD in flags):
            return bw_weights['Wgg']
        elif (Flag.EXIT not in flags):
            return bw_weights['Wgm']
        else:
            raise ValueError('Wge weight does not exist.')
    else:
        raise NotImplementedError()

# Grabbed from torps pathsim
def pathsim_get_position_weights(nodes, cons_rel_stats, position, bw_weights,
                                 bwweightscale):
    """Computes the consensus "bandwidth" weighted by position weights."""
    weights = {}
    for node in nodes:
        bw = float(cons_rel_stats[node].bandwidth)
        weight = (float(pathsim_get_bw_weight(cons_rel_stats[node].flags,
                                              position,bw_weights)) /
                  float(bwweightscale))
        weights[node] = bw * weight
    return weights

# Grabbed from torps pathsim
def pathsim_filter_guards(cons_rel_stats, descriptors):
    """Returns relays filtered by general (non-client-specific) guard criteria.
    In particular, omits checks for IP/family/subnet conflicts within list.  """

    guards = []

    for fprint in cons_rel_stats:
        rel_stat = cons_rel_stats[fprint]
        if ((Flag.RUNNING in rel_stat.flags) and (Flag.VALID in rel_stat.flags)
            and (Flag.GUARD in rel_stat.flags) and (fprint in descriptors)):
            guards.append(fprint)

    return guards

# Grabbed from torps pathsim
def pathsim_timestamp(t):
    """Returns UNIX timestamp"""
    td = t - datetime.datetime(1970, 1, 1)
    ts = td.days*24*60*60 + td.seconds
    return ts
