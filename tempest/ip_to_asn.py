#!/usr/bin/env python3
"""Uses CAIDA pfx2as files to perform IP-to-ASN lookups.
"""

from collections import defaultdict
import csv
import ipaddress

def parse_pfx2as_file(pfx2as_filename):
    """
    Reads a pfx2as file from data.caida.org into a dictionary mapping
    most-significant-network-bit to (prefix, asns) tuples.

    Returns:
        A dictionary mapping msb to a list of (network prefix, asn) tuples.
    """
    first_octet_to_network_asns = defaultdict(list)

    with open(pfx2as_filename, 'r') as pfx2as_file:
        csv_reader = csv.reader(pfx2as_file, delimiter="\t")
        for row in csv_reader:
            network = ipaddress.ip_network("/".join((row[0], row[1])))
            first_octet = network.network_address.packed[0]
            asns = row[2].split("_")
            first_octet_to_network_asns[first_octet].append((network, asns))

    return first_octet_to_network_asns

def ip_to_asns(ip_addr, first_octet_to_network_asns):
    """
    Uses the dictionary created by parse_pfx2as_file() to perform IP-to-ASN
    resolution.

    Keyword Arguments:
        ip_addr -- An ipaddress.IPv4Address to resolve
        first_octet_to_network_asns -- The dict produced by parse_pfx2as_file()

    Returns:
        A list of ASNs which have originated this prefix, or None if no
        resolution can be performed
    """
    best_network = None
    best_asns = None
    first_octet = ip_addr.packed[0]

    for network, asns in first_octet_to_network_asns[first_octet]:
        if ip_addr in network:
            if (best_network is None or network.prefixlen >
                best_network.prefixlen):
                best_network = network
                best_asns = asns

    return best_asns
