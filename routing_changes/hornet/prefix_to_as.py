#!/usr/bin/env python3

import pytricia

def prefix_tree_from_pfx2as(pfx2as_file_contents):
    pyt = pytricia.PyTricia()

    for line in pfx2as_file_contents.splitlines():
        fields = line.split("\t")
        prefix_str = fields[0] + "/" + fields[1]
        asns = fields[2]
        pyt[prefix_str] = asns

    return pyt
