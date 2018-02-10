#!/usr/bin/env python3
"""Uses CAIDA pfx2as files to perform IP-to-ASN lookups.
"""

import pytricia

def prefix_tree_from_pfx2as(pfx2as_file_contents):
    pyt = pytricia.PyTricia()

    for line in pfx2as_file_contents.splitlines():
        fields = line.split("\t")
        prefix_str = fields[0] + "/" + fields[1]
        asns = fields[2]
        pyt[prefix_str] = asns

    return pyt

def prefix_tree_from_pfx2as_file(pfx2as_filename):
    f = open(pfx2as_filename, "r")
    contents = f.read()
    f.close()
    return prefix_tree_from_pfx2as(contents)
