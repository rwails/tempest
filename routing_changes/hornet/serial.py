#!/usr/bin/env python3

import zlib
import ujson

def obj_to_bytes(obj):
    return zlib.compress(ujson.dumps(obj).encode('utf-8'))

def obj_from_bytes(obj_bytes):
    return ujson.loads(zlib.decompress(obj_bytes).decode('utf-8'))
